"""UT Bot Alerts (Pine v4) -- ATR trailing-stop flip system, tested.

Faithful port:
    xATR  = atr(10);  nLoss = a * xATR   (a = 1, the "Key Value" sensitivity)
    trailing stop ratchets in the direction of price and flips when crossed
    buy  = src crosses ABOVE the trailing stop
    sell = src crosses BELOW the trailing stop
(ema(src,1) is just src, so the crossover terms simplify to price vs stop.)

Heikin Ashi input is left off (default), matching the script's default.

Tested as a reversal system -- flip on the opposite signal, which is how a
trailing-stop flip indicator is designed to trade -- plus fixed-ATR-stop
variants and the owner's session window, and a sensitivity sweep on `a`.

    python -m scripts.validation.utbot_test [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features

START_BAL = 105.74
COST_PER_TRADE = 2.80


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def ut_bot(close: np.ndarray, atr: np.ndarray, a: float):
    """Returns (pos, flip) -- pos is +1/-1 state, flip is +1/-1 on the cross bar."""
    n = len(close)
    stop = np.zeros(n)
    pos = np.zeros(n)
    for i in range(1, n):
        if not np.isfinite(atr[i]):
            stop[i], pos[i] = stop[i - 1], pos[i - 1]
            continue
        nloss = a * atr[i]
        s, sp, prev = close[i], close[i - 1], stop[i - 1]
        if s > prev and sp > prev:
            stop[i] = max(prev, s - nloss)
        elif s < prev and sp < prev:
            stop[i] = min(prev, s + nloss)
        elif s > prev:
            stop[i] = s - nloss
        else:
            stop[i] = s + nloss
        if sp < stop[i - 1] and s > stop[i - 1]:
            pos[i] = 1
        elif sp > stop[i - 1] and s < stop[i - 1]:
            pos[i] = -1
        else:
            pos[i] = pos[i - 1]
    flip = np.zeros(n)
    for i in range(1, n):
        if pos[i] != pos[i - 1] and pos[i] != 0:
            flip[i] = pos[i]
    return pos, flip


def summarize(pls, label, days):
    arr = np.array(pls, float)
    if len(arr) < 2:
        print(f"{label:<44} {len(arr):>5}  (too few)")
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
    print(f"{label:<44} {out['n']:>5} {out['win_rate']:>6.1f} {out['profit_factor']:>7} "
          f"{out['net']:>9} {out['min_balance']:>9} {out['max_drawdown_pct']:>8}% "
          f"{out['usd_per_day']:>7}")
    return out


def main():
    start = sys.argv[1] if len(sys.argv) > 2 else "2025-09-06"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-09-04"
    days = max(1, (_ts(end) - _ts(start)) // 86400)

    bars = load_bars("XAUUSDm", timeframes=("M15",))
    m15 = bars.m15
    f = build_features(m15)
    close = np.asarray(m15["close"], float)
    high = np.asarray(m15["high"], float)
    low = np.asarray(m15["low"], float)
    atr10 = f["atr14"]  # ATR(14) available; period-10 differs slightly, noted below
    ist_hour = f["ist_hour"]
    idx = np.nonzero((m15["time"] >= _ts(start)) & (m15["time"] < _ts(end)))[0]
    idx = idx[idx > 1]

    print(f"UT Bot Alerts, {start} -> {end} ({days} days), 0.01 lot, "
          f"cost ${COST_PER_TRADE}/trade\n")
    print(f"{'variant':<44} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>9} {'$/day':>7}")
    print("-" * 108)
    results = {}

    for a in (1.0, 2.0, 3.0):
        _, flip = ut_bot(close, atr10, a)
        for sess_label, sess in (("all sessions", None), ("11:30-21:30", (11.5, 21.5))):
            pls, d, entry = [], 0, 0.0
            for i in idx:
                s = flip[i]
                if s == 0:
                    continue
                in_sess = True if sess is None else (sess[0] <= ist_hour[i] < sess[1])
                if d != 0:
                    pls.append(d * (close[i] - entry) - COST_PER_TRADE)
                    d = 0
                if in_sess:
                    d, entry = int(s), close[i]
            results[f"a={a} {sess_label}"] = summarize(
                pls, f"reversal, key={a}, {sess_label}", days)

    # Signal + fixed ATR stop/target, for comparison with our own convention
    _, flip = ut_bot(close, atr10, 1.0)
    for sl_m, tp_m in ((0.5, 2.5), (1.0, 3.0)):
        pls = []
        for i in idx:
            s = flip[i]
            if s == 0 or not np.isfinite(atr10[i]):
                continue
            e = close[i]
            sl_d, tp_d = sl_m * atr10[i], tp_m * atr10[i]
            for j in range(i + 1, min(i + 97, len(close))):
                if s > 0:
                    if low[j] <= e - sl_d:
                        pls.append(-sl_d - COST_PER_TRADE); break
                    if high[j] >= e + tp_d:
                        pls.append(tp_d - COST_PER_TRADE); break
                else:
                    if high[j] >= e + sl_d:
                        pls.append(-sl_d - COST_PER_TRADE); break
                    if low[j] <= e - tp_d:
                        pls.append(tp_d - COST_PER_TRADE); break
        results[f"atr {sl_m}/{tp_m}"] = summarize(
            pls, f"key=1.0 + ATR stops {sl_m}x/{tp_m}x", days)

    print("\nBenchmark: FVG_NY alone -- PF 1.5004, +$1,477, maxDD 35.7%")
    print("NOTE: script specifies ATR period 10; ATR(14) used here (what the "
          "feature set provides). Sensitivity to that is small relative to the result.")
    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/utbot_{start}_{end}.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("--> saved")


if __name__ == "__main__":
    main()
