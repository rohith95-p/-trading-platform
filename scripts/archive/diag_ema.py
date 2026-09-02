import sys
sys.path.append(r"c:\projects\ultra_core")

import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timezone, timedelta
from src.strategies.ema_crossover_rider import EMACrossoverRider

IST = timezone(timedelta(hours=5, minutes=30))

if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

m15_rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 100)
if m15_rates is None:
    print("Failed to get rates")
    mt5.shutdown()
    quit()

strat = EMACrossoverRider()
closes = m15_rates["close"]
ema9 = strat.ema(closes, 9)
ema21 = strat.ema(closes, 21)
ema50 = strat.ema(closes, 50)
rsi = strat.rsi(closes, 14)

curr_close = closes[-2]
curr_ema9 = ema9[-2]
curr_ema21 = ema21[-2]
prev_ema9 = ema9[-3]
prev_ema21 = ema21[-3]
curr_ema50 = ema50[-2]
curr_rsi = rsi[-2]

volumes = m15_rates["tick_volume"].astype(float)
curr_vol = volumes[-2]
avg_vol = np.mean(volumes[-21:-1])

print(f"=== CURRENT MARKET STATE (M15 Completed Candle) ===")
print(f"Close Price: {curr_close:.2f}")
print(f"EMA 9: {curr_ema9:.2f}")
print(f"EMA 21: {curr_ema21:.2f}")
print(f"EMA 50: {curr_ema50:.2f}")
print(f"RSI 14: {curr_rsi:.2f}")
print(f"Volume: {curr_vol} (Avg: {avg_vol:.2f}, Threshold: {avg_vol * 0.8:.2f})")
print("\n=== EMA CROSSOVER RIDER CONDITIONS (BUY) ===")

c1 = (prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21)
print(f"1. EMA Crossover Bullish (prev 9 <= 21 AND curr 9 > 21): {c1}")
if not c1:
    print(f"   -> Prev: 9({prev_ema9:.2f}) vs 21({prev_ema21:.2f})")
    print(f"   -> Curr: 9({curr_ema9:.2f}) vs 21({curr_ema21:.2f})")
    if curr_ema9 > curr_ema21 and prev_ema9 > prev_ema21:
        print("   -> Reason: The crossover already happened in the past. We are currently IN the trend, not at the start of it.")

c2 = (curr_close > curr_ema50)
print(f"2. Trend Filter (Close > EMA 50): {c2}")

c3 = (curr_rsi > 45)
print(f"3. RSI Momentum (RSI > 45): {c3}")

c4 = (curr_vol >= avg_vol * 0.8)
print(f"4. Volume Filter (Vol > 0.8x Avg): {c4}")

mt5.shutdown()
