"""Tier-2 test: does excluding the Asia/overnight session fix or improve on
the 24h-widened variants from tier2_modified_variants.py?

HYP-030 found that widening to full 24h trading was entry-specific: it helped
the EMA ribbon but nearly ruined the HH/HL structure entry (7 trades, balance
went negative) and made EMA_STACK's own entry more dangerous when paired with
a tight exit (dipped to $10). Asia/overnight (02:30-11:30 IST) is the obvious
suspect -- thinner liquidity, wider relative spread, gap risk. This script
isolates it directly: same three entries, same exits, but with Asia hours
excluded rather than either fully gated to London+NY or fully unrestricted.

Note: the project's own session-tuple helper (see src/research/screener.py
_session_mask) mishandles the wraparound case for a session like "everything
except Asia," so this script does NOT reuse that helper -- it builds the
exclusion mask directly and explicitly.

    python -m scripts.tier2_no_asia
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from src.research.market_study import build_features
from src.strategies.base_strategy import Signal, mt5
from scripts.tier2_screen_survivors import _stats, _ts, RUNS_ROOT

ASIA_START, ASIA_END = 2.5, 11.5  # IST, matches src/research/candidates.py ASIA


def _no_asia_mask(ist_hour: np.ndarray) -> np.ndarray:
    return (ist_hour < ASIA_START) | (ist_hour >= ASIA_END)


class NoAsiaStrategy:
    def __init__(self, name: str, magic: int, rule, tp_atr: float):
        self.name = name
        self.magic = magic
        self.rule = rule
        self.tp_atr = tp_atr

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 220:
            return None
        f = build_features(m15_rates)
        raw = self.rule(f)
        mask = _no_asia_mask(f["ist_hour"])
        sig = np.where(mask, raw, 0)
        s = sig[-2]
        if s == 0 or np.isnan(s):
            return None
        if s > 0:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                      magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


def run() -> None:
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    lib = {c.id: c for c in build_library()}
    print(f"Data hash: {bars.hash_key()}\n")

    variants = [
        ("NOASIA-1_emastack_native", lib["XAU-005"].rule, 3.0, "EMA stack, no-Asia, 3.0/1.5 (compare vs MOD-2's 24h)"),
        ("NOASIA-2_emastack_tight", lib["XAU-006"].rule, 1.5, "EMA stack, no-Asia, 1.5/1.5 (compare vs MOD-3's 24h near-miss)"),
        ("NOASIA-3_hhll_structure", lib["XAU-026"].rule, 3.0, "HH/HL structure, no-Asia, 3.0/1.5 (compare vs MOD-1's near-ruin)"),
    ]

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_no_asia"
    out_dir = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out_dir, exist_ok=True)
    all_results = {}

    hdr = (f"{'id':<28}{'n':>6}{'WR%':>7}{'PF':>8}"
           f"{'net$':>10}{'end$':>10}{'minBal':>9}{'maxDD%pk':>9}{'brch':>6}")
    print(hdr)
    print("-" * len(hdr))

    for key, rule, tp_atr, note in variants:
        cfg = EngineConfig(
            symbol="XAUUSDm", starting_balance=105.74,
            sizing_mode="fixed", fixed_lots=0.01,
            dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
            enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
            history_bars=900, warmup_bars=950,
            daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
            tp_atr_mult=tp_atr,
        )
        strat = NoAsiaStrategy(key, magic=3400 + hash(key) % 90, rule=rule, tp_atr=tp_atr)
        engine = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        result = engine.run([strat], start_ts=_ts("2025-04-03"), end_ts=_ts("2026-08-29"))
        stats = _stats(result.trades, cfg.starting_balance)
        all_results[key] = {"note": note, "in_sample": stats}

        pf_s = "inf" if stats.get("profit_factor") == float("inf") else f"{stats.get('profit_factor', 0):.3f}"
        if stats["trades"] == 0:
            print(f"{key:<28}{'0':>6}  NO TRADES")
        else:
            print(f"{key:<28}{stats['trades']:>6}{stats['win_rate']:>7.1f}"
                  f"{pf_s:>8}{stats['net_pl']:>10,.0f}{stats['end_balance']:>10,.0f}"
                  f"{stats['min_balance']:>9,.0f}{stats['max_dd_pct_of_peak']:>9.1f}"
                  f"{stats['daily_limit_breaches']:>6}", flush=True)

        with open(os.path.join(out_dir, f"trades_{key}.json"), "w", encoding="utf-8") as fh:
            json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)

    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"data_hash": bars.hash_key(), "results": all_results}, fh, indent=2, default=str)
    print(f"\nwritten to {out_dir}")


if __name__ == "__main__":
    run()
