import json
import numpy as np
from src.strategies.portfolio_v4 import FVGNYTight
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    bars = _bars()
    start_date = "2026-08-01"
    end_date = "2026-09-01"

    print("--- ONLY FVG_NY_TIGHT (D1 Gate ON) ---")
    cfg = live_config(enable_d1_bias_gate=True)
    strategies = [FVGNYTight()]
    res = run_window(bars, cfg, start_date, end_date, strategies)
    print(json.dumps(stats(res.trades), indent=2))

if __name__ == "__main__":
    main()
