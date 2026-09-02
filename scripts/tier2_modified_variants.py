"""Tier-2 test of modified candidate variants.

Two hypotheses raised by the screen_survivors sweep:

1. Exit geometry drives survivability more than the entry signal (ledger
   HYP-017/018 already established this for TP width; this checks it holds
   for a non-EMA entry).
2. Session restriction is costing XAU-005 relative to live EMA_STACK, which
   is identical in every other respect (same rule, same 3.0/1.5 exit) but
   trades 24 hours instead of London+NY only.

Three variants, same tier-2 engine / real balance / breaker-on setup as
tier2_screen_survivors.py:

  MOD-1: HH/HL structure entry, widened to 24h session + EMA_STACK's 3.0/1.5
         exit (was NY-only, 3.0/1.5 in XAU-026 -- isolates the session effect
         on a non-EMA entry).
  MOD-2: EMA stack entry, 24h session, 3.0/1.5 exit (should reproduce live
         EMA_STACK's own number if session really is the explanation for the
         XAU-005 gap -- a sanity check as much as a variant).
  MOD-3: HH/HL structure entry, London+NY session (unchanged from XAU-026)
         but with EMA_STACK's habit of never fixing TP tight -- already at
         3.0/1.5, so this arm instead drops the session filter only, keeping
         everything else, to separate session-width from exit-width cleanly.

    python -m scripts.tier2_modified_variants
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library, Candidate, ALL_DAY
from scripts.tier2_screen_survivors import CandidateStrategy, _stats, _ts, RUNS_ROOT


def run() -> None:
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    lib = {c.id: c for c in build_library()}
    print(f"Data hash: {bars.hash_key()}\n")

    base_026 = lib["XAU-026"]   # HH/HL structure [NY 3.0/1.5]
    base_005 = lib["XAU-005"]   # EMA stack [ALL(=LONDON_NY) 3.0/1.5]

    variants = {
        "MOD-1_hhll_24h_3.0_1.5": Candidate(
            id="MOD-1", name="HH/HL structure [24h 3.0/1.5]", family="trend",
            hypothesis="Widening HH/HL to 24h session improves survivability like it does for EMA_STACK.",
            failure_mode="Overnight liquidity is thin; spread cost may eat the wider sample.",
            rule=base_026.rule, session=ALL_DAY, tp_atr=3.0, sl_atr=1.5,
        ),
        "MOD-2_emastack_24h_3.0_1.5": Candidate(
            id="MOD-2", name="EMA stack [24h 3.0/1.5] (sanity check vs live EMA_STACK)", family="trend",
            hypothesis="This should reproduce live EMA_STACK's own survivability number.",
            failure_mode="If it doesn't, the gap isn't session -- something else differs.",
            rule=base_005.rule, session=ALL_DAY, tp_atr=3.0, sl_atr=1.5,
        ),
        "MOD-3_xau006_24h": Candidate(
            id="MOD-3", name="EMA stack [24h 1.5/1.5] (widen the best fixed-TP performer)", family="trend",
            hypothesis="XAU-006 was the best fixed-TP entrant in the sweep; does 24h widen or worsen it?",
            failure_mode="Overnight spread/thin liquidity could erase the tight-exit edge.",
            rule=lib["XAU-006"].rule, session=ALL_DAY, tp_atr=lib["XAU-006"].tp_atr, sl_atr=lib["XAU-006"].sl_atr,
        ),
    }

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_modified_variants"
    out_dir = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out_dir, exist_ok=True)
    all_results = {}

    hdr = (f"{'id':<10}{'name':<48}{'n':>6}{'WR%':>7}{'PF':>8}"
           f"{'net$':>10}{'end$':>10}{'minBal':>9}{'maxDD%pk':>9}{'brch':>6}")
    print(hdr)
    print("-" * len(hdr))

    for key, cand in variants.items():
        cfg = EngineConfig(
            symbol="XAUUSDm", starting_balance=105.74,
            sizing_mode="fixed", fixed_lots=0.01,
            dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
            enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
            history_bars=900, warmup_bars=950,
            daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
            tp_atr_mult=cand.tp_atr,
        )
        strat = CandidateStrategy(cand, magic=3300 + hash(key) % 90)
        engine = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        result = engine.run([strat], start_ts=_ts("2025-04-03"), end_ts=_ts("2026-08-29"))
        stats = _stats(result.trades, cfg.starting_balance)
        all_results[key] = {"name": cand.name, "in_sample": stats}

        pf_s = "inf" if stats.get("profit_factor") == float("inf") else f"{stats.get('profit_factor', 0):.3f}"
        if stats["trades"] == 0:
            print(f"{key:<10}{cand.name:<48}{'0':>6}  NO TRADES")
        else:
            print(f"{key:<10}{cand.name:<48}{stats['trades']:>6}{stats['win_rate']:>7.1f}"
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
