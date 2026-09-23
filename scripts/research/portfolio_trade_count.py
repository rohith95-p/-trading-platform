"""
Test portfolio over the last month to count trades.
"""
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import UltraCorePortfolio
from scripts.validation.part1_suite import _ts, START_BAL

START_DATE = "2026-08-20"
END_DATE = "2026-09-20"
LOT_SIZE = 0.01

def main():
    s = UltraCorePortfolio()
    
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=LOT_SIZE,
        dedup_per_candle=True, max_concurrent=3, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20"
    )
    
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    
    res = eng.run([s], start_ts=_ts(START_DATE), end_ts=_ts(END_DATE))
    
    print(f"Total Portfolio Trades (Aug 20 - Sep 20): {len(res.trades)}")
    
if __name__ == "__main__":
    main()
