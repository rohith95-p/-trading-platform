"""Tier-2 session-sensitivity matrix: for every distinct (entry rule, exit
geometry) combination in the top-10 tier-1 candidates, test all four session
restrictions -- Asia-only, London-only, NY-only, and unrestricted 24h -- at
the real $105.74/0.01-lot/breaker-on constraint.

Motivation: HYP-029/030 showed session width interacts with exit geometry in
entry-specific, sometimes dangerous ways (widening HH/HL structure to 24h
nearly ruined the account; widening EMA_STACK's tight-exit variant to 24h
produced a near-miss down to $10). This asks the follow-up question directly:
does any of these entries have a *specific* session where it performs best,
strongly enough to justify a single-session-restricted deployment?

Ten candidates collapse to seven unique (rule, tp_atr, sl_atr) combinations;
testing each once per session covers all ten.

    python -m scripts.tier2_session_matrix
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
from src.research.candidates import build_library, ASIA, LONDON, NY, ALL_DAY
from src.research.market_study import build_features
from src.strategies.base_strategy import Signal, mt5
from scripts.tier2_screen_survivors import _stats, _ts, RUNS_ROOT

SESSIONS = [
    ("ASIA", ASIA),
    ("LONDON", LONDON),
    ("NY", NY),
    ("24H", ALL_DAY),
]


def _session_mask(ist_hour: np.ndarray, session) -> np.ndarray:
    """Canonical mask -- the private copy here handled `(21.5, 11.5)` but not the
    `(21.5, 26.5)` spelling used elsewhere. Phase 6."""
    from src.research.market_study import session_mask

    return session_mask(ist_hour, session)


class SessionMatrixStrategy:
    def __init__(self, name: str, magic: int, rule, session):
        self.name = name
        self.magic = magic
        self.rule = rule
        self.session = session

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 220:
            return None
        f = build_features(m15_rates)
        raw = self.rule(f)
        mask = _session_mask(f["ist_hour"], self.session)
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

    combos = [
        ("range_rejection_3.0", lib["XAU-049"].rule, 3.0, ["XAU-049"]),
        ("ema_stack_1.5", lib["XAU-006"].rule, 1.5, ["XAU-006", "XAU-002", "XAU-004"]),
        ("ema_stack_3.0", lib["XAU-005"].rule, 3.0, ["XAU-003", "XAU-005"]),
        ("orb_3.0", lib["XAU-075"].rule, 3.0, ["XAU-075"]),
        ("fvg_3.0", lib["XAU-092"].rule, 3.0, ["XAU-092"]),
        ("hhll_structure_3.0", lib["XAU-026"].rule, 3.0, ["XAU-026"]),
        ("squeeze_break_3.0", lib["XAU-062"].rule, 3.0, ["XAU-062"]),
    ]

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_session_matrix"
    out_dir = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out_dir, exist_ok=True)
    all_results = {}

    hdr = (f"{'combo':<22}{'session':<8}{'n':>6}{'WR%':>7}{'PF':>8}"
           f"{'net$':>10}{'end$':>10}{'minBal':>9}{'maxDD%pk':>9}{'brch':>6}")
    print(hdr)
    print("-" * len(hdr))

    magic = 3500
    for combo_name, rule, tp_atr, covers in combos:
        all_results[combo_name] = {"covers": covers, "sessions": {}}
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
            all_results[combo_name]["sessions"][sess_name] = stats

            pf_s = "inf" if stats.get("profit_factor") == float("inf") else f"{stats.get('profit_factor', 0):.3f}"
            if stats["trades"] == 0:
                print(f"{combo_name:<22}{sess_name:<8}{'0':>6}  NO TRADES")
            else:
                print(f"{combo_name:<22}{sess_name:<8}{stats['trades']:>6}{stats['win_rate']:>7.1f}"
                      f"{pf_s:>8}{stats['net_pl']:>10,.0f}{stats['end_balance']:>10,.0f}"
                      f"{stats['min_balance']:>9,.0f}{stats['max_dd_pct_of_peak']:>9.1f}"
                      f"{stats['daily_limit_breaches']:>6}", flush=True)

            with open(os.path.join(out_dir, f"trades_{combo_name}_{sess_name}.json"), "w", encoding="utf-8") as fh:
                json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)

    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"data_hash": bars.hash_key(), "results": all_results}, fh, indent=2, default=str)
    print(f"\nwritten to {out_dir}")


if __name__ == "__main__":
    run()
