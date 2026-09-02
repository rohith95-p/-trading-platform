"""
Comprehensive Strategy Audit & Backtest Script.

This script:
1. Audits all 9 strategies for code correctness (volume source, spread, timeframe usage)
2. Backtests the 2 NEW strategies (EMA_CROSSOVER, MACD_SCALPER) on 30 days of M15 data
3. Also backtests the existing 7 for comparison
4. Reports win rate, total P/L, number of signals, avg risk/reward

Uses LIVE MT5 historical data.
"""

import sys
sys.path.append(r"c:\projects\ultra_core")

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from src.strategies.morning_momentum import MorningMomentum
from src.strategies.ema_pullback import EMAPullback
from src.strategies.asian_sweep import AsianSweep
from src.strategies.fvg_continuation import FVGContinuation
from src.strategies.bollinger_bounce import BollingerBounce
from src.strategies.trend_sniper import TrendSniper
from src.strategies.ema_crossover_rider import EMACrossoverRider
from src.strategies.macd_rsi_scalper import MACDMomentumScalper
from src.core.risk_agent import RiskAgent

IST = timezone(timedelta(hours=5, minutes=30))

if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

# =========================================================================
# PART 1: CODE AUDIT
# =========================================================================
print("=" * 70)
print("PART 1: STRATEGY CODE AUDIT")
print("=" * 70)

ALL_STRATEGIES = [
    MorningMomentum, EMAPullback, AsianSweep, FVGContinuation,
    BollingerBounce, TrendSniper,
    EMACrossoverRider, MACDMomentumScalper,
]

# Check symbol info for spread
info = mt5.symbol_info("XAUUSDm")
if info:
    print(f"\nSymbol: XAUUSDm")
    print(f"  Spread: {info.spread} points")
    print(f"  Point: {info.point}")
    print(f"  Spread in price: {info.spread * info.point:.3f}")
    print(f"  Volume Min: {info.volume_min}, Max: {info.volume_max}, Step: {info.volume_step}")
    print(f"  Trade Tick Size: {info.trade_tick_size}, Tick Value: {info.trade_tick_value}")

print("\n--- Volume Source Audit ---")
import inspect

for StratClass in ALL_STRATEGIES:
    source = inspect.getsource(StratClass.evaluate)
    uses_m5 = "m5_rates" in source and 'volumes = m5_rates' in source
    uses_m15 = 'volumes = m15_rates' in source
    
    vol_source = "M5" if uses_m5 else ("M15" if uses_m15 else "UNKNOWN")
    
    # Check if there's a volume factor/threshold
    vol_factor = "1.0x (strict)" 
    if "0.8" in source:
        vol_factor = "0.8x (relaxed)"
    
    # Check spread handling
    handles_spread = "spread" in source.lower()
    
    strat = StratClass()
    print(f"  {strat.name:20s} | Vol Source: {vol_source:4s} | Vol Threshold: {vol_factor:15s} | Spread Check: {'YES' if handles_spread else 'NO'}")

print("\n--- Timeframe Usage Audit ---")
for StratClass in ALL_STRATEGIES:
    source = inspect.getsource(StratClass.evaluate)
    strat = StratClass()
    uses_index_m2 = "[-2]" in source  # Uses completed candle (correct)
    uses_index_m1 = "[-1]" in source and "len(m15_rates) - 1" not in source  # Uses forming candle (risky)
    
    candle_usage = "Completed [-2]" if uses_index_m2 else "UNKNOWN"
    if uses_index_m1:
        candle_usage += " + FORMING [-1] WARNING"
    
    print(f"  {strat.name:20s} | Candle: {candle_usage}")


# =========================================================================
# PART 2: BACKTEST ON 30 DAYS OF DATA
# =========================================================================
print("\n" + "=" * 70)
print("PART 2: BACKTEST (30 Days of M15 Data)")
print("=" * 70)

# Fetch 30 days of M15 data (~2880 candles) and M5 data (~8640 candles)
m15_rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 3000)
m5_rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M5, 0, 9000)

if m15_rates is None or m5_rates is None:
    print("ERROR: Could not fetch historical data")
    mt5.shutdown()
    quit()

print(f"M15 candles fetched: {len(m15_rates)}")
print(f"M5 candles fetched: {len(m5_rates)}")

m15_df = pd.DataFrame(m15_rates)
m15_df['datetime'] = pd.to_datetime(m15_df['time'], unit='s')
print(f"Date range: {m15_df['datetime'].iloc[0]} to {m15_df['datetime'].iloc[-1]}")

# Spread cost per trade (round trip)
spread_cost = info.spread * info.point if info else 0.26  # ~$2.60 spread for 0.01 lot

# ATR-based SL/TP calculation
def get_atr_at_index(rates, idx, period=14):
    if idx < period + 1:
        return None
    subset = rates[max(0, idx - period - 5):idx + 1]
    atr = RiskAgent.calc_atr(subset, period)
    valid = atr[~np.isnan(atr)]
    return float(valid[-1]) if len(valid) > 0 else None

