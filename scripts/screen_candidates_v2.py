"""Tier-1 screen of the Phase 5 candidate library (candidates_v2.py, 179
candidates), following the exact same discipline as screen_candidates.py:
every candidate reported (no cherry-picking), matched random-entry control,
multiple-testing arithmetic printed alongside.

Phase 2 already showed 4/5 naive session anomalies died under adversarial
testing on this same data -- so nothing here is trusted past this screen
without Phase 8's luck correction and, for anything that clears both, a
tier-2 M1-fidelity re-run.

    python -m scripts.screen_candidates_v2
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.candidates_v2 import build_library_v2
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
    args = ap.parse_args()

    bars = load_bars("XAUUSDm", timeframes=("M15", "D1"))
    t = bars.m15["time"].astype(np.int64)
    rates = bars.m15[(t >= _ts(args.start)) & (t <= _ts(args.end))]
    f = build_features(rates)

    lib = build_library_v2()
    print(f"XAUUSDm M15  {len(rates):,} bars  {args.start} -> {args.end}  "
          f"data {bars.hash_key()}")
    print(f"{len(lib)} candidates (v2) across "
          f"{len(set(c.family for c in lib))} families\n")

    hdr = (f"{'id':<10}{'family':<18}{'sess':<10}{'n':>5}{'WR%':>7}{'expR':>9}"
           f"{'PF':>7}{'ddR':>8}{'edgeR':>9}{'z':>7}")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for c in lib:
        try:
            r = screen(f, c, with_control=True)
        except Exception as e:
            print(f"{c.id:<10} ERROR: {e}")
            continue
        rows.append(r)
        pf = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.3f}"
        sess = f"{c.session[0]:.1f}-{c.session[1]:.1f}"
        print(f"{r.candidate_id:<10}{r.family:<18}{sess:<10}{r.trades:>5}{r.win_rate:>7.1f}"
              f"{r.expectancy_r:>+9.4f}{pf:>7}{r.max_dd_r:>8.1f}"
              f"{r.edge_r:>+9.4f}{r.edge_z:>+7.2f}", flush=True)

    valid = [r for r in rows if r.trades >= args.min_trades]
    print("\n" + "=" * 78)
    print("  SUMMARY (v2 library -- every candidate reported)")
    print("=" * 78)
    print(f"  candidates tested         : {len(rows)}")
    print(f"  with >= {args.min_trades} trades         : {len(valid)}")
    if valid:
        pos = [r for r in valid if r.expectancy_r > 0]
        beat = [r for r in valid if r.edge_r > 0]
        print(f"  positive expectancy (raw) : {len(pos)}  ({len(pos)/len(valid)*100:.0f}%)")
        print(f"  beating matched control   : {len(beat)}  ({len(beat)/len(valid)*100:.0f}%)")
        for z in (1.0, 1.5, 2.0):
            n = sum(1 for r in valid if r.edge_z >= z)
            print(f"  edge_z >= {z}              : {n:>3}   expected by chance: "
                  f"{len(valid)*(1-_norm_cdf(z)):.1f}")
        top = sorted(valid, key=lambda r: -r.edge_z)[:20]
        print("\n  Top 20 by edge_z:")
        for r in top:
            print(f"    {r.candidate_id:<10}{r.family:<18}n={r.trades:<5}"
                  f"expR={r.expectancy_r:+.4f}  edge_z={r.edge_z:+.2f}")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_screen_v2"
    out = os.path.join(OUT, f"{run_id}.json")
    os.makedirs(OUT, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"data_hash": bars.hash_key(), "n_candidates": len(lib),
                   "rows": [r.to_dict() for r in rows]}, fh, indent=2, default=str)
    print(f"\nwritten to {out}")


def _norm_cdf(z):
    import math
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


if __name__ == "__main__":
    main()
