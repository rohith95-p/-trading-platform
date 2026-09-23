import numpy as np
import scipy.stats as stats
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import _LiquidityFilteredFVG
from src.research.metrics import deflated_sharpe_ratio, bonferroni_correction
from scripts.validation.part1_suite import _ts, START_BAL, OOS_START, OOS_END

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

def extract_signals_and_returns(trades):
    return np.array([t.net_pl for t in trades])

def main():
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    cfg = EngineConfig(symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed",
                       fixed_lots=0.01, dedup_per_candle=True, max_concurrent=2, 
                       max_same_direction=2, enable_pyramiding=False, enable_trailing=False, 
                       enable_consolidation_exit=False, history_bars=250, warmup_bars=300,
                       daily_loss_limit_mode="off", enable_d1_bias_gate=True, direction_gate="d1_ema20")
    
    # Hardcoded survivors from the IS run
    survivors = [
        ParameterizedFVG(17.5, 21.5, 0.5, 1.5, "baseline"),
        ParameterizedFVG(17.5, 21.5, 0.5, 3.0, "sweep_or_void"),
        ParameterizedFVG(17.5, 21.5, 0.75, 1.5, "baseline"),
        ParameterizedFVG(17.5, 21.5, 0.75, 3.0, "void"),
        ParameterizedFVG(17.5, 21.5, 1.0, 1.5, "baseline"),
        ParameterizedFVG(17.5, 21.5, 1.0, 3.0, "void"),
        ParameterizedFVG(11.5, 15.5, 0.5, 1.5, "void")
    ]
    
    print(f"Running OOS backtest on {len(survivors)} survivors ({OOS_START} to {OOS_END})...")
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    oos_res = eng.run(survivors, start_ts=_ts(OOS_START), end_ts=_ts(OOS_END))
    
    print(f"\n=== FINAL OOS REALITY CHECK ===")
    real_edges = 0
    total_trials = 120 # Total trials from the generation step
    
    # Approximate variance of IS Sharpe Ratios from the 7 survivors + some failed ones
    # (Using 1.0 as a conservative default for SR variance if unknown, but normally it's ~0.5 for FX)
    is_sr_variance = 1.0 
    
    for cls in survivors:
        strat_trades = [t for t in oos_res.trades if t.strategy == cls.name]
        rets = extract_signals_and_returns(strat_trades)
        
        if len(rets) < 10:
            print(f"  [KILL] {cls.name}: Not enough OOS trades ({len(rets)}).")
            continue
            
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else 0.0
        
        # Standard T-stat (assuming independent trades)
        period_std = np.std(rets)
        if period_std == 0:
            print(f"  [KILL] {cls.name}: Zero variance in returns.")
            continue
            
        t_stat = (np.mean(rets) / period_std) * np.sqrt(len(rets))
        
        # Calculate DSR using total_trials
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
