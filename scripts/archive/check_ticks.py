import MetaTrader5 as mt5
import pandas as pd

if not mt5.initialize():
    print("initialize() failed")
    quit()

rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 5)
if rates is None:
    print("No rates found for XAUUSDm")
else:
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print("Latest 5 M15 candles:")
    print(df[['time', 'open', 'high', 'low', 'close', 'tick_volume']])

tick = mt5.symbol_info_tick("XAUUSDm")
if tick:
    print(f"\nLatest tick time: {pd.to_datetime(tick.time, unit='s')}")
    print(f"Bid: {tick.bid}, Ask: {tick.ask}")

mt5.shutdown()
