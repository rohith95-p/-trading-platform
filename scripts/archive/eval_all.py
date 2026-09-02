import sys
sys.path.append(r"c:\projects\ultra_core")
import MetaTrader5 as mt5
import importlib
import pkgutil
import inspect

import src.strategies
from src.strategies.base_strategy import BaseStrategy

if not mt5.initialize():
    quit()

rates15 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 100)
rates5 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M5, 0, 100)

print("=== EVALUATING ALL STRATEGIES ===")

for loader, module_name, is_pkg in pkgutil.walk_packages(src.strategies.__path__):
    if module_name in ['base_strategy']:
        continue
    full_module_name = f"src.strategies.{module_name}"
    module = importlib.import_module(full_module_name)
    
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
            try:
                strategy = obj()
                sig = strategy.evaluate(rates15, rates5)
                print(f"{strategy.name.ljust(20)} : {'NO SIGNAL' if sig is None else ('BUY' if sig.is_buy else 'SELL')}")
            except Exception as e:
                print(f"{name.ljust(20)} : ERROR {e}")

mt5.shutdown()
