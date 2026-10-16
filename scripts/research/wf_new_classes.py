"""Run the three new strategy classes (src/strategies/new_*.py) through the corrected engine, 24h window. Args: idx outdir"""
import sys, os, json, importlib, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import src.core.market_hours as mh
mh.ENFORCE_TRADING_WINDOW = False
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
SP = [("src.strategies.new_asia_vol_breakout", "AsiaVolBreakout"), ("src.strategies.new_london_open_drive", "LondonOpenDrive"), ("src.strategies.new_daily_open_momentum", "DailyOpenMomentum")]
mod, cls = SP[int(sys.argv[1])]; out = sys.argv[2]
s = getattr(importlib.import_module(mod), cls)()
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
ts = lambda d: int(d.replace(tzinfo=dt.timezone.utc).timestamp())
cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=100000.0, history_bars=600, daily_loss_limit_mode="off")
res = BacktestEngine(bars=bars, cost=SCENARIOS["realistic_ecn"], config=cfg).run([s], ts(dt.datetime(2022, 8, 1)), ts(dt.datetime(2026, 10, 14)))
json.dump([[t.entry_time, t.exit_time, t.net_pl, abs(t.entry_price - t.initial_sl)] for t in res.trades], open(os.path.join(out, f"NEW_{cls}_native.json"), "w"))
print("done", cls, len(res.trades), flush=True)
