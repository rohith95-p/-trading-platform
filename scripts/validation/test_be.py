import json
import numpy as np
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    bars = _bars()
    # Test with BE trigger
    cfg = live_config(be_trigger_atr=2.0, be_offset_atr=0.2)
    
    start_date = "2026-08-01"
    end_date = "2026-09-01"

    print("Running August 2026 with Breakeven Trigger = 2.0 ATR, offset = 0.2 ATR")
    strategies = [cls() for cls in PORTFOLIO_V4]
    res = run_window(bars, cfg, start_date, end_date, strategies)
    
    s = stats(res.trades)
    print(json.dumps(s, indent=2))

if __name__ == "__main__":
    main()
