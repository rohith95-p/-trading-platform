"""Production-grade validation runner with explicit promotion gates.

Usage:
    python -m scripts.production_validation
    python -m scripts.production_validation --profile config/validation_profile.json
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Dict, List, Tuple

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import monte_carlo_paths, summarize
from src.strategies.portfolio_v4 import PORTFOLIO_V4


def _ts(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _load_profile(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_strategies(name: str):
    if name != "portfolio_v4":
        raise ValueError(f"unsupported strategy set: {name}")
    return [cls() for cls in PORTFOLIO_V4]


def _run_window(
    bars,
    config: EngineConfig,
    cost,
    strategies,
    start: str,
    end: str,
) -> Dict[str, Any]:
    engine = BacktestEngine(bars=bars, cost=cost, config=config)
    result = engine.run(strategies, start_ts=_ts(start), end_ts=_ts(end))
    stats = summarize(result.trades, result.equity, config.starting_balance)
    mc = monte_carlo_paths(result.trades, config.starting_balance)
    return {
        "window": {"start": start, "end": end},
        "stats": stats.to_dict(),
        "confidence": {"monte_carlo": mc},
        "diagnostics": result.diagnostics,
        "trades": len(result.trades),
    }


def _walk_windows(start: str, end: str, test_days: int, step_days: int) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    curr = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    while curr < end_dt:
        test_end = min(curr + timedelta(days=test_days), end_dt)
        out.append((curr.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d")))
        curr += timedelta(days=step_days)
    return out


def _evaluate_gates(report: Dict[str, Any], gates: Dict[str, Any]) -> Dict[str, Any]:
    holdout_stats = report["holdout"]["stats"]
    holdout_mc = report["holdout"]["confidence"].get("monte_carlo", {})
    holdout_g = gates.get("holdout", {})

    holdout_pass = (
        holdout_stats.get("profit_factor", 0.0) >= holdout_g.get("pf_min", 0.0)
        and holdout_stats.get("max_drawdown_pct", 9999.0) <= holdout_g.get("max_drawdown_pct_max", 9999.0)
        and holdout_mc.get("prob_50pct_drawdown", 1.0)
        <= holdout_g.get("prob_50pct_drawdown_max", 1.0)
    )

    wf = report["walk_forward"]
    wf_pfs = [w["stats"].get("profit_factor", 0.0) for w in wf if w["trades"] > 0]
    wf_med = median(wf_pfs) if wf_pfs else 0.0
    wf_min = min(wf_pfs) if wf_pfs else 0.0
    wf_g = gates.get("walk_forward", {})
    wf_pass = wf_med >= wf_g.get("median_pf_min", 0.0) and wf_min >= wf_g.get("worst_window_pf_min", 0.0)

    pert = report["perturbations"]
    pert_pfs = [p["stats"].get("profit_factor", 0.0) for p in pert if p["trades"] > 0]
    pert_min = min(pert_pfs) if pert_pfs else 0.0
    pert_g = gates.get("perturbation", {})
    pert_pass = pert_min >= pert_g.get("pf_min", 0.0)

    return {
        "holdout_pass": holdout_pass,
        "walk_forward_pass": wf_pass,
        "perturbation_pass": pert_pass,
        "all_pass": holdout_pass and wf_pass and pert_pass,
        "summary": {
            "holdout_pf": holdout_stats.get("profit_factor", 0.0),
            "holdout_max_dd_pct": holdout_stats.get("max_drawdown_pct", 0.0),
            "holdout_prob_50pct_drawdown": holdout_mc.get("prob_50pct_drawdown", None),
            "walk_forward_median_pf": wf_med,
            "walk_forward_worst_pf": wf_min,
            "perturbation_worst_pf": pert_min,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="config/validation_profile.json")
    args = ap.parse_args()

    profile = _load_profile(args.profile)
    bars = load_bars(profile["symbol"], timeframes=("M15", "M5", "M1", "D1"))

    cfg = EngineConfig(
        symbol=profile["symbol"],
        starting_balance=float(profile["starting_balance"]),
        **profile["frozen_engine_config"],
    )
    cost = SCENARIOS[profile["cost_scenario"]]

    holdout = profile["holdout"]
    holdout_res = _run_window(
        bars=bars,
        config=cfg,
        cost=cost,
        strategies=_build_strategies(profile["strategies"]),
        start=holdout["start"],
        end=holdout["end"],
    )

    wf_cfg = profile["walk_forward"]
    wf_windows = _walk_windows(
        wf_cfg["start"], wf_cfg["end"], int(wf_cfg["test_days"]), int(wf_cfg["step_days"])
    )
    wf_results = [
        _run_window(
            bars=bars,
            config=cfg,
            cost=cost,
            strategies=_build_strategies(profile["strategies"]),
            start=s,
            end=e,
        )
        for s, e in wf_windows
    ]

    pert = profile.get("perturbations", {})
    spread_mult = pert.get("spread_multiplier", [1.0])
    slippage_points = pert.get("slippage_points", [cost.slippage_points])
    pert_results = []
    for sm in spread_mult:
        for sp in slippage_points:
            varied_cost = replace(cost, spread_multiplier=float(sm), slippage_points=float(sp))
            res = _run_window(
                bars=bars,
                config=cfg,
                cost=varied_cost,
                strategies=_build_strategies(profile["strategies"]),
                start=holdout["start"],
                end=holdout["end"],
            )
            res["cost_override"] = {
                "spread_multiplier": float(sm),
                "slippage_points": float(sp),
            }
            pert_results.append(res)

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "profile_path": args.profile,
        "profile": profile,
        "frozen_engine_config": asdict(cfg),
        "holdout": holdout_res,
        "walk_forward": wf_results,
        "perturbations": pert_results,
    }
    report["promotion_decision"] = _evaluate_gates(report, profile.get("promotion_gates", {}))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join("research", "runs", f"{run_id}_production_validation")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    summary = report["promotion_decision"]
    print(f"report: {out_path}")
    print(f"all_pass={summary['all_pass']} details={summary['summary']}")


if __name__ == "__main__":
    main()