# Walk-forward backtest
results = defaultdict(lambda: {
    "signals": 0, "wins": 0, "losses": 0, "total_pl": 0.0,
    "trades": [], "win_streaks": [], "loss_streaks": []
})

for StratClass in ALL_STRATEGIES:
    strat = StratClass()
    strat_name = strat.name
    
    # Walk through each candle
    window_size = 250  # Strategy requires at least 200-250 candles
    
    for i in range(window_size, len(m15_rates) - 5):  # -5 to have room for outcome
        # Create a slice of data up to candle i
        m15_slice = m15_rates[:i + 1]
        
        # Find corresponding M5 data (approximate: 3 M5 candles per M15)
        m5_end_idx = min(i * 3, len(m5_rates) - 1)
        m5_start_idx = max(0, m5_end_idx - 100)
        m5_slice = m5_rates[m5_start_idx:m5_end_idx + 1]
        
        try:
            signal = strat.evaluate(m15_slice, m5_slice)
        except Exception:
            continue
        
        if signal is None:
            continue
        
        results[strat_name]["signals"] += 1
        
        # Simulate trade outcome using ATR-based SL/TP
        entry_price = float(m15_rates[i]["close"])
        atr = get_atr_at_index(m15_rates, i)
        if atr is None:
            continue
        
        sl_dist = 1.5 * atr
        tp_dist = 3.0 * atr
        
        if signal.is_buy:
            sl = entry_price - sl_dist
            tp = entry_price + tp_dist
        else:
            sl = entry_price + sl_dist
            tp = entry_price - tp_dist
        
        # Walk forward to see outcome
        hit_tp = False
        hit_sl = False
        
        for j in range(i + 1, min(i + 20, len(m15_rates))):  # Max 20 candles (5 hours)
            candle_high = float(m15_rates[j]["high"])
            candle_low = float(m15_rates[j]["low"])
            
            if signal.is_buy:
                if candle_low <= sl:
                    hit_sl = True
                    break
                if candle_high >= tp:
                    hit_tp = True
                    break
            else:
                if candle_high >= sl:
                    hit_sl = True
                    break
                if candle_low <= tp:
                    hit_tp = True
                    break
        
        if hit_tp:
            pl = tp_dist - spread_cost
            results[strat_name]["wins"] += 1
            results[strat_name]["total_pl"] += pl
            results[strat_name]["trades"].append(("WIN", pl))
        elif hit_sl:
            pl = -(sl_dist + spread_cost)
            results[strat_name]["losses"] += 1
            results[strat_name]["total_pl"] += pl
            results[strat_name]["trades"].append(("LOSS", pl))
        else:
            # Timed out — close at last candle price
            exit_price = float(m15_rates[min(i + 20, len(m15_rates) - 1)]["close"])
            if signal.is_buy:
                pl = (exit_price - entry_price) - spread_cost
            else:
                pl = (entry_price - exit_price) - spread_cost
            
            if pl > 0:
                results[strat_name]["wins"] += 1
            else:
                results[strat_name]["losses"] += 1
            results[strat_name]["total_pl"] += pl
            results[strat_name]["trades"].append(("TIMEOUT", pl))

# =========================================================================
# PART 3: RESULTS
# =========================================================================
print("\n" + "=" * 70)
print("BACKTEST RESULTS (30 Days, ATR SL=1.5x, TP=3.0x)")
print("=" * 70)
print(f"{'Strategy':20s} | {'Signals':>8s} | {'Wins':>5s} | {'Losses':>6s} | {'Win Rate':>8s} | {'Total P/L':>10s} | {'Avg P/L':>8s}")
print("-" * 85)

for strat_name in sorted(results.keys()):
    r = results[strat_name]
    total = r["wins"] + r["losses"]
    wr = (r["wins"] / total * 100) if total > 0 else 0
    avg_pl = (r["total_pl"] / total) if total > 0 else 0
    
    # Color coding via markers
    marker = "PASS" if wr >= 50 else "WARN" if wr >= 40 else "FAIL"
    
    print(f"{strat_name:20s} | {r['signals']:>8d} | {r['wins']:>5d} | {r['losses']:>6d} | {wr:>7.1f}% | ${r['total_pl']:>9.2f} | ${avg_pl:>7.2f} [{marker}]")

# New strategies specifically
print("\n--- NEW STRATEGIES VERDICT ---")
for name in ["EMA_CROSSOVER", "MACD_SCALPER"]:
    if name in results:
        r = results[name]
        total = r["wins"] + r["losses"]
        wr = (r["wins"] / total * 100) if total > 0 else 0
        if wr >= 45 and total >= 5:
            print(f"  {name}: PASS (Win Rate: {wr:.1f}%, {total} trades) -- SAFE TO DEPLOY")
        elif total < 5:
            print(f"  {name}: INSUFFICIENT DATA ({total} trades) -- NEEDS PARAMETER TUNING")
        else:
            print(f"  {name}: FAIL (Win Rate: {wr:.1f}%, {total} trades) -- DO NOT DEPLOY")
    else:
        print(f"  {name}: NO SIGNALS GENERATED -- NEEDS INVESTIGATION")

mt5.shutdown()
print("\nBacktest complete.")
