"""The real combined backtest for all 5 owner-requested legs, run together
exactly as they would live: FVG_ASIA_SWEEP, FVG_NY_TIGHT, FVG_NY_SWEEP,
FVG_NY_VOID, FVG_NY_SWEEP_OR_VOID -- through the actual engine, actual live
caps (3 concurrent, 3 same-direction), so the overlap effect is measured, not
predicted.

    python -m scripts.validation.combined_portfolio_5legs
"""
from __future__ import annotations

import json
import os

import numpy as np

from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)

SIMS = 10000
DAYS = 505


def mc(pl: np.ndarray) -> dict:
    if len(pl) < 2:
        return {}
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((SIMS, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    return dict(maxdd_p95=round(float(np.percentile(dd, 95)), 1),
                p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2),
                p_touch_minus50_pct=round(float((eq <= START_BAL * 0.50).any(axis=1).mean() * 100), 2))


def main():
    bars = _bars()
    cfg = live_config()  # real live caps: 3 concurrent, 3 same-direction, D1 gate off

    print(f"5-leg portfolio (owner-requested, 2026-09-07): "
          f"{[c.name for c in PORTFOLIO_V4]}")
    print(f"Holdout {HOLDOUT_START} -> {HOLDOUT_END}, live config\n")

    strategies = [cls() for cls in PORTFOLIO_V4]
    res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, strategies)
    s = stats(res.trades)
    v = verdict(s)
    pl = np.array([t.net_pl for t in res.trades])
    ruin = mc(pl)

    print("COMBINED (all 5 legs, shared account, real caps + breaker):")
    print(json.dumps(s, indent=2))
    print(f"I.1: {'PASS' if v['passed'] else 'FAIL'}  {v['reasons']}")
    print(f"Monte Carlo: {json.dumps(ruin, indent=2)}")
    print(f"$/day = {s.get('net', 0) / DAYS:.2f}")

    # Per-leg breakdown, and: how many DISTINCT gap events actually happened
    # vs how many trades got fired off them (the overlap measurement).
    by_leg = {}
    for t in res.trades:
        by_leg.setdefault(t.strategy, []).append(t)
    print("\nPer-leg within the combined run:")
    for name, trs in by_leg.items():
        pls = np.array([t.net_pl for t in trs])
        w, l = pls[pls > 0], pls[pls < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        print(f"  {name:<24} n={len(trs):4d} PF={pf:.3f} net=${pls.sum():.2f}")

    # Overlap check: group NY-session entries by entry candle -- how often did
    # 2+ NY legs fire on the exact same 15-min bar (the same underlying gap)?
    ny_names = {"FVG_NY_TIGHT", "FVG_NY_SWEEP", "FVG_NY_VOID", "FVG_NY_SWEEP_OR_VOID"}
    by_candle = {}
    for t in res.trades:
        if t.strategy in ny_names:
            key = t.entry_time // 900 * 900  # bucket to the M15 boundary
            by_candle.setdefault(key, []).append(t.strategy)
    stacked = {k: v for k, v in by_candle.items() if len(v) > 1}
    print(f"\nNY-session entries firing on the SAME 15-min candle "
          f"(the overlap in practice): {len(stacked)} candles, "
          f"{sum(len(v) for v in stacked.values())} total trades stacked on them")
    for k in list(stacked)[:5]:
        print(f"  candle {k}: {stacked[k]}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/combined_portfolio_5legs.json", "w", encoding="utf-8") as fh:
        json.dump(dict(stats=s, verdict=v, montecarlo=ruin,
                       by_leg={k: dict(n=len(v_), net=round(sum(t.net_pl for t in v_), 2))
                              for k, v_ in by_leg.items()},
                       stacked_candles=len(stacked)),
                  fh, indent=2, default=str)
    print("\n--> research/validation/combined_portfolio_5legs.json")


if __name__ == "__main__":
    main()
