"""Candidate library v2 -- built INSIDE the $100 / 0.01-lot constraint set.

Every candidate is a pure function from a feature frame to a signal array of
-1 / 0 / +1, evaluated on a CLOSED bar and executed at the open of the next one.
No candidate may read any array position at or beyond its own index.

WHY THIS FILE EXISTS SEPARATELY FROM ``candidates.py``
------------------------------------------------------
The v1 library fixed ``sl_atr = 1.5`` for every candidate.  Phase 1 measured that
this is not a neutral default but a *binding* one: at current volatility
1.5xATR ~= $15 = 14.2% of the account, i.e. the v1 library could not have
produced a survivable system regardless of which rule won.  v2 therefore makes
the stop a first-class, deliberately varied design parameter and adds the three
gates Phase 1 showed matter more than the entry rule:

  * ``sl_atr``                  -- varied 0.4-1.25, chosen per SESSION against the
                                   measured noise floor, not per rule.
  * ``max_hold_bars``           -- explicit time stop.  Longs bleed -$0.52/night;
                                   an unbounded hold is a financed short position
                                   against the account.
  * ``spread_ceiling``          -- points.  Do not take the trade if the quoted
                                   spread exceeds this.  A $5 stop dies at 3x
                                   normal spread; a $12 stop does not care.
  * ``volatility_regime_filter`` -- (min, max) on ``atr_pct``.  Breakouts are only
                                   hypothesised to work out of compression and
                                   fades only out of extension; without this gate
                                   the two families are just noise with opposite
                                   signs.

BINDING CONSTRAINTS (Phase 1, verified against the live broker)
--------------------------------------------------------------
Account $105.74, fixed 0.01 lot = 1 oz, so **$1 of stop distance is $1 of risk**.
Workable stop band $5-$10 (4.7%-9.5%).  Measured MAE p50 noise floor by IST
session: ASIA $5.77, LONDON $6.55, OVERLAP $10.14, NY $8.69, LATE $5.16.  A stop
must sit outside the noise floor of its own session, so OVERLAP and NY
structurally require $9-13 stops this account cannot afford -- they are included
anyway, sparsely, so the claim is *tested* rather than assumed.  MFE/MAE ~= 1.0
in every session: there is no free asymmetry, so R:R >= 2 is required and any
edge must come from entry selection.  Shorts have zero swap, longs -$0.52/night,
so short-only variants are listed separately wherever the logic permits.

DESIGN RULES (inherited from v1, unchanged)
-------------------------------------------
- No discretionary language.  Every condition is arithmetic.
- Round parameters chosen a priori.  Nothing here is optimised; the robustness
  pass perturbs these afterwards.  A parameter that had to be tuned to work is
  reported as a failure, not as a result.
- Every candidate names its failure mode.  A setup that cannot say what would
  falsify it is not a hypothesis and does not belong in the library.
- H2 (Asian compression -> London expansion) and H3 (overnight/day reversal) are
  logical opposites.  BOTH are included, on the same data with the same cost
  model, deliberately.  If neither wins the session has no edge; if one wins
  conditionally on range width, that conditioning *is* the strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.research.market_study import true_range

F = Dict[str, np.ndarray]

# ---------------------------------------------------------------------------
# Session windows in IST.  A window with b > 24 wraps past midnight and is
# interpreted as (h >= a) | (h < b - 24), matching screener._session_mask.
# ---------------------------------------------------------------------------
ALL_DAY = (0.0, 24.0)
ASIA = (2.5, 11.5)
LONDON = (11.5, 15.5)
OVERLAP = (15.5, 17.5)
NY = (17.5, 21.5)
LATE = (21.5, 26.5)
LONDON_NY = (11.5, 21.5)
DAY_SESSION = (11.5, 21.5)          # London + Overlap + NY: the "day" of H3
OVERNIGHT = (21.5, 35.5)            # Late + Asia: the "overnight" of H3

# Stop sizing per session, expressed in ATR multiples and cross-checked against
# the measured dollar noise floor at ATR ~= $10.  These are NOT tuned; they are
# "the smallest multiple that clears the measured MAE p50 for this session".
SL_ASIA = 0.6      # ~$6 vs $5.77 floor
SL_LATE = 0.55     # ~$5.5 vs $5.16 floor
SL_LONDON = 0.7    # ~$7 vs $6.55 floor
SL_NY = 0.9        # ~$9 vs $8.69 floor -- 8.5% of account, marginal
SL_OVERLAP = 1.1   # ~$11 vs $10.14 floor -- 10.4% of account, unaffordable

# Spread ceilings in POINTS (median historical 200, current 260).  Tight-stop
# candidates get a tight ceiling because spread is a larger share of their risk.
SPR_TIGHT = 300.0
SPR_NORMAL = 400.0
SPR_LOOSE = 600.0

# Volatility regime gates on atr_pct (percentile of ATR within its trailing year).
VOL_ANY: Optional[Tuple[float, float]] = None
VOL_COMPRESSED = (0.0, 0.40)
VOL_MID = (0.20, 0.80)
VOL_EXTENDED = (0.60, 1.0)
VOL_NOT_EXTREME = (0.0, 0.90)

# Families whose hypothesis is explicitly "one event per session" (H2, H3, ORB,
# H5 band excursions).  Their signals are collapsed to the first occurrence in
# each session window; every other family gets a bar cooldown instead.
ONCE_PER_SESSION_FAMILIES = {
    "asian_breakout", "range_failure", "session_reversal", "opening_range",
    "noise_band",
}


@dataclass
class Candidate:
    """A single falsifiable setup.

    Field meanings that differ from v1:

    sl_atr
        Hard stop in ATR multiples.  First-class and varied.  For candidates
        whose stop is *structural* (range width, sweep extreme) this is the hard
        CAP applied on top -- the account cannot accept an unbounded structural
        stop, so the structural level is used only when it is tighter.
    max_hold_bars
        Time stop in bars of ``timeframe``.  96 M15 bars = 24h.
    spread_ceiling
        Points.  Skip the signal when the quoted spread exceeds this.
    volatility_regime_filter
        ``(min_atr_pct, max_atr_pct)`` or ``None``.  Applied to ``f["atr_pct"]``.
    """

    id: str
    name: str
    family: str
    hypothesis: str
    failure_mode: str
    rule: Callable[[F], np.ndarray]
    session: Tuple[float, float] = ALL_DAY
    timeframe: str = "M15"
    tp_atr: float = 2.0
    sl_atr: float = 0.6
    max_hold_bars: int = 64
    spread_ceiling: float = SPR_NORMAL
    volatility_regime_filter: Optional[Tuple[float, float]] = None
    direction_bias: str = "both"          # "both" | "long" | "short"
    cooldown_bars: int = 4                # min bars between two signals
    once_per_session: bool = False        # at most one signal per session window
    params: Dict[str, float] = field(default_factory=dict)

    # v1 compatibility: the screener reads ``max_bars``.
    @property
    def max_bars(self) -> int:
        return self.max_hold_bars

    @property
    def rr(self) -> float:
        return self.tp_atr / self.sl_atr if self.sl_atr else float("nan")


# ---------------------------------------------------------------------------
# helpers -- all strictly backward-looking
# ---------------------------------------------------------------------------


def _shift(a: np.ndarray, n: int) -> np.ndarray:
    """a[i-n], NaN-padded.  Guarantees no forward reference."""
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


def _ok(a: np.ndarray) -> np.ndarray:
    """NaN-safe boolean cast."""
    return np.nan_to_num(a, nan=0.0).astype(bool)


def _debounce(sig: np.ndarray, k: int) -> np.ndarray:
    """Keep at most one signal every ``k`` bars.

    Most rules here describe a STATE (price is beyond the range edge) rather than
    an EVENT, and a state fires on every subsequent bar until it ends.  Without
    this the library would report 20 trades a day from a hypothesis that claims
    one, and the trade count -- which is what a 5%-risk account actually lives or
    dies by -- would be meaningless.  Applied uniformly to every candidate so it
    is a library convention, not a per-rule tuning knob.
    """
    if k <= 1:
        return sig
    out = np.zeros_like(sig)
    last = -10 ** 9
    nz = np.flatnonzero(sig)
    for i in nz:
        if i - last >= k:
            out[i] = sig[i]
            last = i
    return out


def _once_per(sig: np.ndarray, ist_hour: np.ndarray,
              win: Tuple[float, float]) -> np.ndarray:
    """Keep only the FIRST signal in each occurrence of ``win``.

    This is what "~1 trade per day" means for a session-anchored hypothesis.
    """
    inw = _in_window(ist_hour, win)
    out = np.zeros_like(sig)
    fired = False
    for i in range(len(sig)):
        if not inw[i]:
            fired = False
            continue
        if not fired and sig[i] != 0:
            out[i] = sig[i]
            fired = True
    return out


def _in_window(ist_hour: np.ndarray, win: Tuple[float, float]) -> np.ndarray:
    a, b = win
    if b <= 24.0:
        return (ist_hour >= a) & (ist_hour < b)
    return (ist_hour >= a) | (ist_hour < b - 24.0)


# --- session / day anchored structures -------------------------------------


def _ist_day(f: F) -> np.ndarray:
    """Integer IST calendar day index."""
    return ((f["time"].astype(np.int64) + 19800) // 86400).astype(np.int64)


def _ist_week(f: F) -> np.ndarray:
    return ((f["time"].astype(np.int64) + 19800) // 604800).astype(np.int64)


def _last_session(f: F, win: Tuple[float, float]
                  ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(high, low, open, close) of the most recently COMPLETED occurrence of
    ``win``.

    A session counts as completed only once a bar OUTSIDE the window has been
    seen, so a bar inside the current session sees the PREVIOUS one.  Nothing at
    or beyond index i is read.
    """
    h, l, o, c = f["high"], f["low"], f["open"], f["close"]
    n = len(h)
    inw = _in_window(f["ist_hour"], win)
    oh = np.full(n, np.nan)
    ol = np.full(n, np.nan)
    oo = np.full(n, np.nan)
    oc = np.full(n, np.nan)
    active = False
    ch = cl = co = cc = np.nan
    lh = ll = lo_ = lc = np.nan
    for i in range(n):
        if inw[i]:
            if not active:
                active, ch, cl, co = True, h[i], l[i], o[i]
            else:
                ch = max(ch, h[i])
                cl = min(cl, l[i])
            cc = c[i]
        elif active:
            active = False
            lh, ll, lo_, lc = ch, cl, co, cc
        oh[i], ol[i], oo[i], oc[i] = lh, ll, lo_, lc
    return oh, ol, oo, oc


