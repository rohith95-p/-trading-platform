"""QQE signals (colinmck, Pine v4) -- tested three ways on the current holdout.

QQE standalone was already found to fail (324 trades, PF 0.87, account to
$4.50). Re-running only that would tell us nothing new. The question worth
asking is whether QQE adds anything to the leg we are ACTUALLY running --
FVG_NY -- as a directional filter.

Faithful port of the Pine logic:
    Rsi          = rsi(close, 14)
    RsiMa        = ema(Rsi, 5)
    AtrRsi       = abs(RsiMa[1] - RsiMa)
    MaAtrRsi     = ema(AtrRsi, 27)          # Wilders_Period = 14*2-1
    dar          = ema(MaAtrRsi, 27) * 4.238
    longband/shortband trail; trend flips on cross; FastAtrRsiTL follows trend
    qqeLong fires on the FIRST bar FastAtrRsiTL < RSIndex (QQExlong == 1)
    qqeShort fires on the FIRST bar FastAtrRsiTL > RSIndex

Three variants:
  A  FVG_NY alone                     (baseline -- what we run today)
  B  FVG_NY, but only when QQE trend AGREES with the signal direction
  C  QQE signals standalone           (reproduce the known failure on our window)

    python -m scripts.validation.qqe_test
"""
from __future__ import annotations

import json
import os
from typing import Optional, Tuple

import numpy as np

from src.strategies.portfolio_v4 import FVGNYTight
from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.market_study import build_features, session_mask
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)

SIMS = 10000
DAYS = 505
RSI_PERIOD, SF, QQE_FACTOR = 14, 5, 4.238
WILDERS = RSI_PERIOD * 2 - 1


def _ema(a: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    k = 2.0 / (period + 1.0)
    seed = None
    for i, v in enumerate(a):
        if not np.isfinite(v):
            continue
        seed = v if seed is None else (v - seed) * k + seed
        out[i] = seed
    return out


def _rsi(close: np.ndarray, period: int) -> np.ndarray:
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    d = np.diff(close)
    gain, loss = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    ag, al = gain[:period].mean(), loss[:period].mean()
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, n):
        ag = (ag * (period - 1) + gain[i - 1]) / period
        al = (al * (period - 1) + loss[i - 1]) / period
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def qqe_trend(close: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (trend, fired) where trend is +1/-1 per bar and `fired` is
    +1/-1 only on the bar the cross first happens (the Pine label bars)."""
    rsi = _rsi(close, RSI_PERIOD)
    rsi_ma = _ema(rsi, SF)
    atr_rsi = np.full(len(close), np.nan)
    atr_rsi[1:] = np.abs(rsi_ma[:-1] - rsi_ma[1:])
    dar = _ema(_ema(atr_rsi, WILDERS), WILDERS) * QQE_FACTOR

    n = len(close)
    longband = np.zeros(n)
    shortband = np.zeros(n)
    trend = np.ones(n)
    for i in range(1, n):
        if not (np.isfinite(rsi_ma[i]) and np.isfinite(dar[i])):
            longband[i], shortband[i], trend[i] = longband[i-1], shortband[i-1], trend[i-1]
            continue
        r, rp, d = rsi_ma[i], rsi_ma[i-1], dar[i]
        nl, ns = r - d, r + d
        longband[i] = max(longband[i-1], nl) if (rp > longband[i-1] and r > longband[i-1]) else nl
        shortband[i] = min(shortband[i-1], ns) if (rp < shortband[i-1] and r < shortband[i-1]) else ns
        # cross(RSIndex, shortband[1]) -> 1 ; cross(longband[1], RSIndex) -> -1
        up_cross = (rp <= shortband[i-1]) and (r > shortband[i-1])
        dn_cross = (longband[i-1] <= rp) and (longband[i-1] > r)
        trend[i] = 1 if up_cross else (-1 if dn_cross else trend[i-1])

    tl = np.where(trend == 1, longband, shortband)
    above = tl < rsi_ma          # QQExlong condition
    fired = np.zeros(n)
    for i in range(1, n):
        if not np.isfinite(rsi_ma[i]):
            continue
        if above[i] and not above[i-1]:
            fired[i] = 1
        elif (not above[i]) and above[i-1]:
            fired[i] = -1
    qtrend = np.where(above, 1, -1)
    return qtrend, fired


class FVGQQEFiltered(FVGNYTight):
    """FVG_NY, taken only when QQE's trend agrees with the direction."""
    name = "FVG_NY_QQE"

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        sig = super().evaluate(m15_rates, m5_rates)
        if sig is None:
            return None
        qt, _ = qqe_trend(np.asarray(m15_rates["close"], dtype=float))
        t = qt[-2]
        if (sig.is_buy and t != 1) or ((not sig.is_buy) and t != -1):
            return None
        return sig


class QQEStandalone(BaseStrategy):
    """The Pine script's own long/short labels, traded directly."""
    name = "QQE_STANDALONE"
    magic = 3098
    session = (11.5, 21.5)          # owner's trading window
    sl_atr_mult = 0.75
    tp_atr_mult = 3.0
    execute_immediately = True
    _min_bars = 250

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        if not bool(session_mask(f["ist_hour"], self.session)[-2]):
            return None
        _, fired = qqe_trend(np.asarray(m15_rates["close"], dtype=float))
        s = fired[-2]
        if s == 0:
            return None
        return Signal(direction=mt5.ORDER_TYPE_BUY if s > 0 else mt5.ORDER_TYPE_SELL,
                      strategy_name=self.name, magic=self.magic, is_buy=bool(s > 0))

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


def mc(pl: np.ndarray) -> dict:
    if len(pl) < 2:
        return dict(p_ruin_pct=None)
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    return dict(p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2))


def main():
    bars = _bars()
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    rows = {}
    print(f"QQE test, holdout {HOLDOUT_START} -> {HOLDOUT_END}, STANDARD 0.01 lot, "
          f"1 position\n")
    print(f"{'variant':<32} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>7} {'$/day':>7} {'P(ruin)':>8} {'I.1':>5}")
    print("-" * 104)
    for label, strat in (("A  FVG alone (baseline)", FVGNYTight()),
                         ("B  FVG + QQE trend filter", FVGQQEFiltered()),
                         ("C  QQE standalone", QQEStandalone())):
        res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, [strat])
        s = stats(res.trades)
        v = verdict(s)
        m = mc(np.array([t.net_pl for t in res.trades]))
        per_day = round(s.get("net", 0) / DAYS, 2) if s.get("n") else 0.0
        rows[label] = dict(stats=s, verdict=v, mc=m, usd_per_day=per_day)
        print(f"{label:<32} {s.get('n',0):>5} {s.get('win_rate',0):>6.1f} "
              f"{s.get('profit_factor','-'):>7} {s.get('net','-'):>9} "
              f"{s.get('min_balance','-'):>8} {s.get('max_drawdown_pct','-'):>6}% "
              f"{per_day:>7} {str(m.get('p_ruin_pct')):>8} "
              f"{'PASS' if v['passed'] else 'FAIL':>5}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/qqe_test.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)
    print("\n--> research/validation/qqe_test.json")


if __name__ == "__main__":
    main()
