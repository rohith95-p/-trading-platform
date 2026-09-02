"""Parameter robustness and walk-forward for screen survivors (Parts 11 and 10).

The screen found a cluster around one base setup. Two things separate a real
finding from a fitted one, and both are tested here:

1. **Plateau, not peak.** Perturb every parameter around its chosen value. A
   result that survives only at one setting is noise. A broad region of similar
   performance is evidence.
2. **Walk-forward.** Split the in-sample window into consecutive folds and check
   the sign and magnitude hold across all of them, rather than coming from one
   good stretch.

Neither of these touches the locked holdout. That stays sealed until a single
configuration is nominated.

    python -m scripts.robustness
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

from src.backtesting.data import load_bars
from src.research.candidates import (ALL_DAY, LONDON, LONDON_NY, NY, Candidate,
                                     _roll_max, _roll_min, _shift, _sig)
from src.research.market_study import build_features, ema
from src.research.screener import screen

OUT = os.path.join("research", "screen")


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def make_ema_stack(fast: int, mid: int, slow: int):
    """EMA-stack trend state with configurable periods.

    Recomputed from close each call so the perturbation is genuine rather than
    reusing the cached 20/50/200 columns.
    """
    def rule(f):
        c = f["close"]
        e1, e2, e3 = ema(c, fast), ema(c, mid), ema(c, slow)
        up = (e1 > e2) & (e2 > e3) & (c > e1)
        dn = (e1 < e2) & (e2 < e3) & (c < e1)
        return _sig(up, dn)
    return rule


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()

    bars = load_bars("XAUUSDm", timeframes=("M15", "D1"))
    t = bars.m15["time"].astype(np.int64)
    rates = bars.m15[(t >= _ts(args.start)) & (t <= _ts(args.end))]
    f = build_features(rates)
    print(f"XAUUSDm M15 {len(rates):,} bars  {args.start} -> {args.end}  "
          f"data {bars.hash_key()}\n")

    report: Dict[str, object] = {"window": {"start": args.start, "end": args.end},
                                 "data_hash": bars.hash_key()}

    # ---- 1. parameter plateau -------------------------------------------
    print("=" * 86)
    print("  PARAMETER PLATEAU -- EMA stack, periods perturbed (session ALL, TP3.0/SL1.5)")
    print("=" * 86)
    print(f"  {'fast/mid/slow':<18}{'n':>6}{'WR%':>7}{'expR':>9}{'totR':>9}"
          f"{'PF':>7}{'ctrlR':>9}{'edgeR':>9}{'z':>7}")
    grid = []
    for fast in (10, 15, 20, 25, 30):
        for mid in (40, 50, 60):
            for slow in (150, 200, 250):
                cand = Candidate(
                    id=f"EMA-{fast}-{mid}-{slow}", name=f"stack {fast}/{mid}/{slow}",
                    family="trend", hypothesis="trend state persists",
                    failure_mode="regime change", rule=make_ema_stack(fast, mid, slow),
                    session=LONDON_NY, tp_atr=3.0, sl_atr=1.5, max_bars=96)
                r = screen(f, cand)
                grid.append({"fast": fast, "mid": mid, "slow": slow,
                             "trades": r.trades, "expectancy_r": r.expectancy_r,
                             "total_r": r.total_r, "profit_factor": r.profit_factor,
                             "edge_r": r.edge_r, "edge_z": r.edge_z})
                pf = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.3f}"
                print(f"  {f'{fast}/{mid}/{slow}':<18}{r.trades:>6}{r.win_rate:>7.1f}"
                      f"{r.expectancy_r:>+9.4f}{r.total_r:>+9.1f}{pf:>7}"
                      f"{r.control_expectancy_r:>+9.4f}{r.edge_r:>+9.4f}"
                      f"{r.edge_z:>+7.2f}", flush=True)
    report["plateau"] = grid
    zs = np.array([g["edge_z"] for g in grid])
    es = np.array([g["expectancy_r"] for g in grid])
    print(f"\n  {len(grid)} parameter combinations")
    print(f"    positive expectancy : {int((es > 0).sum())}/{len(grid)}"
          f"  ({(es > 0).mean()*100:.0f}%)")
    print(f"    edge_z > 0          : {int((zs > 0).sum())}/{len(grid)}"
          f"  ({(zs > 0).mean()*100:.0f}%)")
    print(f"    edge_z >= 1.0       : {int((zs >= 1).sum())}/{len(grid)}")
    print(f"    median edge_z       : {np.median(zs):+.2f}   "
          f"min {zs.min():+.2f}   max {zs.max():+.2f}")
    print("    -> a broad positive region is evidence; a lone spike would not be")

    # ---- 2. walk-forward -------------------------------------------------
    print("\n" + "=" * 86)
    print(f"  WALK-FORWARD -- {args.folds} consecutive folds, no refitting")
    print("=" * 86)
    n = len(rates)
    edges = np.linspace(0, n, args.folds + 1).astype(int)
    variants = [("EMA stack 20/50/200 ALL", make_ema_stack(20, 50, 200), LONDON_NY),
                ("EMA stack 20/50/200 NY", make_ema_stack(20, 50, 200), NY),
                ("EMA stack 15/50/200 ALL", make_ema_stack(15, 50, 200), LONDON_NY)]
    wf: Dict[str, List] = {}
    for label, rule, sess in variants:
        print(f"\n  {label}")
        print(f"    {'fold':<7}{'from':<12}{'to':<12}{'n':>6}{'expR':>9}"
              f"{'totR':>9}{'edgeR':>9}{'z':>7}")
        rows = []
        for k in range(args.folds):
            sl = slice(edges[k], edges[k + 1])
            sub = rates[sl]
            if len(sub) < 3000:
                continue
            fs = build_features(sub)
            cand = Candidate(id=f"wf{k}", name=label, family="trend",
                             hypothesis="", failure_mode="", rule=rule,
                             session=sess, tp_atr=3.0, sl_atr=1.5, max_bars=96)
            r = screen(fs, cand)
            d0 = datetime.fromtimestamp(int(sub[0]["time"]), tz=timezone.utc)
            d1 = datetime.fromtimestamp(int(sub[-1]["time"]), tz=timezone.utc)
            rows.append({"fold": k, "from": d0.strftime("%Y-%m-%d"),
                         "to": d1.strftime("%Y-%m-%d"), "trades": r.trades,
                         "expectancy_r": r.expectancy_r, "total_r": r.total_r,
                         "edge_r": r.edge_r, "edge_z": r.edge_z})
            print(f"    {k:<7}{d0:%Y-%m-%d}  {d1:%Y-%m-%d}  {r.trades:>6}"
                  f"{r.expectancy_r:>+9.4f}{r.total_r:>+9.1f}"
                  f"{r.edge_r:>+9.4f}{r.edge_z:>+7.2f}", flush=True)
        wf[label] = rows
        if rows:
            pos = sum(1 for x in rows if x["expectancy_r"] > 0)
            posz = sum(1 for x in rows if x["edge_z"] > 0)
            print(f"    -> {pos}/{len(rows)} folds positive expectancy, "
                  f"{posz}/{len(rows)} folds beat their control")
    report["walk_forward"] = wf

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_robustness.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"\nwritten to {path}")


if __name__ == "__main__":
    main()
