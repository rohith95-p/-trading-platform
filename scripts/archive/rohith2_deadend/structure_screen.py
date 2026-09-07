"""Screen the market-structure candidates (BigBeluga CHoCH/BOS + LuxAlgo order
block) the standard way: isolated backtest + the random-entry control each must
beat.

    python -m scripts.structure_screen
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


lib = {c.id: c for c in build_library()}
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2026-05-21", "2026-08-29", 105.74

# one representative instance of each new primitive (ALL sessions, 3.0/1.5)
TARGETS = [
    ("Structure CHoCH", "XAU-125"),
    ("Structure BOS",   "XAU-131"),
    ("Order block",     "XAU-137"),
]
SESS_ALL = (0.0, 24.0)


def run_candidate(rule, seed=None):
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        tp_atr_mult=3.0, sl_atr_mult_override=1.5, enable_d1_bias_gate=True,
    )
    strat = TightStopStrategy("scr", 9911, rule, SESS_ALL)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([strat], start_ts=_ts(START), end_ts=_ts(END))
    pl = np.array([t.net_pl for t in res.trades])
    return pl


def _random_rule(freq, seed):
    """Fire +/-1 at random on `freq` fraction of bars."""
    rng = np.random.default_rng(seed)
    def rule(f):
        n = len(f["close"])
        s = np.zeros(n, dtype=np.int8)
        pick = rng.random(n) < freq
        s[pick] = rng.choice([-1, 1], pick.sum())
        return s
    return rule


print(f"{START} -> {END} | ${BAL} | 0.01 lots | ALL sessions | 3.0/1.5 ATR | realistic\n")

for name, cid in TARGETS:
    rule = lib[cid].rule
    pl = run_candidate(rule)
    if not len(pl):
        print(f"{name:18s}  NO TRADES"); continue
    w = pl[pl > 0]; l = pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    freq = len(pl) / 9600.0  # ~bars in window

    # random control at matched frequency
    rand_pfs = []
    for k in range(20):
        rpl = run_candidate(_random_rule(freq, 1000 + k))
        if len(rpl):
            rw, rl = rpl[rpl > 0], rpl[rpl < 0]
            rand_pfs.append(rw.sum() / -rl.sum() if len(rl) else 3.0)
    rand_pfs = np.array(rand_pfs)
    p95 = np.percentile(rand_pfs, 95) if len(rand_pfs) else float("nan")
    verdict = "PASS" if pf > p95 else "fail (in the noise)"

    print(f"{name:18s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  | random PF p95={p95:.3f}  -> {verdict}")
