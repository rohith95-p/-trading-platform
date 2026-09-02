"""Adversarial follow-up to the exit sweep.

The sweep's best cell sat at the widest take-profit tested, which is a classic
sign that the search boundary -- not the market -- is setting the answer. Two
things have to be ruled out before "wider is better" counts as a finding:

1. **Boundary artifact.** Extend the range until the curve turns over. If it
   never turns over, the exit is not what is being measured.
2. **Directional beta.** Gold rose steeply across this window. A wider target
   held longer in a rising market earns the drift, not an edge. Splitting P&L by
   direction shows whether the result is a strategy or a long bias.

    python -m scripts.exit_extend
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import bootstrap_expectancy, summarize
from scripts.run_backtest import build_strategies

RUNS_ROOT = os.path.join("research", "runs")


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def direction_split(trades) -> Dict[str, Any]:
    """P&L by side. If one side carries everything, the 'edge' is market drift."""
    out: Dict[str, Any] = {}
    for side, sel in (("LONG", True), ("SHORT", False)):
        t = [x for x in trades if x.is_buy is sel]
        if not t:
            out[side] = {"trades": 0}
            continue
        pls = np.array([x.net_pl for x in t])
        wins, losses = pls[pls > 0], pls[pls < 0]
        gp, gl = float(wins.sum()), float(abs(losses.sum()))
        out[side] = {
            "trades": len(t),
            "win_rate": round(float((pls > 0).mean()) * 100, 2),
            "net_pl": round(float(pls.sum()), 2),
            "profit_factor": round(gp / gl, 3) if gl else float("inf"),
            "expectancy": round(float(pls.mean()), 4),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--cost", default="realistic")
    ap.add_argument("--balance", type=float, default=100000.0)
    ap.add_argument("--tps", nargs="*", type=float, default=[5.0, 6.0, 8.0, 12.0, 20.0])
    ap.add_argument("--strategies", nargs="*",
                    default=["morning_momentum", "ema_pullback", "asian_sweep"])
    args = ap.parse_args()

    bars = load_bars("XAUUSDm")
    print(f"data {bars.hash_key()}  {args.start} -> {args.end}  costs={args.cost}")
    print("\nBoundary test: does the take-profit curve ever turn over?\n")
    hdr = (f"{'TP (xATR)':<12}{'n':>6}{'WR%':>8}{'PF':>8}{'net $':>11}"
           f"{'payoff':>9}{'hold(min)':>11}{'P(e<=0)':>9}")
    print(hdr)
    print("-" * len(hdr))

    rows: List[Dict[str, Any]] = []
    for tp in args.tps:
        cfg = EngineConfig(starting_balance=args.balance, sizing_mode="fixed",
                           dedup_per_candle=True, enable_trailing=False,
                           tp_atr_mult=tp)
        eng = BacktestEngine(bars, SCENARIOS[args.cost], cfg)
        res = eng.run(build_strategies(args.strategies), _ts(args.start), _ts(args.end))
        s = summarize(res.trades, res.equity, cfg.starting_balance)
        b = bootstrap_expectancy(res.trades)
        pf = "inf" if s.profit_factor == float("inf") else f"{s.profit_factor:.3f}"
        print(f"{tp:<12.1f}{s.trades:>6}{s.win_rate:>8.2f}{pf:>8}{s.net_pl:>11,.2f}"
              f"{s.payoff_ratio:>9.3f}{s.median_minutes_open:>11.0f}"
              f"{(b['prob_negative'] if b else 0):>9.0%}", flush=True)
        rows.append({
            "tp_atr_mult": tp,
            "stats": s.to_dict(),
            "bootstrap": b,
            "direction": direction_split(res.trades),
            "by_month": s.by_month,
        })

    print("\n\nDirectional split -- is this an edge or is it the gold rally?\n")
    hdr2 = (f"{'TP':<8}{'side':<8}{'n':>6}{'WR%':>8}{'PF':>9}{'net $':>11}{'exp $':>9}")
    print(hdr2)
    print("-" * len(hdr2))
    for r in rows:
        for side in ("LONG", "SHORT"):
            d = r["direction"][side]
            if not d.get("trades"):
                print(f"{r['tp_atr_mult']:<8.1f}{side:<8}{0:>6}")
                continue
            pf = "inf" if d["profit_factor"] == float("inf") else f"{d['profit_factor']:.3f}"
            print(f"{r['tp_atr_mult']:<8.1f}{side:<8}{d['trades']:>6}{d['win_rate']:>8.2f}"
                  f"{pf:>9}{d['net_pl']:>11,.2f}{d['expectancy']:>9.3f}")

    print("\n\nMonthly consistency of the widest profitable variant\n")
    best = max(rows, key=lambda r: r["stats"]["net_pl"])
    bm = best["by_month"]
    months = sorted(bm)
    pos = sum(1 for m in months if bm[m]["net_pl"] > 0)
    print(f"TP {best['tp_atr_mult']}xATR: {pos}/{len(months)} profitable months")
    print(f"  {'month':<10}{'n':>5}{'wr%':>7}{'net$':>11}")
    for m in months:
        v = bm[m]
        print(f"  {m:<10}{v['trades']:>5}{v['win_rate']:>7.1f}{v['net_pl']:>11.2f}")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_exit_extend"
    out = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "exit_extend.json"), "w", encoding="utf-8") as fh:
        json.dump({"window": {"start": args.start, "end": args.end},
                   "cost": args.cost, "data_hash": bars.hash_key(), "rows": rows},
                  fh, indent=2, default=str)
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
