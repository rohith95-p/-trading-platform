"""Candidate setup library.

Every candidate is a pure function from a feature frame to a signal array of
-1 / 0 / +1, evaluated on a CLOSED bar and executed at the open of the next one.
No candidate may read any array position at or beyond its own index.

Design rules, all of them consequences of what the market study measured:

- **No discretionary language.** "Strong candle" is not a rule; `body > 0.7 * range`
  is. Every condition here is arithmetic.
- **Round parameters.** The market study found no sharp structure to fit to, so
  precise thresholds would be fitting noise. Values are round numbers chosen
  before seeing results, and the robustness pass perturbs them afterwards.
- **Each candidate names its failure mode.** If a setup cannot say what would
  make it stop working, it is not a hypothesis.

The families deliberately include mean-reversion and volatility setups, not only
trend continuation, because follow-through measured 48-50% -- continuation
strategies are betting against the measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from src.research.market_study import ema, parabolic_sar

F = Dict[str, np.ndarray]

# Session windows in IST.
ALL_DAY = (0.0, 24.0)
ASIA = (2.5, 11.5)
LONDON = (11.5, 15.5)
OVERLAP = (15.5, 17.5)
NY = (17.5, 21.5)
LONDON_NY = (11.5, 21.5)
NY_WIDE = (17.5, 23.0)


@dataclass
class Candidate:
    id: str
    name: str
    family: str
    hypothesis: str
    failure_mode: str
    rule: Callable[[F], np.ndarray]
    session: Tuple[float, float] = ALL_DAY
    tp_atr: float = 3.0
    sl_atr: float = 1.5
    max_bars: int = 96
    timeframe: str = "M15"
    params: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# helpers -- all strictly backward-looking
# ---------------------------------------------------------------------------


def _shift(a: np.ndarray, n: int) -> np.ndarray:
    """a[i-n], NaN-padded. Guarantees no forward reference."""
    out = np.full(len(a), np.nan)
    if n < len(a):
        out[n:] = a[:len(a) - n]
    return out


def _roll_max(a: np.ndarray, w: int) -> np.ndarray:
    """Max of the w bars ENDING AT i-1 (excludes the current bar)."""
    out = np.full(len(a), np.nan)
    for i in range(w, len(a)):
        out[i] = a[i - w:i].max()
    return out


def _roll_min(a: np.ndarray, w: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    for i in range(w, len(a)):
        out[i] = a[i - w:i].min()
    return out


def _roll_mean(a: np.ndarray, w: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    cs = np.nancumsum(np.nan_to_num(a))
    out[w:] = (cs[w:] - cs[:-w]) / w
    return out


def _roll_std(a: np.ndarray, w: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    for i in range(w, len(a)):
        out[i] = a[i - w:i].std()
    return out


def _body(f: F) -> np.ndarray:
    return np.abs(f["close"] - f["open"])


def _range(f: F) -> np.ndarray:
    return np.maximum(f["high"] - f["low"], 1e-9)


def _upper_wick(f: F) -> np.ndarray:
    return f["high"] - np.maximum(f["close"], f["open"])


def _lower_wick(f: F) -> np.ndarray:
    return np.minimum(f["close"], f["open"]) - f["low"]


def _sig(long_mask: np.ndarray, short_mask: np.ndarray) -> np.ndarray:
    s = np.zeros(len(long_mask), dtype=np.int8)
    s[np.nan_to_num(long_mask).astype(bool)] = 1
    s[np.nan_to_num(short_mask).astype(bool)] = -1
    return s


# ---------------------------------------------------------------------------
# FAMILY 1 -- Trend / continuation
#
# Measured follow-through is 48-50%, so this family is expected to fail. It is
# included precisely so that expectation is tested rather than assumed, and
# because the three live strategies belong to it.
# ---------------------------------------------------------------------------


def _c_ema_stack(f: F) -> np.ndarray:
    up = (f["ema20"] > f["ema50"]) & (f["ema50"] > f["ema200"]) & (f["close"] > f["ema20"])
    dn = (f["ema20"] < f["ema50"]) & (f["ema50"] < f["ema200"]) & (f["close"] < f["ema20"])
    return _sig(up, dn)


def _c_donchian_break(f: F, w: int = 20) -> np.ndarray:
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    return _sig(f["close"] > hh, f["close"] < ll)


def _c_donchian_break_adx(f: F, w: int = 20, adx_min: float = 25.0) -> np.ndarray:
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    t = f["adx14"] > adx_min
    return _sig((f["close"] > hh) & t, (f["close"] < ll) & t)


def _c_pullback_ema20(f: F) -> np.ndarray:
    up = (f["ema50"] > f["ema200"]) & (_shift(f["low"], 1) <= f["ema20"]) & (f["close"] > f["ema20"])
    dn = (f["ema50"] < f["ema200"]) & (_shift(f["high"], 1) >= f["ema20"]) & (f["close"] < f["ema20"])
    return _sig(up, dn)


def _c_momentum_roc(f: F, w: int = 12, k: float = 1.0) -> np.ndarray:
    roc = (f["close"] - _shift(f["close"], w)) / f["atr14"]
    return _sig(roc > k, roc < -k)


def _c_higher_high_structure(f: F, w: int = 10) -> np.ndarray:
    hh1, hh2 = _roll_max(f["high"], w), _shift(_roll_max(f["high"], w), w)
    ll1, ll2 = _roll_min(f["low"], w), _shift(_roll_min(f["low"], w), w)
    return _sig((hh1 > hh2) & (ll1 > ll2) & (f["close"] > f["ema20"]),
                (hh1 < hh2) & (ll1 < ll2) & (f["close"] < f["ema20"]))


# ---------------------------------------------------------------------------
# FAMILY 2 -- Mean reversion
#
# Autocorrelation at lag 4 was -0.019: weakly negative. If anything on M15 has a
# structural basis it is this family, so it gets the widest coverage.
# ---------------------------------------------------------------------------


def _c_zscore_revert(f: F, w: int = 40, k: float = 2.0) -> np.ndarray:
    m, s = _roll_mean(f["close"], w), _roll_std(f["close"], w)
    z = (f["close"] - m) / np.maximum(s, 1e-9)
    return _sig(z < -k, z > k)


def _c_bb_fade(f: F, w: int = 20, k: float = 2.0) -> np.ndarray:
    m, s = _roll_mean(f["close"], w), _roll_std(f["close"], w)
    up, lo = m + k * s, m - k * s
    return _sig((f["low"] < lo) & (f["close"] > lo), (f["high"] > up) & (f["close"] < up))


def _c_rsi_extreme(f: F, lo: float = 25.0, hi: float = 75.0) -> np.ndarray:
    r, rp = f["rsi14"], _shift(f["rsi14"], 1)
    return _sig((rp < lo) & (r >= lo), (rp > hi) & (r <= hi))


def _c_atr_exhaustion(f: F, k: float = 2.5, w: int = 8) -> np.ndarray:
    move = (f["close"] - _shift(f["close"], w)) / f["atr14"]
    return _sig(move < -k, move > k)


def _c_range_rejection(f: F, w: int = 24) -> np.ndarray:
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    lw, uw, rg = _lower_wick(f), _upper_wick(f), _range(f)
    return _sig((f["low"] <= ll) & (lw / rg > 0.5), (f["high"] >= hh) & (uw / rg > 0.5))


def _c_failed_breakout(f: F, w: int = 20) -> np.ndarray:
    """Price breaks a level then closes back inside -- the sweep-and-reverse core."""
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    return _sig((f["low"] < ll) & (f["close"] > ll) & (f["close"] > f["open"]),
                (f["high"] > hh) & (f["close"] < hh) & (f["close"] < f["open"]))


def _c_vwap_revert(f: F, w: int = 48, k: float = 1.5) -> np.ndarray:
    """Session-agnostic rolling VWAP proxy using tick volume."""
    pv = f["close"] * f["volume"]
    vw = _roll_mean(pv, w) / np.maximum(_roll_mean(f["volume"], w), 1e-9)
    d = (f["close"] - vw) / f["atr14"]
    return _sig(d < -k, d > k)


# ---------------------------------------------------------------------------
# FAMILY 3 -- Volatility regime
# ---------------------------------------------------------------------------


def _c_squeeze_break(f: F, w: int = 20) -> np.ndarray:
    """Bollinger inside Keltner, then a close outside the band."""
    m, s = _roll_mean(f["close"], w), _roll_std(f["close"], w)
    bb_up, bb_lo = m + 2 * s, m - 2 * s
    kc_up, kc_lo = m + 1.5 * f["atr14"], m - 1.5 * f["atr14"]
    sq = _shift((bb_up < kc_up) & (bb_lo > kc_lo), 1).astype(bool)
    return _sig(sq & (f["close"] > bb_up), sq & (f["close"] < bb_lo))


def _c_atr_expansion(f: F, k: float = 1.5) -> np.ndarray:
    a_prev = _roll_mean(f["atr14"], 20)
    exp_ = f["atr14"] > k * a_prev
    return _sig(exp_ & (f["close"] > f["open"]), exp_ & (f["close"] < f["open"]))


def _c_nr7_break(f: F, w: int = 7) -> np.ndarray:
    """Narrowest range in w bars, then break of that bar's extreme."""
    rg = _range(f)
    narrow = _shift(rg, 1) <= _shift(_roll_min(rg, w), 1)
    return _sig(narrow & (f["close"] > _shift(f["high"], 1)),
                narrow & (f["close"] < _shift(f["low"], 1)))


