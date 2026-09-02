"""Phase 13 exit research: sweep the exit geometry over a fixed entry signal.

Entries are held constant, so every difference between rows is caused by the
exit alone. Neighbourhoods are swept rather than single values -- a lone
profitable cell surrounded by losing ones is a fitting artifact, not a finding.

    python -m scripts.exit_research --start 2025-04-03 --end 2026-08-29
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import bootstrap_expectancy, summarize
from scripts.run_backtest import build_strategies

RUNS_ROOT = os.path.join("research", "runs")


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--cost", default="realistic")
    ap.add_argument("--balance", type=float, default=100000.0)
    ap.add_argument("--strategies", nargs="*",
                    default=["morning_momentum", "ema_pullback", "asian_sweep"])
    args = ap.parse_args()

    bars = load_bars("XAUUSDm")
    rows: List[Dict[str, Any]] = []

    variants: List[Dict[str, Any]] = [
        {"name": "no-trail TP3.0", "enable_trailing": False, "tp_atr_mult": 3.0},
        {"name": "no-trail TP2.0", "enable_trailing": False, "tp_atr_mult": 2.0},
        {"name": "no-trail TP1.5", "enable_trailing": False, "tp_atr_mult": 1.5},
        {"name": "no-trail TP4.0", "enable_trailing": False, "tp_atr_mult": 4.0},
        {"name": "no-trail TP5.0", "enable_trailing": False, "tp_atr_mult": 5.0},
    ]
    # Trail neighbourhood: activation x distance
    for act in (0.7, 1.0, 1.5, 2.0):
        for dist in (0.3, 0.5, 1.0, 1.5):
            if dist > act:
                continue
            variants.append({
                "name": f"trail act{act} dist{dist}",
                "enable_trailing": True,
                "trail_activation_atr": act,
                "trail_distance_atr": dist,
                "tp_atr_mult": 3.0,
            })

    hdr = (f"{'exit variant':<26}{'n':>6}{'WR%':>8}{'BE%':>8}{'PF':>8}"
           f"{'net $':>10}{'exp R':>9}{'payoff':>8}{'capture':>9}{'P(e<=0)':>9}")
    print(f"data {bars.hash_key()}  {args.start} -> {args.end}  costs={args.cost}\n")
    print(hdr)
    print("-" * len(hdr))

    for v in variants:
        name = v.pop("name")
        cfg = EngineConfig(starting_balance=args.balance, sizing_mode="fixed",
                           dedup_per_candle=True, **v)
        eng = BacktestEngine(bars, SCENARIOS[args.cost], cfg)
        res = eng.run(build_strategies(args.strategies), _ts(args.start), _ts(args.end))
        s = summarize(res.trades, res.equity, cfg.starting_balance)
        b = bootstrap_expectancy(res.trades)
        pf = "inf" if s.profit_factor == float("inf") else f"{s.profit_factor:.3f}"
        print(f"{name:<26}{s.trades:>6}{s.win_rate:>8.2f}{s.breakeven_win_rate:>8.2f}"
              f"{pf:>8}{s.net_pl:>10,.2f}{s.expectancy_r:>9.4f}"
              f"{s.payoff_ratio:>8.3f}{s.mfe_capture:>9.3f}"
              f"{(b['prob_negative'] if b else 0):>9.0%}", flush=True)
        rows.append({"variant": name, "config": v, "stats": s.to_dict(), "bootstrap": b})

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_exit_research"
    out = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "exit_research.json"), "w", encoding="utf-8") as fh:
        json.dump({"window": {"start": args.start, "end": args.end},
                   "cost": args.cost, "data_hash": bars.hash_key(),
                   "strategies": args.strategies, "rows": rows},
                  fh, indent=2, default=str)
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
