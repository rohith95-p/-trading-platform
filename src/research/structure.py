"""Market-structure primitives -- BigBeluga "MS Trend Matrix" logic, reduced to
strictly backward-looking arithmetic for backtesting and analysis.

What this gives you, per bar:
  - confirmed pivot highs / lows (swing points the market actually printed)
  - the active swing-high and swing-low level at each bar (structural S/R)
  - a binary trend state that flips on a close through the last opposite pivot
  - BOS vs CHoCH classification of each flip / continuation

Nothing here looks ahead: a pivot at bar p is only *visible* from bar p+length
onward (that is BigBeluga's `ta.pivothigh(len, len)` -- a len-bar lookahead that
we honour by shifting confirmation forward).

Optional volatility-swap (LuxAlgo trick): on a bar whose range >= k*ATR(200),
use the opposite extreme for pivot detection, so blow-off bars don't define
false pivots.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from src.research.market_study import atr as _atr_struct


BULLISH = 1
BEARISH = -1


def _pivot_raw(x: np.ndarray, length: int, want_high: bool) -> np.ndarray:
    """Index p is a pivot if x[p] is the strict extreme of x[p-length : p+length+1].
    Returns a bool array marked at p (NOT shifted for confirmation yet)."""
    n = len(x)
    out = np.zeros(n, dtype=bool)
    for p in range(length, n - length):
        w = x[p - length: p + length + 1]
        if want_high:
            if x[p] == w.max() and (w == x[p]).sum() == 1:
                out[p] = True
        else:
            if x[p] == w.min() and (w == x[p]).sum() == 1:
                out[p] = True
    return out


def compute(rates: np.ndarray, length: int = 10,
            vol_swap_k: float = 0.0) -> Dict[str, np.ndarray]:
    """Full structure frame.

    Args:
        rates: structured array with high/low/close (and time).
        length: pivot lookback == lookahead (BigBeluga msLen, default 10).
        vol_swap_k: if > 0, swap high/low for pivot detection on bars whose
            range >= vol_swap_k * ATR(200). 2.0 matches LuxAlgo. 0 disables.

    Returns dict of per-bar arrays:
        pivot_high_val / pivot_low_val : the last CONFIRMED pivot level, forward
            filled, visible only from confirmation bar onward.
        trend       : +1 / -1, BigBeluga binary state.
        event       : +2 bull CHoCH, +1 bull BOS, -1 bear BOS, -2 bear CHoCH, 0.
        dist_to_ph / dist_to_pl : (close - pivot) in price units.
    """
    h = rates["high"].astype(float)
    l = rates["low"].astype(float)
    c = rates["close"].astype(float)
    n = len(c)

    ph_src, pl_src = h, l
    if vol_swap_k > 0:
        a200 = _atr_struct(rates, 200)
        rng = h - l
        with np.errstate(invalid="ignore"):
            spike = rng >= vol_swap_k * np.nan_to_num(a200, nan=np.inf)
        ph_src = np.where(spike, l, h)
        pl_src = np.where(spike, h, l)

    is_ph = _pivot_raw(ph_src, length, True)
    is_pl = _pivot_raw(pl_src, length, False)

    pivot_high_val = np.full(n, np.nan)
    pivot_low_val = np.full(n, np.nan)
    trend = np.zeros(n, dtype=np.int8)
    event = np.zeros(n, dtype=np.int8)

    last_ph = np.nan
    last_pl = np.nan
    last_ph_bar = -1
    last_pl_bar = -1
    state = BEARISH  # BigBeluga seeds `direction = false`

    # LuxAlgo-style order blocks: the origin candle of the move that broke
    # structure. We track the most recent unmitigated block of each side.
    bull_ob_hi = np.full(n, np.nan)
    bull_ob_lo = np.full(n, np.nan)
    bear_ob_hi = np.full(n, np.nan)
    bear_ob_lo = np.full(n, np.nan)
    cur_bull_hi = cur_bull_lo = np.nan
    cur_bear_hi = cur_bear_lo = np.nan

    for i in range(n):
        # a pivot at bar (i - length) becomes visible now
        src_bar = i - length
        if src_bar >= 0:
            if is_ph[src_bar]:
                last_ph = h[src_bar]
                last_ph_bar = src_bar
            if is_pl[src_bar]:
                last_pl = l[src_bar]
                last_pl_bar = src_bar

        # crossover / crossunder of the last confirmed pivot by the close
        prev_c = c[i - 1] if i > 0 else c[i]
        broke_up = (not np.isnan(last_ph)) and prev_c <= last_ph < c[i]
        broke_dn = (not np.isnan(last_pl)) and prev_c >= last_pl > c[i]

        if broke_up and state == BEARISH:
            state = BULLISH
            event[i] = 2          # bullish CHoCH (trend flip up)
        elif broke_dn and state == BULLISH:
            state = BEARISH
            event[i] = -2         # bearish CHoCH (trend flip down)
        elif broke_up and state == BULLISH:
            event[i] = 1          # bullish BOS (continuation)
        elif broke_dn and state == BEARISH:
            event[i] = -1         # bearish BOS (continuation)

        # order block: on any bullish break, the origin candle is the lowest
        # (parsed) low from the pivot that was broken to here; mirror for bearish.
        if broke_up and last_ph_bar >= 0:
            seg = pl_src[last_ph_bar:i + 1]
            ob = last_ph_bar + int(np.argmin(seg))
            cur_bull_hi, cur_bull_lo = h[ob], l[ob]
        if broke_dn and last_pl_bar >= 0:
            seg = ph_src[last_pl_bar:i + 1]
            ob = last_pl_bar + int(np.argmax(seg))
            cur_bear_hi, cur_bear_lo = h[ob], l[ob]

        # mitigation: block is gone once price closes through its far edge
        if not np.isnan(cur_bull_lo) and c[i] < cur_bull_lo:
            cur_bull_hi = cur_bull_lo = np.nan
        if not np.isnan(cur_bear_hi) and c[i] > cur_bear_hi:
            cur_bear_hi = cur_bear_lo = np.nan

        trend[i] = state
        pivot_high_val[i] = last_ph
        pivot_low_val[i] = last_pl
        bull_ob_hi[i], bull_ob_lo[i] = cur_bull_hi, cur_bull_lo
        bear_ob_hi[i], bear_ob_lo[i] = cur_bear_hi, cur_bear_lo

    return {
        "pivot_high_val": pivot_high_val,
        "pivot_low_val": pivot_low_val,
        "trend": trend,
        "event": event,
        "dist_to_ph": c - pivot_high_val,
        "dist_to_pl": c - pivot_low_val,
        "bull_ob_hi": bull_ob_hi,
        "bull_ob_lo": bull_ob_lo,
        "bear_ob_hi": bear_ob_hi,
        "bear_ob_lo": bear_ob_lo,
    }


def trend_series(rates: np.ndarray, length: int = 10) -> np.ndarray:
    """Just the +1/-1 trend state -- for use as a direction gate."""
    return compute(rates, length)["trend"]


def _compute_from_arrays(h: np.ndarray, l: np.ndarray, c: np.ndarray,
                         length: int = 10) -> Dict[str, np.ndarray]:
    """Same as compute() but takes bare arrays (feature-dict friendly).
    No vol-swap (needs true-range, not available here)."""
    rec = np.empty(len(c), dtype=[("high", float), ("low", float), ("close", float)])
    rec["high"], rec["low"], rec["close"] = h, l, c
    return compute(rec, length, vol_swap_k=0.0)
