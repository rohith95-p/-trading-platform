import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v5_9_leg import PORTFOLIO as PORTFOLIO_V5

def run_monte_carlo():
    sym = "XAUUSDm"
    print(f"Loading {sym} data...")
    bars = load_bars(symbol=sym, timeframes=("M15", "M5", "M1", "D1"))

    cfg = EngineConfig(
        symbol=sym, starting_balance=100.0,
        sizing_mode="fixed", fixed_lots=0.01,
        max_concurrent=2, max_same_direction=2,
        enable_trailing=False, enable_pyramiding=False,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True,
    )

    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic_ecn"], config=cfg)
    instances = [s() for s in PORTFOLIO_V5]
    print("Running baseline backtest to collect trades...")
    res = eng.run(instances)
    
    trade_pls = [t.net_pl for t in res.trades]
    n_trades = len(trade_pls)
    
    if n_trades == 0:
        print("No trades generated.")
        return
        
    print(f"Collected {n_trades} trades. Running 1000 Monte Carlo simulations...")
    
    simulations = 1000
    ruined_count = 0
    margin_floor = 50.0
    start_bal = cfg.starting_balance
    
    for i in range(simulations):
        # Sample with replacement
        sampled_pls = np.random.choice(trade_pls, size=n_trades, replace=True)
        # Calculate equity curve
        equity_curve = start_bal + np.cumsum(sampled_pls)
        # Check if it ever hits the margin floor
        if np.any(equity_curve < margin_floor):
            ruined_count += 1
            
    p_ruin = (ruined_count / simulations) * 100.0
    
    print("\n" + "="*50)
    print("MONTE CARLO ACCOUNT FEASIBILITY")
    print("="*50)
    print(f"Strategy: PORTFOLIO_V5 (XAUUSDm)")
    print(f"Simulations: {simulations}")
    print(f"Original Trades: {n_trades}")
    print(f"Margin Floor: ${margin_floor:.2f}")
    print(f"P(ruin): {p_ruin:.1f}%")
    print("="*50)
    
    if p_ruin < 1.0:
        print("✓ PASS: P(ruin) < 1%")
    else:
        print("✗ FAIL: P(ruin) >= 1%")

if __name__ == "__main__":
    run_monte_carlo()
