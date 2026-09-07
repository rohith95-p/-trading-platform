"""Backtest on the current legs, through the engine as it stands now
(Highlander one-FVG-per-candle rule, Friday flatten, 06:00-21:30 trading
window, live caps + 6% breaker).

Runs two configs so the "5 legs" question is answered directly:
  * PORTFOLIO_V4 as imported (the live set)
  * PORTFOLIO_V4 + FVGAsiaSweep (the full 5-leg owner-requested set)

    python -m scripts.validation.aug_5legs [START] [END]   # default: August 2026
"""
from __future__ import annotations

import json
import sys

import numpy as np

from src.strategies.portfolio_v4 import PORTFOLIO_V4, FVGAsiaSweep
from scripts.validation.part1_suite import (
    live_config, run_window, _bars, stats, verdict)

START = sys.argv[1] if len(sys.argv) > 1 else "2026-08-01"
END = sys.argv[2] if len(sys.argv) > 2 else "2026-09-01"


def show(title, bars, cfg, classes):
    print(f"\n{'='*70}\n{title}: {[c.name for c in classes]}\n{'='*70}")
    res = run_window(bars, cfg, START, END, [c() for c in classes])
    if not res.trades:
        print("No trades.")
        return
    s = stats(res.trades)
    v = verdict(s)
    print(json.dumps(s, indent=2))
    print(f"I.1 gate: {'PASS' if v['passed'] else 'FAIL'}  {v['reasons']}")

    by_leg = {}
    for t in res.trades:
        by_leg.setdefault(t.strategy, []).append(t)
    print("\nper-leg:")
    for name, trs in sorted(by_leg.items()):
        pls = np.array([t.net_pl for t in trs])
        w, l = pls[pls > 0], pls[pls < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        print(f"  {name:<24} n={len(trs):3d}  PF={pf:6.3f}  net=${pls.sum():8.2f}  "
              f"WR={len(w)/len(pls)*100:4.0f}%")

    print("\ntrades:")
    for t in sorted(res.trades, key=lambda x: x.entry_time):
        dt = np.datetime64(int(t.entry_time), 's').astype(str)
        print(f"  [{dt}] {t.strategy:<22} {'BUY ' if t.is_buy else 'SELL'} "
              f"entry {t.entry_price:8.2f}  exit {t.exit_price:8.2f}  "
              f"net {t.net_pl:7.2f}  {t.exit_reason}")


def main():
    bars = _bars()
    cfg = live_config()
    print(f"Backtest  ({START} -> {END})  live config, realistic costs")
    show("LIVE SET (PORTFOLIO_V4)", bars, cfg, list(PORTFOLIO_V4))
    show("5-LEG SET (+ FVG_ASIA_SWEEP)", bars, cfg, list(PORTFOLIO_V4) + [FVGAsiaSweep])


if __name__ == "__main__":
    main()
