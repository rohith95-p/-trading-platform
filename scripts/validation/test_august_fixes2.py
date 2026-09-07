import json
import numpy as np
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    bars = _bars()
    start_date = "2026-08-01"
    end_date = "2026-09-01"

    print("--- Variant 1: D1 Gate ON ---")
    cfg1 = live_config(enable_d1_bias_gate=True)
    strategies1 = [cls() for cls in PORTFOLIO_V4]
    res1 = run_window(bars, cfg1, start_date, end_date, strategies1)
    print(json.dumps(stats(res1.trades), indent=2))

    print("\n--- Variant 2: Wider Stops (SL=1.0, TP=3.0) ---")
    cfg2 = live_config()
    strategies2 = []
    for cls in PORTFOLIO_V4:
        inst = cls()
        inst.sl_atr_mult = 1.0
        inst.tp_atr_mult = 3.0
        strategies2.append(inst)
    res2 = run_window(bars, cfg2, start_date, end_date, strategies2)
    print(json.dumps(stats(res2.trades), indent=2))

if __name__ == "__main__":
    main()
