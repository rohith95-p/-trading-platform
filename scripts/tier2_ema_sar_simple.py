"""Tier-2 engine validation of EMA SAR (simple) candidate at 0.01 fixed lots.

This is the simpler SAR variant (EMA200 filter + SAR flip, no ADX/ChoCh/volume)
that ranked #11 in the 120-candidate screen with 1,451 trades and edge_z +1.88.

    python -m scripts.tier2_ema_sar_simple

Runs on:
- In-sample: 2025-04-03 to 2026-08-29
- Locked holdout: 2022-06-08 to 2025-04-02 (only if in-sample is positive)

Uses the tier-2 full engine (M1 sub-bar walk, realistic costs, actual RiskManager).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars, SymbolSpec
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import CostModel
from src.research.candidates import Candidate, LONDON_NY, _c_ema_sar_simple
from src.research.market_study import build_features


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


class EmasarSimpleStrategy:
    """Tier-2 live-compatible wrapper around the tier-1 screening rule."""

    name = "EMASAR_SIMPLE"
    magic = 3003

    def __init__(self):
        pass

    def evaluate(self, m15_rates, m5_rates=None):
        if m15_rates is None or len(m15_rates) < 220:
            return None

        f = build_features(m15_rates)
        signals = _c_ema_sar_simple(f).astype(int)

        if signals[-2] == 0:
            return None

        from src.strategies.base_strategy import Signal, mt5
        if signals[-2] > 0:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        else:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                          magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


def run_test() -> None:
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    print(f"Data hash: {bars.hash_key()}\n")

    # --- In-sample: 2025-04-03 to 2026-08-29 ---
    print("=" * 86)
    print("  TIER-2 IN-SAMPLE (2025-04-03 to 2026-08-29)")
    print("=" * 86)

    t_start_is = _ts("2025-04-03")
    t_end_is = _ts("2026-08-29")

    config_is = EngineConfig(
        symbol="XAUUSDm",
        starting_balance=105.74,
        history_bars=250,
        loop_interval_sec=60,
        dedup_per_candle=True,
        max_concurrent=3,
        spread_gate_blocks_management=True,
        sizing_mode="fixed",
        fixed_lots=0.01,
        risk_pct=0.15,
    )

    cost = CostModel(spread_source="bar")
    engine_is = BacktestEngine(bars=bars, cost=cost, config=config_is)
    result_is = engine_is.run([EmasarSimpleStrategy()], start_ts=t_start_is, end_ts=t_end_is)

    print(f"  Trades: {len(result_is.trades)}")
    if result_is.trades:
        rs = np.array([t.r_multiple for t in result_is.trades])
        wins = (rs > 0).sum()
        wr = wins / len(rs) * 100
        exp = rs.mean()
        gross = sum(t.gross_pl for t in result_is.trades)
        loss = sum(-t.gross_pl for t in result_is.trades if t.gross_pl < 0)
        pf = gross / loss if loss > 0 else float("inf")
        dd = float((np.maximum.accumulate(np.concatenate([[0], np.cumsum(rs)])) -
                   np.concatenate([[0], np.cumsum(rs)])).max())

        print(f"  Win rate: {wr:.1f}% ({wins}/{len(rs)})")
        print(f"  Expectancy: {exp:+.4f}R")
        print(f"  Profit factor: {pf:.3f}")
        print(f"  Total P/L (R): {rs.sum():+.1f}")
        print(f"  Max drawdown: {dd:.1f}R")

        if exp > 0:
            # --- Locked holdout: only if in-sample is positive ---
            print("\n" + "=" * 86)
            print("  TIER-2 LOCKED HOLDOUT (2022-06-08 to 2025-04-02)")
            print("=" * 86)

            t_start_ho = _ts("2022-06-08")
            t_end_ho = _ts("2025-04-02")

            engine_ho = BacktestEngine(bars=bars, cost=cost, config=config_is)
            result_ho = engine_ho.run([EmasarSimpleStrategy()], start_ts=t_start_ho, end_ts=t_end_ho)

            print(f"  Trades: {len(result_ho.trades)}")
            if result_ho.trades:
                rs_ho = np.array([t.r_multiple for t in result_ho.trades])
                wins_ho = (rs_ho > 0).sum()
                wr_ho = wins_ho / len(rs_ho) * 100
                exp_ho = rs_ho.mean()
                gross_ho = sum(t.gross_pl for t in result_ho.trades)
                loss_ho = sum(-t.gross_pl for t in result_ho.trades if t.gross_pl < 0)
                pf_ho = gross_ho / loss_ho if loss_ho > 0 else float("inf")
                dd_ho = float((np.maximum.accumulate(np.concatenate([[0], np.cumsum(rs_ho)])) -
                              np.concatenate([[0], np.cumsum(rs_ho)])).max())

                print(f"  Win rate: {wr_ho:.1f}% ({wins_ho}/{len(rs_ho)})")
                print(f"  Expectancy: {exp_ho:+.4f}R")
                print(f"  Profit factor: {pf_ho:.3f}")
                print(f"  Total P/L (R): {rs_ho.sum():+.1f}")
                print(f"  Max drawdown: {dd_ho:.1f}R")

            else:
                print("  NO TRADES in holdout")
        else:
            print("\n  In-sample negative; skipping holdout.")
    else:
        print("  NO TRADES in in-sample window")


if __name__ == "__main__":
    run_test()
