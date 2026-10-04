import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from scripts.validation.part1_suite import run_window, stats, live_config
from src.backtesting.data import load_bars
from src.strategies.portfolio_v5_6_leg import PORTFOLIO

import multiprocessing

def run_combination(args):
    sl, tp, start_date, end_date = args
    if tp / sl < 1.0:
        return None
        
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    
    # Monkey patch locally in this process
    for strat_cls in PORTFOLIO:
        strat_cls.sl_atr_mult = sl
        strat_cls.tp_atr_mult = tp
        
    strategies = [cls() for cls in PORTFOLIO]
    res = run_window(bars, live_config(), start_date, end_date, strategies)
    
    if res and res.trades:
        res_stats = stats(res.trades)
        pf = res_stats['profit_factor']
        win_rate = res_stats['win_rate']
        max_dd = res_stats['max_drawdown_pct']
        net_pl = res_stats['net']
        n_trades = res_stats['n']
        return (sl, tp, n_trades, win_rate, pf, max_dd, net_pl)
    return (sl, tp, 0, 0.0, 0.0, 0.0, 0.0)

def main():
    print("Preparing parallel sweep...")
    sl_values = [0.1, 0.3, 0.5, 1.0]
    tp_values = [1.0, 1.5, 2.0, 3.0]
    start_date = "2026-06-01"
    end_date = "2026-09-27"
    
    combos = [(sl, tp, start_date, end_date) for sl in sl_values for tp in tp_values if tp/sl >= 1.0]
    
    print("\nStarting Parameter Sweep...")
    print(f"{'SL':<5} | {'TP':<5} | {'Trades':<8} | {'Win Rate':<10} | {'PF':<8} | {'Max DD':<8} | {'Net P&L':<10}")
    print("-" * 65)
    
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        for result in pool.imap_unordered(run_combination, combos):
            if result:
                sl, tp, n_trades, win_rate, pf, max_dd, net_pl = result
                print(f"{sl:<5} | {tp:<5} | {n_trades:<8} | {win_rate:>8.1f}% | {pf:>8.3f} | {max_dd:>7.1f}% | ${net_pl:>8.2f}")

if __name__ == '__main__':
    main()
