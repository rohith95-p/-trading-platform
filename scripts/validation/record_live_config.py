"""Run the current live config through the OOS holdout and record it in
research/validation_ledger.json so main_loop's config-integrity gate will start.

The config recorded is SystemConfig.from_live() -- the exact fingerprint
main_loop checks. The backtest uses an EngineConfig built to MATCH live
(max_concurrent=2, daily 6%, trailing/pyramid off, D1 gate on), not
part1_suite.live_config() which uses max_concurrent=3.

    python -m scripts.validation.record_live_config
"""
from __future__ import annotations

import json

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.core.system_config import SystemConfig
from src.core import validation_ledger
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _ts, stats, verdict, START_BAL

HOLDOUT_START = "2025-01-01"
HOLDOUT_END = "2026-05-20"


def main():
    live = SystemConfig.from_live()
    fp = live.fingerprint()
    print(f"live fingerprint: {fp}")
    if validation_ledger.lookup(fp):
        print("already recorded -- nothing to do.")
        return

    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True,
        max_concurrent=live.max_concurrent_positions,
        max_same_direction=live.max_same_direction_positions,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=live.daily_loss_limit_pct,
        enable_d1_bias_gate=live.enable_d1_gate, direction_gate="d1_ema20",
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4],
                  start_ts=_ts(HOLDOUT_START), end_ts=_ts(HOLDOUT_END))
    s = stats(res.trades)
    v = verdict(s)
    print(json.dumps(s, indent=2))
    print(f"I.1 gate: {'PASS' if v['passed'] else 'FAIL'}  {v['reasons']}")

    result = {
        "window": f"{HOLDOUT_START} -> {HOLDOUT_END}",
        "n_trades": s.get("n"), "win_rate_pct": round(s.get("win_rate", 0), 1),
        "profit_factor": s.get("profit_factor"), "net_usd": s.get("net"),
        "min_balance_usd": s.get("min_balance"), "max_drawdown_pct": s.get("max_drawdown_pct"),
        "end_balance_usd": s.get("end_balance"),
        "i1_pass": v["passed"], "i1_reasons": v["reasons"],
    }
    notes = ("2-leg FVG-only PORTFOLIO_V4 (FVG_NY_TIGHT + FVG_NY_SWEEP_OR_VOID), "
             "D1 EMA20 gate ON (HYP-065), trailing/pyramiding OFF, max 2 concurrent, "
             "06:00-21:30 IST window. Quick single-holdout recording (owner asked "
             "for backtest-only, not the full part1 suite) to clear the startup "
             "config gate for the 2026-09-08 week. Sweep/Void legs dropped as dead "
             "(0 trades, Highlander). See RESEARCH_LEDGER + docs/REPO_GUIDE.md.")
    rec_fp = validation_ledger.record(live, result, source="scripts/validation/record_live_config.py", notes=notes)
    print(f"\nrecorded under fingerprint {rec_fp}")

    report = validation_ledger.check_live_config()
    print(f"check_live_config -> validated={report['validated']}")


if __name__ == "__main__":
    main()
