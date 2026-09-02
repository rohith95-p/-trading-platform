"""Is the LuxAlgo FVG definition better than the live one?

The live FVG_NY leg (XAU-092 / _c_fvg) fires on ANY 3-bar gap, any size.
LuxAlgo adds two conditions: a close confirmation on the middle bar, and a
minimum gap size as a % of price. This tests whether those filter out losers
or just cut the sample.

Same window / session / SL-TP as the live leg so only the entry rule changes.

    python -m scripts.luxalgo_fvg_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from scripts.phase3_worker import TightStopStrategy


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _shift(a, n):
    out = np.full(len(a), np.nan)
    if n < len(a):
        out[n:] = a[:len(a) - n]
    return out


def _sig(lo, sh):
    s = np.zeros(len(lo), dtype=np.int8)
    s[np.nan_to_num(lo).astype(bool)] = 1
    s[np.nan_to_num(sh).astype(bool)] = -1
    return s


def live_fvg(f):
    """Current live rule: bar[i-2].high < bar[i].low. Any size."""
    return _sig(_shift(f["high"], 2) < f["low"], _shift(f["low"], 2) > f["high"])


def luxalgo_fvg(threshold_pct):
    """LuxAlgo: + middle-bar close confirmation + minimum gap size."""
    def rule(f):
        h2, l2 = _shift(f["high"], 2), _shift(f["low"], 2)
        c1 = _shift(f["close"], 1)
        t = threshold_pct / 100.0
        with np.errstate(invalid="ignore", divide="ignore"):
            bull = (f["low"] > h2) & (c1 > h2) & ((f["low"] - h2) / h2 > t)
            bear = (f["high"] < l2) & (c1 < l2) & ((l2 - f["high"]) / f["high"] > t)
        return _sig(bull, bear)
    return rule


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2026-05-21", "2026-08-29", 105.74
NY = (17.5, 21.5)

VARIANTS = [
    ("LIVE      _c_fvg, any gap", live_fvg),
    ("Lux t=0.00%  +close confirm only", luxalgo_fvg(0.00)),
    ("Lux t=0.02%  (~$0.9 gap)", luxalgo_fvg(0.02)),
    ("Lux t=0.05%  (~$2.2 gap)", luxalgo_fvg(0.05)),
    ("Lux t=0.10%  (~$4.4 gap)", luxalgo_fvg(0.10)),
    ("Lux t=0.20%  (~$8.7 gap)", luxalgo_fvg(0.20)),
]

print(f"{START} -> {END} | NY session | SL 0.5xATR / TP 2.5xATR | 0.01 lots | realistic costs\n")

for label, rule in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=900, warmup_bars=950, daily_loss_limit_mode="off",
        tp_atr_mult=2.5, sl_atr_mult_override=0.5, enable_d1_bias_gate=True,
    )
    strat = TightStopStrategy("fvg_test", 3013, rule, NY)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([strat], start_ts=_ts(START), end_ts=_ts(END))

    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:36s}  NO TRADES")
        continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{label:36s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  "
          f"PF={pf:6.3f}  net=${pl.sum():8.2f}  maxDD={dd:5.1f}%")
