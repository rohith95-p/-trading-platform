"""Run the session matrix for a single (rule, tp_atr) combo, given on argv[1].
Splits tier2_session_matrix.py's work across parallel OS processes.

    python -m scripts.tier2_session_matrix_one <combo_name>
"""
from __future__ import annotations
import sys, json, os
from dataclasses import asdict
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library, ASIA, LONDON, NY, ALL_DAY
from scripts.tier2_screen_survivors import _stats, _ts, RUNS_ROOT
from scripts.tier2_session_matrix import SessionMatrixStrategy, SESSIONS

COMBOS = {
    "range_rejection_3.0": ("XAU-049", 3.0),
    "ema_stack_1.5": ("XAU-006", 1.5),
    "ema_stack_3.0": ("XAU-005", 3.0),
    "orb_3.0": ("XAU-075", 3.0),
    "fvg_3.0": ("XAU-092", 3.0),
    "hhll_structure_3.0": ("XAU-026", 3.0),
    "squeeze_break_3.0": ("XAU-062", 3.0),
}

def main():
    combo_name = sys.argv[1]
    out_dir = sys.argv[2]
    cand_id, tp_atr = COMBOS[combo_name]
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    lib = {c.id: c for c in build_library()}
    rule = lib[cand_id].rule

    results = {}
    magic = 3500 + hash(combo_name) % 90
    for sess_name, sess in SESSIONS:
        magic += 1
        cfg = EngineConfig(
            symbol="XAUUSDm", starting_balance=105.74,
            sizing_mode="fixed", fixed_lots=0.01,
            dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
            enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
            history_bars=900, warmup_bars=950,
            daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
            tp_atr_mult=tp_atr,
        )
        strat = SessionMatrixStrategy(f"{combo_name}_{sess_name}", magic, rule, sess)
        engine = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        result = engine.run([strat], start_ts=_ts("2025-04-03"), end_ts=_ts("2026-08-29"))
        stats = _stats(result.trades, cfg.starting_balance)
        results[sess_name] = stats
        pf_s = "inf" if stats.get("profit_factor") == float("inf") else f"{stats.get('profit_factor', 0):.3f}"
        if stats["trades"] == 0:
            print(f"{combo_name:<22}{sess_name:<8}{'0':>6}  NO TRADES", flush=True)
        else:
            print(f"{combo_name:<22}{sess_name:<8}{stats['trades']:>6}{stats['win_rate']:>7.1f}"
                  f"{pf_s:>8}{stats['net_pl']:>10,.0f}{stats['end_balance']:>10,.0f}"
                  f"{stats['min_balance']:>9,.0f}{stats['max_dd_pct_of_peak']:>9.1f}"
                  f"{stats['daily_limit_breaches']:>6}", flush=True)
        with open(os.path.join(out_dir, f"trades_{combo_name}_{sess_name}.json"), "w", encoding="utf-8") as fh:
            json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)

    with open(os.path.join(out_dir, f"result_{combo_name}.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)

if __name__ == "__main__":
    main()
