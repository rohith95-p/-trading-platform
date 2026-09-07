"""QQE tested on its own terms, not wrapped in our framework's assumptions.

The previous test (qqe_test.py) gave QQE our session window and our ATR
stops -- neither of which the Pine script defines. This tests the indicator
the way it is actually designed to be traded: a reversal system. Enter long on
the qqeLong label, hold until qqeShort, flip. No stops, no targets, no session
filter -- exactly what the script plots.

Then, separately, the variants that add one assumption at a time, so it is
visible which assumption (if any) is what breaks it.

P&L is computed directly from M15 closes at 0.01 lot (1 oz => $1 per $1 move),
with realistic per-trade cost applied, rather than routed through the engine,
so nothing about our SL/TP machinery colours the result.

    python -m scripts.validation.qqe_native
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features
from scripts.validation.qqe_test import qqe_trend

IST = timezone(timedelta(hours=5, minutes=30))
START_BAL = 105.74
HOLDOUT_START, HOLDOUT_END = "2025-01-01", "2026-05-20"
DAYS = 505

# Cost per round trip at 0.01 lot: ~$2.60 spread (260 points) + ~$0.20 slippage.
# Matches the "realistic" scenario the engine uses.
COST_PER_TRADE = 2.80


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def summarize(pls, label, extra=""):
    arr = np.array(pls, dtype=float)
    if len(arr) < 2:
        print(f"{label:<44} {len(arr):>5}  (too few trades)")
        return dict(n=int(len(arr)))
    w, l = arr[arr > 0], arr[arr < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = START_BAL + np.cumsum(arr)
    peak = np.maximum.accumulate(np.concatenate(([START_BAL], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    out = dict(n=int(len(arr)), win_rate=round(float(len(w) / len(arr) * 100), 1),
               profit_factor=round(pf, 4), net=round(float(arr.sum()), 2),
               min_balance=round(float(bal.min()), 2),
               end_balance=round(float(bal[-1]), 2),
               max_drawdown_pct=round(dd, 2),
               usd_per_day=round(float(arr.sum()) / DAYS, 2))
    print(f"{label:<44} {out['n']:>5} {out['win_rate']:>6.1f} "
          f"{out['profit_factor']:>7} {out['net']:>9} {out['min_balance']:>8} "
          f"{out['max_drawdown_pct']:>6}% {out['usd_per_day']:>7}  {extra}")
    return out


def main():
    bars = load_bars("XAUUSDm", timeframes=("M15",))
    m15 = bars.m15
    lo, hi = _ts(HOLDOUT_START), _ts(HOLDOUT_END)
    m = (m15["time"] >= lo) & (m15["time"] < hi)
    idx = np.nonzero(m)[0]
    if len(idx) < 500:
        print("not enough bars"); return

    # Compute QQE over the full series (needs warmup), then slice.
    close_all = np.asarray(m15["close"], dtype=float)
    qtrend, fired = qqe_trend(close_all)
    f = build_features(m15)
    ist_hour = f["ist_hour"]
    atr = f["atr14"]

    print(f"QQE on its own terms, holdout {HOLDOUT_START} -> {HOLDOUT_END}, "
          f"0.01 lot, cost ${COST_PER_TRADE}/trade\n")
    print(f"{'variant':<44} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>7} {'$/day':>7}")
    print("-" * 104)

    results = {}

    # --- 1. Pure reversal system: long on qqeLong, flip on qqeShort ---------
    for session_label, sess in (("all sessions", None), ("11:30-21:30 IST", (11.5, 21.5))):
        pls = []
        pos_dir, entry_px = 0, 0.0
        for i in idx:
            if sess is not None:
                h = ist_hour[i]
                in_sess = sess[0] <= h < sess[1]
            else:
                in_sess = True
            s = fired[i]
            if s == 0:
                continue
            px = close_all[i]
            if pos_dir != 0:                      # close the open side on a flip
                pls.append(pos_dir * (px - entry_px) - COST_PER_TRADE)
                pos_dir = 0
            if in_sess:                            # open the new side
                pos_dir = 1 if s > 0 else -1
                entry_px = px
        results[f"reversal, {session_label}"] = summarize(
            pls, f"1. reversal (flip on opposite), {session_label}")

    # --- 2. Signal + fixed ATR stops, all sessions -------------------------
    for sl_m, tp_m in ((0.75, 3.0), (1.0, 2.0), (2.0, 4.0)):
        pls = []
        for i in idx:
            s = fired[i]
            if s == 0 or not np.isfinite(atr[i]) or atr[i] <= 0:
                continue
            entry = close_all[i]
            sl_d, tp_d = sl_m * atr[i], tp_m * atr[i]
            # walk forward on M15 highs/lows until one is touched (SL first)
            resolved = None
            for j in range(i + 1, min(i + 1 + 96, len(close_all))):
                hh, ll = float(m15["high"][j]), float(m15["low"][j])
                if s > 0:
                    if ll <= entry - sl_d:
                        resolved = -sl_d; break
                    if hh >= entry + tp_d:
                        resolved = tp_d; break
                else:
                    if hh >= entry + sl_d:
                        resolved = -sl_d; break
                    if ll <= entry - tp_d:
                        resolved = tp_d; break
            if resolved is not None:
                pls.append(resolved - COST_PER_TRADE)
        results[f"atr {sl_m}/{tp_m}"] = summarize(
            pls, f"2. signal + ATR stops {sl_m}x/{tp_m}x, all sessions")

    # --- 3. Trend-following exposure: hold whichever way QQE points --------
    pls = []
    prev = 0
    entry_px = 0.0
    for i in idx:
        t = qtrend[i]
        if t != prev:
            if prev != 0:
                pls.append(prev * (close_all[i] - entry_px) - COST_PER_TRADE)
            prev, entry_px = t, close_all[i]
    results["always-in trend"] = summarize(
        pls, "3. always-in (hold QQE trend direction)")

    print()
    print("Benchmark: FVG_NY alone, same holdout -- "
          "n=990 WR 23.5% PF 1.5004 net $1477 minBal $104.20 maxDD 35.7% $2.93/day")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/qqe_native.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\n--> research/validation/qqe_native.json")


if __name__ == "__main__":
    main()
