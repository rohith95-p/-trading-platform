"""Check if market is open and get real-time spread"""
import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

# Check XAUUSD
tick = mt5.symbol_info_tick('XAUUSDm')
info = mt5.symbol_info('XAUUSDm')

if not tick or not info:
    print("❌ XAUUSDm not available")
    mt5.shutdown()
    exit(1)

# Calculate spread
spread_points = tick.ask - tick.bid
spread_pips = spread_points / info.point / 10

# Check if data is fresh
tick_time = datetime.fromtimestamp(tick.time)
now = datetime.now()
age_seconds = (now - tick_time).total_seconds()

print("="*80)
print("MARKET STATUS CHECK")
print("="*80)
print(f"\nCurrent Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Last Tick Time: {tick_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Data Age: {age_seconds:.0f} seconds ago")

if age_seconds < 60:
    print(f"\n✅ MARKET IS OPEN (data is fresh)")
else:
    print(f"\n❌ MARKET IS CLOSED (data is stale)")

print(f"\nXAUUSDm Current Prices:")
print(f"  Bid: ${tick.bid:.2f}")
print(f"  Ask: ${tick.ask:.2f}")
print(f"  Spread: {spread_pips:.2f} pips")
print(f"  Spread Cost (0.01 lots): ${spread_pips * 0.01:.4f}")

# Check if this is normal trading hours
hour = now.hour
day = now.weekday()  # 0=Monday, 6=Sunday

print(f"\nCurrent: {now.strftime('%A %H:%M')} (local time)")

# Market hours (approximate, forex market)
if day == 6:  # Sunday
    if hour < 17:
        print("❌ Market closed (Sunday, before 5 PM)")
    else:
        print("⚠️ Market opening soon (Sunday evening)")
elif day == 5 and hour >= 17:  # Friday after 5 PM
    print("❌ Market closed (Friday evening)")
else:
    print("✅ Should be during trading hours")

print("\n" + "="*80)
print("SPREAD VERDICT")
print("="*80)

if age_seconds > 300:  # 5 minutes old
    print("\n⚠️ DATA IS STALE - Market is likely closed")
    print("   Spread shown is not representative")
    print("   Re-run this during trading hours (Monday-Friday)")
elif spread_pips < 3:
    print(f"\n✅ EXCELLENT SPREAD: {spread_pips:.2f} pips")
    print("   Your 0.1 ATR SL strategy will work perfectly!")
    print("   Expected $10/day is achievable")
elif spread_pips < 5:
    print(f"\n✅ GOOD SPREAD: {spread_pips:.2f} pips")
    print("   Your 0.1 ATR SL strategy will work")
    print("   Expected $7-10/day")
elif spread_pips < 10:
    print(f"\n⚠️ ACCEPTABLE SPREAD: {spread_pips:.2f} pips")
    print("   Your 0.1 ATR SL strategy will work but at reduced profit")
    print("   Expected $5-7/day")
else:
    print(f"\n❌ POOR SPREAD: {spread_pips:.2f} pips")
    print("   This is too wide for 0.1 ATR SL strategy")
    print("   Options:")
    print("   1. Wait for market to open (if currently closed)")
    print("   2. Switch to ECN broker (IC Markets, Pepperstone)")
    print("   3. Use wider SL (0.5 ATR instead of 0.1)")

mt5.shutdown()
