"""
Test NVMR_sl0.4_tp1.5 from Aug 20 to Sep 20 and print all trade logs.
"""
import numpy as np
from datetime import datetime
import pandas as pd

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.bible_strategies import NVMRStrategy
from scripts.validation.part1_suite import _ts, START_BAL

# User requested window (2 months)
START_DATE = "2026-07-24"
END_DATE = "2026-09-24"
LOT_SIZE = 0.02

def main():
    print(f"=== RECENT PERFORMANCE TEST: {START_DATE} to {END_DATE} ===")
    print(f"Strategy: NVMR | SL: 0.4x ATR | TP: 1.5x ATR")
    print(f"Lot Size: {LOT_SIZE}")
    print("========================================================\n")
    
    # 1. Setup Strategy
    s = NVMRStrategy()
    s.sl_atr_mult = 0.4
    s.tp_atr_mult = 1.5
    s.name = "NVMR_sl0.4_tp1.5"
    s.magic = 9999
    
    # 2. Setup Engine
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=LOT_SIZE,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20"
    )
    
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    
    # 3. Run
    res = eng.run([s], start_ts=_ts(START_DATE), end_ts=_ts(END_DATE))
    
    # 4. Print Trades
    print("--- TRADE LOGS ---")
    if not res.trades:
        print("No trades taken in this window.")
    else:
        for i, t in enumerate(res.trades, 1):
            entry_time = pd.to_datetime(t.entry_time, unit='s').strftime('%Y-%m-%d %H:%M')
            exit_time = pd.to_datetime(t.exit_time, unit='s').strftime('%Y-%m-%d %H:%M')
            direction = "BUY " if t.is_buy else "SELL"
            result = "WIN " if t.net_pl > 0 else "LOSS"
            
            print(f"Trade {i:02d}: {direction} @ {t.entry_price:.2f} (Time: {entry_time})")
            print(f"          EXIT @ {t.exit_price:.2f} (Time: {exit_time})")
            print(f"          Result: {result} | PnL: ${t.net_pl:.2f}")
            print(f"          SL: {t.sl:.2f} | TP: {t.tp:.2f}\n")
            
    # 5. Summary
    pnls = np.array([t.net_pl for t in res.trades])
    if len(pnls) > 0:
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        net = pnls.sum()
        pf = wins.sum() / -losses.sum() if len(losses) > 0 else float('inf')
        wr = len(wins) / len(pnls) * 100
        
        print("--- SUMMARY ---")
        print(f"Total Trades: {len(pnls)}")
        print(f"Win Rate:     {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"Profit Factor:{pf:.2f}")
        print(f"Net Earnings: ${net:.2f}")
        if len(wins) > 0:
            print(f"Avg Win:      ${np.mean(wins):.2f}")
        if len(losses) > 0:
            print(f"Avg Loss:     ${np.mean(losses):.2f}")

if __name__ == "__main__":
    main()