def _c_low_vol_revert(f: F, k: float = 0.7) -> np.ndarray:
    """Mean reversion, but only when volatility is compressed."""
    quiet = f["atr14"] < k * _roll_mean(f["atr14"], 50)
    m, s = _roll_mean(f["close"], 20), _roll_std(f["close"], 20)
    z = (f["close"] - m) / np.maximum(s, 1e-9)
    return _sig(quiet & (z < -1.5), quiet & (z > 1.5))


# ---------------------------------------------------------------------------
# FAMILY 4 -- Session / time structure
#
# The market study found NY (17:30-21:30 IST) carries ~50% more range than
# London, contradicting the project's "London is golden" architecture.
# ---------------------------------------------------------------------------


def _c_orb(f: F, w: int = 4) -> np.ndarray:
    """Opening-range break of the first w bars of the active session."""
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    return _sig(f["close"] > hh, f["close"] < ll)


def _c_session_sweep_revert(f: F, w: int = 32) -> np.ndarray:
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    return _sig((f["low"] < ll) & (f["close"] > ll),
                (f["high"] > hh) & (f["close"] < hh))


def _c_prev_day_level(f: F, w: int = 96) -> np.ndarray:
    """Reaction at the previous 24h high/low (96 M15 bars)."""
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    return _sig((f["low"] <= ll) & (f["close"] > ll),
                (f["high"] >= hh) & (f["close"] < hh))


