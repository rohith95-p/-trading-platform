import MetaTrader5 as mt5
import datetime

if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()
    quit()

print("Terminal Info:", mt5.terminal_info())
print("Time Current (Broker Time):", mt5.symbol_info_tick("XAUUSDm").time)
print("Time Current (as datetime):", datetime.datetime.fromtimestamp(mt5.symbol_info_tick("XAUUSDm").time))
mt5.shutdown()
