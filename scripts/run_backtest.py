"""Run the execution-realistic backtest and write a reproducible run manifest.

    python -m scripts.run_backtest --config head
    python -m scripts.run_backtest --config repaired --start 2025-04-01

Every run writes research/runs/<id>/ containing the config, the data hashes, the
full trade list and the stats. Nothing is reported that cannot be regenerated
from that directory.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.backtesting.costs import SCENARIOS, CostModel
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import (
    bootstrap_expectancy,
    drop_best_worst,
    monte_carlo_paths,
    summarize,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backtest")

RUNS_ROOT = os.path.join("research", "runs")


def build_strategies(names: List[str]):
    from src.strategies.archive.asian_sweep import AsianSweep
    from src.strategies.archive.ema_pullback import EMAPullback
    from src.strategies.ema_stack import EMAStack
    from src.strategies.archive.morning_momentum import MorningMomentum

    available = {
        "morning_momentum": MorningMomentum,
        "ema_pullback": EMAPullback,
        "asian_sweep": AsianSweep,
        "ema_stack": EMAStack,   # RESEARCH ONLY -- not live-approved
    }
    return [available[n]() for n in names]


# Named configurations. "head" reproduces the code as deployed; the others
# change exactly one thing each so the difference is attributable.
CONFIGS: Dict[str, Dict[str, Any]] = {
    "head": {
        "daily_loss_limit_mode": "off",
        "risk_pct": 0.05,
    },
    # Edge-isolation variants: constant lot size, so results measure the signal
    # rather than the compounding failure of 15% sizing.
    "head_fixedlot": {"sizing_mode": "fixed"},
    "dedup_fixedlot": {"sizing_mode": "fixed", "dedup_per_candle": True},
    "notrail_fixedlot": {"sizing_mode": "fixed", "enable_trailing": False},
    "nocons_fixedlot": {"sizing_mode": "fixed", "enable_consolidation_exit": False},
    "nopyr_fixedlot": {"sizing_mode": "fixed", "enable_pyramiding": False},
    "nod1_fixedlot": {"sizing_mode": "fixed", "enable_d1_bias_gate": False},
    "widewarm_fixedlot": {"sizing_mode": "fixed", "history_bars": 1200, "warmup_bars": 1250},
    "stack_research": {
        "sizing_mode": "fixed",
        "dedup_per_candle": True,
        "enable_trailing": False,
        "enable_pyramiding": False,
        "enable_consolidation_exit": False,
        "history_bars": 900,          # EMA200 needs room to converge
        "warmup_bars": 950,
        "daily_loss_limit_mode": "off",
    },
    # Like-for-like with the tier-1 screen: one position at a time. A state
    # signal re-fires every candle while the state holds, so without this the
    # engine silently runs 3x leverage versus what was screened.
    "stack_single": {
        "sizing_mode": "fixed",
        "dedup_per_candle": True,
        "enable_trailing": False,
        "enable_pyramiding": False,
        "enable_consolidation_exit": False,
        "max_concurrent": 1,
        "max_same_direction": 1,
        "history_bars": 900,
        "warmup_bars": 950,
        "daily_loss_limit_mode": "off",
    },
    "clean_fixedlot": {
        "sizing_mode": "fixed",
        "dedup_per_candle": True,
        "spread_gate_blocks_management": False,
        "daily_loss_limit_mode": "balance_pct",
    },
    "dedup_only": {"dedup_per_candle": True},
    "lotcap_only": {"lot_cap": 0.01},
    "no_trailing": {"enable_trailing": False},
    "wide_warmup": {"history_bars": 1200, "warmup_bars": 1250},
    "repaired": {
        "dedup_per_candle": True,
        "lot_cap": 0.01,
        "spread_gate_blocks_management": False,
        "daily_loss_limit_mode": "balance_pct",
    },
    "repaired_risk2pct": {
        "dedup_per_candle": True,
        "risk_pct": 0.02,
        "lot_cap": None,
        "spread_gate_blocks_management": False,
        "daily_loss_limit_mode": "balance_pct",
    },
}


def _ts(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSDm")
    ap.add_argument("--config", default="head", choices=sorted(CONFIGS))
    ap.add_argument("--cost", default="realistic", choices=sorted(SCENARIOS))
    ap.add_argument("--strategies", nargs="*",
                    default=["morning_momentum", "ema_pullback", "asian_sweep"])
    ap.add_argument("--start", default=None, help="YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD")
    ap.add_argument("--balance", type=float, default=105.74)
    ap.add_argument("--tag", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    bars = load_bars(args.symbol)
    log.info(
        "data: M15=%d M5=%s M1=%s D1=%s  hash=%s",
        len(bars.m15),
        len(bars.m5) if bars.m5 is not None else "-",
        len(bars.m1) if bars.m1 is not None else "-",
        len(bars.d1) if bars.d1 is not None else "-",
        bars.hash_key(),
    )

    cfg = EngineConfig(symbol=args.symbol, starting_balance=args.balance,
                       **CONFIGS[args.config])
    cost = SCENARIOS[args.cost]
    strategies = build_strategies(args.strategies)

    engine = BacktestEngine(bars, cost, cfg)
    result = engine.run(
        strategies,
        start_ts=_ts(args.start) if args.start else None,
        end_ts=_ts(args.end) if args.end else None,
    )

    stats = summarize(result.trades, result.equity, cfg.starting_balance)
    confidence = {
        "bootstrap_expectancy": bootstrap_expectancy(result.trades),
        "monte_carlo": monte_carlo_paths(result.trades, cfg.starting_balance),
        "outlier_dependence": drop_best_worst(result.trades),
    }

    run_id = (
        f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_{args.config}_{args.cost}"
        + (f"_{args.tag}" if args.tag else "")
    )
    out = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": args.symbol,
        "config_name": args.config,
        "cost_scenario": args.cost,
        "cost_model": asdict(cost),
        "strategies": args.strategies,
        "window": {"start": args.start, "end": args.end},
        "engine_config": result.config,
        "data_hash": result.data_hash,
        "data_manifests": {
            k: {"sha256": v.sha256, "bars": v.bars,
                "first": v.first_time, "last": v.last_time}
            for k, v in bars.manifests.items()
        },
        "diagnostics": result.diagnostics,
        "stats": stats.to_dict(),
        "confidence": confidence,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    with open(os.path.join(out, "trades.json"), "w", encoding="utf-8") as fh:
        json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)

    if not args.quiet:
        _print(manifest, stats, result)
    log.info("run written to %s", out)


def _print(manifest, stats, result) -> None:
    s = stats
    print()
    print("=" * 72)
    print(f"  {manifest['config_name'].upper()}  |  costs: {manifest['cost_scenario']}"
          f"  |  data {manifest['data_hash']}")
    print("=" * 72)
    print(f"  trades {s.trades:<6} win rate {s.win_rate:>6.2f}%   "
          f"breakeven needed {s.breakeven_win_rate:>6.2f}%  ({s.win_rate_margin:+.2f})")
    print(f"  net    ${s.net_pl:<10,.2f} PF {s.profit_factor:<7.3f} "
          f"expectancy ${s.expectancy:.3f}/trade  ({s.expectancy_r:+.4f} R)")
    print(f"  avg win ${s.avg_win:<8,.2f} avg loss ${s.avg_loss:<8,.2f} "
          f"payoff {s.payoff_ratio:.3f}")
    print(f"  max DD ${s.max_drawdown:,.2f} ({s.max_drawdown_pct:.1f}%)  "
          f"over {s.max_drawdown_duration_days:.0f}d   recovery {s.recovery_factor:.2f}")
    print(f"  balance ${s.start_balance:,.2f} -> ${s.end_balance:,.2f} "
          f"({s.return_pct:+.1f}%)   max consec losses {s.max_consec_losses}")
    print(f"  MFE {s.avg_mfe_r:+.3f}R  MAE {s.avg_mae_r:+.3f}R  "
          f"capture {s.mfe_capture:.3f}   median hold {s.median_minutes_open:.0f} min")
    print(f"  duplicates {s.duplicate_trades} (${s.duplicate_pl:,.2f})   "
          f"pyramids {s.pyramid_trades} (${s.pyramid_pl:,.2f})   "
          f"ambiguous {s.ambiguous_trades}")
    print(f"  exits: {dict(sorted(s.exit_reasons.items(), key=lambda kv: -kv[1]))}")

    if s.by_strategy:
        print("\n  per strategy:")
        for k, v in sorted(s.by_strategy.items(), key=lambda kv: -kv[1]["net_pl"]):
            print(f"    {k:<20} n={v['trades']:<5} wr={v['win_rate']:>5.1f}%  "
                  f"PF={v['profit_factor']:<7} net=${v['net_pl']:,.2f}")

    c = manifest["confidence"]
    if c.get("bootstrap_expectancy"):
        b = c["bootstrap_expectancy"]
        print(f"\n  bootstrap expectancy 90% CI: "
              f"[{b['p05']:+.3f}, {b['p95']:+.3f}]  P(edge<=0) = {b['prob_negative']:.1%}")
    if c.get("monte_carlo"):
        m = c["monte_carlo"]
        print(f"  reshuffled max DD: median ${m['median_max_dd']:,.2f}  "
              f"p95 ${m['p95_max_dd']:,.2f}   P(-50% acct) = {m['prob_50pct_drawdown']:.1%}")
    if c.get("outlier_dependence"):
        d = c["outlier_dependence"]
        print(f"  drop best 3 trades: ${d['drop_best_3']:,.2f}   "
              f"top-3 = {d['top3_share_of_gross_profit']:.0f}% of gross profit")

    d = result.diagnostics
    print(f"\n  diagnostics: {json.dumps(d)}")
    print()


if __name__ == "__main__":
    main()
