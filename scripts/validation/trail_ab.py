"""Trailing-stop A/B on the current 2-leg PORTFOLIO_V4, current engine.

Trailing (engine default): activates at 0.7xATR profit, follows 0.3xATR behind.
Everything else = live config.

    python -m scripts.validation.trail_ab [START] [END]
"""
from __future__ import annotations

import json
import sys

import numpy as np

from scripts.validation.part1_suite import live_config, run_window, _bars, stats

WINDOWS = [
    ("Aug 2026", "2026-08-01", "2026-09-01"),
    ("3 months", "2026-06-04", "2026-09-04"),
    ("1 year",   "2025-09-04", "2026-09-04"),
]
if len(sys.argv) > 2:
    WINDOWS = [("custom", sys.argv[1], sys.argv[2])]


def row(bars, start, end, trailing):
    cfg = live_config(enable_trailing=trailing)
    res = run_window(bars, cfg, start, end)
    s = stats(res.trades)
    return s, res.trades


def main():
    bars = _bars()
    for label, start, end in WINDOWS:
        print(f"\n=== {label}  ({start} -> {end}) ===")
        print(f"{'':10} {'n':>4} {'WR%':>5} {'PF':>7} {'net$':>9} {'maxDD%':>7} {'minBal':>8} {'endBal':>8}")
        for name, tr in (("trail OFF", False), ("trail ON", True)):
            s, _ = row(bars, start, end, tr)
            print(f"{name:10} {s.get('n',0):>4} {s.get('win_rate',0):>5.1f} "
                  f"{s.get('profit_factor','-'):>7} {s.get('net','-'):>9} "
                  f"{s.get('max_drawdown_pct','-'):>7} {s.get('min_balance','-'):>8} "
                  f"{s.get('end_balance','-'):>8}")


if __name__ == "__main__":
    main()
