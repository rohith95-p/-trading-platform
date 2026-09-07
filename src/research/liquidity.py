"""LuxAlgo-style liquidity context, ported from the pasted 'Buyside & Sellside
Liquidity' Pine script -- used as a FILTER on the existing FVG signal, not as
its own trigger. Validated 2026-09-07 (HYP-059/060): the sweep filter and a
size-based "void" filter each independently improved FVG_NY's risk profile,
and the union of the two (sweep_or_void) beat plain FVG on both drawdown and
ruin probability across every session tested.

Two ideas extracted from the script:

  LIQUIDITY SWEEP: the script clusters 3+ pivot highs/lows within atr/margin
  of each other into a "level," and marks it breached once price trades
  through it. The idea: a gap forming just after such a breach is a footprint
  of forced flow (stops actually being run), not drift.

  LIQUIDITY VOID: the script's own literal definition of a bullish void is
        low - high[2] > atr(200)  and  low > high[2]  and  close[1] > high[2]
  which is an FVG with a minimum-size threshold set by the market's own
  long-run volatility (ATR200) rather than an arbitrary % of price.

Both are strictly backward-looking: a pivot at bar p is only usable once
p + PIVOT_LEN + 1 bars have passed, matching the Pine script's own `[1]`
right-side offset.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

PIVOT_LEN = 7           # script's "Detection Length" default
LIQ_MARGIN = 10 / 6.9   # script's default margin -> atr / liqMar
MIN_CLUSTER = 3          # script requires count > 2


def _atr_local(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR from raw arrays (liquidity_state needs values mid-array,
    where src/research/market_study.atr()'s structured-dtype input doesn't fit)."""
    n = len(high)
    tr = np.full(n, np.nan)
    tr[1:] = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
    out = np.full(n, np.nan)
    if n > period:
        out[period] = np.nanmean(tr[1:period + 1])
        for i in range(period + 1, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def liquidity_state(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                    lookback_breach: int = 12) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (buy_swept, sell_swept) bool arrays: was a clustered liquidity
    level breached within the last `lookback_breach` bars."""
    n = len(high)
    atr10 = _atr_local(high, low, close, 10)
    ph_idx, pl_idx = [], []
    for i in range(PIVOT_LEN + 1, n - 1):
        w_h = high[i - PIVOT_LEN:i + 2]
        if high[i] == w_h.max() and np.argmax(w_h) == PIVOT_LEN:
            ph_idx.append(i)
        w_l = low[i - PIVOT_LEN:i + 2]
        if low[i] == w_l.min() and np.argmin(w_l) == PIVOT_LEN:
            pl_idx.append(i)

    buy_swept = np.zeros(n, dtype=bool)
    sell_swept = np.zeros(n, dtype=bool)

    def build(pivots, prices, is_buy):
        levels = []
        for k, p in enumerate(pivots):
            confirm = p + PIVOT_LEN + 1
            if confirm >= n or not np.isfinite(atr10[confirm]):
                continue
            band = atr10[confirm] / LIQ_MARGIN
            cluster = [prices[q] for q in pivots[max(0, k - 20):k + 1]
                       if abs(prices[q] - prices[p]) <= band]
            if len(cluster) >= MIN_CLUSTER:
                mid = float(np.mean([min(cluster), max(cluster)]))
                levels.append((confirm, mid - band, mid + band))
        for confirm, lo_b, hi_b in levels:
            for j in range(confirm, min(confirm + 500, n)):
                if is_buy and high[j] > hi_b:
                    buy_swept[j:min(j + lookback_breach, n)] = True
                    break
                if (not is_buy) and low[j] < lo_b:
                    sell_swept[j:min(j + lookback_breach, n)] = True
                    break

    build(ph_idx, high, True)
    build(pl_idx, low, False)
    return buy_swept, sell_swept


def is_liquidity_void(h2: float, l2: float, hi_i: float, lo_i: float, close_prev: float,
                      atr200: float, mult: float = 1.0):
    """Bullish/bearish void per the script's own definition, gap-size
    threshold set by ATR200. Returns (is_bull_void, is_bear_void)."""
    if not np.isfinite(atr200):
        return False, False
    bull = (lo_i - h2) > atr200 * mult and lo_i > h2 and close_prev > h2
    bear = (l2 - hi_i) > atr200 * mult and hi_i < l2 and close_prev < l2
    return bull, bear
