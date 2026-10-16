"""Run H1 Donchian through the corrected full engine at 0.01 lot on a $186 account."""
import sys, os, dataclasses, datetime as dt, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize
from src.strategies.h1_donchian import H1Donchian

sl, tp = float(sys.argv[1]), float(sys.argv[2])
gate = (sys.argv[3] != "nogate") if len(sys.argv) > 3 else True
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
ts = lambda y, m, d: int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())
coarse = dataclasses.replace(bars, m1=None)
for label, b, a, e in [("coarse 2022-08..2026-07", coarse, ts(2022, 8, 1), ts(2026, 7, 1)),
                       ("M1     2026-07..10    ", bars, ts(2026, 7, 6), ts(2026, 10, 13))]:
    cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=186.0,
                       history_bars=600, enable_d1_bias_gate=gate)
    res = BacktestEngine(bars=b, cost=SCENARIOS["realistic_ecn"], config=cfg).run(
        [H1Donchian(100, sl, tp)], a, e)
    d = summarize(res.trades, res.equity, 186.0).to_dict()
    bal = np.array([186.0] + [t.balance_after for t in res.trades])
    peak = np.maximum.accumulate(bal)
    ddd = (peak - bal).max()
    losses = [-t.net_pl for t in res.trades if t.net_pl < 0]
    print(f"SL{sl}/TP{tp} gate={gate} {label} n={d['trades']:4d} win={d['win_rate']:4.1f}% PF={d['profit_factor']:.2f} "
          f"net=${d['net_pl']:8.2f} end=${bal[-1]:8.2f} min=${bal.min():8.2f} maxDD=${ddd:7.2f} ({ddd/peak[np.argmax(peak-bal)]*100:4.1f}%) "
          f"avgLoss=${np.mean(losses) if losses else 0:5.1f} maxLosses={d.get('max_consec_losses')}", flush=True)
