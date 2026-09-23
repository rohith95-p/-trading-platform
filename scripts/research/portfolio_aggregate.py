"""
Script to test the new updated portfolio over the last week and month.
Outputs aggregate metrics and a flat list of every trade.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import START_BAL

def run_evaluation(start_date, end_date, label, bars):
    print(f"\n{'='*70}")
    print(f"EVALUATION: {label} ({start_date} -> {end_date})")
    print(f"Portfolio Legs: {[cls().name for cls in PORTFOLIO_V4]}")
    print(f"{'='*70}")
    
    # Instantiate portfolio legs
    legs = [cls() for cls in PORTFOLIO_V4]
    
    # Engine config for 0.02 lots as requested
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=0.02,
        dedup_per_candle=True, max_concurrent=len(PORTFOLIO_V4), max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20"
    )
    
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    
    start_ts = int(pd.to_datetime(start_date).timestamp())
    end_ts = int(pd.to_datetime(end_date).timestamp())
    
    res = eng.run(legs, start_ts=start_ts, end_ts=end_ts)
    
    if not res.trades:
        print("No trades found in this period.")
        return
        
    print("\n--- ALL TRADES ---")
    for i, t in enumerate(res.trades, 1):
        entry_time = pd.to_datetime(t.entry_time, unit='s').strftime('%Y-%m-%d %H:%M')
        exit_time = pd.to_datetime(t.exit_time, unit='s').strftime('%Y-%m-%d %H:%M')
        direction = "BUY " if t.is_buy else "SELL"
        res_str = "WIN " if t.net_pl > 0 else "LOSS"
        print(f"[{t.strategy}] {direction} @ {entry_time} -> {exit_time} | {res_str} | PnL: ${t.net_pl:.2f}")
        
    # Metrics
    pnls = np.array([t.net_pl for t in res.trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    
    win_rate = len(wins) / len(pnls) * 100
    loss_rate = len(losses) / len(pnls) * 100
    net_profit = pnls.sum()
    end_balance = START_BAL + net_profit
    
    # Equity curve and DD
    equity_curve = START_BAL + np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (running_max - equity_curve) / running_max
    max_dd = np.max(drawdowns) * 100 if len(drawdowns) > 0 else 0
    least_balance = np.min(equity_curve) if len(equity_curve) > 0 else START_BAL
    
    print("\n--- AGGREGATE METRICS ---")
    print(f"Total Trades:  {len(pnls)}")
    print(f"Win Rate:      {win_rate:.1f}%")
    print(f"Loss Rate:     {loss_rate:.1f}%")
    print(f"Total Losses:  ${abs(losses.sum()):.2f}")
    print(f"Total Wins:    ${wins.sum():.2f}")
    print(f"Net Profit:    ${net_profit:.2f}")
    print(f"Start Balance: ${START_BAL:.2f}")
    print(f"End Balance:   ${end_balance:.2f}")
    print(f"Least Balance: ${least_balance:.2f} (Lowest Point)")
    print(f"Max Drawdown:  {max_dd:.2f}%")

def main():
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    
    # This month (Aug 24 to Sep 24)
    run_evaluation("2026-08-24", "2026-09-24", "THIS MONTH", bars)
    
    # This week (Sep 17 to Sep 24)
    run_evaluation("2026-09-17", "2026-09-24", "THIS WEEK", bars)

if __name__ == "__main__":
    main()