def _session_running(f: F, win: Tuple[float, float]
                     ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(high_so_far, low_so_far, session_open, bars_elapsed) for the CURRENT
    occurrence of ``win``, inclusive of bar i (which is closed).  NaN outside."""
    h, l, o = f["high"], f["low"], f["open"]
    n = len(h)
    inw = _in_window(f["ist_hour"], win)
    rh = np.full(n, np.nan)
    rl = np.full(n, np.nan)
    ro = np.full(n, np.nan)
    rn = np.full(n, np.nan)
    active = False
    ch = cl = co = np.nan
    k = 0
    for i in range(n):
        if inw[i]:
            if not active:
                active, ch, cl, co, k = True, h[i], l[i], o[i], 0
            else:
                ch = max(ch, h[i])
                cl = min(cl, l[i])
            k += 1
            rh[i], rl[i], ro[i], rn[i] = ch, cl, co, k
        else:
            active = False
    return rh, rl, ro, rn


def _opening_range(f: F, win: Tuple[float, float], k: int
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """High/low of the first ``k`` bars of the current occurrence of ``win``.

    NaN until those k bars have CLOSED, then held for the rest of the window.
    """
    h, l = f["high"], f["low"]
    n = len(h)
    inw = _in_window(f["ist_hour"], win)
    oh = np.full(n, np.nan)
    ol = np.full(n, np.nan)
    active = False
    ch = cl = np.nan
    cnt = 0
    for i in range(n):
        if inw[i]:
            if not active:
                active, ch, cl, cnt = True, h[i], l[i], 1
            else:
                if cnt < k:
                    ch = max(ch, h[i])
                    cl = min(cl, l[i])
                cnt += 1
            if cnt >= k:
                oh[i], ol[i] = ch, cl
        else:
            active = False
    return oh, ol


def _prev_day(f: F) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(high, low, open, close) of the previous COMPLETED IST day."""
    day = _ist_day(f)
    h, l, o, c = f["high"], f["low"], f["open"], f["close"]
    n = len(h)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    po = np.full(n, np.nan)
    pc = np.full(n, np.nan)
    cur = day[0]
    ch, cl, co, cc = h[0], l[0], o[0], c[0]
    lh = ll = lo_ = lc = np.nan
    for i in range(n):
        if day[i] != cur:
            lh, ll, lo_, lc = ch, cl, co, cc
            cur, ch, cl, co = day[i], h[i], l[i], o[i]
        else:
            ch = max(ch, h[i]) if i else h[i]
            cl = min(cl, l[i]) if i else l[i]
        cc = c[i]
        ph[i], pl[i], po[i], pc[i] = lh, ll, lo_, lc
    return ph, pl, po, pc


def _prev_week(f: F) -> Tuple[np.ndarray, np.ndarray]:
    wk = _ist_week(f)
    h, l = f["high"], f["low"]
    n = len(h)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    cur = wk[0]
    ch, cl = h[0], l[0]
    lh = ll = np.nan
    for i in range(n):
        if wk[i] != cur:
            lh, ll = ch, cl
            cur, ch, cl = wk[i], h[i], l[i]
        else:
            ch = max(ch, h[i]) if i else h[i]
            cl = min(cl, l[i]) if i else l[i]
        ph[i], pl[i] = lh, ll
    return ph, pl


def _day_open(f: F) -> np.ndarray:
    """Open of the current IST day (known from its first bar onward)."""
    day = _ist_day(f)
    o = f["open"]
    n = len(o)
    out = np.full(n, np.nan)
    cur = day[0]
    val = o[0]
    for i in range(n):
        if day[i] != cur:
            cur, val = day[i], o[i]
        out[i] = val
    return out


def _trailing_day_range(f: F, n_days: int = 14) -> np.ndarray:
    """H5: mean high-low range of the previous ``n_days`` COMPLETED IST days.

    This is the self-rescaling noise band from Zarattini et al.: one parameter,
    no fixed dollar threshold, so it survives a change of volatility regime
    instead of being silently recalibrated by it.
    """
    day = _ist_day(f)
    h, l = f["high"], f["low"]
    n = len(h)
    out = np.full(n, np.nan)
    hist: List[float] = []
    cur = day[0]
    ch, cl = h[0], l[0]
    for i in range(n):
        if day[i] != cur:
            hist.append(ch - cl)
            if len(hist) > n_days:
                hist.pop(0)
            cur, ch, cl = day[i], h[i], l[i]
        else:
            ch = max(ch, h[i]) if i else h[i]
            cl = min(cl, l[i]) if i else l[i]
        if len(hist) >= n_days:
            out[i] = float(np.mean(hist))
    return out


def _session_range_history(f: F, win: Tuple[float, float], n_days: int = 20
                           ) -> Tuple[np.ndarray, np.ndarray]:
    """(width_of_last_completed_session, its percentile within the previous
    ``n_days`` completed sessions of the same window)."""
    sh, sl_, _, _ = _last_session(f, win)
    width = sh - sl_
    n = len(width)
    pct = np.full(n, np.nan)
    hist: List[float] = []
    prev = np.nan
    cur_pct = np.nan
    for i in range(n):
        w = width[i]
        if np.isnan(w):
            continue
        if np.isnan(prev) or w != prev:
            # A newly completed session: rank it against the previous n_days
            # completed sessions, then add it to the history.
            cur_pct = float(np.mean(np.array(hist) < w)) if len(hist) >= 5 else np.nan
            hist.append(float(w))
            if len(hist) > n_days:
                hist.pop(0)
            prev = w
        pct[i] = cur_pct
    return width, pct


def _tod_atr(f: F, n_days: int = 20) -> np.ndarray:
    """H6: time-of-day-conditioned volatility.

    Mean true range of the SAME intraday slot over the previous ``n_days``
    occurrences, strictly before bar i.  Andersen-Bollerslev: intraday
    volatility is dominated by a deterministic time-of-day component, so a flat
    24h ATR is systematically too wide at 03:00 IST and too tight at 18:00 IST.
    A stop sized on flat ATR is therefore mis-sized at every hour of the day.
    """
    tr = true_range(f["high"], f["low"], f["close"])
    slot = np.round(f["ist_hour"] * 4.0).astype(int) % 96
    n = len(tr)
    out = np.full(n, np.nan)
    buf: Dict[int, List[float]] = {}
    for i in range(n):
        s = int(slot[i])
        b = buf.setdefault(s, [])
        if len(b) >= max(5, n_days // 2):
            out[i] = float(np.mean(b))
        b.append(float(tr[i]))
        if len(b) > n_days:
            b.pop(0)
    return out


def _round_level(price: np.ndarray, step: float) -> np.ndarray:
    return np.round(price / step) * step


def _vol_gate(f: F, gate: Optional[Tuple[float, float]]) -> np.ndarray:
    if gate is None:
        return np.ones(len(f["close"]), dtype=bool)
    lo, hi = gate
    p = f["atr_pct"]
    # NaN atr_pct means "not enough history to judge the regime" -> allow, the
    # backtester's warm-up handles it.  Do not silently drop the early sample.
    return np.isnan(p) | ((p >= lo) & (p <= hi))


# ===========================================================================
# FAMILY: asian_breakout  (H2 -- compression -> expansion)
#
# The single most saturated gold EA archetype (R9/R10/R11).  Included with the
# range-width gate the vendor versions omit: breaking an abnormally WIDE Asian
# range gives a stop this account cannot pay for, and breaking an abnormally
# NARROW one is whipsaw.  The naive ungated version is included first as the
# control, so "the gate is what matters" is a measurable claim rather than an
# assertion.
# ===========================================================================


def _mk_range_break(src: Tuple[float, float], trade: Tuple[float, float],
                    pct_lo: float = 0.0, pct_hi: float = 1.0,
                    max_width_band: float = 99.0,
                    buffer_atr: float = 0.0,
                    noise_band_k: float = 0.0,
                    side: str = "both") -> Callable[[F], np.ndarray]:
    """Break of the completed ``src`` session range, taken during ``trade``.

    ``noise_band_k`` > 0 replaces the fixed buffer with H5's self-rescaling
    threshold: the break must clear the edge by k x (trailing 14-day mean daily
    range), so the same rule means the same thing in 2020 and in 2026.
    """
    def rule(f: F) -> np.ndarray:
        hi, lo, _, _ = _last_session(f, src)
        width, pct = _session_range_history(f, src)
        band = _trailing_day_range(f, 14)
        buf = buffer_atr * f["atr14"]
        if noise_band_k:
            buf = buf + noise_band_k * band
        inw = _in_window(f["ist_hour"], trade)
        gate = inw & (np.isnan(band) | _ok(width <= max_width_band * band))
        gate &= np.isnan(pct) | ((pct >= pct_lo) & (pct <= pct_hi))
        up = gate & _ok(f["close"] > hi + buf)
        dn = gate & _ok(f["close"] < lo - buf)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_range_break_retest(src: Tuple[float, float], trade: Tuple[float, float]
                           ) -> Callable[[F], np.ndarray]:
    """Break of the range edge on a previous bar, then a pullback that closes
    back through the edge in the break direction."""
    def rule(f: F) -> np.ndarray:
        hi, lo, _, _ = _last_session(f, src)
        inw = _in_window(f["ist_hour"], trade)
        broke_up = _ok(_shift((f["close"] > hi).astype(float), 1))
        broke_dn = _ok(_shift((f["close"] < lo).astype(float), 1))
        up = inw & broke_up & _ok(f["low"] <= hi) & _ok(f["close"] > hi)
        dn = inw & broke_dn & _ok(f["high"] >= lo) & _ok(f["close"] < lo)
        return _sig(up, dn)
    return rule


def _mk_range_break_failure(src: Tuple[float, float], trade: Tuple[float, float]
                            ) -> Callable[[F], np.ndarray]:
    """The adversary of ``_mk_range_break``: price leaves the range and closes
    back inside it.  If the breakout family has no edge, this one should."""
    def rule(f: F) -> np.ndarray:
        hi, lo, _, _ = _last_session(f, src)
        inw = _in_window(f["ist_hour"], trade)
        up = inw & _ok(f["low"] < lo) & _ok(f["close"] > lo) & _ok(f["close"] > f["open"])
        dn = inw & _ok(f["high"] > hi) & _ok(f["close"] < hi) & _ok(f["close"] < f["open"])
        return _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: session_reversal  (H3 -- overnight / day return reversal)
#
# Tier A support (A8, A20): strong negative autocorrelation between overnight
# and intraday gold returns.  This is the LOGICAL OPPOSITE of H2 and is run on
# the same bars with the same costs on purpose.
# ===========================================================================


def _mk_session_move_fade(src: Tuple[float, float], trade: Tuple[float, float],
                          k_band: float = 0.5, side: str = "both"
                          ) -> Callable[[F], np.ndarray]:
    """Fade the completed ``src`` session's net directional move during ``trade``.

    "Large" is defined against the trailing 14-day mean daily range (H5), not
    against a fixed dollar figure, so the definition does not drift with regime.
    """
    def rule(f: F) -> np.ndarray:
        _, _, so, sc = _last_session(f, src)
        band = _trailing_day_range(f, 14)
        move = sc - so
        inw = _in_window(f["ist_hour"], trade)
        big = _ok(np.abs(move) > k_band * band)
        up = inw & big & _ok(move < 0)
        dn = inw & big & _ok(move > 0)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_close_position_fade(src: Tuple[float, float], trade: Tuple[float, float],
                            edge: float = 0.20) -> Callable[[F], np.ndarray]:
    """Fade based on WHERE in its own range the prior session closed, rather
    than on how far it travelled.  Closing in the top 20% of the Asian range is
    a positioning statement; closing mid-range is not."""
    def rule(f: F) -> np.ndarray:
        hi, lo, _, sc = _last_session(f, src)
        width = np.maximum(hi - lo, 1e-9)
        pos = (sc - lo) / width
        inw = _in_window(f["ist_hour"], trade)
        return _sig(inw & _ok(pos <= edge), inw & _ok(pos >= 1.0 - edge))
    return rule


def _mk_prev_day_return_fade(trade: Tuple[float, float], k: float = 1.0
                             ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        _, _, po, pc = _prev_day(f)
        band = _trailing_day_range(f, 14)
        r = pc - po
        inw = _in_window(f["ist_hour"], trade)
        big = _ok(np.abs(r) > k * band)
        return _sig(inw & big & _ok(r < 0), inw & big & _ok(r > 0))
    return rule


def _mk_gap_fade(trade: Tuple[float, float], k: float = 0.5
                 ) -> Callable[[F], np.ndarray]:
    """Day opens away from the previous day's close by more than k x band; fade
    back toward it.  The weekend gap version of the overnight-reversal claim."""
    def rule(f: F) -> np.ndarray:
        _, _, _, pc = _prev_day(f)
        do = _day_open(f)
        band = _trailing_day_range(f, 14)
        gap = do - pc
        inw = _in_window(f["ist_hour"], trade)
        big = _ok(np.abs(gap) > k * band)
        return _sig(inw & big & _ok(gap < 0), inw & big & _ok(gap > 0))
    return rule


# ===========================================================================
# FAMILY: opening_range -- and its FAILURE twin
# ===========================================================================


def _mk_orb(win: Tuple[float, float], k: int, buffer_atr: float = 0.0,
            noise_band_k: float = 0.0, side: str = "both"
            ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        oh, ol = _opening_range(f, win, k)
        buf = buffer_atr * f["atr14"]
        if noise_band_k:
            buf = buf + noise_band_k * _trailing_day_range(f, 14)
        up = _ok(f["close"] > oh + buf)
        dn = _ok(f["close"] < ol - buf)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_orb_failure(win: Tuple[float, float], k: int) -> Callable[[F], np.ndarray]:
    """Opening range is broken, then price closes back inside it.  A5/A6 claim
    ORB works; A7 says only where intraday trending exists.  This candidate is
    the measurement of that conditional, not a separate belief."""
    def rule(f: F) -> np.ndarray:
        oh, ol = _opening_range(f, win, k)
        broke_up = _ok(_shift((f["high"] > oh).astype(float), 1))
        broke_dn = _ok(_shift((f["low"] < ol).astype(float), 1))
        up = broke_dn & _ok(f["close"] > ol) & _ok(f["close"] > f["open"])
        dn = broke_up & _ok(f["close"] < oh) & _ok(f["close"] < f["open"])
        return _sig(up, dn)
    return rule


def _mk_orb_retest(win: Tuple[float, float], k: int) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        oh, ol = _opening_range(f, win, k)
        broke_up = _ok(_shift((f["close"] > oh).astype(float), 1))
        broke_dn = _ok(_shift((f["close"] < ol).astype(float), 1))
        up = broke_up & _ok(f["low"] <= oh) & _ok(f["close"] > oh)
        dn = broke_dn & _ok(f["high"] >= ol) & _ok(f["close"] < ol)
        return _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: liquidity_sweep  (H4)
#
# R1's public version has NO PRICE STOP -- only an end-of-day time stop.  At
# 0.01 lot on $105 an unbounded loss is account death, so every candidate here
# carries a hard ATR stop and the structural extreme is used only as a cap.
# ===========================================================================


def _mk_level_sweep_reclaim(level_fn: str, side: str = "both",
                            wick_frac: float = 0.30
                            ) -> Callable[[F], np.ndarray]:
    """Trade through a reference level, then close back on the original side.

    ``level_fn`` selects the reference: previous-day extremes, previous-week
    extremes, or the previous Asian-session extremes.
    """
    def rule(f: F) -> np.ndarray:
        if level_fn == "pdh_pdl":
            hi, lo, _, _ = _prev_day(f)
        elif level_fn == "pwh_pwl":
            hi, lo = _prev_week(f)
        elif level_fn == "asia":
            hi, lo, _, _ = _last_session(f, ASIA)
        elif level_fn == "late":
            hi, lo, _, _ = _last_session(f, LATE)
        else:
            hi, lo, _, _ = _last_session(f, LONDON)
        rg = _range(f)
        lw, uw = _lower_wick(f), _upper_wick(f)
        up = _ok(f["low"] < lo) & _ok(f["close"] > lo) & _ok(lw / rg > wick_frac)
        dn = _ok(f["high"] > hi) & _ok(f["close"] < hi) & _ok(uw / rg > wick_frac)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_round_sweep(step: float, tol_atr: float = 0.25, side: str = "both"
                    ) -> Callable[[F], np.ndarray]:
    """A12/A13: round numbers act as barriers where stops cluster.  A13 weakens
    A12, so the prior here is low and the candidate exists to kill it cheaply."""
    def rule(f: F) -> np.ndarray:
        lvl = _round_level(f["close"], step)
        tol = tol_atr * f["atr14"]
        rg = _range(f)
        lw, uw = _lower_wick(f), _upper_wick(f)
        near = _ok(np.abs(f["close"] - lvl) < tol)
        up = near & _ok(f["low"] < lvl) & _ok(f["close"] > lvl) & _ok(lw / rg > 0.3)
        dn = near & _ok(f["high"] > lvl) & _ok(f["close"] < lvl) & _ok(uw / rg > 0.3)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_round_break(step: float, buffer_atr: float = 0.20
                    ) -> Callable[[F], np.ndarray]:
    """The opposite of ``_mk_round_sweep``: a decisive close through a round
    level continues.  Round numbers cannot be both a barrier and a launchpad;
    running both settles it."""
    def rule(f: F) -> np.ndarray:
        lvl = _round_level(f["close"], step)
        buf = buffer_atr * f["atr14"]
        pc = _shift(f["close"], 1)
        up = _ok(pc < lvl) & _ok(f["close"] > lvl + buf)
        dn = _ok(pc > lvl) & _ok(f["close"] < lvl - buf)
        return _sig(up, dn)
    return rule


def _mk_equal_extremes_sweep(w: int = 20, tol_atr: float = 0.15
                             ) -> Callable[[F], np.ndarray]:
    """Two comparable prior extremes (a "double top/bottom" stated as
    arithmetic), then a sweep and reclaim of them."""
    def rule(f: F) -> np.ndarray:
        h1 = _roll_max(f["high"], w)
        h2 = _shift(_roll_max(f["high"], w), w)
        l1 = _roll_min(f["low"], w)
        l2 = _shift(_roll_min(f["low"], w), w)
        tol = tol_atr * f["atr14"]
        eq_h = _ok(np.abs(h1 - h2) < tol)
        eq_l = _ok(np.abs(l1 - l2) < tol)
        up = eq_l & _ok(f["low"] < l1) & _ok(f["close"] > l1)
        dn = eq_h & _ok(f["high"] > h1) & _ok(f["close"] < h1)
        return _sig(up, dn)
    return rule


def _mk_session_extreme_sweep(win: Tuple[float, float], min_bars: int = 8
                              ) -> Callable[[F], np.ndarray]:
    """Sweep of the CURRENT session's own developing extreme, late in that
    session.  The stop is the sweep wick; the target is the other side."""
    def rule(f: F) -> np.ndarray:
        rh, rl, _, rn = _session_running(f, win)
        prev_h, prev_l = _shift(rh, 1), _shift(rl, 1)
        late = _ok(rn >= min_bars)
        rg = _range(f)
        up = late & _ok(f["low"] < prev_l) & _ok(f["close"] > prev_l) & _ok(_lower_wick(f) / rg > 0.4)
        dn = late & _ok(f["high"] > prev_h) & _ok(f["close"] < prev_h) & _ok(_upper_wick(f) / rg > 0.4)
        return _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: noise_band  (H5 standalone)
# ===========================================================================


def _mk_noise_band_break(anchor: str, k: float, win: Tuple[float, float],
                         side: str = "both") -> Callable[[F], np.ndarray]:
    """Close beyond anchor +/- k x (trailing 14-day mean daily range).

    One parameter (k), self-rescaling.  Directly addresses R12's finding that
    fixed configurations tuned on 2023-2026 gold fail in 2013/2020/2022.
    """
    def rule(f: F) -> np.ndarray:
        band = _trailing_day_range(f, 14)
        if anchor == "day_open":
            a = _day_open(f)
        elif anchor == "prev_close":
            _, _, _, a = _prev_day(f)
        else:
            _, _, a, _ = _session_running(f, win)
        inw = _in_window(f["ist_hour"], win)
        up = inw & _ok(f["close"] > a + k * band)
        dn = inw & _ok(f["close"] < a - k * band)
        if side == "long":
            dn = np.zeros_like(dn)
        elif side == "short":
            up = np.zeros_like(up)
        return _sig(up, dn)
    return rule


def _mk_noise_band_fade(anchor: str, k: float, win: Tuple[float, float]
                        ) -> Callable[[F], np.ndarray]:
    """Beyond the band by a large multiple, fade back toward the anchor."""
    def rule(f: F) -> np.ndarray:
        band = _trailing_day_range(f, 14)
        a = _day_open(f) if anchor == "day_open" else _session_running(f, win)[2]
        inw = _in_window(f["ist_hour"], win)
        up = inw & _ok(f["close"] < a - k * band)
        dn = inw & _ok(f["close"] > a + k * band)
        return _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: tod_volatility  (H6)
#
# Every rule here measures the bar against the volatility NORMAL FOR THIS HOUR
# rather than against a flat 24h ATR.  If H6 is right, the same structural rule
# should behave differently under the two normalisations -- which is exactly
# what the paired flat-ATR candidates elsewhere in this file let us check.
# ===========================================================================


def _mk_tod_spike(k: float, mode: str = "continue") -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        tr = true_range(f["high"], f["low"], f["close"])
        norm = _tod_atr(f, 20)
        spike = _ok(tr > k * norm)
        bull = spike & _ok(f["close"] > f["open"])
        bear = spike & _ok(f["close"] < f["open"])
        return _sig(bull, bear) if mode == "continue" else _sig(bear, bull)
    return rule


def _mk_tod_quiet_break(w: int = 8, k: float = 0.6) -> Callable[[F], np.ndarray]:
    """Volatility below its own time-of-day norm for w bars, then a break of
    that quiet window's extreme.  Compression measured correctly for the hour."""
    def rule(f: F) -> np.ndarray:
        tr = true_range(f["high"], f["low"], f["close"])
        norm = _tod_atr(f, 20)
        quiet_bar = np.where(np.isnan(norm), 0.0, (tr < k * norm).astype(float))
        quiet = _ok(_roll_mean(quiet_bar, w) >= 0.99)
        hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
        return _sig(quiet & _ok(f["close"] > hh), quiet & _ok(f["close"] < ll))
    return rule


def _mk_tod_relative_move(w: int = 8, k: float = 2.0, mode: str = "fade"
                          ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        norm = _tod_atr(f, 20)
        move = (f["close"] - _shift(f["close"], w)) / np.maximum(norm, 1e-9)
        up, dn = _ok(move > k), _ok(move < -k)
        return _sig(dn, up) if mode == "fade" else _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: structure  (BOS / CHoCH / displacement / FVG)
# ===========================================================================


def _mk_bos_retest(w: int = 20) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
        broke_up = _ok(_shift((f["close"] > hh).astype(float), 1))
        broke_dn = _ok(_shift((f["close"] < ll).astype(float), 1))
        return _sig(broke_up & _ok(f["low"] <= _shift(hh, 1)) & _ok(f["close"] > _shift(hh, 1)),
                    broke_dn & _ok(f["high"] >= _shift(ll, 1)) & _ok(f["close"] < _shift(ll, 1)))
    return rule


def _mk_choch(w: int = 12) -> Callable[[F], np.ndarray]:
    """Change of character: a trend by swing structure, then the FIRST break of
    the opposing swing.  Reversal, not continuation."""
    def rule(f: F) -> np.ndarray:
        hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
        hh_p, ll_p = _shift(hh, w), _shift(ll, w)
        up_trend = _ok((hh > hh_p) & (ll > ll_p))
        dn_trend = _ok((hh < hh_p) & (ll < ll_p))
        return _sig(dn_trend & _ok(f["close"] > hh), up_trend & _ok(f["close"] < ll))
    return rule


def _mk_displacement(k: float = 1.5, mode: str = "continue", body_frac: float = 0.6
                     ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        big = _ok((_body(f) > k * f["atr14"]) & (_body(f) / _range(f) > body_frac))
        bull = big & _ok(f["close"] > f["open"])
        bear = big & _ok(f["close"] < f["open"])
        return _sig(bull, bear) if mode == "continue" else _sig(bear, bull)
    return rule


def _mk_fvg_entry(mode: str = "continue") -> Callable[[F], np.ndarray]:
    """A three-bar imbalance formed earlier, then price returns into it."""
    def rule(f: F) -> np.ndarray:
        h3, l3 = _shift(f["high"], 3), _shift(f["low"], 3)
        h1, l1 = _shift(f["high"], 1), _shift(f["low"], 1)
        bull_gap = _ok(h3 < l1)
        bear_gap = _ok(l3 > h1)
        back_in = _ok(f["low"] <= l1) & _ok(f["close"] > h3)
        back_in_s = _ok(f["high"] >= h1) & _ok(f["close"] < l3)
        up = bull_gap & back_in
        dn = bear_gap & back_in_s
        return _sig(up, dn) if mode == "continue" else _sig(dn, up)
    return rule


def _mk_inside_break(n_inside: int = 2) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        ref_h = _shift(f["high"], n_inside + 1)
        ref_l = _shift(f["low"], n_inside + 1)
        ok = np.ones(len(f["close"]), dtype=bool)
        for j in range(1, n_inside + 1):
            ok &= _ok((_shift(f["high"], j) < ref_h) & (_shift(f["low"], j) > ref_l))
        return _sig(ok & _ok(f["close"] > ref_h), ok & _ok(f["close"] < ref_l))
    return rule


# ===========================================================================
# FAMILY: contraction  (volatility contraction -> expansion)
# ===========================================================================


def _mk_nr_break(w: int = 7) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        rg = _range(f)
        narrow = _ok(_shift(rg, 1) <= _shift(_roll_min(rg, w), 1))
        return _sig(narrow & _ok(f["close"] > _shift(f["high"], 1)),
                    narrow & _ok(f["close"] < _shift(f["low"], 1)))
    return rule


def _mk_squeeze(mode: str = "break", w: int = 20) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        m, s = _roll_mean(f["close"], w), _roll_std(f["close"], w)
        bb_up, bb_lo = m + 2 * s, m - 2 * s
        kc_up, kc_lo = m + 1.5 * f["atr14"], m - 1.5 * f["atr14"]
        sq = _ok(_shift(((bb_up < kc_up) & (bb_lo > kc_lo)).astype(float), 1))
        up, dn = sq & _ok(f["close"] > bb_up), sq & _ok(f["close"] < bb_lo)
        return _sig(up, dn) if mode == "break" else _sig(dn, up)
    return rule


def _mk_range_pct_break(w: int = 24, pct: float = 0.25) -> Callable[[F], np.ndarray]:
    """The w-bar range is in the bottom ``pct`` of its own trailing
    distribution, then the range breaks."""
    def rule(f: F) -> np.ndarray:
        hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
        width = hh - ll
        thr = _roll_mean(width, 200) * (2.0 * pct)
        tight = _ok(width < thr)
        return _sig(tight & _ok(f["close"] > hh), tight & _ok(f["close"] < ll))
    return rule


def _mk_coil_expand(w: int = 12) -> Callable[[F], np.ndarray]:
    """ATR falling for w bars then a bar whose range exceeds 2x the compressed
    ATR.  Contraction and expansion measured as one event, not two rules."""
    def rule(f: F) -> np.ndarray:
        a = f["atr14"]
        falling = _ok(a < _shift(a, w))
        expand = _ok(_range(f) > 2.0 * _shift(a, 1))
        cond = falling & expand
        return _sig(cond & _ok(f["close"] > f["open"]), cond & _ok(f["close"] < f["open"]))
    return rule


# ===========================================================================
# FAMILY: rejection / exhaustion
# ===========================================================================


def _mk_session_extreme_rejection(win: Tuple[float, float], wick_frac: float = 0.5,
                                  min_bars: int = 6) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        rh, rl, _, rn = _session_running(f, win)
        prev_h, prev_l = _shift(rh, 1), _shift(rl, 1)
        late = _ok(rn >= min_bars)
        rg = _range(f)
        up = late & _ok(f["low"] <= prev_l) & _ok(_lower_wick(f) / rg > wick_frac)
        dn = late & _ok(f["high"] >= prev_h) & _ok(_upper_wick(f) / rg > wick_frac)
        return _sig(up, dn)
    return rule


def _mk_extension_exhaustion(w: int = 8, k: float = 2.0, wick_frac: float = 0.35
                             ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        move = (f["close"] - _shift(f["close"], w)) / np.maximum(f["atr14"], 1e-9)
        rg = _range(f)
        up = _ok(move < -k) & _ok(_lower_wick(f) / rg > wick_frac)
        dn = _ok(move > k) & _ok(_upper_wick(f) / rg > wick_frac)
        return _sig(up, dn)
    return rule


def _mk_momentum_divergence(w: int = 20) -> Callable[[F], np.ndarray]:
    """Price makes a new w-bar extreme, RSI does not confirm.  Stated purely
    arithmetically -- no chart reading."""
    def rule(f: F) -> np.ndarray:
        hh, ll = _roll_max(f["high"], w), _roll_min(f["low"], w)
        rmax, rmin = _roll_max(f["rsi14"], w), _roll_min(f["rsi14"], w)
        dn = _ok(f["high"] > hh) & _ok(f["rsi14"] < rmax)
        up = _ok(f["low"] < ll) & _ok(f["rsi14"] > rmin)
        return _sig(up, dn)
    return rule


def _mk_volume_climax(k: float = 3.0, wick_frac: float = 0.4
                      ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        v = f["volume"]
        big = _ok(v > k * _roll_mean(v, 50))
        rg = _range(f)
        return _sig(big & _ok(_lower_wick(f) / rg > wick_frac),
                    big & _ok(_upper_wick(f) / rg > wick_frac))
    return rule


def _mk_three_push(w: int = 6) -> Callable[[F], np.ndarray]:
    """Three consecutive higher w-bar highs (or lower lows), then a close
    against the last push.  Exhaustion stated as a counting rule."""
    def rule(f: F) -> np.ndarray:
        hh = _roll_max(f["high"], w)
        ll = _roll_min(f["low"], w)
        rising = _ok((hh > _shift(hh, w)) & (_shift(hh, w) > _shift(hh, 2 * w)))
        falling = _ok((ll < _shift(ll, w)) & (_shift(ll, w) < _shift(ll, 2 * w)))
        return _sig(falling & _ok(f["close"] > _shift(f["high"], 1)),
                    rising & _ok(f["close"] < _shift(f["low"], 1)))
    return rule


# ===========================================================================
# FAMILY: mean_reversion (anchored)
# ===========================================================================


def _mk_session_open_revert(win: Tuple[float, float], k: float = 1.5
                            ) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        _, _, so, rn = _session_running(f, win)
        d = (f["close"] - so) / np.maximum(f["atr14"], 1e-9)
        gate = _ok(rn >= 4)
        return _sig(gate & _ok(d < -k), gate & _ok(d > k))
    return rule


def _mk_session_vwap_revert(win: Tuple[float, float], k: float = 1.5
                            ) -> Callable[[F], np.ndarray]:
    """Session-anchored VWAP, reset at the session boundary.  The rolling VWAP
    in v1 had no anchor and was therefore not a session statistic at all."""
    def rule(f: F) -> np.ndarray:
        inw = _in_window(f["ist_hour"], win)
        c, v = f["close"], f["volume"]
        n = len(c)
        vw = np.full(n, np.nan)
        pv = 0.0
        vv = 0.0
        active = False
        for i in range(n):
            if inw[i]:
                if not active:
                    active, pv, vv = True, 0.0, 0.0
                pv += c[i] * v[i]
                vv += v[i]
                vw[i] = pv / vv if vv > 0 else np.nan
            else:
                active = False
        d = (c - vw) / np.maximum(f["atr14"], 1e-9)
        return _sig(_ok(d < -k), _ok(d > k))
    return rule


def _mk_bb_fade(w: int = 20, k: float = 2.0) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        m, s = _roll_mean(f["close"], w), _roll_std(f["close"], w)
        up, lo = m + k * s, m - k * s
        return _sig(_ok((f["low"] < lo) & (f["close"] > lo)),
                    _ok((f["high"] > up) & (f["close"] < up)))
    return rule


def _mk_prev_close_retest(k: float = 0.25) -> Callable[[F], np.ndarray]:
    """Return to the previous day's close after having left it.  The most
    watched non-extreme level on the chart."""
    def rule(f: F) -> np.ndarray:
        _, _, _, pc = _prev_day(f)
        tol = k * f["atr14"]
        near = _ok(np.abs(f["close"] - pc) < tol)
        away = _ok(np.abs(_shift(f["close"], 4) - pc) > 4 * tol)
        up = near & away & _ok(_shift(f["close"], 4) < pc)
        dn = near & away & _ok(_shift(f["close"], 4) > pc)
        return _sig(up, dn)
    return rule


# ===========================================================================
# FAMILY: mtf_alignment  (daily / weekly bias as a one-way filter)
#
# H10: adds no trades, only removes them.  Tested as a paired ablation against
# the ungated candidate, never assumed.
# ===========================================================================


def _mk_daily_bias_sweep(level: str = "pdh_pdl") -> Callable[[F], np.ndarray]:
    """R1's actual stated logic: previous-day close vs open sets the bias, then
    only the sweep in the bias direction is taken.  With a hard stop, unlike R1."""
    base = _mk_level_sweep_reclaim(level)
    def rule(f: F) -> np.ndarray:
        s = base(f)
        _, _, po, pc = _prev_day(f)
        bull = _ok(pc > po)
        bear = _ok(pc < po)
        s = s.copy()
        s[(s > 0) & ~bull] = 0
        s[(s < 0) & ~bear] = 0
        return s
    return rule


def _mk_weekly_bias_break(win: Tuple[float, float]) -> Callable[[F], np.ndarray]:
    def rule(f: F) -> np.ndarray:
        pwh, pwl = _prev_week(f)
        mid = (pwh + pwl) / 2.0
        bull = _ok(f["close"] > mid)
        hh, ll = _roll_max(f["high"], 20), _roll_min(f["low"], 20)
        inw = _in_window(f["ist_hour"], win)
        return _sig(inw & bull & _ok(f["close"] > hh),
                    inw & ~bull & _ok(f["close"] < ll))
    return rule


def _mk_htf_pullback(win: Tuple[float, float]) -> Callable[[F], np.ndarray]:
    """Daily direction from the previous day's body, entry on an intraday
    pullback to the session open.  Two timeframes, one rule."""
    def rule(f: F) -> np.ndarray:
        _, _, po, pc = _prev_day(f)
        _, _, so, rn = _session_running(f, win)
        bull, bear = _ok(pc > po), _ok(pc < po)
        gate = _ok(rn >= 4)
        crossed_down = _ok(_shift(f["close"], 1) < so) & _ok(f["close"] > so)
        crossed_up = _ok(_shift(f["close"], 1) > so) & _ok(f["close"] < so)
        return _sig(gate & bull & crossed_down, gate & bear & crossed_up)
    return rule


# ===========================================================================
# Registry
# ===========================================================================


def _mk(cid: str, name: str, family: str, hyp: str, fail: str,
        fn: Callable[[F], np.ndarray], **kw) -> Candidate:
    return Candidate(id=cid, name=name, family=family, hypothesis=hyp,
                     failure_mode=fail, rule=fn, **kw)


def build_library_v2() -> List[Candidate]:
    """The v2 candidate library.

    Composition is deliberate, not incidental:

    * The library is BIASED toward ASIA and LATE because those are the only
      sessions whose measured noise floor ($5.77 / $5.16) fits inside a stop
      this account can pay for.
    * LONDON, NY and OVERLAP candidates are present but sparse.  They exist so
      that "this account cannot afford the loud sessions" is a result rather
      than a premise.  Their stops are sized honestly (SL_NY, SL_OVERLAP), which
      means several of them are flagged unaffordable BY CONSTRUCTION -- that is
      the point.
    * Short-only twins are listed separately wherever the logic is symmetric,
      because short swap is $0.00 and long swap is -$0.52/night.
    * Every breakout candidate has a fade counterpart somewhere in the file.
    """
    lib: List[Candidate] = []
    n = [0]

    def add(name: str, family: str, hyp: str, fail: str,
            fn: Callable[[F], np.ndarray], session: Tuple[float, float],
            sl_atr: float, tp_atr: float, max_hold_bars: int,
            spread_ceiling: float = SPR_NORMAL,
            vol: Optional[Tuple[float, float]] = None,
            bias: str = "both", once: Optional[bool] = None, cooldown: int = 4,
            **params) -> None:
        n[0] += 1
        if once is None:
            once = family in ONCE_PER_SESSION_FAMILIES

        # The rule as written describes a CONDITION; what the account trades is
        # an ENTRY.  Direction bias is applied first (so a filtered-out long
        # cannot consume the slot of a valid short), then ``once`` collapses a
        # session-anchored hypothesis to its first occurrence per session -- the
        # "~1 trade/day" claim taken literally -- or ``cooldown`` does the same
        # job for rules with no session anchor.  Applied here rather than inside
        # each rule so it is a uniform library convention that cannot be tuned
        # per candidate.
        def wrapped(f: F, _b=fn, _s=session, _bias=bias,
                    _once=once, _k=cooldown) -> np.ndarray:
            s = np.asarray(_b(f)).astype(np.int8).copy()
            if _bias == "short":
                s[s > 0] = 0
            elif _bias == "long":
                s[s < 0] = 0
            return _once_per(s, f["ist_hour"], _s) if _once else _debounce(s, _k)

        lib.append(_mk(f"XV2-{n[0]:03d}", name, family, hyp, fail, wrapped,
                       session=session, sl_atr=sl_atr, tp_atr=tp_atr,
                       max_hold_bars=max_hold_bars,
                       spread_ceiling=spread_ceiling,
                       volatility_regime_filter=vol,
                       direction_bias=bias, cooldown_bars=cooldown,
                       once_per_session=once, params=params))

    # -------------------------------------------------------------------
    # H2 -- asian_breakout.  Asia range broken during London.
    # -------------------------------------------------------------------
    add("Asia range break -> London (naive control)", "asian_breakout",
        "The compressed Asian range is broken and extended by London order flow.",
        "The most saturated gold EA archetype; if it survives cost, it is because "
        "the gate does the work, so the ungated control must underperform the gated "
        "versions or the whole family is noise.",
        _mk_range_break(ASIA, LONDON), LONDON, SL_LONDON, 2.1, 32, SPR_NORMAL, VOL_ANY)
    add("Asia range break -> London, compressed range only", "asian_breakout",
        "Expansion follows compression: the break only pays when the Asian range "
        "sat in the bottom 40% of its own trailing 20-day distribution.",
        "If the compressed subset performs the same as the naive control, "
        "compression carries no information and H11 is false.",
        _mk_range_break(ASIA, LONDON, pct_lo=0.0, pct_hi=0.4),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_COMPRESSED)
    add("Asia range break -> London, mid-percentile band", "asian_breakout",
        "Neither an abnormally narrow (whipsaw) nor abnormally wide (unaffordable "
        "stop) Asian range breaks cleanly; only the middle band does.",
        "A middle-band filter is a two-sided cut and is the most likely place in "
        "this file for an accidental fit; it fails if either tail performs equally.",
        _mk_range_break(ASIA, LONDON, pct_lo=0.3, pct_hi=0.7),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_MID)
    add("Asia range break -> London, affordable width only", "asian_breakout",
        "Only breaks whose Asian range is under HALF the trailing 14-day mean daily "
        "range are tradeable: a wider range implies a structural stop far above "
        "this account's $10 ceiling, so the trade cannot be taken as designed.",
        "Measured: the Asian range averages ~$64 against a ~$100 daily range and a "
        "~$10.7 M15 ATR, so the TRUE structural stop for this family is ~6xATR and "
        "unaffordable. If the affordable subset has no edge, H2 is only profitable "
        "at risk levels this account cannot take -- a fatal result, not a tuning "
        "problem.",
        _mk_range_break(ASIA, LONDON, max_width_band=0.5),
        LONDON, SL_LONDON, 2.8, 32, SPR_TIGHT, VOL_ANY)
    add("Asia range break -> London, ATR buffer", "asian_breakout",
        "A break must clear the edge by 0.25xATR to distinguish a real break from "
        "a wick through the level.",
        "If the buffer only removes trades without improving expectancy, the "
        "false-break story is wrong and the losses are elsewhere.",
        _mk_range_break(ASIA, LONDON, buffer_atr=0.25),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY)
    add("Asia range break -> London, H5 noise band", "asian_breakout",
        "H5 as the threshold mechanism inside H2: the break must clear the edge by "
        "0.15x the trailing 14-day mean daily range, so the rule self-rescales.",
        "If the self-rescaling threshold performs no better out-of-regime than the "
        "fixed ATR buffer, H5's central claim (regime portability) is unsupported.",
        _mk_range_break(ASIA, LONDON, noise_band_k=0.15),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY)
    add("Asia range break -> London, SHORT only", "asian_breakout",
        "The same break, shorts only, exploiting the $0.00 short swap.",
        "If shorts alone do not pay, the swap asymmetry is too small to matter and "
        "direction filtering is a free lunch that does not exist.",
        _mk_range_break(ASIA, LONDON, side="short"),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY, bias="short")
    add("Asia range break -> London, LONG only", "asian_breakout",
        "The same break, longs only; the swap-paying twin of the short variant.",
        "Must underperform the short twin by at least the swap or the swap model "
        "is not being applied.",
        _mk_range_break(ASIA, LONDON, side="long"),
        LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY, bias="long")
    add("Asia range break -> London, break + retest", "asian_breakout",
        "Entering on the retest of the broken edge, not the break itself, converts "
        "a wide structural stop into an affordable one.",
        "Most clean breaks never retest; if the retest subset is tiny or its "
        "expectancy is worse, the entry improvement is imaginary.",
        _mk_range_break_retest(ASIA, LONDON),
        LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Asia range break -> NY (delayed expansion)", "asian_breakout",
        "If London fails to break the Asian range, NY does; the expansion is not "
        "tied to the London clock specifically.",
        "If NY breaks work and London breaks do not, the 'London opens the range' "
        "mechanism is wrong even if the pattern pays.",
        _mk_range_break(ASIA, NY), NY, SL_NY, 2.2, 32, SPR_LOOSE, VOL_ANY)
    add("Asia range break -> Overlap", "asian_breakout",
        "The Overlap carries the deepest liquidity, so the Asian range break should "
        "resolve there most cleanly.",
        "The Overlap noise floor is $10.14 -- 9.6% of the account per trade. This "
        "candidate fails on affordability even if it wins on expectancy.",
        _mk_range_break(ASIA, OVERLAP), OVERLAP, SL_OVERLAP, 2.2, 24, SPR_LOOSE, VOL_ANY)
    add("Late range break -> Asia", "asian_breakout",
        "The same compression-expansion mechanism one session earlier: the quiet "
        "LATE range is broken by early Asian flow.",
        "Both sessions are quiet, so there may be no expansion event at all -- the "
        "mechanism requires an incoming liquidity shift, not just a new clock.",
        _mk_range_break(LATE, ASIA), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Late range break -> Asia, SHORT only", "asian_breakout",
        "Same, shorts only, in the cheapest session pair available to this account.",
        "If this fails, the cheapest-stop corner of the search space is empty and "
        "the account has no affordable breakout at all.",
        _mk_range_break(LATE, ASIA, side="short"),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY, bias="short")
    add("London range break -> NY", "asian_breakout",
        "The London range, not the Asian one, is the range NY resolves.",
        "Confounded with plain NY momentum; if it matches a generic NY breakout it "
        "adds nothing.",
        _mk_range_break(LONDON, NY), NY, SL_NY, 2.2, 32, SPR_LOOSE, VOL_ANY)
    add("Asia range break -> London, extended-vol regime", "asian_breakout",
        "Breakouts pay in high-volatility regimes because the follow-through is "
        "larger relative to a fixed stop.",
        "Directly contradicts the compression variant; both cannot be right, and "
        "if both look good the difference is noise.",
        _mk_range_break(ASIA, LONDON), LONDON, SL_LONDON, 2.8, 32, SPR_LOOSE, VOL_EXTENDED)

    # -------------------------------------------------------------------
    # H2's own adversary: the range-break FAILURE
    # -------------------------------------------------------------------
    add("Asia range break failure -> fade (London)", "range_failure",
        "The Asian range break is a liquidity event, not an expansion event: price "
        "leaves the range and closes back inside.",
        "If both this and the plain break are profitable, the exit geometry rather "
        "than the entry is producing the result.",
        _mk_range_break_failure(ASIA, LONDON),
        LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Asia range break failure -> fade (Asia, late)", "range_failure",
        "The same failure pattern against the LATE range, traded in Asia where the "
        "stop is affordable.",
        "Quiet-session reversals may be too small to clear the spread even when the "
        "direction is right.",
        _mk_range_break_failure(LATE, ASIA),
        ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Asia range break failure -> fade, SHORT only", "range_failure",
        "Failed upside breaks of the Asian range, shorts only.",
        "Upside failures may simply be rarer than downside ones, leaving too few "
        "trades to measure.",
        _mk_range_break_failure(ASIA, LONDON),
        LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY, bias="short")
    add("London range break failure -> fade (NY)", "range_failure",
        "Failed break of the London range during NY.",
        "NY stops cost ~$9 (8.5% of account); the edge must be large enough to "
        "justify that, not merely positive.",
        _mk_range_break_failure(LONDON, NY), NY, SL_NY, 2.2, 24, SPR_LOOSE, VOL_ANY)

    # -------------------------------------------------------------------
    # H3 -- session_reversal.  The logical opposite of H2, same bars.
    # -------------------------------------------------------------------
    add("Asia move fade in London (0.5x band)", "session_reversal",
        "A8/A20: overnight and intraday gold returns are strongly negatively "
        "autocorrelated, so a directional Asian session is given back in London.",
        "If the fade and the breakout are both profitable on the same bars, the "
        "result is an artifact of exits; if neither is, the session has no edge.",
        _mk_session_move_fade(ASIA, LONDON, 0.5),
        LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("Asia move fade in London (1.0x band, extreme only)", "session_reversal",
        "Only an unusually large overnight move mean-reverts; a normal one is "
        "just drift.",
        "Raising the threshold cuts the sample hard; a good result on 30 trades is "
        "not distinguishable from luck.",
        _mk_session_move_fade(ASIA, LONDON, 1.0),
        LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Asia move fade in London, SHORT only", "session_reversal",
        "Fading an Asian rally, shorts only -- the swap-free half of H3.",
        "If only the short half works, the effect may be a funding/carry artifact "
        "rather than the claimed return reversal.",
        _mk_session_move_fade(ASIA, LONDON, 0.5, side="short"),
        LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY, bias="short")
    add("Asia move fade in London, LONG only", "session_reversal",
        "Fading an Asian selloff, longs only.",
        "Long holds pay -$0.52/night; a multi-session hold must beat that before "
        "it beats zero.",
        _mk_session_move_fade(ASIA, LONDON, 0.5, side="long"),
        LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY, bias="long")
    add("Overnight move fade in day session", "session_reversal",
        "A8 stated at its natural boundary: the LATE+ASIA overnight block is faded "
        "across the whole LONDON..NY day block.",
        "The academic result uses exchange session boundaries that do not exist on "
        "24h spot; if the effect vanishes under our boundaries, it was an artifact "
        "of the close price, not a tradeable process.",
        _mk_session_move_fade(OVERNIGHT, DAY_SESSION, 0.5),
        DAY_SESSION, SL_LONDON, 2.8, 40, SPR_NORMAL, VOL_ANY)
    add("Day move fade in Late session", "session_reversal",
        "The mirror of H3: the LONDON..NY day move is given back in the LATE "
        "session, where this account's stop is cheapest ($5.16 floor).",
        "The Late session may simply be too illiquid to carry the reversal, in "
        "which case the direction is right and the fill is not.",
        _mk_session_move_fade(DAY_SESSION, LATE, 0.5),
        LATE, SL_LATE, 2.6, 20, SPR_TIGHT, VOL_ANY)
    add("Day move fade in Late session, SHORT only", "session_reversal",
        "Same, shorts only, in the cheapest session with zero swap.",
        "This is the single best constraint-fitting cell in the library; if it "
        "fails, the constraint-fit reasoning has produced nothing.",
        _mk_session_move_fade(DAY_SESSION, LATE, 0.5, side="short"),
        LATE, SL_LATE, 2.6, 20, SPR_TIGHT, VOL_ANY, bias="short")
    add("Asia close-position fade in London", "session_reversal",
        "Where the Asian session closed WITHIN its range matters more than how far "
        "it travelled: a close in the top 20% is a stretched book.",
        "Close position and net move are correlated; if this matches the move-fade "
        "candidate it is not a distinct hypothesis.",
        _mk_close_position_fade(ASIA, LONDON),
        LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("Asia close-position fade in Asia's own tail", "session_reversal",
        "The same statistic applied within the Asian session itself, where the "
        "stop is affordable.",
        "Using a session's close position while still inside that session is only "
        "valid against the PREVIOUS day's session -- if the lag makes it stale, "
        "the signal decays to nothing.",
        _mk_close_position_fade(LATE, ASIA),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Previous-day return fade at Asia open", "session_reversal",
        "A whole-day directional move is partially reversed the following day.",
        "This is daily-horizon mean reversion, which the literature places at "
        "multi-year horizons; at daily horizon it may not exist.",
        _mk_prev_day_return_fade(ASIA, 1.0),
        ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY)
    add("Previous-day return fade at Asia open, SHORT only", "session_reversal",
        "Same, shorts only.",
        "Gold's multi-year drift is upward; a short-only daily fade is fighting "
        "that drift and must overcome it.",
        _mk_prev_day_return_fade(ASIA, 1.0),
        ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY, bias="short")
    add("Day-open gap fade", "session_reversal",
        "A day that opens far from the previous close (mostly the Monday gap) "
        "closes the gap.",
        "Spot gold trades ~24h, so true gaps only occur at the weekend -- the "
        "sample is one observation per week at best.",
        _mk_gap_fade(ASIA, 0.5), ASIA, SL_ASIA, 2.5, 48, SPR_TIGHT, VOL_ANY)
    add("Day-open gap fade, Late session", "session_reversal",
        "The gap-closing flow arrives late in the day rather than at the open.",
        "If both the early and late versions work equally, timing carries no "
        "information and only the gap does.",
        _mk_gap_fade(LATE, 0.5), LATE, SL_LATE, 2.5, 20, SPR_TIGHT, VOL_ANY)

    # -------------------------------------------------------------------
    # opening_range -- break AND failure, per session
    # -------------------------------------------------------------------
    for sess_name, sess, sl, spr in (("ASIA", ASIA, SL_ASIA, SPR_TIGHT),
                                     ("LONDON", LONDON, SL_LONDON, SPR_NORMAL),
                                     ("NY", NY, SL_NY, SPR_LOOSE),
                                     ("LATE", LATE, SL_LATE, SPR_TIGHT)):
        add(f"Opening range break 1h [{sess_name}]", "opening_range",
            "A5/A6/A9: the first block of a session prices new information and sets "
            "the session's direction.",
            "A7 says ORB only works where intraday trending exists; if gold's "
            "measured follow-through is ~50%, this family is a coin flip minus cost.",
            _mk_orb(sess, 4), sess, sl, 2.5, 24, spr, VOL_ANY)
        add(f"Opening range FAILURE 1h [{sess_name}]", "opening_range",
            "The opening-range break is a stop run: price breaks the range and "
            "closes back inside it.",
            "The exact adversary of the ORB candidate above; if both look "
            "profitable the measurement is wrong.",
            _mk_orb_failure(sess, 4), sess, sl, 2.5, 24, spr, VOL_ANY)
        add(f"Opening range break 30m [{sess_name}]", "opening_range",
            "A shorter opening block reacts faster to the information shock.",
            "R12: the finer the time window, the faster the edge decays; a 30m "
            "range should be strictly worse than a 1h one if that is true.",
            _mk_orb(sess, 2), sess, sl, 2.5, 24, spr, VOL_ANY)

    add("Opening range break 1h [LONDON] + H5 noise band", "opening_range",
        "The opening range must be exceeded by 0.10x the trailing 14-day daily "
        "range, not merely touched.",
        "If the band adds nothing over the raw ORB, the false-break explanation "
        "for ORB failure is wrong.",
        _mk_orb(LONDON, 4, noise_band_k=0.10),
        LONDON, SL_LONDON, 2.8, 24, SPR_NORMAL, VOL_ANY)
    add("Opening range break 1h [ASIA] + H5 noise band", "opening_range",
        "The same self-rescaling threshold in the affordable session.",
        "The Asian session's daily-range-relative moves are small; the band may "
        "gate out every trade.",
        _mk_orb(ASIA, 4, noise_band_k=0.10),
        ASIA, SL_ASIA, 2.8, 24, SPR_TIGHT, VOL_ANY)
    add("Opening range break 1h [LATE] + H5 noise band", "opening_range",
        "Same again in the cheapest session.",
        "Same gating risk, plus a shorter session in which to reach target.",
        _mk_orb(LATE, 4, noise_band_k=0.10),
        LATE, SL_LATE, 2.8, 18, SPR_TIGHT, VOL_ANY)
    add("Opening range break 1h [LONDON] SHORT only", "opening_range",
        "London ORB, shorts only.",
        "If the long half carries the result, the effect is gold's upward drift "
        "rather than a session mechanism.",
        _mk_orb(LONDON, 4, side="short"),
        LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY, bias="short")
    add("Opening range break 1h [ASIA] SHORT only", "opening_range",
        "Asia ORB, shorts only, zero swap.",
        "Same drift objection as above.",
        _mk_orb(ASIA, 4, side="short"),
        ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY, bias="short")
    add("Opening range retest [LONDON]", "opening_range",
        "Entering on the retest of the opening-range edge gives a tighter stop for "
        "the same target.",
        "Retests are rare; the sample may not support a conclusion.",
        _mk_orb_retest(LONDON, 4), LONDON, SL_LONDON, 3.0, 24, SPR_NORMAL, VOL_ANY)
    add("Opening range retest [ASIA]", "opening_range",
        "Same, in the affordable session.",
        "Asian retests may be indistinguishable from chop.",
        _mk_orb_retest(ASIA, 4), ASIA, SL_ASIA, 3.0, 24, SPR_TIGHT, VOL_ANY)
    add("Opening range break 1h [LONDON], compressed regime", "opening_range",
        "ORB only works out of a compressed volatility regime.",
        "H11 applied to ORB; falsified if the compressed subset matches the "
        "unconditional one.",
        _mk_orb(LONDON, 4), LONDON, SL_LONDON, 2.8, 24, SPR_NORMAL, VOL_COMPRESSED)
    add("Opening range break 1h [OVERLAP]", "opening_range",
        "The deepest-liquidity block should give the cleanest opening range.",
        "Overlap requires a ~$10-11 stop = >10% of the account; unaffordable even "
        "if profitable.",
        _mk_orb(OVERLAP, 2), OVERLAP, SL_OVERLAP, 2.2, 12, SPR_LOOSE, VOL_ANY)

    # -------------------------------------------------------------------
    # H4 -- liquidity_sweep
    # -------------------------------------------------------------------
    add("PDH/PDL sweep + reclaim [ASIA]", "liquidity_sweep",
        "R1/A21: price runs the previous day's extreme, triggers clustered stops, "
        "then reclaims the level as the uninformed flow is absorbed.",
        "R1's version has NO price stop and reports no profit factor; with a hard "
        "stop the 71% claimed win rate should collapse toward breakeven.",
        _mk_level_sweep_reclaim("pdh_pdl"), ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY)
    add("PDH/PDL sweep + reclaim [LATE]", "liquidity_sweep",
        "Same mechanism in the cheapest session.",
        "Late-session sweeps may be thin-book artifacts that do not reclaim.",
        _mk_level_sweep_reclaim("pdh_pdl"), LATE, SL_LATE, 3.0, 20, SPR_TIGHT, VOL_ANY)
    add("PDH/PDL sweep + reclaim [LONDON]", "liquidity_sweep",
        "Same mechanism where the flow that runs the level is largest.",
        "London sweeps are more likely to be genuine repricings that do not revert.",
        _mk_level_sweep_reclaim("pdh_pdl"), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("PDH/PDL sweep + reclaim [NY]", "liquidity_sweep",
        "Same mechanism in the session with the most scheduled data.",
        "NY stops cost ~$9; and news-driven sweeps do not reclaim.",
        _mk_level_sweep_reclaim("pdh_pdl"), NY, SL_NY, 3.0, 32, SPR_LOOSE, VOL_ANY)
    add("PDH sweep + reclaim, SHORT only [ASIA]", "liquidity_sweep",
        "Only the sweep of the previous day HIGH, shorts only, zero swap.",
        "Upside sweeps in Asia are rare; sample size may be the binding limit.",
        _mk_level_sweep_reclaim("pdh_pdl", side="short"),
        ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY, bias="short")
    add("PDL sweep + reclaim, LONG only [ASIA]", "liquidity_sweep",
        "Only the sweep of the previous day LOW, longs only.",
        "Long holds accrue -$0.52/night; a 48-bar hold can span a rollover.",
        _mk_level_sweep_reclaim("pdh_pdl", side="long"),
        ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY, bias="long")
    add("Asian high/low sweep + reclaim [LONDON]", "liquidity_sweep",
        "The Asian session extremes are the nearest well-known level at the London "
        "open and are where the overnight stops sit.",
        "Indistinguishable from the Asia-range-break-failure candidate unless the "
        "wick condition does real work.",
        _mk_level_sweep_reclaim("asia"), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Asian high/low sweep + reclaim, SHORT only [LONDON]", "liquidity_sweep",
        "Same, shorts only.",
        "Same objection; plus a short in London may be fighting the day's trend.",
        _mk_level_sweep_reclaim("asia"),
        LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY, bias="short")
    add("Late-session high/low sweep + reclaim [ASIA]", "liquidity_sweep",
        "The LATE session's extremes are swept early in Asia.",
        "Both sessions are thin; the 'clustered stops' mechanism may not have "
        "enough participants to exist.",
        _mk_level_sweep_reclaim("late"), ASIA, SL_ASIA, 3.0, 32, SPR_TIGHT, VOL_ANY)
    add("Previous-week high/low sweep + reclaim [ASIA]", "liquidity_sweep",
        "A weekly extreme is a larger stop cluster than a daily one, so the "
        "reclaim should be correspondingly larger.",
        "Roughly one event per week per side -- the sample will be small enough "
        "that any result is fragile.",
        _mk_level_sweep_reclaim("pwh_pwl"), ASIA, SL_ASIA, 4.0, 64, SPR_TIGHT, VOL_ANY)
    add("Previous-week high/low sweep + reclaim [LATE]", "liquidity_sweep",
        "Same, in the cheapest session.",
        "Same sample-size objection, made worse by the session filter.",
        _mk_level_sweep_reclaim("pwh_pwl"), LATE, SL_LATE, 4.0, 20, SPR_TIGHT, VOL_ANY)
    add("Current-session extreme sweep [ASIA]", "liquidity_sweep",
        "The session's own developing extreme, once at least 8 bars old, is itself "
        "a stop cluster.",
        "A developing extreme is not a level anyone else is watching; the "
        "mechanism (A21) may simply be absent.",
        _mk_session_extreme_sweep(ASIA), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Current-session extreme sweep [LONDON]", "liquidity_sweep",
        "Same within London.",
        "Same objection.",
        _mk_session_extreme_sweep(LONDON), LONDON, SL_LONDON, 2.5, 16, SPR_NORMAL, VOL_ANY)
    add("Current-session extreme sweep [LATE]", "liquidity_sweep",
        "Same within the Late session.",
        "Same objection, with the fewest bars per session of any window here.",
        _mk_session_extreme_sweep(LATE, min_bars=6), LATE, SL_LATE, 2.5, 16, SPR_TIGHT, VOL_ANY)
    add("Equal-extremes sweep + reclaim [ASIA]", "liquidity_sweep",
        "Two comparable prior extremes concentrate stops between them; the sweep of "
        "the pair is a larger liquidity event than a single extreme.",
        "The 0.15xATR equality tolerance is arbitrary and is the most likely place "
        "here for the pattern to be a definition rather than a fact.",
        _mk_equal_extremes_sweep(), ASIA, SL_ASIA, 3.0, 32, SPR_TIGHT, VOL_ANY)
    add("Equal-extremes sweep + reclaim [LONDON]", "liquidity_sweep",
        "Same in London.",
        "Same objection.",
        _mk_equal_extremes_sweep(), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Daily-bias PDH/PDL sweep [ASIA]", "liquidity_sweep",
        "R1's stated rule: previous-day close vs open sets the bias and only the "
        "sweep in that direction is taken.",
        "The bias filter halves the sample; if the filtered version is no better, "
        "R1's bias step is decoration.",
        _mk_daily_bias_sweep(), ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY)
    add("Daily-bias PDH/PDL sweep [LONDON]", "liquidity_sweep",
        "Same in London where R1's original testing implicitly sat.",
        "Same objection.",
        _mk_daily_bias_sweep(), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)

    # -------------------------------------------------------------------
    # round_number  (A12 supported, A13 weakened -- low prior on purpose)
    # -------------------------------------------------------------------
    add("Round $10 sweep + reject [ASIA]", "round_number",
        "A12: round numbers are psychological barriers where stops cluster, so a "
        "sweep of a $10 level reverts.",
        "A13 failed to replicate A12 cleanly, and at $4,400 gold a $10 level is "
        "0.2% away -- the grid may be too dense to mean anything.",
        _mk_round_sweep(10.0), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Round $25 sweep + reject [ASIA]", "round_number",
        "A coarser grid should be a stronger barrier than a dense one.",
        "If $25 and $10 behave identically, the level is not the mechanism.",
        _mk_round_sweep(25.0), ASIA, SL_ASIA, 2.8, 24, SPR_TIGHT, VOL_ANY)
    add("Round $50 sweep + reject [ASIA]", "round_number",
        "The coarsest grid tested; at $4,400 gold, $50 levels are the analogue of "
        "the $10 levels A12 studied at $400 gold.",
        "Scale-adjusting the grid to preserve A12's relative spacing is itself an "
        "assumption; if none of the three grids works the family is dead.",
        _mk_round_sweep(50.0), ASIA, SL_ASIA, 3.0, 32, SPR_TIGHT, VOL_ANY)
    add("Round $50 sweep + reject [LATE]", "round_number",
        "Same coarse grid in the cheapest session.",
        "Same objection.",
        _mk_round_sweep(50.0), LATE, SL_LATE, 3.0, 20, SPR_TIGHT, VOL_ANY)
    add("Round $50 sweep + reject [LONDON]", "round_number",
        "Same coarse grid where the order flow that respects levels is largest.",
        "Same objection.",
        _mk_round_sweep(50.0), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Round $50 sweep + reject, SHORT only [ASIA]", "round_number",
        "Rejection from above a round level, shorts only.",
        "Same objection plus a halved sample.",
        _mk_round_sweep(50.0, side="short"),
        ASIA, SL_ASIA, 3.0, 32, SPR_TIGHT, VOL_ANY, bias="short")
    add("Round $50 decisive break [ASIA]", "round_number",
        "The opposite of the barrier claim: a decisive close through a round level "
        "continues, because the barrier's defenders have been cleared.",
        "A level cannot be both a barrier and a launchpad; if both variants look "
        "profitable, round numbers are doing nothing and the exits are.",
        _mk_round_break(50.0), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Round $50 decisive break [LONDON]", "round_number",
        "Same in London.",
        "Same objection.",
        _mk_round_break(50.0), LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("Round $25 decisive break [ASIA]", "round_number",
        "Same at the intermediate grid.",
        "Same objection.",
        _mk_round_break(25.0), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)

    # -------------------------------------------------------------------
    # H5 -- noise_band standalone
    # -------------------------------------------------------------------
    for k in (0.25, 0.40, 0.60):
        add(f"Noise-band break from day open (k={k}) [ASIA]", "noise_band",
            "A4: a move beyond the trailing 14-day average intraday range is an "
            "imbalance, not noise; the threshold rescales with the regime.",
            "If a fixed-ATR threshold performs identically, the self-rescaling "
            "property is cosmetic and H5's regime-portability claim is unsupported.",
            _mk_noise_band_break("day_open", k, ASIA),
            ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Noise-band break from day open (k=0.40) [LONDON]", "noise_band",
        "Same, in the session where the band is most likely to be exceeded.",
        "Exceeding the band by London is near-automatic on trending days; the "
        "signal may be a tautology rather than a filter.",
        _mk_noise_band_break("day_open", 0.40, LONDON),
        LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("Noise-band break from day open (k=0.40) [NY]", "noise_band",
        "Same in NY.",
        "Same objection, plus a ~$9 stop.",
        _mk_noise_band_break("day_open", 0.40, NY),
        NY, SL_NY, 2.5, 32, SPR_LOOSE, VOL_ANY)
    add("Noise-band break from day open (k=0.40) [LATE]", "noise_band",
        "Same in the cheapest session.",
        "By the Late session most of the day's range is already spent; the band "
        "may be exceeded with no move left.",
        _mk_noise_band_break("day_open", 0.40, LATE),
        LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Noise-band break from session open (k=0.25) [ASIA]", "noise_band",
        "Anchoring to the session open rather than the day open makes the band a "
        "session statistic.",
        "The Asian session's share of the daily range is small, so a day-scaled "
        "band may never be reached inside it.",
        _mk_noise_band_break("session_open", 0.25, ASIA),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Noise-band break from session open (k=0.25) [LATE]", "noise_band",
        "Same in the Late session.",
        "Same objection.",
        _mk_noise_band_break("session_open", 0.25, LATE),
        LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Noise-band break from previous close (k=0.50) [ASIA]", "noise_band",
        "Anchoring to the previous day's close makes the band an overnight-move "
        "statistic and links H5 to H3's boundary.",
        "If this matches the day-open anchor, the anchor carries no information.",
        _mk_noise_band_break("prev_close", 0.50, ASIA),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Noise-band break, SHORT only (k=0.40) [ASIA]", "noise_band",
        "Same, shorts only.",
        "Same objection plus a halved sample.",
        _mk_noise_band_break("day_open", 0.40, ASIA, side="short"),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY, bias="short")
    add("Noise-band FADE (k=1.0) [ASIA]", "noise_band",
        "Beyond 1.0x the trailing daily range the move is exhausted rather than "
        "confirmed, and reverts toward the day open.",
        "The exact adversary of the break variants; both cannot be right.",
        _mk_noise_band_fade("day_open", 1.0, ASIA),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Noise-band FADE (k=1.0) [LATE]", "noise_band",
        "Same in the Late session, where the day's move is most likely complete.",
        "Same objection.",
        _mk_noise_band_fade("day_open", 1.0, LATE),
        LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Noise-band FADE (k=1.5, extreme) [LATE]", "noise_band",
        "Only a 1.5x band excursion is exhausted; 1.0x is still trend.",
        "Raising the threshold to 1.5x may leave fewer than 50 events.",
        _mk_noise_band_fade("day_open", 1.5, LATE),
        LATE, SL_LATE, 3.0, 18, SPR_TIGHT, VOL_ANY)
    add("Noise-band FADE (k=1.0) [NY]", "noise_band",
        "Same in NY, where the largest excursions occur.",
        "NY stop cost ~$9; and NY excursions are often news-driven trends, not "
        "exhaustion.",
        _mk_noise_band_fade("day_open", 1.0, NY),
        NY, SL_NY, 2.5, 32, SPR_LOOSE, VOL_ANY)

    # -------------------------------------------------------------------
    # H6 -- tod_volatility.  Stops and thresholds sized to the HOUR.
    # -------------------------------------------------------------------
    add("Time-of-day vol spike continuation (3x slot norm) [ASIA]", "tod_volatility",
        "A19: intraday volatility is dominated by a deterministic time-of-day "
        "component, so a spike must be measured against the norm FOR THAT SLOT. A "
        "3x slot-relative spike is real news arriving in a quiet hour.",
        "If flat-ATR spike detection performs the same, the time-of-day correction "
        "does not matter and A19's implication for us is overstated.",
        _mk_tod_spike(3.0, "continue"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Time-of-day vol spike FADE (3x slot norm) [ASIA]", "tod_volatility",
        "The same slot-relative spike is an illiquidity artifact and reverts.",
        "Adversary of the continuation twin; both cannot be right.",
        _mk_tod_spike(3.0, "fade"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Time-of-day vol spike continuation (3x) [LATE]", "tod_volatility",
        "Same in the Late session.",
        "Late-session spikes are the most likely to be liquidity gaps rather than "
        "information.",
        _mk_tod_spike(3.0, "continue"), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Time-of-day vol spike FADE (3x) [LATE]", "tod_volatility",
        "Same, faded.",
        "Adversary of the above.",
        _mk_tod_spike(3.0, "fade"), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Time-of-day vol spike continuation (4x) [LONDON]", "tod_volatility",
        "A higher multiple is required in an already-volatile hour.",
        "London's slot norm is already large; a 4x spike may be pure news, where "
        "retail spread is worst.",
        _mk_tod_spike(4.0, "continue"), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Time-of-day quiet compression break [ASIA]", "tod_volatility",
        "Eight consecutive bars below 0.6x their own slot norm is genuine "
        "compression; the subsequent range break is the expansion.",
        "Flat-ATR compression screens select the Asian session automatically; if "
        "slot-relative compression selects the same bars, H6 adds nothing here.",
        _mk_tod_quiet_break(8, 0.6), ASIA, SL_ASIA, 2.8, 32, SPR_TIGHT, VOL_ANY)
    add("Time-of-day quiet compression break [LATE]", "tod_volatility",
        "Same in the Late session.",
        "Same objection.",
        _mk_tod_quiet_break(8, 0.6), LATE, SL_LATE, 2.8, 18, SPR_TIGHT, VOL_ANY)
    add("Time-of-day quiet compression break [LONDON]", "tod_volatility",
        "Compression inside a normally-loud hour should be the strongest "
        "compression signal available.",
        "It may also be so rare that it never fires.",
        _mk_tod_quiet_break(8, 0.6), LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY)
    add("Time-of-day relative move FADE (2x, 8 bars) [ASIA]", "tod_volatility",
        "A move of 2x the slot-normal volatility over 8 bars is stretched for that "
        "hour and reverts.",
        "The flat-ATR version of this is in the exhaustion family; if they agree, "
        "the normalisation is irrelevant.",
        _mk_tod_relative_move(8, 2.0, "fade"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Time-of-day relative move CONTINUE (2x, 8 bars) [ASIA]", "tod_volatility",
        "The same stretch is momentum, not exhaustion.",
        "Adversary of the above.",
        _mk_tod_relative_move(8, 2.0, "continue"),
        ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Time-of-day relative move FADE (2x) [LATE]", "tod_volatility",
        "Same fade in the Late session.",
        "Same objection.",
        _mk_tod_relative_move(8, 2.0, "fade"), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Time-of-day relative move FADE (2.5x) [NY]", "tod_volatility",
        "Same fade where slot norms are largest.",
        "A ~$9 stop and news-driven trends both work against a fade here.",
        _mk_tod_relative_move(8, 2.5, "fade"), NY, SL_NY, 2.5, 24, SPR_LOOSE, VOL_ANY)

    # -------------------------------------------------------------------
    # structure -- BOS / CHoCH / displacement / FVG / inside bars
    # -------------------------------------------------------------------
    add("BOS + retest [ASIA]", "structure",
        "A break of a 20-bar structural level that is retested and holds marks a "
        "genuine repricing rather than a wick.",
        "Retest is a definition, not an observation; few clean instances, and the "
        "level is only 'structure' because we drew a rolling window there.",
        _mk_bos_retest(20), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("BOS + retest [LONDON]", "structure",
        "Same in London.",
        "Same objection.",
        _mk_bos_retest(20), LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("BOS + retest [LATE]", "structure",
        "Same in the cheapest session.",
        "Same objection; and Late has too few bars for a 20-bar structure to form "
        "inside the session.",
        _mk_bos_retest(20), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("BOS + retest, SHORT only [ASIA]", "structure",
        "Same, shorts only.",
        "Same objection plus a halved sample.",
        _mk_bos_retest(20), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY, bias="short")
    add("Change of character [ASIA]", "structure",
        "The FIRST break against an established swing sequence marks a regime "
        "change, unlike a break with the trend which is continuation.",
        "Swing structure is lagging by construction; the character has usually "
        "already changed by the time the rule detects it.",
        _mk_choch(12), ASIA, SL_ASIA, 2.8, 32, SPR_TIGHT, VOL_ANY)
    add("Change of character [LONDON]", "structure",
        "Same in London.",
        "Same objection.",
        _mk_choch(12), LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY)
    add("Change of character [LATE]", "structure",
        "Same in the Late session.",
        "Same objection.",
        _mk_choch(12), LATE, SL_LATE, 2.8, 18, SPR_TIGHT, VOL_ANY)
    add("Change of character, extended regime [ASIA]", "structure",
        "A character change only means something after an extended move.",
        "Conditioning on extension after the fact is the classic way to make a "
        "reversal rule look good in-sample.",
        _mk_choch(12), ASIA, SL_ASIA, 2.8, 32, SPR_TIGHT, VOL_EXTENDED)
    add("Displacement continuation [ASIA]", "structure",
        "A bar whose body exceeds 1.5xATR and fills 60% of its range is a "
        "one-sided repricing that continues.",
        "Large bodies are frequently the END of a move; measured follow-through in "
        "gold is ~48-50%, so this should fail.",
        _mk_displacement(1.5, "continue"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Displacement FADE [ASIA]", "structure",
        "The same bar is exhaustion and reverts.",
        "Adversary of the above; both cannot be right.",
        _mk_displacement(1.5, "fade"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Displacement continuation [LONDON]", "structure",
        "Same in London where displacement is most likely to be information.",
        "Same objection.",
        _mk_displacement(1.5, "continue"), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Displacement FADE [LATE]", "structure",
        "Late-session displacement is a liquidity gap and reverts.",
        "Thin-book moves may not revert until the next session opens, past the "
        "time stop.",
        _mk_displacement(1.5, "fade"), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Displacement continuation, SHORT only [ASIA]", "structure",
        "Same, shorts only.",
        "Same objection plus a halved sample.",
        _mk_displacement(1.5, "continue"),
        ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY, bias="short")
    add("FVG re-entry continuation [ASIA]", "structure",
        "A three-bar imbalance is unfilled inventory; price returning into it "
        "continues in the direction that created it.",
        "On a 24h instrument three-bar gaps are mostly noise, and the 'imbalance' "
        "reading has no order-book evidence behind it.",
        _mk_fvg_entry("continue"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("FVG re-entry FADE [ASIA]", "structure",
        "The return into the gap is the reversal, not the continuation.",
        "Adversary of the above.",
        _mk_fvg_entry("fade"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("FVG re-entry continuation [LONDON]", "structure",
        "Same in London.",
        "Same objection.",
        _mk_fvg_entry("continue"), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Two-bar inside break [ASIA]", "structure",
        "Two consecutive bars contained within one reference bar is compression; "
        "the break of the reference bar is the expansion.",
        "Compression predicts expansion but not direction -- this rule assumes it "
        "predicts both.",
        _mk_inside_break(2), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Two-bar inside break [LATE]", "structure",
        "Same in the Late session.",
        "Same objection.",
        _mk_inside_break(2), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Three-bar inside break [ASIA]", "structure",
        "A longer contained sequence is stronger compression.",
        "Longer sequences are rarer; the sample may collapse.",
        _mk_inside_break(3), ASIA, SL_ASIA, 2.8, 24, SPR_TIGHT, VOL_ANY)

    # -------------------------------------------------------------------
    # contraction -> expansion
    # -------------------------------------------------------------------
    add("NR7 break [ASIA]", "contraction",
        "The narrowest range in seven bars precedes a directional expansion.",
        "One of the most published patterns in existence; if it still works after "
        "cost, the reason is the session filter, not the pattern.",
        _mk_nr_break(7), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("NR7 break [LATE]", "contraction",
        "Same in the Late session.",
        "Same objection.",
        _mk_nr_break(7), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("NR7 break [LONDON]", "contraction",
        "Same in London.",
        "Same objection.",
        _mk_nr_break(7), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("NR4 break [ASIA]", "contraction",
        "A shorter compression window fires more often for the same mechanism.",
        "If NR4 and NR7 differ materially, the window length is being fitted.",
        _mk_nr_break(4), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Squeeze break [ASIA]", "contraction",
        "Bollinger bands inside Keltner channels is volatility compression; the "
        "close outside the band is the release.",
        "Compression reliably predicts expansion but NOT its direction; the "
        "direction half of this rule is unsupported.",
        _mk_squeeze("break"), ASIA, SL_ASIA, 2.8, 32, SPR_TIGHT, VOL_COMPRESSED)
    add("Squeeze break [LONDON]", "contraction",
        "Same in London.",
        "Same objection.",
        _mk_squeeze("break"), LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_COMPRESSED)
    add("Squeeze break [LATE]", "contraction",
        "Same in the Late session.",
        "Same objection.",
        _mk_squeeze("break"), LATE, SL_LATE, 2.8, 18, SPR_TIGHT, VOL_COMPRESSED)
    add("Squeeze FAILURE fade [ASIA]", "contraction",
        "The first move out of a squeeze is the false one.",
        "Adversary of the squeeze break; both cannot be right.",
        _mk_squeeze("fade"), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_COMPRESSED)
    add("Range-percentile compression break [ASIA]", "contraction",
        "The 24-bar range in the bottom quartile of its own trailing distribution "
        "is compression measured relative to the instrument, not to a constant.",
        "Same direction problem as the squeeze; and the percentile is computed on "
        "a 200-bar window that spans several sessions.",
        _mk_range_pct_break(24, 0.25), ASIA, SL_ASIA, 2.8, 32, SPR_TIGHT, VOL_ANY)
    add("Range-percentile compression break [LATE]", "contraction",
        "Same in the Late session.",
        "Same objection.",
        _mk_range_pct_break(24, 0.25), LATE, SL_LATE, 2.8, 18, SPR_TIGHT, VOL_ANY)
    add("Range-percentile compression break [LONDON]", "contraction",
        "Same in London.",
        "Same objection.",
        _mk_range_pct_break(24, 0.25), LONDON, SL_LONDON, 2.8, 32, SPR_NORMAL, VOL_ANY)
    add("Coil-then-expand [ASIA]", "contraction",
        "Contraction and expansion as ONE event: ATR falling over 12 bars followed "
        "immediately by a bar exceeding 2x the compressed ATR.",
        "Requiring both in one bar may make the rule so rare it cannot be measured, "
        "and the expansion bar itself may be the whole move.",
        _mk_coil_expand(12), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Coil-then-expand [LONDON]", "contraction",
        "Same in London.",
        "Same objection.",
        _mk_coil_expand(12), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Coil-then-expand [LATE]", "contraction",
        "Same in the Late session.",
        "Same objection.",
        _mk_coil_expand(12), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)

    # -------------------------------------------------------------------
    # rejection / exhaustion
    # -------------------------------------------------------------------
    add("Session high/low rejection [ASIA]", "rejection",
        "A long wick at the session's own developing extreme is a failed attempt "
        "to extend, and the session reverts within itself.",
        "Wicks are extremely common and most carry no information; the 0.5 wick "
        "fraction is the only thing separating signal from every bar.",
        _mk_session_extreme_rejection(ASIA), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Session high/low rejection [LONDON]", "rejection",
        "Same in London.",
        "Same objection.",
        _mk_session_extreme_rejection(LONDON), LONDON, SL_LONDON, 2.5, 16, SPR_NORMAL, VOL_ANY)
    add("Session high/low rejection [LATE]", "rejection",
        "Same in the Late session.",
        "Same objection; Late sessions are short so 'developing extreme' is based "
        "on few bars.",
        _mk_session_extreme_rejection(LATE, min_bars=4), LATE, SL_LATE, 2.5, 16, SPR_TIGHT, VOL_ANY)
    add("Session HIGH rejection, SHORT only [ASIA]", "rejection",
        "Only rejection from the session high, shorts only, zero swap.",
        "Same objection plus a halved sample.",
        _mk_session_extreme_rejection(ASIA),
        ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY, bias="short")
    add("Session high/low rejection [NY]", "rejection",
        "Same in NY.",
        "A ~$9 stop makes a 2.5R target a $22 move; NY sessions may not offer it "
        "within the time stop.",
        _mk_session_extreme_rejection(NY), NY, SL_NY, 2.5, 16, SPR_LOOSE, VOL_ANY)
    add("Extension exhaustion (2xATR / 8 bars + wick) [ASIA]", "rejection",
        "A 2xATR move in 8 bars that ends with a 35% opposing wick has overshot.",
        "Exhaustion is only identifiable afterwards; in a trend the move simply "
        "continues and the wick means nothing.",
        _mk_extension_exhaustion(8, 2.0), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_EXTENDED)
    add("Extension exhaustion [LATE]", "rejection",
        "Same in the Late session, where the day's move is most likely complete.",
        "Same objection.",
        _mk_extension_exhaustion(8, 2.0), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_EXTENDED)
    add("Extension exhaustion [LONDON]", "rejection",
        "Same in London.",
        "Same objection.",
        _mk_extension_exhaustion(8, 2.0), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_EXTENDED)
    add("Extension exhaustion (3xATR, extreme) [ASIA]", "rejection",
        "Only a 3xATR overshoot is genuinely exhausted.",
        "Raising the bar cuts the sample to the point where a good result is "
        "indistinguishable from luck.",
        _mk_extension_exhaustion(8, 3.0), ASIA, SL_ASIA, 3.0, 24, SPR_TIGHT, VOL_ANY)
    add("Momentum divergence at 20-bar extreme [ASIA]", "rejection",
        "A new 20-bar price extreme that RSI does not confirm marks weakening "
        "participation.",
        "Divergence is the single most cherry-picked pattern in technical analysis; "
        "stated arithmetically it fires constantly and predicts nothing.",
        _mk_momentum_divergence(20), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Momentum divergence at 20-bar extreme [LONDON]", "rejection",
        "Same in London.",
        "Same objection.",
        _mk_momentum_divergence(20), LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)
    add("Momentum divergence, SHORT only [ASIA]", "rejection",
        "Same, shorts only.",
        "Same objection plus a halved sample.",
        _mk_momentum_divergence(20),
        ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY, bias="short")
    add("Volume climax reversal [ASIA]", "rejection",
        "A bar with 3x average tick volume and a 40% opposing wick is a capitulation "
        "that reverses.",
        "Tick volume is not traded volume; on a CFD feed it is a quote-update count "
        "and may track spread widening rather than participation.",
        _mk_volume_climax(3.0), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Volume climax reversal [LONDON]", "rejection",
        "Same in London.",
        "Same objection.",
        _mk_volume_climax(3.0), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Volume climax reversal [LATE]", "rejection",
        "Same in the Late session.",
        "Same objection; Late tick counts are lowest so a 3x multiple is easiest to "
        "hit for mechanical reasons.",
        _mk_volume_climax(3.0), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)
    add("Three-push exhaustion [ASIA]", "rejection",
        "Three successively higher 6-bar highs followed by a close below the prior "
        "bar's low is a completed push sequence.",
        "Counting pushes is pattern-matching after the fact; the third push is only "
        "the last one because the rule stopped counting.",
        _mk_three_push(6), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Three-push exhaustion [LONDON]", "rejection",
        "Same in London.",
        "Same objection.",
        _mk_three_push(6), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Three-push exhaustion [LATE]", "rejection",
        "Same in the Late session.",
        "Same objection.",
        _mk_three_push(6), LATE, SL_LATE, 2.5, 18, SPR_TIGHT, VOL_ANY)

    # -------------------------------------------------------------------
    # mean_reversion (anchored)
    # -------------------------------------------------------------------
    add("Session-open reversion (1.5xATR) [ASIA]", "mean_reversion",
        "Within a quiet session price oscillates around its opening print, so a "
        "1.5xATR excursion from it reverts.",
        "In a trending session the excursion extends; and the Asian session is "
        "exactly where an overnight trend would run undisturbed.",
        _mk_session_open_revert(ASIA, 1.5), ASIA, SL_ASIA, 2.0, 24, SPR_TIGHT, VOL_ANY)
    add("Session-open reversion (1.5xATR) [LATE]", "mean_reversion",
        "Same in the Late session.",
        "Same objection.",
        _mk_session_open_revert(LATE, 1.5), LATE, SL_LATE, 2.0, 16, SPR_TIGHT, VOL_ANY)
    add("Session-open reversion (2.0xATR) [ASIA]", "mean_reversion",
        "A larger excursion is a stronger reversion signal.",
        "Larger excursions are also more likely to be genuine trends.",
        _mk_session_open_revert(ASIA, 2.0), ASIA, SL_ASIA, 2.5, 24, SPR_TIGHT, VOL_ANY)
    add("Session-open reversion (2.0xATR) [LONDON]", "mean_reversion",
        "Same in London.",
        "London is where new information arrives; reversion should be weakest here.",
        _mk_session_open_revert(LONDON, 2.0), LONDON, SL_LONDON, 2.2, 16, SPR_NORMAL, VOL_ANY)
    add("Session-open reversion, SHORT only [ASIA]", "mean_reversion",
        "Same, shorts only.",
        "Same objection plus a halved sample.",
        _mk_session_open_revert(ASIA, 1.5),
        ASIA, SL_ASIA, 2.0, 24, SPR_TIGHT, VOL_ANY, bias="short")
    add("Session VWAP reversion (1.5xATR) [ASIA]", "mean_reversion",
        "A session-anchored VWAP is the session's fair value; deviation from it "
        "reverts. Anchored, unlike v1's rolling VWAP which had no session reset.",
        "Tick volume is a quote-update count, so this VWAP is only loosely "
        "volume-weighted and may be little more than a moving average.",
        _mk_session_vwap_revert(ASIA, 1.5), ASIA, SL_ASIA, 2.2, 24, SPR_TIGHT, VOL_ANY)
    add("Session VWAP reversion (1.5xATR) [LONDON]", "mean_reversion",
        "Same in London.",
        "Same objection.",
        _mk_session_vwap_revert(LONDON, 1.5), LONDON, SL_LONDON, 2.2, 16, SPR_NORMAL, VOL_ANY)
    add("Session VWAP reversion (1.5xATR) [LATE]", "mean_reversion",
        "Same in the Late session.",
        "Same objection; Late tick volume is thinnest.",
        _mk_session_vwap_revert(LATE, 1.5), LATE, SL_LATE, 2.2, 16, SPR_TIGHT, VOL_ANY)
    add("Session VWAP reversion (2.0xATR) [NY]", "mean_reversion",
        "Same in NY where volume is real enough for VWAP to mean something.",
        "A ~$9 stop; and NY deviations are news-driven.",
        _mk_session_vwap_revert(NY, 2.0), NY, SL_NY, 2.2, 16, SPR_LOOSE, VOL_ANY)
    add("Bollinger fade [ASIA]", "mean_reversion",
        "Piercing a 2-sigma band and closing back inside reverts.",
        "Band breaks precede expansion as often as reversion; this is the null "
        "candidate for the whole mean-reversion family.",
        _mk_bb_fade(20, 2.0), ASIA, SL_ASIA, 2.0, 24, SPR_TIGHT, VOL_ANY)
    add("Bollinger fade [LATE]", "mean_reversion",
        "Same in the Late session.",
        "Same objection.",
        _mk_bb_fade(20, 2.0), LATE, SL_LATE, 2.0, 16, SPR_TIGHT, VOL_ANY)
    add("Bollinger fade, compressed regime [ASIA]", "mean_reversion",
        "Reversion works specifically when volatility is compressed.",
        "Compressed volatility also means the target is small relative to spread; "
        "the direction can be right and the trade still lose.",
        _mk_bb_fade(20, 2.0), ASIA, SL_ASIA, 2.0, 24, SPR_TIGHT, VOL_COMPRESSED)
    add("Previous-day close retest [ASIA]", "mean_reversion",
        "The previous day's close is the most-watched non-extreme level; price "
        "returning to it after leaving is a magnet effect.",
        "'Most watched' is an assertion about other participants that we have no "
        "evidence for; the level may just be where price already was.",
        _mk_prev_close_retest(0.25), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Previous-day close retest [LONDON]", "mean_reversion",
        "Same in London.",
        "Same objection.",
        _mk_prev_close_retest(0.25), LONDON, SL_LONDON, 2.5, 32, SPR_NORMAL, VOL_ANY)

    # -------------------------------------------------------------------
    # mtf_alignment  (H10 -- filters, tested as ablations)
    # -------------------------------------------------------------------
    add("Weekly-bias 20-bar break [ASIA]", "mtf_alignment",
        "A11: only take intraday breaks aligned with the higher-timeframe "
        "direction, here the previous week's midpoint.",
        "Halves the sample on an already small trade count, and time-series "
        "momentum is documented to have decayed post-2010.",
        _mk_weekly_bias_break(ASIA), ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY)
    add("Weekly-bias 20-bar break [LONDON]", "mtf_alignment",
        "Same in London.",
        "Same objection.",
        _mk_weekly_bias_break(LONDON), LONDON, SL_LONDON, 3.0, 32, SPR_NORMAL, VOL_ANY)
    add("Weekly-bias 20-bar break [LATE]", "mtf_alignment",
        "Same in the Late session.",
        "Same objection.",
        _mk_weekly_bias_break(LATE), LATE, SL_LATE, 3.0, 18, SPR_TIGHT, VOL_ANY)
    add("Weekly-bias 20-bar break, SHORT only [ASIA]", "mtf_alignment",
        "Same, shorts only.",
        "Shorting a market with a documented long-run upward drift needs the "
        "weekly filter to be genuinely informative, not merely recent.",
        _mk_weekly_bias_break(ASIA),
        ASIA, SL_ASIA, 3.0, 48, SPR_TIGHT, VOL_ANY, bias="short")
    add("Daily-bias pullback to session open [ASIA]", "mtf_alignment",
        "Previous-day direction sets the bias; the entry is the first pullback "
        "through the session open in that direction. Two timeframes, one rule.",
        "Previous-day direction has near-zero autocorrelation at daily horizon; if "
        "so the bias half contributes nothing and this is a pullback rule.",
        _mk_htf_pullback(ASIA), ASIA, SL_ASIA, 2.5, 32, SPR_TIGHT, VOL_ANY)
    add("Daily-bias pullback to session open [LONDON]", "mtf_alignment",
        "Same in London.",
        "Same objection.",
        _mk_htf_pullback(LONDON), LONDON, SL_LONDON, 2.5, 24, SPR_NORMAL, VOL_ANY)
    add("Daily-bias pullback to session open [NY]", "mtf_alignment",
        "Same in NY.",
        "Same objection plus a ~$9 stop.",
        _mk_htf_pullback(NY), NY, SL_NY, 2.5, 24, SPR_LOOSE, VOL_ANY)
    add("Daily-bias pullback to session open [LATE]", "mtf_alignment",
        "Same in the Late session.",
        "Same objection; and the Late session may not contain a pullback at all.",
        _mk_htf_pullback(LATE), LATE, SL_LATE, 2.5, 16, SPR_TIGHT, VOL_ANY)

    return lib


def library_summary(lib: Optional[Sequence[Candidate]] = None) -> Dict[str, Dict[str, int]]:
    """Counts by family, session and direction bias -- used by the index writer."""
    lib = list(build_library_v2()) if lib is None else list(lib)
    names = {ASIA: "ASIA", LONDON: "LONDON", OVERLAP: "OVERLAP", NY: "NY",
             LATE: "LATE", DAY_SESSION: "DAY(LDN-NY)", ALL_DAY: "ALL"}
    fam: Dict[str, int] = {}
    sess: Dict[str, int] = {}
    bias: Dict[str, int] = {}
    for c in lib:
        fam[c.family] = fam.get(c.family, 0) + 1
        s = names.get(c.session, str(c.session))
        sess[s] = sess.get(s, 0) + 1
        bias[c.direction_bias] = bias.get(c.direction_bias, 0) + 1
    return {"family": fam, "session": sess, "bias": bias, "total": {"n": len(lib)}}


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(library_summary(), indent=2))
