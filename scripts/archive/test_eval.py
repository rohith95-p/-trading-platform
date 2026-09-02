import sys
import os
sys.path.append(r"c:\projects\ultra_core")
import MetaTrader5 as mt5
import numpy as np
from src.strategies.asian_sweep import AsianSweep
from src.strategies.morning_momentum import MorningMomentum

if not mt5.initialize():
    quit()

rates15 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M15, 0, 100)
rates5 = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M5, 0, 100)

asian = AsianSweep()
momentum = MorningMomentum()

print("Evaluating Asian Sweep...")
sig_a = asian.evaluate(rates15, rates5)
print(f"Asian Sweep Signal: {sig_a}")

print("Evaluating Morning Momentum...")
sig_m = momentum.evaluate(rates15, rates5)
print(f"Morning Momentum Signal: {sig_m}")

mt5.shutdown()
