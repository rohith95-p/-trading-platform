"""LOOP iteration 1 -- improve the FVG_NY leg (the weakest, most spread-sensitive).

FVG_NY fires on ANY 3-bar gap. Isolated, a minimum gap-size filter took it from
PF 1.66 -> 2.11 (scripts/luxalgo_fvg_ab.py). This tests that filter INSIDE the
full 4-leg portfolio, plus an ATR-relative gap filter.

  baseline           : FVG_NY as-is (any gap)
  min gap 0.03% price : ~$1.3 minimum gap
  min gap 0.05% price : ~$2.2
  min gap 0.10% price : ~$4.4
  min gap 0.5x ATR    : gap must be at least half the ATR

Only the FVG leg is wrapped; the other 3 legs are untouched.

    python -m scripts.fvg_improve_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4, FVGNYTight
from src.strategies.base_strategy import Signal, mt5
from src.research.market_study import build_features, session_mask, atr as _atr


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


class FVGSized:
    """FVGNYTight, but the gap must clear a minimum size."""
    def __init__(self, mode):
        self._base = FVGNYTight()
        self._mode = mode        # ("pct", x) or ("atr", x) or ("none", 0)
        self.name = self._base.name
        self.magic = self._base.magic
        self.execute_immediately = True
        self.session = self._base.session
        self.sl_atr_mult = self._base.sl_atr_mult
        self.tp_atr_mult = self._base.tp_atr_mult
        self._min_bars = self._base._min_bars

    def check_pending_confirmation(self, m15):
        return None

    def set_pending(self, s, t):
        pass

    def evaluate(self, m15_rates, m5_rates=None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        h, l = f["high"], f["low"]
        h2 = np.concatenate([[np.nan, np.nan], h[:-2]])
        l2 = np.concatenate([[np.nan, np.nan], l[:-2]])
        bull_gap = l - h2          # >0 when a bullish gap exists
        bear_gap = l2 - h          # >0 when a bearish gap exists
        j = -2
        mask = session_mask(f["ist_hour"], self.session)[j]
        if not mask:
            return None

        kind, x = self._mode
        if kind == "pct":
            thr_up = x / 100.0 * f["close"][j]
            thr_dn = thr_up
        elif kind == "atr":
            a = _atr(m15_rates, 14)[j]
            thr_up = thr_dn = x * a
        else:
            thr_up = thr_dn = 0.0

        if bull_gap[j] > max(thr_up, 0):
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        if bear_gap[j] > max(thr_dn, 0):
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                          magic=self.magic, is_buy=False)
        return None


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2026-05-21", "2026-08-29", 105.74
OTHER = [c for c in PORTFOLIO_V4 if c is not FVGNYTight]


def run(fvg_leg):
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, direction_gate="d1_ema20",
    )
    legs = [c() for c in OTHER] + [fvg_leg]
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run(legs, start_ts=_ts(START), end_ts=_ts(END))
    return res


print(f"{START} -> {END} | ${BAL} | 0.01 | 4 legs | FVG leg gets a min-gap filter\n")
VARIANTS = [
    ("baseline (any gap)",      FVGNYTight()),
    ("min gap 0.03% price",     FVGSized(("pct", 0.03))),
    ("min gap 0.05% price",     FVGSized(("pct", 0.05))),
    ("min gap 0.10% price",     FVGSized(("pct", 0.10))),
    ("min gap 0.5x ATR",        FVGSized(("atr", 0.5))),
]
for label, leg in VARIANTS:
    res = run(leg)
    pl = np.array([t.net_pl for t in res.trades])
    fvg = np.array([t.net_pl for t in res.trades if t.strategy == "FVG_NY_TIGHT"])
    if not len(pl):
        print(f"{label:22s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    fpf = fvg[fvg > 0].sum() / -fvg[fvg < 0].sum() if (fvg < 0).any() else float("inf")
    print(f"{label:22s}  total n={len(pl):3d} PF={pf:5.3f} net=${pl.sum():7.2f} DD={dd:4.1f}%  "
          f"| FVG leg: n={len(fvg):3d} net=${fvg.sum():7.2f} PF={fpf:5.2f}")
