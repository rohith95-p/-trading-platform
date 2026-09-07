"""Owner decision 2026-09-06: trade 11:30-21:30 IST only, no night trades.

That window removes SQUEEZE_ASIA entirely (its session is 02:30-11:30). The
holdout regime breakdown says that leg contributed +$1,412 of the portfolio's
+$3,030, so this is not a cosmetic change -- it roughly halves the trade
population. It may still be the right call on risk, which is what this
measures.

Also tested: dropping RANGEREJECTION_NY_TIGHT, which the same breakdown shows
is a net loser over the holdout (n=300, PF 0.982, -$23) -- if it's dead weight
inside the new window, better to know now than to carry it into a paper test.

    python -m scripts.validation.session_1130_2130
"""
from __future__ import annotations

import json
import os

import numpy as np

from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)
from src.strategies.portfolio_v4 import (
    SqueezeBreakAsia, EMAStackLondonTight, FVGNYTight, RangeRejectionNYTight)

SIMS = 10000


def mc_ruin(pl: np.ndarray) -> dict:
    if not len(pl):
        return {}
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((SIMS, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    return dict(p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2),
                maxdd_p50=round(float(np.percentile(dd, 50)), 1),
                maxdd_p95=round(float(np.percentile(dd, 95)), 1))


VARIANTS = {
    "A_all4_current": [SqueezeBreakAsia, EMAStackLondonTight, FVGNYTight, RangeRejectionNYTight],
    "B_1130_2130_no_asia": [EMAStackLondonTight, FVGNYTight, RangeRejectionNYTight],
    "C_1130_2130_no_asia_no_rangerej": [EMAStackLondonTight, FVGNYTight],
    "D_fvg_only": [FVGNYTight],
}


def main():
    bars = _bars()
    days = 505  # 2025-01-01 -> 2026-05-20
    out = {}
    print(f"Holdout {HOLDOUT_START} -> {HOLDOUT_END}, live config, $ {START_BAL} start\n")
    print(f"{'variant':<34} {'n':>5} {'PF':>7} {'net$':>9} {'minBal':>8} "
          f"{'maxDD':>7} {'$/day':>7} {'P(ruin)':>8} {'I.1':>5}")
    print("-" * 100)
    for name, legs in VARIANTS.items():
        res = run_window(bars, live_config(), HOLDOUT_START, HOLDOUT_END,
                         [c() for c in legs])
        s = stats(res.trades)
        v = verdict(s)
        pl = np.array([t.net_pl for t in res.trades])
        m = mc_ruin(pl)
        s["usd_per_day"] = round(s.get("net", 0) / days, 2)
        out[name] = dict(legs=[c.name for c in legs], stats=s, verdict=v, montecarlo=m)
        print(f"{name:<34} {s.get('n',0):>5} {s.get('profit_factor','-'):>7} "
              f"{s.get('net','-'):>9} {s.get('min_balance','-'):>8} "
              f"{s.get('max_drawdown_pct','-'):>6}% {s['usd_per_day']:>7} "
              f"{m.get('p_ruin_pct','-'):>7}% {'PASS' if v['passed'] else 'FAIL':>5}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/session_1130_2130.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("\n--> research/validation/session_1130_2130.json")


if __name__ == "__main__":
    main()
