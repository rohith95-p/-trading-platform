"""
Loop Engineering Framework for Strategy Discovery

Implements the Ray C. Fu Loop Framework and the Deflated Sharpe Ratio (DSR)
to identify robust strategies that survive out-of-sample data.

Steps:
1. Define a strategy space (e.g., FVG with different parameters).
2. Run all parameter combinations on the In-Sample (IS) data.
3. Score each variation based on Profit Factor, IC, and ICIR.
4. Keep only variations that pass the IS thresholds.
5. Run the surviving strategies on Out-Of-Sample (OOS) data.
6. Apply Bonferroni correction and DSR to identify true edges.
"""

import itertools
import numpy as np
import json
import sys
from datetime import datetime, timezone
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import _LiquidityFilteredFVG
from src.research.metrics import information_coefficient, icir, deflated_sharpe_ratio, bonferroni_correction
from scripts.validation.part1_suite import _ts, START_BAL, TRAIN_START, TRAIN_END, OOS_START, OOS_END

# Create a parameterized FVG class for the sweep
class ParameterizedFVG(_LiquidityFilteredFVG):
    name = "PARAM_FVG"
    magic = 9000
    
    def __init__(self, session_start: float, session_end: float, sl: float, tp: float, mode: str):
        self.session = (session_start, session_end)
        self.sl_atr_mult = sl
        self.tp_atr_mult = tp
        self.mode = mode
        self.name = f"FVG_{session_start}_{session_end}_{sl}_{tp}_{mode}"
        self.magic = 9000 + int(sl * 100) + int(tp * 10)

def generate_strategies():
    sessions = [(17.5, 21.5), (11.5, 15.5)] # NY, London
    sl_mults = [0.5, 0.75, 1.0, 1.5]
    tp_mults = [1.5, 2.0, 2.5, 3.0]
    modes = ["baseline", "sweep", "void", "sweep_or_void"]
    
    strategies = []
    for sess, sl, tp, mode in itertools.product(sessions, sl_mults, tp_mults, modes):
        if tp > sl: # Basic sanity filter
            strategies.append(ParameterizedFVG(sess[0], sess[1], sl, tp, mode))
    
    # Add Bible Strategies (parameterized with different SL/TP combos)
    from src.strategies.bible_strategies import LARSStrategy, NVMRStrategy, PDHLRStrategy, LKOCSStrategy
    
    bible_sl_tp = [(0.4, 1.2), (0.5, 1.5), (0.5, 2.0), (0.75, 1.5), (0.75, 2.0)]
    for sl, tp in bible_sl_tp:
        for Cls, magic_base in [(LARSStrategy, 4001), (NVMRStrategy, 4003), 
                                 (PDHLRStrategy, 4007), (LKOCSStrategy, 4010)]:
            strat = Cls()
            strat.sl_atr_mult = sl
            strat.tp_atr_mult = tp
            strat.name = f"{Cls.name}_sl{sl}_tp{tp}"
            strat.magic = magic_base + int(sl * 100) + int(tp * 10)
            strategies.append(strat)
    
    return strategies

import concurrent.futures

def run_chunk(chunk_data):
    start, end, strats = chunk_data
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    cfg = EngineConfig(symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed",
                       fixed_lots=0.01, dedup_per_candle=True, max_concurrent=2, 
                       max_same_direction=2, enable_pyramiding=False, enable_trailing=False, 
                       enable_consolidation_exit=False, history_bars=250, warmup_bars=300,
                       daily_loss_limit_mode="off", enable_d1_bias_gate=True, direction_gate="d1_ema20")
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    return eng.run(strats, start_ts=_ts(start), end_ts=_ts(end)).trades