# ---------------------------------------------------------------------------
# FAMILY 5 -- Market structure / liquidity
#
# The institutional concepts, reduced to arithmetic. No "order block" here has
# any meaning beyond what is written in the code.
# ---------------------------------------------------------------------------


def _c_displacement(f: F, k: float = 1.5) -> np.ndarray:
    """A bar whose body exceeds k*ATR, taken as continuation."""
    big = _body(f) > k * f["atr14"]
    return _sig(big & (f["close"] > f["open"]), big & (f["close"] < f["open"]))


def _c_fvg(f: F) -> np.ndarray:
    """Fair-value gap: bar i-2 high < bar i low (bullish), strictly backward."""
    h2, l2 = _shift(f["high"], 2), _shift(f["low"], 2)
    return _sig(h2 < f["low"], l2 > f["high"])


def _c_liquidity_sweep(f: F, w: int = 12) -> np.ndarray:
    """Wick through a recent extreme, body closing back inside."""
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    lw, uw, rg = _lower_wick(f), _upper_wick(f), _range(f)
    return _sig((f["low"] < ll) & (f["close"] > ll) & (lw / rg > 0.4),
                (f["high"] > hh) & (f["close"] < hh) & (uw / rg > 0.4))


def _c_bos_retest(f: F, w: int = 20) -> np.ndarray:
    """Break of structure, then a pullback close back through the broken level."""
    hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
    broke_up = _shift((f["close"] > hh).astype(float), 1).astype(bool)
    broke_dn = _shift((f["close"] < ll).astype(float), 1).astype(bool)
    return _sig(broke_up & (f["low"] <= _shift(hh, 1)) & (f["close"] > _shift(hh, 1)),
                broke_dn & (f["high"] >= _shift(ll, 1)) & (f["close"] < _shift(ll, 1)))


