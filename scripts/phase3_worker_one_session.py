"""Phase 3 worker split to (rule, single session) granularity, so London/NY
don't wait behind Asia/Late finishing first inside a shared per-rule worker.

    python -m scripts.phase3_worker_one_session <combo> <TIGHT|WIDE> <SESSION> <out_dir>
"""
from __future__ import annotations
import sys, json, os
from dataclasses import asdict
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy, RULES, _stats, _ts
from scripts.tier2_screen_survivors import RUNS_ROOT

SESSIONS = {"ASIA": (2.5, 11.5), "LATE": (21.5, 24.0), "LONDON": (11.5, 15.5), "NY": (17.5, 21.5)}
TIGHT_SL = [0.5, 0.75, 1.0]
TIGHT_TP = {0.5: [1.5, 2.5], 0.75: [2.25, 3.0], 1.0: [2.0, 3.0]}
WIDE_SL = [1.5, 2.0]
WIDE_TP = {1.5: [2.0, 3.0, 4.5], 2.0: [3.0, 4.0]}

def main():
    combo, mode, sess_name, out_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    sl_mults, tp_map = (TIGHT_SL, TIGHT_TP) if mode == "TIGHT" else (WIDE_SL, WIDE_TP)
    sess = SESSIONS[sess_name]
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    lib = {c.id: c for c in build_library()}
    rule = lib[RULES[combo]].rule
    magic = 4000 + hash(f"{combo}{mode}{sess_name}") % 900

    for sl in sl_mults:
        for tp in tp_map[sl]:
            magic += 1
            cfg = EngineConfig(symbol="XAUUSDm", starting_balance=105.74, sizing_mode="fixed",
                fixed_lots=0.01, dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
                enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
                history_bars=900, warmup_bars=950, daily_loss_limit_mode="balance_pct",
                daily_loss_limit_pct=0.06, tp_atr_mult=tp, sl_atr_mult_override=sl)
            strat = TightStopStrategy(f"{combo}_{sess_name}", magic, rule, sess)
            eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
            res = eng.run([strat], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
            s = _stats(res.trades, 105.74)
            if s is None:
                print(f"{combo:<16}{sess_name:<8}{sl:>5.2f}{tp:>5.2f}    0  NO TRADES", flush=True)
                continue
            pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
            print(f"{combo:<16}{sess_name:<8}{sl:>5.2f}{tp:>5.2f}{s['n']:>5}"
                  f"{s['wr']:>7.1f}{pf:>7}{s['exp_r']:>8.3f}{s['net']:>8.0f}"
                  f"{s['min_bal']:>8.0f}{s['max_dd_pct']:>7.1f}"
                  f"{s['avg_stop_usd']:>7.2f}{s['avg_risk_pct']:>7.1f}", flush=True)

if __name__ == "__main__":
    main()
