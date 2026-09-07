"""Confluence A/B: do BigBeluga structure trend and LuxAlgo order blocks improve
the 4 portfolio_v4 legs when used as a FILTER (not as entries)?

Each leg's own entry rule is unchanged. A signal is only taken if the extra
condition agrees:
  - struct  : M15 structure trend must match the signal direction
  - ob      : price must be within `OB_TOL_ATR` of an unmitigated same-direction
              order block (or inside one)
  - both    : struct AND ob

    python -m scripts.confluence_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from src.strategies.base_strategy import Signal, mt5
from src.research.structure import compute
from src.research.market_study import atr as _atr

OB_TOL_ATR = 1.0


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


class ConfluenceWrap:
    """Wraps a portfolio_v4 leg, vetoing its signal unless confluence agrees."""
    def __init__(self, leg, mode):
        self._leg = leg
        self._mode = mode          # "none" | "struct" | "ob" | "both"
        self.name = leg.name
        self.magic = leg.magic
        self.execute_immediately = getattr(leg, "execute_immediately", True)
        for attr in ("sl_atr_mult", "tp_atr_mult", "session", "candidate_id"):
            if hasattr(leg, attr):
                setattr(self, attr, getattr(leg, attr))

    def check_pending_confirmation(self, m15):
        return None

    def set_pending(self, sig, t):
        pass

    def evaluate(self, m15_rates, m5_rates=None):
        sig = self._leg.evaluate(m15_rates, m5_rates)
        if sig is None or self._mode == "none":
            return sig
        if m15_rates is None or len(m15_rates) < 60:
            return None

        s = compute(m15_rates, 10)
        j = -2  # last closed bar, same index the legs read
        ok = True

        if self._mode in ("struct", "both"):
            tr = s["trend"][j]
            ok = ok and ((tr > 0) == sig.is_buy)

        if self._mode in ("ob", "both"):
            atr = _atr(m15_rates, 14)[j]
            c = float(m15_rates["close"][j])
            if sig.is_buy:
                lo, hi = s["bull_ob_lo"][j], s["bull_ob_hi"][j]
                near = (not np.isnan(lo)) and (lo - OB_TOL_ATR * atr) <= c <= (hi + OB_TOL_ATR * atr)
            else:
                lo, hi = s["bear_ob_lo"][j], s["bear_ob_hi"][j]
                near = (not np.isnan(hi)) and (lo - OB_TOL_ATR * atr) <= c <= (hi + OB_TOL_ATR * atr)
            ok = ok and near

        return sig if ok else None


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2026-05-21", "2026-08-29", 105.74


def run(mode):
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, direction_gate="d1_ema20",
    )
    legs = [ConfluenceWrap(c(), mode) for c in PORTFOLIO_V4]
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run(legs, start_ts=_ts(START), end_ts=_ts(END))
    return np.array([t.net_pl for t in res.trades])


print(f"{START} -> {END} | ${BAL} | 0.01 | 4 legs + D1 EMA20 gate | confluence filter on top\n")
for label, mode in [("baseline (no confluence filter)", "none"),
                    ("+ structure trend agrees",        "struct"),
                    ("+ near an order block",            "ob"),
                    ("+ structure AND order block",      "both")]:
    pl = run(mode)
    if not len(pl):
        print(f"{label:34s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{label:34s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  DD={dd:5.1f}%")
