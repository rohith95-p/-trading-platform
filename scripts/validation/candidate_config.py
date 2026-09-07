"""The best configuration the evidence actually points to, tested end to end.

Assembled from what was measured 2026-09-06, not from preference:
  * FVG_NY_TIGHT alone -- HYP-054: best PF (1.432) and lowest ruin (11.6%) of
    every leg combination tested, and its 17:30-21:30 session sits entirely
    inside the owner's 11:30-21:30 no-night-trades rule.
  * Cent-account sizing -- HYP-051: risk-per-trade is what drives ruin, and on
    a Standard account 0.01 lot is the floor. An Exness Cent account
    (XAUUSDc, 0.10 cent-lot = 1/10th notional) is the only way to go below it
    at $100. This was Part II.1 option (B) and was never acted on.

Tests the combination at several risk scales against I.1's and I.3's actual
pass bars, so the recommendation is a measurement rather than an opinion.

    python -m scripts.validation.candidate_config
"""
from __future__ import annotations

import json
import os

import numpy as np

from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict, PASS_PF, PASS_MAXDD)
from src.strategies.portfolio_v4 import FVGNYTight

SIMS = 10000
DAYS = 505


def mc(pl: np.ndarray, scale: float) -> dict:
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))] * scale
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((SIMS, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    wins = paths > 0
    gw = np.where(wins, paths, 0).sum(axis=1)
    gl = -np.where(~wins, paths, 0).sum(axis=1)
    pf = np.divide(gw, gl, out=np.full(SIMS, np.inf), where=gl > 0)
    return dict(
        scale=scale,
        pf_p5=round(float(np.percentile(pf, 5)), 3),
        pf_p50=round(float(np.percentile(pf, 50)), 3),
        maxdd_p50=round(float(np.percentile(dd, 50)), 1),
        maxdd_p95=round(float(np.percentile(dd, 95)), 1),
        p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 3),
        p_touch_minus50_pct=round(float((eq <= START_BAL * 0.50).any(axis=1).mean() * 100), 2),
        median_end=round(float(np.median(eq[:, -1])), 2),
        median_usd_per_day=round(float((np.median(eq[:, -1]) - START_BAL) / DAYS), 3),
        i3_passed=bool(np.percentile(dd, 95) < 40.0
                       and (eq <= START_BAL * 0.20).any(axis=1).mean() * 100 < 1.0),
    )


def main():
    bars = _bars()
    # FVG_NY alone. max_concurrent 1 -- one leg, one position at a time; this
    # also satisfies the Part II ladder's rule for a sub-$200 balance.
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, [FVGNYTight()])
    s = stats(res.trades)
    v = verdict(s)
    pl = np.array([t.net_pl for t in res.trades])

    print(f"CANDIDATE: FVG_NY_TIGHT alone, 1 position, holdout "
          f"{HOLDOUT_START} -> {HOLDOUT_END}\n")
    print(json.dumps(s, indent=2))
    print(f"\nI.1 at full (Standard 0.01 lot) risk: "
          f"{'PASS' if v['passed'] else 'FAIL'}  {v['reasons']}")

    print(f"\n{'scale':>6} {'route':<32} {'PF p50':>7} {'p95 DD':>7} "
          f"{'P(ruin)':>9} {'$/day':>7} {'I.3':>5}")
    print("-" * 78)
    routes = {1.0: "Standard 0.01 lot @ $100",
              0.5: "Cent 0.50 lot (or ~$200 std)",
              0.25: "Cent 0.25 lot (or ~$400 std)",
              0.1: "Cent 0.10 lot @ $100",
              0.05: "Cent 0.05 lot @ $100"}
    rows = []
    for sc in (1.0, 0.5, 0.25, 0.1, 0.05):
        m = mc(pl, sc)
        m["route"] = routes[sc]
        rows.append(m)
        print(f"{sc:>6.2f} {routes[sc]:<32} {m['pf_p50']:>7} {m['maxdd_p95']:>6.1f}% "
              f"{m['p_ruin_pct']:>8.3f}% {m['median_usd_per_day']:>7.3f} "
              f"{'PASS' if m['i3_passed'] else 'FAIL':>5}")

    best = next((r for r in rows if r["i3_passed"]), None)
    print()
    if best:
        print(f"RECOMMENDED: {best['route']}")
        print(f"  P(ruin) {best['p_ruin_pct']}%, 95th-pct drawdown {best['maxdd_p95']}%, "
              f"median ${best['median_usd_per_day']}/day on $100")
        print(f"  Clears I.3 (95th-pct DD < {PASS_MAXDD - 5}%, P(ruin) < 1%). "
              f"Honest tradeoff: this is cents per day, not dollars.")
    else:
        print("No tested scale clears I.3 even on the best single leg.")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/candidate_config.json", "w", encoding="utf-8") as f:
        json.dump(dict(holdout=s, verdict=v, scales=rows), f, indent=2)
    print("\n--> research/validation/candidate_config.json")


if __name__ == "__main__":
    main()
