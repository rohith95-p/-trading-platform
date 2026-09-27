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
from datetime import datetime, timezone, timedelta
from collections import defaultdict

ALL = [NVMRStrategy, LiquiditySweepReversal, PDHLRStrategy, NYLiquidityExpansion,
       BBMeanReversionStrat, EURUSDAsianRange, ForexSessionMomentum, TrendPullbackStrat, FVGNYTight]

print("Loading bars...", flush=True)
bars = load_bars('XAUUSDm', timeframes=('M15','M5','M1','D1'))

STARTING_BALANCE = 171.14  # Live MT5 account balance as of 2026-09-28

cfg = EngineConfig(
    symbol='XAUUSDm', starting_balance=STARTING_BALANCE,
    sizing_mode='fixed', fixed_lots=0.01,
    max_concurrent=3, max_same_direction=3,
    enable_trailing=False, enable_pyramiding=False,
    daily_loss_limit_mode='balance_pct', daily_loss_limit_pct=0.06,
    enable_d1_bias_gate=True,
)

START = datetime(2026, 8, 28, tzinfo=timezone.utc)
END   = datetime(2026, 9, 28, tzinfo=timezone.utc)

strats = []
for cls in ALL:
    s = cls(); s.sl_atr_mult = 0.1; s.tp_atr_mult = 1.0
    strats.append(s)

print("Running backtest Aug 28 -> Sep 28...", flush=True)
eng = BacktestEngine(bars=bars, cost=SCENARIOS['realistic_ecn'], config=cfg)
res = eng.run(strats, start_ts=int(START.timestamp()), end_ts=int(END.timestamp()))

# --- Group trades by day ---
daily = defaultdict(lambda: {'pnl': 0.0, 'wins': 0, 'losses': 0, 'trades': 0})
for t in res.trades:
    close_dt = datetime.fromtimestamp(t.exit_time, tz=timezone.utc)
    day_key = close_dt.strftime('%Y-%m-%d %a')
    daily[day_key]['pnl'] += t.net_pl
    daily[day_key]['trades'] += 1
    if t.net_pl > 0:
        daily[day_key]['wins'] += 1
    else:
        daily[day_key]['losses'] += 1

# --- Print daily log ---
print("\n========== DAILY TRADE LOG: Aug 28 – Sep 28 ==========")
print(f"{'Date':<18} | {'Trades':<6} | {'W':<3} | {'L':<3} | {'Daily PnL':<12} | {'Cumulative'}")
print("-" * 70)

cumulative = 0.0
total_days_traded = 0
total_profit_days = 0
total_loss_days = 0

for day in sorted(daily.keys()):
    d = daily[day]
    cumulative += d['pnl']
    pnl_str = f"+${d['pnl']:.2f}" if d['pnl'] >= 0 else f"-${abs(d['pnl']):.2f}"
    balance_str = f"${STARTING_BALANCE + cumulative:.2f}"
    flag = "[+]" if d['pnl'] > 0 else "[-]"
    print(f"{flag} {day:<16} | {d['trades']:<6} | {d['wins']:<3} | {d['losses']:<3} | {pnl_str:<12} | Balance: {balance_str}")
    total_days_traded += 1
    if d['pnl'] > 0: total_profit_days += 1
    else: total_loss_days += 1

# --- Summary stats ---
st = summarize(res.trades, res.equity, cfg.starting_balance).to_dict()
total_net = st.get('net_pl', 0.0)
avg_per_day = total_net / max(total_days_traded, 1)

print("\n========== SUMMARY ==========")
print(f"Total Trades   : {st.get('trades', 0)}")
print(f"Win Rate       : {st.get('win_rate', 0.0):.2f}%")
print(f"Profit Factor  : {st.get('profit_factor', 0.0):.2f}")
print(f"Total Net P&L  : ${total_net:.2f}")
print(f"Max Drawdown   : {st.get('max_drawdown_pct', 0.0):.2f}%")
print(f"Days Traded    : {total_days_traded}")
print(f"Profit Days    : {total_profit_days}")
print(f"Loss Days      : {total_loss_days}")
print(f"Avg Profit/Day : ${avg_per_day:.2f}")
print(f"Avg Trades/Day : {st.get('trades', 0) / max(total_days_traded, 1):.1f}")
