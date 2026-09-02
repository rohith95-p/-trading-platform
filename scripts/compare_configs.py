"""Run the config matrix and tabulate it.

    python -m scripts.compare_configs --start 2025-04-03 --end 2026-08-29

Each config changes one thing against `head`, so the delta between two rows is
attributable to that one change. This is the ablation the project never had.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import (
    bootstrap_expectancy,
    drop_best_worst,
    monte_carlo_paths,
    summarize,
)
from scripts.run_backtest import CONFIGS, build_strategies

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger("compare")

RUNS_ROOT = os.path.join("research", "runs")


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def run_one(bars, config_name: str, cost_name: str, strategies: List[str],
            start: str, end: str, balance: float) -> Dict[str, Any]:
    cfg = EngineConfig(starting_balance=balance, **CONFIGS[config_name])
    eng = BacktestEngine(bars, SCENARIOS[cost_name], cfg)
    res = eng.run(build_strategies(strategies), _ts(start), _ts(end))
    stats = summarize(res.trades, res.equity, cfg.starting_balance)
    return {
        "config": config_name,
        "cost": cost_name,
        "stats": stats,
        "diag": res.diagnostics,
        "confidence": {
            "bootstrap": bootstrap_expectancy(res.trades),
            "monte_carlo": monte_carlo_paths(res.trades, cfg.starting_balance),
            "outliers": drop_best_worst(res.trades),
        },
        "engine_config": res.config,
        "data_hash": res.data_hash,
    }


HDR = (f"{'config':<20}{'cost':<13}{'n':>6}{'WR%':>8}{'BE%':>8}"
       f"{'PF':>8}{'net $':>11}{'exp $':>9}{'maxDD%':>9}{'dups':>7}{'P(e<=0)':>9}")


def fmt(r: Dict[str, Any]) -> str:
    s = r["stats"]
    b = r["confidence"]["bootstrap"]
    pf = s.profit_factor
    pf_s = "inf" if pf == float("inf") else f"{pf:.3f}"
    pn = f"{b['prob_negative']:.0%}" if b else "-"
    return (f"{r['config']:<20}{r['cost']:<13}{s.trades:>6}{s.win_rate:>8.2f}"
            f"{s.breakeven_win_rate:>8.2f}{pf_s:>8}{s.net_pl:>11,.2f}"
            f"{s.expectancy:>9.3f}{s.max_drawdown_pct:>9.1f}"
            f"{s.duplicate_trades:>7}{pn:>9}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSDm")
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--balance", type=float, default=105.74)
    ap.add_argument("--configs", nargs="*", default=list(CONFIGS))
    ap.add_argument("--costs", nargs="*", default=["realistic"])
    ap.add_argument("--strategies", nargs="*",
                    default=["morning_momentum", "ema_pullback", "asian_sweep"])
    ap.add_argument("--tag", default="matrix")
    args = ap.parse_args()

    bars = load_bars(args.symbol)
    print(f"data {bars.hash_key()}  window {args.start} -> {args.end}  "
          f"start balance ${args.balance:,.2f}\n")
    print(HDR)
    print("-" * len(HDR))

    rows: List[Dict[str, Any]] = []
    for cost in args.costs:
        for name in args.configs:
            r = run_one(bars, name, cost, args.strategies, args.start, args.end,
                        args.balance)
            rows.append(r)
            print(fmt(r), flush=True)

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_{args.tag}"
    out = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "matrix.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": args.symbol,
                "window": {"start": args.start, "end": args.end},
                "start_balance": args.balance,
                "strategies": args.strategies,
                "data_hash": bars.hash_key(),
                "data_manifests": {
                    k: {"sha256": v.sha256, "bars": v.bars, "first": v.first_time,
                        "last": v.last_time}
                    for k, v in bars.manifests.items()
                },
                "rows": [
                    {
                        "config": r["config"], "cost": r["cost"],
                        "stats": r["stats"].to_dict(), "diagnostics": r["diag"],
                        "confidence": r["confidence"], "engine_config": r["engine_config"],
                    }
                    for r in rows
                ],
            },
            fh, indent=2, default=str,
        )
    print(f"\nwritten to {out}")

    # Detail for the rows that matter most
    for r in rows:
        s = r["stats"]
        if r["config"] not in ("head", "repaired", "repaired_risk2pct"):
            continue
        print(f"\n--- {r['config']} / {r['cost']} ---")
        print(f"  exits {dict(sorted(s.exit_reasons.items(), key=lambda kv: -kv[1]))}")
        print(f"  MFE {s.avg_mfe_r:+.3f}R  MAE {s.avg_mae_r:+.3f}R  "
              f"capture {s.mfe_capture:.3f}  payoff {s.payoff_ratio:.3f}")
        for k, v in sorted(s.by_strategy.items(), key=lambda kv: -kv[1]["net_pl"]):
            print(f"    {k:<20} n={v['trades']:<5} wr={v['win_rate']:>5.1f}%  "
                  f"PF={v['profit_factor']:<8} net=${v['net_pl']:,.2f}")
        mc = r["confidence"]["monte_carlo"]
        if mc:
            print(f"  reshuffled: median DD ${mc['median_max_dd']:,.2f}  "
                  f"p95 ${mc['p95_max_dd']:,.2f}  P(-50%)={mc['prob_50pct_drawdown']:.1%}")


if __name__ == "__main__":
    main()