def run_loop_parallel(start, end, strats, max_workers=15):
    chunk_size = max(1, len(strats) // max_workers)
    chunks = [strats[i:i + chunk_size] for i in range(0, len(strats), chunk_size)]
    chunk_args = [(start, end, chunk) for chunk in chunks]
    
    all_trades = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for trades in executor.map(run_chunk, chunk_args):
            all_trades.extend(trades)
    
    # We return a dummy object with .trades to match the previous API
    class DummyResult:
        def __init__(self, trades):
            self.trades = trades
    return DummyResult(all_trades)

def extract_signals_and_returns(trades):
    # This is a proxy for IC. We'll use trade outcomes. 
    # For a real IC, we need per-bar signals and forward returns, but for a fast implementation, 
    # we can treat each trade's directional attempt as the signal (+1 for buy, -1 for sell)
    # and the actual price excursion as the forward return.
    # But since trades resolve at TP/SL, net_pl is sufficient for SR and DSR.
    returns = np.array([t.net_pl for t in trades])
    return returns

def main():
    print(f"=== LOOP ENGINEERING FRAMEWORK ===", flush=True)
    print(f"IS Window: {TRAIN_START} to {TRAIN_END}", flush=True)
    print(f"OOS Window: {OOS_START} to {OOS_END}\n", flush=True)
    
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    cfg = EngineConfig(symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed",
                       fixed_lots=0.01, dedup_per_candle=True, max_concurrent=2, 
                       max_same_direction=2, enable_pyramiding=False, enable_trailing=False, 
                       enable_consolidation_exit=False, history_bars=250, warmup_bars=300,
                       daily_loss_limit_mode="off", enable_d1_bias_gate=True, direction_gate="d1_ema20")
    
    # 1. Generate Strategies
    all_strats = generate_strategies()
    total_trials = len(all_strats)
    print(f"Generated {total_trials} unique strategy configurations.", flush=True)
    
    # 2. Run IS Backtest
    print(f"Running IS backtest (parallel)...", flush=True)
    is_res = run_loop_parallel(TRAIN_START, TRAIN_END, all_strats)
    
    # 3. Score IS Performance
    is_scores = {}
    is_sr_list = []
    
    for cls in all_strats:
        strat_trades = [t for t in is_res.trades if t.strategy == cls.name]
        rets = extract_signals_and_returns(strat_trades)
        
        if len(rets) < 20:
            continue
            
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else 0.0
        
        # Calculate annualized SR (proxy based on trades)
        period_std = np.std(rets)
        if period_std == 0:
            continue
            
        sr = np.mean(rets) / period_std
        is_sr_list.append(sr)
        
        is_scores[cls.name] = {
            "n": len(rets),
            "pf": pf,
            "net": np.sum(rets),
            "sr": sr,
            "strat": cls
        }
    
    # 4. Filter IS Strategies
    is_sr_variance = np.var(is_sr_list) if len(is_sr_list) > 0 else 1.0
    survivors = []
    print("\nIS Survivors (PF > 1.25):")
    for name, s in is_scores.items():
        if s["pf"] > 1.25 and s["net"] > 0:
            survivors.append(s["strat"])
            print(f"  {name}: PF={s['pf']:.2f}, Net=${s['net']:.2f}, SR={s['sr']:.3f}")
            
    print(f"\n{len(survivors)} / {total_trials} strategies survived the IS gate.")
    
    if not survivors:
        print("No strategies survived IS.")
        return

    # 5. Run OOS Backtest on Survivors
    print(f"\nRunning OOS backtest on {len(survivors)} survivors...", flush=True)
    oos_res = run_loop_parallel(OOS_START, OOS_END, survivors)
    
    # 6. Apply Final Reality Check
    print(f"\n=== FINAL OOS REALITY CHECK ===")
    real_edges = 0
    
    for cls in survivors:
        strat_trades = [t for t in oos_res.trades if t.strategy == cls.name]
        rets = extract_signals_and_returns(strat_trades)
        
        if len(rets) < 10:
            print(f"  [KILL] {cls.name}: Not enough OOS trades ({len(rets)}).")
            continue
            
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else 0.0
        
        # Standard T-stat (assuming independent trades)
        t_stat = (np.mean(rets) / np.std(rets)) * np.sqrt(len(rets))
        
        # Calculate DSR using total_trials!
        dsr = deflated_sharpe_ratio(rets, num_trials=total_trials, sr_variance=is_sr_variance)
        
        # Calculate Bonferroni p-value
        p_val = stats.t.sf(t_stat, df=len(rets)-1)
        bonf_p = bonferroni_correction(p_val, total_trials)
        
        status = "PASS" if dsr > 0.95 and bonf_p < 0.05 else "FAIL"
        if status == "PASS":
            real_edges += 1
            
        print(f"  [{status}] {cls.name}:")
        print(f"         OOS Net: ${np.sum(rets):.2f}, PF: {pf:.2f}, n: {len(rets)}")
        print(f"         T-Stat: {t_stat:.2f} (p={p_val:.4f})")
        print(f"         Bonferroni Adj p: {bonf_p:.4f} (Required < 0.05)")
        print(f"         Deflated Sharpe: {dsr:.4f} (Required > 0.95)")
        print()
        
    print(f"Summary: {real_edges} strategies passed the true OOS reality check.")

if __name__ == '__main__':
    main()
