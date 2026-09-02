"""Tier-1 screen of the full candidate library.

    python -m scripts.screen_candidates

Reports EVERY candidate, not just survivors (Part 24). The multiple-testing
arithmetic is printed alongside the results, because with ~100 candidates a
handful will clear any threshold by chance and that has to be priced in.

In-sample window only. The locked holdout is never read here.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.candidates import build_library
from src.research.market_study import build_features
from src.research.screener import screen

OUT = os.path.join("research", "screen")


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--no-control", action="store_true")
    args = ap.parse_args()

    bars = load_bars("XAUUSDm", timeframes=("M15", "D1"))
    t = bars.m15["time"].astype(np.int64)
    rates = bars.m15[(t >= _ts(args.start)) & (t <= _ts(args.end))]
    f = build_features(rates)

    lib = build_library()
    print(f"XAUUSDm M15  {len(rates):,} bars  {args.start} -> {args.end}  "
          f"data {bars.hash_key()}")
    print(f"{len(lib)} candidates across "
          f"{len(set(c.family for c in lib))} families\n")

    hdr = (f"{'id':<9}{'family':<16}{'n':>5}{'WR%':>7}{'expR':>9}{'totR':>9}"
           f"{'PF':>7}{'ddR':>8}{'ctrlR':>9}{'edgeR':>9}{'z':>7}")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for c in lib:
        r = screen(f, c, with_control=not args.no_control)
        rows.append(r)
        pf = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.3f}"
        print(f"{r.candidate_id:<9}{r.family:<16}{r.trades:>5}{r.win_rate:>7.1f}"
              f"{r.expectancy_r:>+9.4f}{r.total_r:>+9.1f}{pf:>7}{r.max_dd_r:>8.1f}"
              f"{r.control_expectancy_r:>+9.4f}{r.edge_r:>+9.4f}{r.edge_z:>+7.2f}",
              flush=True)

    # ---- summary -------------------------------------------------------
    valid = [r for r in rows if r.trades >= args.min_trades]
    print("\n" + "=" * 78)
    print("  SUMMARY (Part 24 -- every candidate reported, winners not cherry-picked)")
    print("=" * 78)
    print(f"  candidates tested         : {len(rows)}")
    print(f"  with >= {args.min_trades} trades         : {len(valid)}")
    if not valid:
        print("  nothing to evaluate")
        return

    pos_r = [r for r in valid if r.expectancy_r > 0]
    print(f"  positive expectancy (raw) : {len(pos_r)}  "
          f"({len(pos_r)/len(valid)*100:.0f}%)")
    beat = [r for r in valid if r.edge_z > 0]
    print(f"  beating matched control   : {len(beat)}  "
          f"({len(beat)/len(valid)*100:.0f}%)  <- the number that matters")
    for z in (1.0, 1.5, 2.0):
        k = [r for r in valid if r.edge_z >= z]
        exp_chance = len(valid) * (1 - _norm_cdf(z))
        print(f"  edge_z >= {z}              : {len(k):>3}   "
              f"expected by chance: {exp_chance:.1f}")

    print("\n  Top 12 by edge over control (edge_z):")
    print(f"    {'id':<9}{'name':<44}{'n':>5}{'expR':>9}{'edgeR':>9}{'z':>7}")
    for r in sorted(valid, key=lambda x: -x.edge_z)[:12]:
        print(f"    {r.candidate_id:<9}{r.name[:43]:<44}{r.trades:>5}"
              f"{r.expectancy_r:>+9.4f}{r.edge_r:>+9.4f}{r.edge_z:>+7.2f}")

    print("\n  By family (median edge_z, share beating control):")
    fams = sorted(set(r.family for r in valid))
    print(f"    {'family':<18}{'n cand':>8}{'med z':>9}{'beat ctrl':>12}")
    fam_rows = {}
    for fam in fams:
        g = [r for r in valid if r.family == fam]
        med = float(np.median([r.edge_z for r in g]))
        share = sum(1 for r in g if r.edge_z > 0) / len(g)
        fam_rows[fam] = {"candidates": len(g), "median_edge_z": round(med, 3),
                         "share_beating_control": round(share, 3)}
        print(f"    {fam:<18}{len(g):>8}{med:>+9.2f}{share*100:>11.0f}%")

    os.makedirs(OUT, exist_ok=True)
    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_screen"
    path = os.path.join(OUT, f"{run_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "window": {"start": args.start, "end": args.end},
            "data_hash": bars.hash_key(),
            "bars": int(len(rates)),
            "n_candidates": len(rows),
            "min_trades": args.min_trades,
            "by_family": fam_rows,
            "results": [r.to_dict() for r in rows],
        }, fh, indent=2, default=str)
    print(f"\n  written to {path}")


def _norm_cdf(z: float) -> float:
    import math
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


if __name__ == "__main__":
    main()
