"""Is there ANY configuration where $100 survives this edge?

I.3 measured P(ruin) = 39.4% at the live config, and the Part II sizing ladder
made it 42.4% -- reducing concurrency doesn't help, because ruin is driven by
risk-per-trade relative to bankroll, not by how many positions run at once. On
a Standard account 0.01 lot IS the broker floor, so risk-per-trade cannot be
reduced there at all.

This sweeps risk-scale directly to find the level at which the SAME edge
becomes survivable, and maps each level onto a real, executable route:

  scale 1.00  = Standard account, 0.01 lot (today) -- the floor, cannot go lower
  scale 0.10  = Exness CENT account (XAUUSDc): 0.10 cent-lot is 1/10th the
                notional, i.e. the 10x finer granularity Part II.1 option (B)
                already proposed
  other scales = equivalently, the same 0.01 lot on a proportionally larger
                account (scale 0.5 ~ $200, scale 0.2 ~ $500, scale 0.1 ~ $1000)

    python -m scripts.validation.survivable_size
"""
from __future__ import annotations

import json
import os

import numpy as np

from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars, stats)

SIMS = 10000
RUIN_FRAC = 0.20
SCALES = (1.0, 0.75, 0.5, 0.35, 0.25, 0.2, 0.15, 0.1, 0.05)


def mc(pl: np.ndarray, scale: float, sims: int = SIMS) -> dict:
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(sims, n))] * scale
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((sims, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    return dict(
        scale=scale,
        p_ruin_pct=round(float((eq <= START_BAL * RUIN_FRAC).any(axis=1).mean() * 100), 2),
        p_touch_minus50_pct=round(float((eq <= START_BAL * 0.50).any(axis=1).mean() * 100), 2),
        maxdd_p50=round(float(np.percentile(dd, 50)), 1),
        maxdd_p95=round(float(np.percentile(dd, 95)), 1),
        median_end_balance=round(float(np.median(eq[:, -1])), 2),
        median_net=round(float(np.median(eq[:, -1]) - START_BAL), 2),
    )


def main():
    bars = _bars()
    res = run_window(bars, live_config(), HOLDOUT_START, HOLDOUT_END)
    pl = np.array([t.net_pl for t in res.trades])
    s = stats(res.trades)
    days = 505  # 2025-01-01 -> 2026-05-20
    print(f"Base holdout: n={s['n']} PF={s['profit_factor']} net=${s['net']} "
          f"avg_win=${s['avg_win']} avg_loss=${s['avg_loss']}\n")

    print(f"{'scale':>6} {'route':<34} {'P(ruin)':>8} {'P(-50%)':>8} "
          f"{'medDD':>7} {'p95DD':>7} {'med $/day':>10}")
    print("-" * 88)
    rows = []
    routes = {
        1.0: "Standard 0.01 lot @ $100 (today)",
        0.75: "~$140 account, or 0.0075 equiv",
        0.5: "~$200 account",
        0.35: "~$290 account",
        0.25: "~$400 account",
        0.2: "~$500 account",
        0.15: "~$670 account",
        0.1: "CENT acct 0.10 lot, or ~$1000",
        0.05: "CENT acct 0.05 lot, or ~$2000",
    }
    first_pass = None
    for sc in SCALES:
        r = mc(pl, sc)
        r["route"] = routes.get(sc, "")
        r["median_usd_per_day"] = round(r["median_net"] / days, 2)
        rows.append(r)
        flag = ""
        if r["p_ruin_pct"] < 1.0 and first_pass is None:
            first_pass = sc
            flag = "  <-- first to clear P(ruin) < 1%"
        print(f"{sc:>6.2f} {r['route']:<34} {r['p_ruin_pct']:>7.2f}% "
              f"{r['p_touch_minus50_pct']:>7.2f}% {r['maxdd_p50']:>6.1f}% "
              f"{r['maxdd_p95']:>6.1f}% {r['median_usd_per_day']:>10.2f}{flag}")

    print()
    if first_pass:
        row = next(r for r in rows if r["scale"] == first_pass)
        print(f"SURVIVABLE AT: risk scale {first_pass} -- {row['route']}")
        print(f"  P(ruin) {row['p_ruin_pct']}%, median max drawdown {row['maxdd_p50']}%, "
              f"median ${row['median_usd_per_day']}/day")
        print(f"  Note the tradeoff: $/day falls proportionally with risk. Survivability "
              f"and daily return are the same dial.")
    else:
        print("NO tested scale clears P(ruin) < 1% -- the edge's own volatility is too "
              "high for this bankroll at any executable size.")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/survivable_size.json", "w", encoding="utf-8") as f:
        json.dump(dict(base=s, rows=rows, first_pass_scale=first_pass), f, indent=2)
    print("\n--> research/validation/survivable_size.json")


if __name__ == "__main__":
    main()
