"""Is M15 the wrong timeframe, or is gold just efficient?

The project has only ever looked at M15. The M15 study found follow-through at
48-50% and autocorrelation near zero -- i.e. no momentum to trade. Before
concluding that no directional edge exists, the same measurements have to be run
on higher timeframes, where trend persistence is usually stronger.

This uses the in-sample window only on M15/H1 to stay consistent with the rest
of the research; H4 and D1 use their full available history because their sample
counts are otherwise too small to say anything, and that is stated in the output.

    python -m scripts.timeframe_study
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import (
    autocorrelation,
    barrier_baseline,
    build_features,
    excursion_baseline,
    follow_through,
)

OUT = os.path.join("research", "market")


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    args = ap.parse_args()

    bars = load_bars("XAUUSDm", timeframes=("M15", "H1", "H4", "D1"))
    series = {"M15": bars.m15, "H1": bars.__dict__.get("h1"), "D1": bars.d1}

    # BarSet has no h1/h4 fields; load them straight from the cache.
    for tf in ("H1", "H4"):
        p = os.path.join("research", "data", f"XAUUSDm_{tf}.npy")
        if os.path.exists(p):
            series[tf] = np.load(p)

    report = {}
    print(f"{'TF':<5}{'bars':>8}{'window':>26}{'AC(1)':>9}{'AC(4)':>9}"
          f"{'cont@1ATR/4':>13}{'cont@1ATR/16':>14}{'fwd ATR':>10}")
    print("-" * 94)

    for tf in ("M15", "H1", "H4", "D1"):
        arr = series.get(tf)
        if arr is None or len(arr) < 500:
            print(f"{tf:<5} unavailable")
            continue
        # M15/H1 have enough bars to honour the in-sample window; H4/D1 do not.
        if tf in ("M15", "H1"):
            t = arr["time"].astype(np.int64)
            arr = arr[(t >= _ts(args.start)) & (t <= _ts(args.end))]
            win = f"{args.start}..{args.end}"
        else:
            win = "full history"

        f = build_features(arr)
        ac = autocorrelation(f, lags=(1, 2, 4, 8))
        ft4 = follow_through(f, 1.0, 4)
        ft16 = follow_through(f, 1.0, 16)
        report[tf] = {"bars": int(len(arr)), "window": win, "autocorr": ac,
                      "follow_through_4": ft4, "follow_through_16": ft16}
        c4 = ft4["continuation_rate"]
        c16 = ft16["continuation_rate"]
        print(f"{tf:<5}{len(arr):>8}{win:>26}{ac.get('lag_1', float('nan')):>9.4f}"
              f"{ac.get('lag_4', float('nan')):>9.4f}"
              f"{(c4*100 if c4 else float('nan')):>12.1f}%"
              f"{(c16*100 if c16 else float('nan')):>13.1f}%"
              f"{ft16['mean_forward_atr']:>+10.4f}")

    print("\nBarrier hit rates vs a driftless random walk (random long entry):")
    print(f"{'TF':<5}{'TP/SL':<10}{'observed':>10}{'rand walk':>12}{'excess':>10}{'exp R':>10}")
    print("-" * 60)
    for tf in ("M15", "H1", "H4", "D1"):
        arr = series.get(tf)
        if arr is None or len(arr) < 500:
            continue
        if tf in ("M15", "H1"):
            t = arr["time"].astype(np.int64)
            arr = arr[(t >= _ts(args.start)) & (t <= _ts(args.end))]
        f = build_features(arr)
        rows = []
        for tp, sl in ((1.5, 1.5), (3.0, 1.5)):
            b = barrier_baseline(f, tp, sl, max_bars=96, sample=3000)
            if not b:
                continue
            rows.append(b)
            print(f"{tf:<5}{f'{tp}/{sl}':<10}{b['observed_win_rate']:>10.4f}"
                  f"{b['random_walk_win_rate']:>12.4f}{b['excess']:>+10.4f}"
                  f"{(b['expectancy_R'] or 0):>+10.4f}")
        report.setdefault(tf, {})["barriers"] = rows

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "timeframe_study.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"\nwritten to {os.path.join(OUT, 'timeframe_study.json')}")


if __name__ == "__main__":
    main()
