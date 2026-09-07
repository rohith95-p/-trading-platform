import json
import numpy as np
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    bars = _bars()
    
    # Variant 1: Breakeven at +1.0 ATR (2R)
    cfg1 = live_config(be_trigger_atr=1.0, be_offset_atr=0.1)
    
    # Variant 2: Trailing stop
    cfg2 = live_config(enable_trailing=True)
    
    start_date = "2026-08-01"
    end_date = "2026-09-01"
    strategies = [cls() for cls in PORTFOLIO_V4]

    print("--- Variant 1: Breakeven at 1.0 ATR (2R) ---")
    res1 = run_window(bars, cfg1, start_date, end_date, strategies)
    print(json.dumps(stats(res1.trades), indent=2))
    
    print("\n--- Variant 2: Trailing Stop ON ---")
    # need fresh strategy objects!
    strategies2 = [cls() for cls in PORTFOLIO_V4]
    res2 = run_window(bars, cfg2, start_date, end_date, strategies2)
    print(json.dumps(stats(res2.trades), indent=2))

if __name__ == "__main__":
    main()
