"""
Monte Carlo Stress Tester (Skill #17)
Simulates 1000 equity curves by bootstrapping trades from the winning candidate.
Calculates Risk of Ruin and 95% Confidence Interval for Drawdown.
"""
import sys
import numpy as np
from datetime import datetime

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.bible_strategies import PDHLRStrategy, NVMRStrategy, LARSStrategy, LKOCSStrategy
from scripts.validation.part1_suite import _ts, START_BAL

# The wrapper we used in the search
class SessionGatedStrategy:
    def __init__(self, base_strategy):
        self.base = base_strategy
        self.name = f"{base_strategy.name}_GATED"
        self.magic = base_strategy.magic
        self.execute_immediately = getattr(base_strategy, "execute_immediately", True)
        self.edge_trigger = getattr(base_strategy, "edge_trigger", False)
        
    def evaluate(self, m15_rates, m5_rates=None):
        if m15_rates is None or len(m15_rates) < 2:
            return None
        ts = m15_rates["time"][-1]
        dt = datetime.fromtimestamp(ts)
        ist_hour = dt.hour + (dt.minute / 60.0) + 5.5
        if ist_hour >= 24:
            ist_hour -= 24
        if not (9.0 <= ist_hour <= 21.5):
            return None
        return self.base.evaluate(m15_rates, m5_rates)
        
    def check_pending_confirmation(self, m15_rates):
        return self.base.check_pending_confirmation(m15_rates)
        
    def set_pending(self, signal, candle_time):
        self.base.set_pending(signal, candle_time)

def run_monte_carlo(strat_name, trades, num_simulations=1000):
    print("="*70)
    print(f"MONTE CARLO STRESS TEST: {strat_name}")
    print(f"Simulating {num_simulations} alternative equity curves...")
    print("="*70)
    
    # Extract trade PnL
    pnls = np.array([t.net_pl for t in trades])
    if len(pnls) < 20:
        print("Not enough trades for a valid Monte Carlo simulation.")
        return
        
    initial_balance = START_BAL
    max_dds = []
    end_equities = []
    ruin_count = 0
    ruin_threshold = initial_balance * 0.50 # 50% drawdown = ruin
    
    # Monte Carlo Bootstrap
    np.random.seed(42) # For reproducibility
    for i in range(num_simulations):
        # Sample with replacement
        sampled_pnls = np.random.choice(pnls, size=len(pnls), replace=True)
        equity_curve = initial_balance + np.cumsum(sampled_pnls)
        
        # Calculate Drawdown
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (running_max - equity_curve) / running_max
        max_dd = np.max(drawdowns) * 100
        max_dds.append(max_dd)
        
        end_equities.append(equity_curve[-1])
        
        # Check Ruin
        if np.min(equity_curve) < ruin_threshold:
            ruin_count += 1
            
    # Metrics
    mean_end_equity = np.mean(end_equities)
    mean_max_dd = np.mean(max_dds)
    p95_dd = np.percentile(max_dds, 95)
    p_ruin = (ruin_count / num_simulations) * 100
    
    print(f"Original Trades: {len(pnls)}")
    print(f"Mean End Equity: ${mean_end_equity:.2f} (Start: ${initial_balance})")
    print(f"Mean Max Drawdown: {mean_max_dd:.2f}%")
    print(f"95th Percentile Max Drawdown: {p95_dd:.2f}%")
    print(f"Probability of Ruin (50% DD): {p_ruin:.1f}%")
    
    if p_ruin < 5.0 and p95_dd < 35.0:
        print("\n✅ STRESS TEST PASSED: Strategy is robust.")
    else:
        print("\n❌ STRESS TEST FAILED: Risk of ruin or extreme drawdown is too high.")

def _make_cfg():
    return EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=0.02,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20"
    )

def main():
    try:
        with open("scripts/research/best_10_target.txt", "r") as f:
            best_name = f.read().strip()
    except FileNotFoundError:
        print("No best strategy found. Run search first.")
        return
        
    print(f"Reading target strategy: {best_name}")
    
    # Parse the name to rebuild it: e.g., NVMR_sl0.5_tp3.0
    parts = best_name.split("_")
    base_name = parts[0]
    sl = float(parts[1].replace("sl", ""))
    tp = float(parts[2].replace("tp", ""))
    
    if base_name == "PDHLR": s = PDHLRStrategy()
    elif base_name == "NVMR": s = NVMRStrategy()
    elif base_name == "LARS": s = LARSStrategy()
    elif base_name == "LKOCS": s = LKOCSStrategy()
    else:
        print("Unknown base strategy.")
        return
        
    s.sl_atr_mult = sl
    s.tp_atr_mult = tp
    s.name = best_name
    
    # Run a full holdout backtest to get all trades for the MC simulation
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_make_cfg())
    print("Running full backtest for data collection (2025-01-01 -> 2026-05-20)...")
    res = eng.run([s], start_ts=_ts("2025-01-01"), end_ts=_ts("2026-05-20"))
    
    run_monte_carlo(best_name, res.trades)

if __name__ == "__main__":
    main()
