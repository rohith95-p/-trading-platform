import sys
sys.path.insert(0, r'c:\projects\ultra_core')
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize
from src.strategies.bible_strategies import NVMRStrategy, PDHLRStrategy
from src.strategies.liquidity_sweep_reversal import LiquiditySweepReversal
from src.strategies.ny_liquidity_expansion import NYLiquidityExpansion
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat
from src.strategies.eurusd_asian_range import EURUSDAsianRange
from src.strategies.forex_session_momentum import ForexSessionMomentum
from src.strategies.portfolio_v4 import FVGNYTight
from datetime import datetime, timezone

ALL = [NVMRStrategy, LiquiditySweepReversal, PDHLRStrategy, NYLiquidityExpansion,
       BBMeanReversionStrat, EURUSDAsianRange, ForexSessionMomentum, TrendPullbackStrat, FVGNYTight]

print("Loading bars...")
bars = load_bars('XAUUSDm', timeframes=('M15','M5','M1','D1'))
print("Done. Running period tests...\n")

cfg = EngineConfig(
    symbol='XAUUSDm', starting_balance=100.0,
    sizing_mode='fixed', fixed_lots=0.01,
    max_concurrent=3, max_same_direction=3,
    enable_trailing=False, enable_pyramiding=False,
    daily_loss_limit_mode='balance_pct', daily_loss_limit_pct=0.06,
    enable_d1_bias_gate=True,
)

periods = [
    ('LAST WEEK  (Sep 21-28)', datetime(2026,9,21,tzinfo=timezone.utc), datetime(2026,9,28,tzinfo=timezone.utc)),
    ('LAST MONTH (Aug 28-Sep 28)', datetime(2026,8,28,tzinfo=timezone.utc), datetime(2026,9,28,tzinfo=timezone.utc)),
]

for label, start, end in periods:
    strats = []
    for cls in ALL:
        s = cls()
        s.sl_atr_mult = 0.1
        s.tp_atr_mult = 1.0
        strats.append(s)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS['realistic_ecn'], config=cfg)
    res = eng.run(strats, start_ts=int(start.timestamp()), end_ts=int(end.timestamp()))
    st = summarize(res.trades, res.equity, cfg.starting_balance).to_dict()
    print(f"--- {label} ---")
    print(f"  Trades : {st.get('trades', 0)}")
    print(f"  PF     : {st.get('profit_factor', 0.0):.2f}")
    print(f"  Net PL : ${st.get('net_pl', 0.0):.2f}")
    print(f"  Max DD : {st.get('max_drawdown_pct', 0.0):.2f}%")
    print(f"  Win Rate: {st.get('win_rate', 0.0):.2f}%")
    print()
