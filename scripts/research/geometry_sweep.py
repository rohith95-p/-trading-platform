"""Does SL/TP geometry explain the live legs' results? Solo legs, corrected engine,
0.01 lot, $10k start, realistic_ecn, live window + D1 gate. Args: worker n_workers out.jsonl"""
import sys, os, json, dataclasses, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize
from src.strategies.portfolio_v5_core import PORTFOLIO

GEOMS = [(0.5, 1.5), (1.0, 2.0), (1.0, 3.0), (1.5, 3.0), (2.0, 4.0)]
if os.environ.get("GEOMS"): GEOMS = [tuple(map(float, g.split("/"))) for g in os.environ["GEOMS"].split(",")]
YEARS_ALL = {"2022-24": (dt.datetime(2022, 8, 1), dt.datetime(2025, 1, 1)), "2025": (dt.datetime(2025, 1, 1), dt.datetime(2026, 1, 1)),
         "2026": (dt.datetime(2026, 1, 1), dt.datetime(2026, 10, 14))}
YEARS = {k: YEARS_ALL[k] for k in os.environ.get("YRS", "2025,2026").split(",")}
wi, nw, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
ts = lambda d: int(d.replace(tzinfo=dt.timezone.utc).timestamp())
jobs = [(li, g, y) for li in range(len(PORTFOLIO)) for g in GEOMS for y in YEARS]
for k, (li, g, y) in enumerate(jobs):
    if k % nw != wi: continue
    s = PORTFOLIO[li](); s.sl_atr_mult, s.tp_atr_mult = g
    cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=10000.0)
    res = BacktestEngine(bars=bars, cost=SCENARIOS["realistic_ecn"], config=cfg).run([s], ts(YEARS[y][0]), ts(YEARS[y][1]))
    d = summarize(res.trades, res.equity, 10000.0).to_dict()
    rec = dict(leg=s.name, sl=g[0], tp=g[1], year=y, n=d["trades"], win=d["win_rate"], pf=d["profit_factor"], net=d["net_pl"])
    open(out, "a").write(json.dumps(rec) + "\n"); print(rec, flush=True)
