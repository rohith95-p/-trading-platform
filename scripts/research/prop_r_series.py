"""Run H1 Donchian through the corrected engine and dump per-trade data
(size-independent R) for prop-challenge simulation. Args: channel sl tp out.json"""
import sys, os, json, dataclasses, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.strategies.h1_donchian import H1Donchian

ch, sl, tp, out = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
ts = lambda y, m, d: int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())
b = dataclasses.replace(bars, m1=None)
cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=100000.0,
                   history_bars=600, daily_loss_limit_mode="off")
res = BacktestEngine(bars=b, cost=SCENARIOS["realistic_ecn"], config=cfg).run(
    [H1Donchian(ch, sl, tp)], ts(2022, 8, 1), ts(2026, 10, 13))
# [entry_time, net_pl $ at 0.01 lot, initial risk $ at 0.01 lot (1 oz => $ per $1)]
json.dump([[t.entry_time, t.net_pl, abs(t.entry_price - t.initial_sl)] for t in res.trades], open(out, "w"))
print("done", ch, sl, tp, len(res.trades), flush=True)
