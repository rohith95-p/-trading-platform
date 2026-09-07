import json
import sys
import numpy as np
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    print("Loading bars...", flush=True)
    bars = _bars()
    
    start_date = "2025-09-01"
    end_date = "2026-09-01"
    
    print(f"Running 1-year backtest from {start_date} to {end_date}...", flush=True)

    # Use D1 gate ON as we just fixed it
    cfg = live_config(enable_d1_bias_gate=True)
    strategies = [cls() for cls in PORTFOLIO_V4]
    
    res = run_window(bars, cfg, start_date, end_date, strategies)
    
    print("\nCOMBINED RESULT (1 Year):")
    print(json.dumps(stats(res.trades), indent=2))
    
    print("\nPer-leg breakdown:")
    for cls in PORTFOLIO_V4:
        leg_trades = [t for t in res.trades if t.strategy == cls.name]
        leg_st = stats(leg_trades)
        pf = leg_st.get("profit_factor", 0.0)
        net = leg_st.get("net", 0.0)
        n = leg_st.get("n", 0)
        print(f"  {cls.name:25} n={n:4} PF={pf:.3f} net=${net:.2f}")

if __name__ == "__main__":
    main()
