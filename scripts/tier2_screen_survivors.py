"""Tier-2 survivability pass over the top tier-1 screen candidates.

The tier-1 screen (scripts/screen_candidates.py) ranks 120 candidates by edge
over a matched random-entry control using a fast approximation: next-bar
entry, half-spread cost, no daily caps, no M1 sub-bar walk. XAU-119 and
XAU-120 both looked strong there (edge_z +2.77 and +1.88) and both collapsed
to ~$0 in the full tier-2 engine (HYP-025/026) -- the fast screen cannot see
the compounding effect of the 6%-daily-loss breaker at a $105.74 balance.

This script takes that lesson and applies it broadly: run every candidate
that beat its control in tier-1 (not just the SAR ones) through the real
tier-2 engine at the user's actual constraint -- $105.74 starting balance,
fixed 0.01 lots, live daily-loss breaker on -- and report which ones (if any)
actually survive. Every candidate tested is reported, not just winners
(project rule: no cherry-picking).

    python -m scripts.tier2_screen_survivors
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
from src.research.candidates import build_library, Candidate
from src.research.market_study import build_features
from src.strategies.base_strategy import Signal, mt5

RUNS_ROOT = os.path.join("research", "runs")

# Candidates to test: the top-12-by-edge_z from the 2026-08-31 screen
# (research/screen/20260831-183504_screen.json), minus XAU-119/120 which are
# already settled (HYP-025/026), plus the two SAR ones for reference.
CANDIDATE_IDS = [
    "XAU-049",  # Range rejection wick [LONDON 3.0/1.5]  edge_z +3.78
    "XAU-006",  # EMA stack continuation [ALL 1.5/1.5]    edge_z +3.27
    "XAU-003",  # EMA stack continuation [NY 3.0/1.5]     edge_z +3.09
    "XAU-075",  # Opening range break [NY 3.0/1.5]        edge_z +2.74
    "XAU-092",  # Fair value gap [NY 3.0/1.5]              edge_z +2.65
    "XAU-005",  # EMA stack continuation [ALL 3.0/1.5]    edge_z +2.07
    "XAU-002",  # EMA stack continuation [LONDON 1.5/1.5] edge_z +2.03
    "XAU-026",  # HH/HL structure [NY 3.0/1.5]            edge_z +1.99
    "XAU-062",  # Squeeze breakout [NY 3.0/1.5]            edge_z +1.94
    "XAU-004",  # EMA stack continuation [NY 1.5/1.5]     edge_z +1.79
]


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _session_mask(ist_hour: np.ndarray, session) -> np.ndarray:
    """Canonical mask. The private copy that used to live here dropped the
    post-midnight half of any wraparound session (Phase 0 finding)."""
    from src.research.market_study import session_mask

    return session_mask(ist_hour, session)


class CandidateStrategy:
    """Tier-2 live-compatible wrapper around a tier-1 screening candidate."""

    def __init__(self, cand: Candidate, magic: int):
        self.cand = cand
        self.name = cand.id
        self.magic = magic
        self._min_bars = 220  # EMA200 warm-up

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None

        f = build_features(m15_rates)
        raw = self.cand.rule(f)
        mask = _session_mask(f["ist_hour"], self.cand.session)
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


def _stats(trades, start_bal: float) -> dict:
    if not trades:
        return {"trades": 0}
    net = np.array([t.net_pl for t in trades])
    bal_after = np.array([t.balance_after for t in trades])
    balances = np.concatenate([[start_bal], bal_after])
    peak = np.maximum.accumulate(balances)
    dd_abs = peak - balances
    dd_pct_peak = np.divide(dd_abs, peak, out=np.zeros_like(dd_abs), where=peak > 0)
    wins = net[net > 0]
    losses = net[net < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    daily_pl: dict = {}
    daily_start_bal: dict = {}
    running_bal = start_bal
    for t in trades:
        d = datetime.fromtimestamp(t.exit_time, tz=timezone.utc).date().isoformat()
        if d not in daily_start_bal:
            daily_start_bal[d] = running_bal
        daily_pl[d] = daily_pl.get(d, 0.0) + t.net_pl
        running_bal = t.balance_after
    breaches = sum(1 for d, pl in daily_pl.items() if pl < -0.06 * daily_start_bal[d])

    return {
        "trades": len(trades),
        "win_rate": float(len(wins) / len(net) * 100),
        "profit_factor": pf,
        "expectancy_r": float(np.mean([t.r_multiple for t in trades])),
        "net_pl": float(net.sum()),
        "start_balance": start_bal,
        "end_balance": float(bal_after[-1]),
        "min_balance": float(balances.min()),
        "max_dd_pct_of_peak": float(dd_pct_peak.max() * 100),
        "daily_limit_breaches": breaches,
        "trading_days": len(daily_pl),
        "ruined": bool(bal_after[-1] <= 5.0),
    }


def run() -> None:
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    lib = {c.id: c for c in build_library()}
    print(f"Data hash: {bars.hash_key()}\n")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_screen_survivors"
    out_dir = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out_dir, exist_ok=True)
    all_results = {}

    hdr = (f"{'id':<9}{'name':<44}{'n':>6}{'WR%':>7}{'PF':>8}"
           f"{'net$':>10}{'end$':>10}{'minBal':>9}{'maxDD%pk':>9}{'brch':>6}")
    print(hdr)
    print("-" * len(hdr))

    for cid in CANDIDATE_IDS:
        cand = lib[cid]
        cfg = EngineConfig(
            symbol="XAUUSDm",
            starting_balance=105.74,
            sizing_mode="fixed",
            fixed_lots=0.01,
            dedup_per_candle=True,
            max_concurrent=1,
            max_same_direction=1,
            enable_pyramiding=False,
            enable_consolidation_exit=False,
            enable_trailing=False,
            history_bars=900,
            warmup_bars=950,
            daily_loss_limit_mode="balance_pct",
            daily_loss_limit_pct=0.06,
            tp_atr_mult=cand.tp_atr,
        )
        strat = CandidateStrategy(cand, magic=3200 + int(cid.split("-")[1]))
        engine = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        result = engine.run([strat], start_ts=_ts("2025-04-03"), end_ts=_ts("2026-08-29"))
        stats = _stats(result.trades, cfg.starting_balance)
        all_results[cid] = {"name": cand.name, "config": {"tp_atr": cand.tp_atr,
                             "sl_atr": cand.sl_atr, "session": list(cand.session)},
                             "in_sample": stats}

        pf_s = "inf" if stats.get("profit_factor") == float("inf") else f"{stats.get('profit_factor', 0):.3f}"
        if stats["trades"] == 0:
            print(f"{cid:<9}{cand.name:<44}{'0':>6}  NO TRADES")
        else:
            print(f"{cid:<9}{cand.name:<44}{stats['trades']:>6}{stats['win_rate']:>7.1f}"
                  f"{pf_s:>8}{stats['net_pl']:>10,.0f}{stats['end_balance']:>10,.0f}"
                  f"{stats['min_balance']:>9,.0f}{stats['max_dd_pct_of_peak']:>9.1f}"
                  f"{stats['daily_limit_breaches']:>6}", flush=True)

        with open(os.path.join(out_dir, f"trades_{cid}.json"), "w", encoding="utf-8") as fh:
            json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)

    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"data_hash": bars.hash_key(), "results": all_results}, fh, indent=2, default=str)
    print(f"\nwritten to {out_dir}")


if __name__ == "__main__":
    run()
