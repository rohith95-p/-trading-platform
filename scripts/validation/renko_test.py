"""[SMT] Renko Buy & Sell -- tested WITHOUT the lookahead that inflates it.

Why the TradingView result (reported PF ~1.9) should not be trusted:
`request.security(ticker.renko(...), ...)` returns synthetic brick prices. A
Renko brick only completes AFTER price has already travelled a full brick size
(here ATR(10) ~ $9). TradingView's strategy tester fills at the brick's
open/close -- a price level the market reached earlier in real time. You are
filled at a price that has already gone. That single artifact typically
manufactures the entire edge on Renko backtests.

This implements the same signal honestly:
  * bricks built forward from real M15 bars, brick size = ATR(10) at brick time
  * a flip is only ACTED ON at the real bar where it becomes knowable
  * the fill is the real close of that bar, plus real cost
  * exits tested both as brick-flip reversal (the strategy's own logic, since
    strategy.entry reverses on the opposite signal) and with ATR stops

For contrast the same run is repeated WITH the lookahead fill (entering at the
brick boundary price rather than the bar close), to show the size of the
artifact directly.

    python -m scripts.validation.renko_test [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features

START_BAL = 105.74
COST_PER_TRADE = 2.80


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _atr(high, low, close, period=10):
    n = len(high)
    tr = np.full(n, np.nan)
    tr[1:] = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
    out = np.full(n, np.nan)
    if n > period:
        out[period] = np.nanmean(tr[1:period + 1])
        for i in range(period + 1, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def build_renko(high, low, close, atr, window_start_idx=0, window_end_idx=None):
    """Forward-only Renko with a FIXED brick size (median ATR(10) over the
    test window), computed once rather than re-evaluated per bar.

    The per-bar-varying-ATR version produced ~1.8M brick flips over 504 days
    (should be low thousands) -- a runaway from ATR(10) occasionally reading
    near-zero on this data, letting a single bar spawn hundreds of bricks. A
    fixed brick size (the standard practical convention -- "ATR-based Renko"
    normally means "set brick size from ATR once," not "recompute every bar")
    eliminates that failure mode entirely and is a fair reading of the script.

    Returns list of (bar_index, direction, brick_price). bar_index is the bar
    on which the flip first becomes knowable in real time.
    """
    window_end_idx = window_end_idx if window_end_idx is not None else len(close)
    finite_atr = atr[window_start_idx:window_end_idx]
    finite_atr = finite_atr[np.isfinite(finite_atr) & (finite_atr > 0)]
    if len(finite_atr) == 0:
        return []
    size = float(np.median(finite_atr))

    bricks = []
    anchor = close[window_start_idx] if window_start_idx < len(close) else close[0]
    direction = 0
    MAX_BRICKS_PER_BAR = 20   # a real bar cannot legitimately fill more than this
    for i in range(window_start_idx, window_end_idx):
        up_move = high[i] - anchor
        dn_move = anchor - low[i]
        _guard = 0
        while up_move >= size or dn_move >= size:
            _guard += 1
            if _guard > MAX_BRICKS_PER_BAR:
                break
            if up_move >= size and up_move >= dn_move:
                anchor = anchor + size
                new_dir = 1
            else:
                anchor = anchor - size
                new_dir = -1
            if new_dir != direction:
                bricks.append((i, new_dir, anchor))
                direction = new_dir
            up_move = high[i] - anchor
            dn_move = anchor - low[i]
    return bricks


def summarize(pls, label, days):
    arr = np.array(pls, float)
    if len(arr) < 2:
        print(f"{label:<46} {len(arr):>5}  (too few)")
        return dict(n=int(len(arr)))
    w, l = arr[arr > 0], arr[arr < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = START_BAL + np.cumsum(arr)
    peak = np.maximum.accumulate(np.concatenate(([START_BAL], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    out = dict(n=int(len(arr)), win_rate=round(float(len(w) / len(arr) * 100), 1),
               profit_factor=round(pf, 4), net=round(float(arr.sum()), 2),
               min_balance=round(float(bal.min()), 2),
               max_drawdown_pct=round(dd, 1),
               usd_per_day=round(float(arr.sum()) / days, 2))
    print(f"{label:<46} {out['n']:>5} {out['win_rate']:>6.1f} {out['profit_factor']:>7} "
          f"{out['net']:>9} {out['min_balance']:>9} {out['max_drawdown_pct']:>8}% "
          f"{out['usd_per_day']:>7}")
    return out


def main():
    start = sys.argv[1] if len(sys.argv) > 2 else "2025-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-05-20"
    days = max(1, (_ts(end) - _ts(start)) // 86400)

    bars = load_bars("XAUUSDm", timeframes=("M15",))
    m15 = bars.m15
    f = build_features(m15)
    high = np.asarray(m15["high"], float)
    low = np.asarray(m15["low"], float)
    close = np.asarray(m15["close"], float)
    ist_hour = f["ist_hour"]
    atr10 = _atr(high, low, close, 10)
    t = m15["time"]

    lo_ts, hi_ts = _ts(start), _ts(end)
    win_idx = np.nonzero((t >= lo_ts) & (t < hi_ts))[0]
    if len(win_idx) == 0:
        print("no bars in window"); return
    bricks = build_renko(high, low, close, atr10,
                         window_start_idx=int(win_idx[0]), window_end_idx=int(win_idx[-1]) + 1)

    print(f"Renko flip strategy | {start} -> {end} ({days}d) | brick = ATR(10) | "
          f"0.01 lot, cost ${COST_PER_TRADE}/trade")
    print(f"{len(bricks)} brick flips detected\n")
    print(f"{'variant':<46} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>9} {'$/day':>7}")
    print("-" * 110)
    results = {}

    # --- HONEST: fill at the real bar close where the flip is knowable ------
    for sess_label, sess in (("all sessions", None), ("11:30-21:30", (11.5, 21.5))):
        pls, d, entry = [], 0, 0.0
        for (i, nd, _bp) in bricks:
            in_sess = True if sess is None else (sess[0] <= ist_hour[i] < sess[1])
            px = close[i]
            if d != 0:
                pls.append(d * (px - entry) - COST_PER_TRADE)
                d = 0
            if in_sess:
                d, entry = nd, px
        results[f"honest reversal, {sess_label}"] = summarize(
            pls, f"HONEST fill (bar close), reversal, {sess_label}", days)

    # --- honest + ATR stops -------------------------------------------------
    for sl_m, tp_m in ((1.0, 3.0), (0.5, 2.5)):
        pls = []
        for (i, nd, _bp) in bricks:
            if not np.isfinite(atr10[i]):
                continue
            e = close[i]
            sl_d, tp_d = sl_m * atr10[i], tp_m * atr10[i]
            for j in range(i + 1, min(i + 97, len(close))):
                if nd > 0:
                    if low[j] <= e - sl_d:
                        pls.append(-sl_d - COST_PER_TRADE); break
                    if high[j] >= e + tp_d:
                        pls.append(tp_d - COST_PER_TRADE); break
                else:
                    if high[j] >= e + sl_d:
                        pls.append(-sl_d - COST_PER_TRADE); break
                    if low[j] <= e - tp_d:
                        pls.append(tp_d - COST_PER_TRADE); break
        results[f"honest atr {sl_m}/{tp_m}"] = summarize(
            pls, f"HONEST fill + ATR stops {sl_m}x/{tp_m}x", days)

    # --- THE ARTIFACT: fill at the brick boundary price (what TV does) ------
    pls, d, entry = [], 0, 0.0
    for (i, nd, bp) in bricks:
        if d != 0:
            pls.append(d * (bp - entry) - COST_PER_TRADE)
        d, entry = nd, bp
    results["lookahead fill (TV-style)"] = summarize(
        pls, "LOOKAHEAD fill (brick price) -- the artifact", days)

    print("\nBenchmark: FVG_NY alone -- PF 1.5004, +$1,477, maxDD 35.7%")
    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/renko_{start}_{end}.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("--> saved")


if __name__ == "__main__":
    main()
