"""Run research-library candidates (XV2-*/XAU-*) through the corrected engine as strategies, 24h window allowed
(Atlas does not impose the bot's 06:00-21:30 IST window). Args: worker n_workers outdir"""
import sys, os, json, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import numpy as np
import src.core.market_hours as mh
mh.ENFORCE_TRADING_WINDOW = False
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from src.research.candidates_v2 import build_library_v2
from src.research.market_study import build_features, session_mask
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

LIB = {c.id: c for c in build_library() + build_library_v2()}

class CandidateStrategy(BaseStrategy):
    execute_immediately = True
    edge_trigger = False
    _min_bars = 250
    def __init__(self, cid):
        c = LIB[cid]; self.c = c; self.name = cid; self.magic = 8000 + (abs(hash(cid)) % 900)
        self.session = c.session; self.sl_atr_mult = c.sl_atr; self.tp_atr_mult = c.tp_atr
    def evaluate(self, m15_rates, m5_rates=None):
        if m15_rates is None or len(m15_rates) < self._min_bars: return None
        f = build_features(m15_rates)
        sig = np.where(session_mask(f["ist_hour"], self.session), self.c.rule(f), 0)
        s = sig[-2]
        if s == 0 or (isinstance(s, float) and np.isnan(s)): return None
        return Signal(direction=mt5.ORDER_TYPE_BUY if s > 0 else mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=bool(s > 0))
    def check_pending_confirmation(self, m15_rates): return None
    def set_pending(self, signal, candle_time): pass

IDS = ["XV2-104", "XV2-111", "XV2-108", "XV2-078", "XV2-132", "XV2-084"]
if __name__ == "__main__":
    wi, nw, outdir = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    ts = lambda d: int(d.replace(tzinfo=dt.timezone.utc).timestamp())
    for k, cid in enumerate(IDS):
        if k % nw != wi: continue
        s = CandidateStrategy(cid)
        cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=100000.0, daily_loss_limit_mode="off")
        res = BacktestEngine(bars=bars, cost=SCENARIOS["realistic_ecn"], config=cfg).run([s], ts(dt.datetime(2022, 8, 1)), ts(dt.datetime(2026, 10, 14)))
        json.dump([[t.entry_time, t.exit_time, t.net_pl, abs(t.entry_price - t.initial_sl)] for t in res.trades], open(os.path.join(outdir, f"{cid}_native.json"), "w"))
        print("done", cid, len(res.trades), flush=True)
