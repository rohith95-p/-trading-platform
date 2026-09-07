"""Backtest for August 2026 (last month)."""
from __future__ import annotations
import json
import numpy as np

from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import (
    START_BAL, live_config, run_window, _bars, stats, verdict)

def main():
    bars = _bars()
    cfg = live_config()
    
    start_date = "2026-08-01"
    end_date = "2026-09-01"

    print(f"5-leg portfolio (Highlander + Capital Fortress)")
    print(f"Holdout {start_date} -> {end_date}, live config\n")

    strategies = [cls() for cls in PORTFOLIO_V4]
    res = run_window(bars, cfg, start_date, end_date, strategies)
    
    if not res.trades:
        print("No trades were taken during this period.")
        return
        
    s = stats(res.trades)
    
    print("COMBINED RESULT (Aug 2026):")
    print(json.dumps(s, indent=2))
    
    # Print individual trades for diagnosis
    print("\n--- August Trade Log ---")
    for t in sorted(res.trades, key=lambda x: x.entry_time):
        dt = np.datetime64(t.entry_time, 's').astype(str)
        print(f"[{dt}] {t.strategy} {'BUY ' if t.is_buy else 'SELL'} | Entry: {t.entry_price:.2f} | Exit: {t.exit_price:.2f} | Net: {t.net_pl:.2f} | MFE_R: {t.mfe_r:.2f} | Reason: {t.exit_reason}")
    
    by_leg = {}
    for t in res.trades:
        by_leg.setdefault(t.strategy, []).append(t)
    print("\nPer-leg within the combined run:")
    for name, trs in by_leg.items():
        pls = np.array([t.net_pl for t in trs])
        w, l = pls[pls > 0], pls[pls < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        print(f"  {name:<24} n={len(trs):4d} PF={pf:.3f} net=${pls.sum():.2f}")

    # Overlap check
    ny_names = {"FVG_NY_TIGHT", "FVG_NY_SWEEP", "FVG_NY_VOID", "FVG_NY_SWEEP_OR_VOID"}
    by_candle = {}
    for t in res.trades:
        if t.strategy in ny_names:
            key = t.entry_time // 900 * 900
            by_candle.setdefault(key, []).append(t.strategy)
    stacked = {k: v for k, v in by_candle.items() if len(v) > 1}
    print(f"\nNY-session entries firing on the SAME 15-min candle: {len(stacked)} candles, {sum(len(v) for v in stacked.values())} total trades stacked on them")

if __name__ == "__main__":
    main()