def _c_engulfing(f: F) -> np.ndarray:
    po, pc = _shift(f["open"], 1), _shift(f["close"], 1)
    bull = (f["close"] > f["open"]) & (pc < po) & (f["close"] > po) & (f["open"] < pc)
    bear = (f["close"] < f["open"]) & (pc > po) & (f["close"] < po) & (f["open"] > pc)
    return _sig(bull, bear)


def _c_structure_break_choch(f: F, length: int = 10) -> np.ndarray:
    """BigBeluga MS Trend Matrix entry: enter on a structure trend FLIP (CHoCH).
    Long when close crosses the last confirmed pivot high while trend was down;
    short on the mirror."""
    from src.research.structure import _compute_from_arrays
    s = _compute_from_arrays(f["high"], f["low"], f["close"], length)
    ev = s["event"]
    return _sig(ev == 2, ev == -2)


def _c_structure_break_bos(f: F, length: int = 10) -> np.ndarray:
    """Structure CONTINUATION (BOS): close breaks a pivot in the direction of the
    existing trend."""
    from src.research.structure import _compute_from_arrays
    s = _compute_from_arrays(f["high"], f["low"], f["close"], length)
    ev = s["event"]
    return _sig(ev == 1, ev == -1)


def _c_order_block(f: F, length: int = 10) -> np.ndarray:
    """LuxAlgo SMC order block: price returns to the origin candle of the move
    that broke structure, and holds it. Long = wick into an unmitigated bullish
    OB, close back above its low, bullish candle. Mirror for short."""
    from src.research.structure import _compute_from_arrays
    s = _compute_from_arrays(f["high"], f["low"], f["close"], length)
    lo, hi, cl, op = f["low"], f["high"], f["close"], f["open"]
    b_hi, b_lo = s["bull_ob_hi"], s["bull_ob_lo"]
    r_hi, r_lo = s["bear_ob_hi"], s["bear_ob_lo"]
    long_mask = (~np.isnan(b_lo)) & (lo <= b_hi) & (cl >= b_lo) & (cl > op)
    short_mask = (~np.isnan(r_hi)) & (hi >= r_lo) & (cl <= r_hi) & (cl < op)
    return _sig(long_mask, short_mask)


def _c_inside_bar_break(f: F) -> np.ndarray:
    ph, pl = _shift(f["high"], 1), _shift(f["low"], 1)
    pph, ppl = _shift(f["high"], 2), _shift(f["low"], 2)
    inside = _shift(((f["high"] < pph) & (f["low"] > ppl)).astype(float), 0).astype(bool)
    inside = (ph < pph) & (pl > ppl)
    return _sig(inside & (f["close"] > ph), inside & (f["close"] < pl))


# ---------------------------------------------------------------------------
# FAMILY 7 -- Confluence / Multi-condition (new)
#
# These are research candidates based on Parabolic SAR and deep EMA confluence.
# The full 7-condition version is expected to fire rarely; the simple variant
# lets us measure if rarity alone explains any edge.
# ---------------------------------------------------------------------------


