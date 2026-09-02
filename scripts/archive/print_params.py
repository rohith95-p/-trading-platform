import sys
sys.path.append(r"c:\projects\ultra_core")
import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timezone, timedelta
from src.strategies.morning_momentum import MorningMomentum

if not mt5.initialize():
    quit()

rates15 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 100)
rates5 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M5, 0, 100)

IST = timezone(timedelta(hours=5, minutes=30))

print("=== ASIAN SWEEP PARAMETERS ===")
asian_high = -np.inf
asian_low = np.inf
found_candles = 0
latest_time = datetime.fromtimestamp(int(rates15[-2]["time"]), tz=timezone.utc).astimezone(IST)
today_date = latest_time.date()

for i in range(len(rates15) - 1, max(-1, len(rates15) - 50), -1):
    dt = datetime.fromtimestamp(int(rates15[i]["time"]), tz=timezone.utc).astimezone(IST)
    if dt.date() != today_date:
        continue
    h_tv = dt.hour + dt.minute / 60.0
    if 5.5 <= h_tv < 11.5:
        found_candles += 1
        asian_high = max(asian_high, float(rates15[i]["high"]))
        asian_low = min(asian_low, float(rates15[i]["low"]))

print(f"Session Active (9:00 - 21:30 IST): {'YES' if 9.0 <= (latest_time.hour + latest_time.minute/60.0) < 21.5 else 'NO'}")
print(f"Asian Candles Found: {found_candles} (Needs >= 4)")
if found_candles >= 4:
    asian_range = asian_high - asian_low
    print(f"Asian High: {asian_high:.3f}")
    print(f"Asian Low: {asian_low:.3f}")
    print(f"Asian Range Size: {asian_range:.3f} (Needs between 5 and 35)")
    
    closes = rates15["close"]
    highs = rates15["high"]
    lows = rates15["low"]
    
    print("\nBUY SWEEP CHECK:")
    print(f"  Candle N-1 Low < Asian Low: {lows[-3] < asian_low} ({lows[-3]:.3f} < {asian_low:.3f})")
    print(f"  Candle N-1 Close < Asian Low: {closes[-3] < asian_low} ({closes[-3]:.3f} < {asian_low:.3f})")
    print(f"  Candle N Close > Asian Low: {closes[-2] > asian_low} ({closes[-2]:.3f} > {asian_low:.3f})")
    
    print("\nSELL SWEEP CHECK:")
    print(f"  Candle N-1 High > Asian High: {highs[-3] > asian_high} ({highs[-3]:.3f} > {asian_high:.3f})")
    print(f"  Candle N-1 Close > Asian High: {closes[-3] > asian_high} ({closes[-3]:.3f} > {asian_high:.3f})")
    print(f"  Candle N Close < Asian High: {closes[-2] < asian_high} ({closes[-2]:.3f} < {asian_high:.3f})")

print("\n=== MORNING MOMENTUM PARAMETERS ===")
mm = MorningMomentum()
closes = rates15["close"]
ema20 = mm.ema(closes, 20)
rsi = mm.rsi(closes, 14)

curr_close = closes[-2]
prev_high = rates15["high"][-3]
prev_low = rates15["low"][-3]
curr_high = rates15["high"][-2]
curr_low = rates15["low"][-2]
curr_ema = ema20[-2]
curr_rsi = rsi[-2]

volumes = rates5["tick_volume"].astype(float)
curr_vol = volumes[-2]
avg_vol = np.mean(volumes[-21:-1])

print(f"1. TREND (Close vs EMA20): Close={curr_close:.3f}, EMA={curr_ema:.3f}")
print(f"   - Is BUY Trend: {'YES' if curr_close > curr_ema else 'NO'}")
print(f"   - Is SELL Trend: {'YES' if curr_close < curr_ema else 'NO'}")

print(f"2. BREAKOUT:")
print(f"   - Is BUY Breakout (Curr High > Prev High): {'YES' if curr_high > prev_high else 'NO'} ({curr_high:.3f} > {prev_high:.3f})")
print(f"   - Is SELL Breakout (Curr Low < Prev Low): {'YES' if curr_low < prev_low else 'NO'} ({curr_low:.3f} < {prev_low:.3f})")

print(f"3. VOLUME (M5 Tick Vol > 20-per Avg):")
print(f"   - Current Vol={curr_vol:.1f}, Avg Vol={avg_vol:.1f}")
print(f"   - Is Volume OK: {'YES' if curr_vol > avg_vol else 'NO'}")

print(f"4. MOMENTUM (RSI 14): {curr_rsi:.2f}")
print(f"   - Is BUY Momentum (50-65): {'YES' if 50 <= curr_rsi <= 65 else 'NO'}")
print(f"   - Is SELL Momentum (35-50): {'YES' if 35 <= curr_rsi <= 50 else 'NO'}")

mt5.shutdown()
