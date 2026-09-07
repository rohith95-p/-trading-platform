"""The real combined backtest for the new 2-leg portfolio (FVG_ASIA_SWEEP +
FVG_NY_SWEEP_OR_VOID), through the actual engine with the actual live config
-- not the isolated single-leg numbers each was picked on.

Asia and NY don't overlap in time, but they share the same account: the 6%
daily-loss breaker and the exposure caps. HYP-047 already found this kind of
interaction can matter (one leg's losses can burn the shared daily budget and
block the other leg's later good trades). This is the honest number.

    python -m scripts.validation.combined_portfolio_v5
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
    return dict(pf_p50=round(float(np.percentile((np.where(paths > 0, paths, 0).sum(axis=1) /
                    np.maximum(-np.where(paths < 0, paths, 0).sum(axis=1), 1e-9)), 50)), 3),
                maxdd_p95=round(float(np.percentile(dd, 95)), 1),
                p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2))


def main():
    bars = _bars()
    cfg = live_config()  # exact live caps: 3 concurrent, 3 same-direction, D1 gate off

    print(f"Combined portfolio v5: {[c.name for c in PORTFOLIO_V4]}")
    print(f"Holdout {HOLDOUT_START} -> {HOLDOUT_END}, live config\n")

    # Run each leg isolated too, for the "isolated vs combined" comparison.
    print(f"{'leg (isolated)':<26} {'n':>5} {'PF':>7} {'net$':>9} {'minBal':>8} {'maxDD':>7}")
    for cls in PORTFOLIO_V4:
        iso_cfg = live_config(max_concurrent=1, max_same_direction=1)
        res = run_window(bars, iso_cfg, HOLDOUT_START, HOLDOUT_END, [cls()])
        s = stats(res.trades)
        print(f"{cls.name:<26} {s.get('n',0):>5} {s.get('profit_factor','-'):>7} "
              f"{s.get('net','-'):>9} {s.get('min_balance','-'):>8} {s.get('max_drawdown_pct','-'):>6}%")

    strategies = [cls() for cls in PORTFOLIO_V4]
    res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, strategies)
    s = stats(res.trades)
    v = verdict(s)
    pl = np.array([t.net_pl for t in res.trades])
    ruin = mc(pl)

    print(f"\n{'COMBINED (shared account, real caps + breaker)':<48}")
    print(json.dumps(s, indent=2))
    print(f"I.1: {'PASS' if v['passed'] else 'FAIL'}  {v['reasons']}")
    print(f"Monte Carlo: {json.dumps(ruin, indent=2)}")
    print(f"$/day = {s.get('net',0)/DAYS:.2f}")

    # per-leg breakdown within the combined run
    by_leg = {}
    for t in res.trades:
        by_leg.setdefault(t.strategy, []).append(t.net_pl)
    print("\nPer-leg within the combined run:")
    for name, pls in by_leg.items():
        arr = np.array(pls)
        w, l = arr[arr > 0], arr[arr < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        print(f"  {name:<26} n={len(arr):4d} PF={pf:.3f} net=${arr.sum():.2f}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/combined_portfolio_v5.json", "w", encoding="utf-8") as fh:
        json.dump(dict(stats=s, verdict=v, montecarlo=ruin,
                       by_leg={k: dict(n=len(v_), net=round(sum(v_), 2)) for k, v_ in by_leg.items()}),
                  fh, indent=2, default=str)
    print("\n--> research/validation/combined_portfolio_v5.json")


if __name__ == "__main__":
    main()