def _ema_parabolic_sar(c: np.ndarray, h: np.ndarray, l: np.ndarray,
                       fast: int = 7, mid: int = 21, slow: int = 200,
                       step: float = 0.02, increment: float = 0.02,
                       max_step: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute EMA7/21/200 and Parabolic SAR for the given arrays.

    Returns (e7, e21, e200, sar) as numpy arrays, all same length as input.
    """
    e7 = ema(c, fast)
    e21 = ema(c, mid)
    e200 = ema(c, slow)
    sar = parabolic_sar(h, l, step, increment, max_step)
    return e7, e21, e200, sar


def _c_ema_sar_full(f: F) -> np.ndarray:
    """Full 7-condition SAR confluence: EMA stack + SAR flip + ADX + ChoCh + volume."""
    c, h, l = f["close"], f["high"], f["low"]
    e7, e21, e200, sar = _ema_parabolic_sar(c, h, l)

    # Condition 1: EMA stack aligned
    long_aligned = (e7 > e21) & (e21 > e200)
    short_aligned = (e7 < e21) & (e21 < e200)

    # Condition 2: Price on correct side of EMA7
    c_above = c > e7
    c_below = c < e7

    # Condition 3: SAR flip in trend direction (price crossed SAR)
    sar_long = c > sar
    sar_short = c < sar

    # Condition 4: ADX > 25 (strong trend)
    adx_ok = f["adx14"] > 25.0

    # Condition 5: Change of character (break of prior 5-bar swing)
    swing_bars = 5
    swing_high = _roll_max(h, swing_bars)
    swing_low = _roll_min(l, swing_bars)
    choch_bull = l < swing_low  # break below prior lows
    choch_bear = h > swing_high  # break above prior highs

    # Condition 6: Volume confirmation (M5 preferred, M15 fallback)
    vol_avg = _roll_mean(f["volume"], 20)
    vol_ok = f["volume"] > vol_avg

    # All 7 conditions for LONG
    long_signal = long_aligned & c_above & sar_long & adx_ok & choch_bull & vol_ok
    # All 7 conditions for SHORT
    short_signal = short_aligned & c_below & sar_short & adx_ok & choch_bear & vol_ok

    return _sig(long_signal, short_signal)


def _c_ema_sar_simple(f: F) -> np.ndarray:
    """Simple SAR confluence: EMA200 filter + SAR flip only (no ADX/ChoCh/volume)."""
    c, h, l = f["close"], f["high"], f["low"]
    e7, e21, e200, sar = _ema_parabolic_sar(c, h, l)

    long_signal = (c > e200) & (c > sar)
    short_signal = (c < e200) & (c < sar)

    return _sig(long_signal, short_signal)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _mk(cid, name, family, hyp, fail, fn, **kw) -> Candidate:
    return Candidate(id=cid, name=name, family=family, hypothesis=hyp,
                     failure_mode=fail, rule=fn, **kw)


def build_library() -> List[Candidate]:
    """The full candidate library.

    Each base setup is instantiated across the sessions and exit geometries that
    are plausible for it, which is where the count comes from. Session and exit
    are treated as part of the candidate, not as free parameters to optimise
    after the fact.
    """
    lib: List[Candidate] = []
    n = [0]

    def add(name, family, hyp, fail, fn, sessions, exits, **kw):
        for sess_name, sess in sessions:
            for tp, sl in exits:
                n[0] += 1
                lib.append(_mk(
                    f"XAU-{n[0]:03d}", f"{name} [{sess_name} {tp}/{sl}]", family,
                    hyp, fail, fn, session=sess, tp_atr=tp, sl_atr=sl, **kw))

    SESS_MAIN = [("LONDON", LONDON), ("NY", NY), ("ALL", LONDON_NY)]
    SESS_ALL = [("ALL", ALL_DAY)]
    EX_STD = [(3.0, 1.5), (1.5, 1.5)]
    EX_ONE = [(3.0, 1.5)]

    # --- trend / continuation ---
    add("EMA stack continuation", "trend",
        "Aligned EMAs mark a persistent trend that continues.",
        "Follow-through measured 48-50%; expected to fail.",
        _c_ema_stack, SESS_MAIN, EX_STD)
    add("Donchian-20 breakout", "trend",
        "A 20-bar range break is followed by expansion in the break direction.",
        "Gold breaks and reverts; false breaks dominate.",
        _c_donchian_break, SESS_MAIN, EX_STD)
    add("Donchian-20 breakout + ADX>25", "trend",
        "Breakouts only work when a trend is already established.",
        "ADX is backward-looking; high ADX often marks exhaustion.",
        _c_donchian_break_adx, SESS_MAIN, EX_ONE)
    add("EMA20 pullback continuation", "trend",
        "Pullbacks to the 20 EMA in a stacked trend resume.",
        "This is the live EMAPullback logic; included as the incumbent benchmark.",
        _c_pullback_ema20, SESS_MAIN, EX_STD)
    add("ROC momentum", "trend",
        "Strong recent momentum persists.",
        "Autocorrelation is ~0 at every lag measured.",
        _c_momentum_roc, SESS_MAIN, EX_ONE)
    add("HH/HL structure", "trend",
        "Rising swing structure continues.",
        "Swing definitions are lagging; structure flips after the move.",
        _c_higher_high_structure, SESS_MAIN, EX_ONE)

    # --- mean reversion ---
    add("Z-score reversion (40,2.0)", "mean_reversion",
        "Extreme deviation from a rolling mean reverts.",
        "In a trending regime the deviation extends instead.",
        _c_zscore_revert, SESS_MAIN, EX_STD)
    add("Bollinger band fade", "mean_reversion",
        "Price piercing a 2-sigma band and closing back inside reverts.",
        "Band breaks precede expansion as often as reversion.",
        _c_bb_fade, SESS_MAIN, EX_STD)
    add("RSI extreme exit", "mean_reversion",
        "Leaving an RSI extreme marks reversal onset.",
        "RSI extremes persist in trends.",
        _c_rsi_extreme, SESS_MAIN, EX_STD)
    add("ATR exhaustion fade", "mean_reversion",
        "A move of 2.5 ATR in 8 bars overshoots and retraces.",
        "Exhaustion is only identifiable afterwards.",
        _c_atr_exhaustion, SESS_MAIN, EX_ONE)
    add("Range rejection wick", "mean_reversion",
        "A long wick at a range extreme marks rejection.",
        "Wicks are common; most carry no information.",
        _c_range_rejection, SESS_MAIN, EX_ONE)
    add("Failed breakout reversal", "mean_reversion",
        "Breaking a 20-bar level then closing back inside traps breakout traders.",
        "Requires the reversal to exceed the spread; may be too small.",
        _c_failed_breakout, SESS_MAIN, EX_STD)
    add("Rolling VWAP reversion", "mean_reversion",
        "Deviation from volume-weighted price reverts.",
        "Tick volume is a poor proxy for traded volume.",
        _c_vwap_revert, SESS_MAIN, EX_ONE)

    # --- volatility ---
    add("Squeeze breakout", "volatility",
        "Compression resolves into expansion; direction given by the break.",
        "Compression predicts expansion but not direction.",
        _c_squeeze_break, SESS_MAIN, EX_ONE)
    add("ATR expansion continuation", "volatility",
        "Volatility expansion carries price in the expanding direction.",
        "Expansion is often a spike that immediately reverts.",
        _c_atr_expansion, SESS_MAIN, EX_ONE)
    add("NR7 breakout", "volatility",
        "The narrowest bar in 7 precedes a directional break.",
        "Classic pattern; heavily published, likely arbitraged.",
        _c_nr7_break, SESS_MAIN, EX_ONE)
    add("Low-vol mean reversion", "volatility",
        "Reversion works specifically when volatility is compressed.",
        "Compressed volatility also means small targets relative to spread.",
        _c_low_vol_revert, SESS_MAIN, EX_ONE)

    # --- session / time ---
    add("Opening range break", "session",
        "The first hour of a session sets a range whose break continues.",
        "Gold's session opens are noisy; ORB is widely traded.",
        _c_orb, [("LONDON", LONDON), ("NY", NY), ("ASIA", ASIA)], EX_STD)
    add("Session extreme sweep reversal", "session",
        "Sweeping a session extreme then closing back inside reverses.",
        "Depends on the sweep being liquidity-driven rather than trend.",
        _c_session_sweep_revert, [("LONDON", LONDON), ("NY", NY), ("ALL", LONDON_NY)], EX_STD)
    add("Previous-day level reaction", "session",
        "Prior 24h high/low act as support/resistance.",
        "Levels are self-fulfilling only while widely watched.",
        _c_prev_day_level, [("LONDON", LONDON), ("NY", NY), ("ALL", LONDON_NY)], EX_ONE)

    # --- structure / liquidity ---
    add("Displacement continuation", "structure",
        "An outsized body signals institutional participation and continues.",
        "Large bodies are frequently the end of a move.",
        _c_displacement, SESS_MAIN, EX_ONE)
    add("Fair value gap", "structure",
        "Price gaps leave imbalances that price continues away from.",
        "FVGs on a 24h instrument are mostly noise.",
        _c_fvg, SESS_MAIN, EX_ONE)
    add("Liquidity sweep reversal", "structure",
        "A wick through a 12-bar extreme with the body closing back inside reverses.",
        "This is the AsianSweep concept generalised; may be too frequent.",
        _c_liquidity_sweep, SESS_MAIN, EX_STD)
    add("BOS + retest", "structure",
        "A structure break that is retested and holds continues.",
        "Retest definition is arbitrary; few clean instances.",
        _c_bos_retest, SESS_MAIN, EX_ONE)
    add("Engulfing reversal", "structure",
        "An engulfing bar marks a shift in control.",
        "The most published candlestick pattern in existence.",
        _c_engulfing, SESS_MAIN, EX_ONE)
    add("Inside-bar break", "structure",
        "Consolidation inside the prior bar then a break continues.",
        "Same compression-does-not-predict-direction problem.",
        _c_inside_bar_break, SESS_MAIN, EX_ONE)

    # --- trend / confluence (new) ---
    add("EMA SAR confluence (full 7)", "trend",
        "EMA stack aligned + SAR flip + ADX>25 + ChoCh + volume all simultaneously.",
        "So selective (7 independent conditions) it may never fire.",
        _c_ema_sar_full, SESS_MAIN, EX_STD)
    add("EMA SAR confluence (simple)", "trend",
        "EMA200 filter + SAR flip only, no ADX/ChoCh/volume gates.",
        "Simpler = higher signal frequency but lower quality per signal.",
        _c_ema_sar_simple, SESS_MAIN, EX_STD)

    # --- market structure (BigBeluga MS Trend Matrix), rohith-2 ---
    add("Structure break CHoCH", "structure",
        "A close through the last confirmed opposite pivot flips the trend -- "
        "enter on that flip.",
        "10-bar lookahead pivot means the flip is confirmed late; the move may "
        "be half done.",
        _c_structure_break_choch, SESS_MAIN, EX_STD)
    add("Structure break BOS", "structure",
        "A close through a pivot in the direction of the existing trend "
        "continues it.",
        "Continuation breaks in gold revert as often as they run "
        "(follow-through ~48-50%).",
        _c_structure_break_bos, SESS_MAIN, EX_STD)
    add("Order block retest", "structure",
        "Price returns to the origin candle of a structure-breaking move and "
        "holds the zone (LuxAlgo SMC order block).",
        "OB zones are wide and frequently overrun; the 'hold' may be one bar "
        "of noise before continuation through.",
        _c_order_block, SESS_MAIN, EX_STD)

    return lib
