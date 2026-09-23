"""
Massive Grid Search for 10+ High-Performance XAUUSD Strategies
Executes autonomously and logs results to markdown.
"""

import numpy as np
import scipy.stats as stats
import itertools
import concurrent.futures
import time

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.metrics import deflated_sharpe_ratio, bonferroni_correction
from scripts.validation.part1_suite import _ts, START_BAL, TRAIN_START, TRAIN_END, OOS_START, OOS_END
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat, SessionBreakoutStrat
from src.strategies.bible_strategies import LARSStrategy, NVMRStrategy

MAX_WORKERS = 15
IS_PF_GATE = 1.40  # Hard gate for profitability
IS_WR_GATE = 60.0  # Hard gate for win rate

def generate_grid():
    strats = []
    
    # Batch 6: High-Precision Filtering (1:1 RR)
    # We return to the 1:1 RR (0.5/0.5, 0.75/0.75) which guarantees a 1.4+ PF *IF* we hit 60% WR.
    # To hit 60% WR, we will use the engine's aggressive 'both' direction gate.
    rr_combos = [(0.5, 0.5), (0.6, 0.6), (0.75, 0.75), (0.8, 0.8), (1.0, 1.0)]
    
    # We will test all 5 paradigms again with these 1:1 targets
    for sess in [(11.5, 15.5), (17.5, 21.5)]:
        for fast, slow in [(13, 34)]:
            for sl, tp in rr_combos:
                strats.append(TrendPullbackStrat(session=sess, fast_ema=fast, slow_ema=slow, pullback_ema=fast, sl=sl, tp=tp))

    for sess in [(11.5, 15.5), (17.5, 21.5)]:
        for period, std in [(20, 2.0)]:
            for sl, tp in rr_combos:
                strats.append(BBMeanReversionStrat(session=sess, bb_period=period, bb_std=std, sl=sl, tp=tp))

    for r_s, r_e, t_s, t_e in [(5.5, 11.5, 11.5, 13.5)]:
        for sl, tp in rr_combos:
            strats.append(SessionBreakoutStrat(range_start=r_s, range_end=r_e, trade_start=t_s, trade_end=t_e, sl=sl, tp=tp))
            
    for sl, tp in rr_combos:
        s1 = LARSStrategy()
        s1.sl_atr_mult, s1.tp_atr_mult = sl, tp
        s1.name = f"LARS_Ext_sl{sl}_tp{tp}_kz2h"
        s1.magic = 8000 + int(sl*100) + int(tp*10)
        strats.append(s1)

    for sl, tp in rr_combos:
        s1 = NVMRStrategy()
        s1.sl_atr_mult, s1.tp_atr_mult = sl, tp
        s1.name = f"NVMR_Ext_sl{sl}_tp{tp}_std1.7"
        s1.magic = 9000 + int(sl*100) + int(tp*10)
        strats.append(s1)

    return strats

def _cfg():
    return EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="both",
        enable_trailing=False,
        structural_tp=True, structural_tp_len=10, structural_tp_buffer_atr=0.1
    )

def _run_chunk(args):
    start, end, strat_list = args
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_cfg())
    # FULL HISTORY TEST for robust DSR
    return eng.run(strat_list, start_ts=_ts("2022-06-07"), end_ts=_ts("2026-08-31")).trades

def run_parallel(strats):
    chunk_size = max(1, len(strats) // MAX_WORKERS)
    chunks = [strats[i:i + chunk_size] for i in range(0, len(strats), chunk_size)]
    all_trades = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as exe:
        # Dummy start/end, overridden in _run_chunk
        for trades in exe.map(_run_chunk, [("2022", "2026", c) for c in chunks]):
            all_trades.extend(trades)
    return all_trades

def score_trades(trades):
    rets = np.array([t.net_pl for t in trades])
    if len(rets) < 20: return 0.0, 0.0, 0, 0.0
    w, l = rets[rets > 0], rets[rets < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    wr = 100 * len(w) / len(rets)
    std = rets.std()
    sr = (rets.mean() / std) if std > 0 else 0
    return pf, wr, len(rets), sr

def main():
    print("Generating Massive Grid (Batch 5: Wide-Risk Structural-TP)...", flush=True)
    all_strats = generate_grid()
    total_trials = len(all_strats)
    print(f"Total strategies in grid: {total_trials}", flush=True)
    
    print(f"\n--- Running Full History Test (2022-2026) ---", flush=True)
    
    all_trades_list = run_parallel(all_strats)
    
    by_name = {}
    for t in all_trades_list:
        by_name.setdefault(t.strategy, []).append(t)
        
    final_winners = []
    is_srs = []
    
    for s_name, trades in by_name.items():
        pf, wr, n, sr = score_trades(trades)
        if n >= 20: is_srs.append(sr)
        
    is_sr_var = np.var(is_srs) if is_srs else 1.0
    
    with open(r"C:\Users\rohit\.gemini\antigravity-ide\brain\64de4bd5-d403-492e-b38e-307078b319ba\massive_search_results.md", "w") as f:
        f.write("# Batch 5: Wide-Risk Structural-TP Massive Grid Search Results\n\n")
        f.write(f"- Total Strategies Tested: {total_trials}\n")
        f.write(f"- Empirical SR Variance (for DSR calibration): {is_sr_var:.6f}\n\n")
        f.write("## Strategy Analysis (Full History 2022-2026)\n\n")
        f.write("| Strategy | PF | WR | n | Bonf-p | DSR | Status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        
        for s_name, trades in by_name.items():
            rets = np.array([t.net_pl for t in trades])
            if len(rets) < 100:
                f.write(f"| {s_name} | - | - | {len(rets)} | - | - | KILLED (Low n) |\n")
                continue
                
            w, l = rets[rets > 0], rets[rets < 0]
            pf = float(w.sum() / -l.sum()) if len(l) else 0.0
            wr = 100 * len(w) / len(rets)
            std = rets.std()
            if std == 0: continue
            
            t_stat = (rets.mean() / std) * np.sqrt(len(rets))
            p_val = float(stats.t.sf(t_stat, df=len(rets) - 1))
            bonf_p = bonferroni_correction(p_val, total_trials)
            dsr = deflated_sharpe_ratio(rets, num_trials=total_trials, sr_variance=is_sr_var)
            
            # The strict criteria requested by user: >60% WR, >1.4 PF
            ok = (dsr > 0.90) and (bonf_p < 0.05) and (pf >= 1.40) and (wr >= 60.0)
            status = "**WINNER**" if ok else "FAIL"
            
            if ok:
                final_winners.append(s_name)
                
            f.write(f"| {s_name} | {pf:.2f} | {wr:.1f}% | {len(rets)} | {bonf_p:.4f} | {dsr:.4f} | {status} |\n")
            if pf >= 1.25 and wr >= 50.0:
                print(f"  {s_name[:40]:40s}: PF={pf:.2f} WR={wr:.1f}% n={len(rets):3d} Bonf={bonf_p:.4f} DSR={dsr:.4f} -> {status}", flush=True)

    print("\n--- FINAL VERDICT ---", flush=True)
    if final_winners:
        print(f"FOUND {len(final_winners)} WINNERS:")
        for w in final_winners:
            print(f"  {w}")
    else:
        print("No strategies passed the strict DSR/Bonferroni gate.")

if __name__ == "__main__":
    main()
