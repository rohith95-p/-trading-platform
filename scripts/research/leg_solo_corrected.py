import sys, os, dataclasses, datetime as dt, time
sys.path.insert(0, r"C:\projects\ultra_core"); os.chdir(r"C:\projects\ultra_core")
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize
from src.strategies.portfolio_v5_core import PORTFOLIO
idx=int(sys.argv[1]); cls=PORTFOLIO[idx]
bars = load_bars("XAUUSDm", timeframes=("M15","M5","M1","D1"))
ts=lambda y,m,d:int(dt.datetime(y,m,d,tzinfo=dt.timezone.utc).timestamp())
coarse=dataclasses.replace(bars,m1=None)
for label,b,a,e in [("coarse-fixed 2022-08..2026-07",coarse,ts(2022,8,1),ts(2026,7,1)),
                     ("M1 2026-07..10",bars,ts(2026,7,6),ts(2026,10,13))]:
    cfg=EngineConfig(sizing_mode="fixed",fixed_lots=0.01,starting_balance=10000.0)
    res=BacktestEngine(bars=b,cost=SCENARIOS["realistic_ecn"],config=cfg).run([cls()],a,e)
    d=summarize(res.trades,res.equity,cfg.starting_balance).to_dict()
    print(f"{cls().name:22s} {label:30s} n={d['trades']:5d} win={d['win_rate']:5.1f}% PF={d['profit_factor']:.3f} net=${d['net_pl']:8.2f} exp/trade=${d['net_pl']/max(d['trades'],1):.3f}",flush=True)
