"""Empirical characterisation of XAUUSD before any strategy is proposed.

Every candidate setup in this project has to point at a measured property of the
instrument. This module produces those measurements, so a hypothesis can be
grounded in something rather than borrowed from a forum post.

It deliberately establishes the **null baselines** first: what excursion profile,
follow-through rate and directional efficiency does gold produce with no signal
at all? A strategy that matches the null is not a strategy. The random-entry
control already showed that the three live strategies sit on the null, so these
baselines are the bar every candidate must clear.

All statistics are computed on broker M15 bars, in-sample window only. The
locked holdout (2022-06-07 -> 2025-04-02) is never touched here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))

# Sessions in IST, matching how the live system labels them.
SESSIONS = {
    "ASIA": (2.5, 11.5),
    "LONDON": (11.5, 15.5),
    "OVERLAP": (15.5, 17.5),
    "NY": (17.5, 21.5),
    "LATE": (21.5, 26.5),  # wraps past midnight
}


# ---------------------------------------------------------------------------
# Indicators (vectorised, Wilder-smoothed to match the live implementations)
# ---------------------------------------------------------------------------


def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    tr = np.empty(len(h))
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum(h[1:] - l[1:],
                        np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return tr


def wilder(x: np.ndarray, period: int) -> np.ndarray:
    """Wilder's smoothing, seeded with an SMA -- same convention as RiskManager."""
    out = np.full(len(x), np.nan)
    if len(x) < period:
        return out
    out[period - 1] = x[:period].mean()
    for i in range(period, len(x)):
        out[i] = (out[i - 1] * (period - 1) + x[i]) / period
    return out


def atr(rates: np.ndarray, period: int = 14) -> np.ndarray:
    return wilder(true_range(rates["high"], rates["low"], rates["close"]), period)


def adx(rates: np.ndarray, period: int = 14) -> np.ndarray:
    """Proper Wilder ADX. The old backtester computed DX and called it ADX."""
    h, l, c = rates["high"], rates["low"], rates["close"]
    up = np.zeros(len(h))
    dn = np.zeros(len(h))
    up[1:] = h[1:] - h[:-1]
    dn[1:] = l[:-1] - l[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)

    tr_s = wilder(true_range(h, l, c), period)
    plus_s = wilder(plus_dm, period)
    minus_s = wilder(minus_dm, period)

    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100.0 * plus_s / tr_s
        mdi = 100.0 * minus_s / tr_s
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    return wilder(np.nan_to_num(dx, nan=0.0), period)


def ema(x: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < period:
        return out
    out[period - 1] = x[:period].mean()
    k = 2.0 / (period + 1)
    for i in range(period, len(x)):
        out[i] = x[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(x: np.ndarray, period: int = 14) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < period + 1:
        return out
    d = np.diff(x)
    g = np.where(d > 0, d, 0.0)
    lo = np.where(d < 0, -d, 0.0)
    ag, al = g[:period].mean(), lo[:period].mean()
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period, len(d)):
        ag = (ag * (period - 1) + g[i]) / period
        al = (al * (period - 1) + lo[i]) / period
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def efficiency_ratio(c: np.ndarray, period: int = 20) -> np.ndarray:
    """Kaufman efficiency ratio: |net move| / sum(|bar moves|).

    Near 1.0 = clean directional travel. Near 0.0 = chop. This is the single
    most direct numeric definition of the "choppiness" the project has been
    describing qualitatively.
    """
    out = np.full(len(c), np.nan)
    if len(c) <= period:
        return out
    absd = np.abs(np.diff(c))
    for i in range(period, len(c)):
        denom = absd[i - period:i].sum()
        out[i] = abs(c[i] - c[i - period]) / denom if denom > 0 else 0.0
    return out


def time_of_day_atr(
    rates: np.ndarray,
    period: int = 14,
    bucket_minutes: int = 60,
    tz: timezone = IST,
    min_samples: int = 20,
) -> Dict[str, np.ndarray]:
    """ATR conditioned on hour-of-day, alongside the flat 24h ATR.

    **Why this exists.** Every stop in this system is `k * ATR14`, and ATR14 on
    M15 bars is a flat 24-hour average. Andersen & Bollerslev showed intraday
    volatility follows a strong, stable diurnal pattern -- for gold the London/NY
    overlap runs several times the late-Asia trough. A flat ATR is therefore
    *systematically* too wide during quiet hours (the stop sits far beyond any
    plausible adverse move, so losers are maximally expensive) and too tight
    during active hours (the stop sits inside routine noise, so winners are
    stopped out before they work). That is a bias with a known sign, not noise,
    and it distorts every ATR-based stop this project has ever backtested.

    This is a *measurement*, not a change to live behaviour: nothing calls it
    yet. It is here so a stop rule scaled by time-of-day can be compared against
    the flat rule on the same bars.

    Args:
        rates: structured bar array with `time`, `high`, `low`, `close`.
        period: Wilder period, matching `atr()`.
        bucket_minutes: width of each time-of-day bucket. 60 gives 24 buckets;
            15 gives 96, one per M15 bar of the day.
        tz: timezone the buckets are defined in. IST, matching how this project
            labels sessions.
        min_samples: buckets with fewer observations than this get NaN rather
            than a mean of three numbers presented as a volatility profile.

    Returns:
        flat_atr:     the ordinary ATR14, one value per bar (the baseline).
        bucket:       bucket index for each bar.
        bucket_atr:   mean ATR within each bucket, indexed by bucket.
        bucket_n:     observation count per bucket.
        bucket_ratio: bucket_atr / overall mean ATR. This is the correction
            factor: 1.4 means a flat ATR understates this hour by 40%.
        atr_tod:      per-bar ATR rescaled by its bucket ratio, i.e. what a
            time-of-day-aware ATR would have read on each bar.
    """
    if bucket_minutes <= 0 or 1440 % bucket_minutes:
        raise ValueError("bucket_minutes must divide 1440")

    flat = atr(rates, period)
    n_buckets = 1440 // bucket_minutes

    times = rates["time"].astype(np.int64)
    minute_of_day = np.array([
        (lambda d: d.hour * 60 + d.minute)(
            datetime.fromtimestamp(int(t), tz=timezone.utc).astimezone(tz)
        )
        for t in times
    ])
    bucket = (minute_of_day // bucket_minutes).astype(np.int64)

    bucket_atr = np.full(n_buckets, np.nan)
    bucket_n = np.zeros(n_buckets, dtype=np.int64)
    valid = ~np.isnan(flat)
    for b in range(n_buckets):
        sel = valid & (bucket == b)
        cnt = int(sel.sum())
        bucket_n[b] = cnt
        if cnt >= min_samples:
            bucket_atr[b] = float(flat[sel].mean())

    overall = float(np.nanmean(flat)) if valid.any() else np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        bucket_ratio = bucket_atr / overall if overall and overall == overall else np.full(
            n_buckets, np.nan)

    # Per-bar view: the flat ATR scaled to its own hour. Buckets without enough
    # data fall back to the flat value rather than inventing a correction.
    ratio_per_bar = bucket_ratio[bucket]
    ratio_per_bar = np.where(np.isnan(ratio_per_bar), 1.0, ratio_per_bar)
    atr_tod = flat * ratio_per_bar

    return {
        "flat_atr": flat,
        "bucket": bucket,
        "bucket_atr": bucket_atr,
        "bucket_n": bucket_n,
        "bucket_ratio": bucket_ratio,
        "atr_tod": atr_tod,
        "bucket_minutes": np.array([bucket_minutes], dtype=np.int64),
    }


def parabolic_sar(h: np.ndarray, l: np.ndarray, c: np.ndarray,
                  step: float = 0.02, increment: float = 0.02,
                  max_step: float = 0.2) -> np.ndarray:
    """Parabolic SAR: sequential, stateful calculation, not fully vectorizable.

    Returns SAR level for each bar. SAR is computed backward through the array
    to capture state. Start value is the prior bar's low (LONG init) or high
    (SHORT init) at index i-1. As the prior trend is unknown at bar 0, SAR[0]
    is NaN.

    Args:
        h, l, c: high, low, close arrays (same length, floats).
        step: initial acceleration, typically 0.02 (2%).
        increment: step increase per new extreme, typically 0.02.
        max_step: maximum acceleration, typically 0.2 (20%).

    Returns:
        SAR array, same length as input. SAR[i] is the stop level for a
        position that entered at the end of bar i-1 and is held through bar i.
    """
    n = len(h)
    sar = np.full(n, np.nan, dtype=float)
    if n < 2:
        return sar

    long = True  # Start assuming long
    af = step
    hp = h[0]
    lp = l[0]
    sar[1] = l[0]  # SAR for bar 1 is the low of bar 0

    for i in range(1, n):
        if long:
            sar[i] = max(sar[i - 1], lp) if i > 1 else lp
            if h[i] > hp:
                hp = h[i]
                af = min(af + increment, max_step)
            sar[i] = sar[i] + af * (hp - sar[i])
            sar[i] = min(sar[i], l[i], l[i - 1] if i > 1 else l[i])
            if l[i] < sar[i]:
                long = False
                sar[i] = hp
                lp = l[i]
                af = step
        else:
            sar[i] = min(sar[i - 1], hp) if i > 1 else hp
            if l[i] < lp:
                lp = l[i]
                af = min(af + increment, max_step)
            sar[i] = sar[i] - af * (sar[i] - lp)
            sar[i] = max(sar[i], h[i], h[i - 1] if i > 1 else h[i])
            if h[i] > sar[i]:
                long = True
                sar[i] = lp
                hp = h[i]
                af = step

    return sar


def change_of_character(c: np.ndarray, h: np.ndarray, l: np.ndarray,
                       ema_short: np.ndarray, ema_long: np.ndarray,
                       swing_bars: int = 5) -> np.ndarray:
    """Identify a change of character (ChoCh): a break of the recent swing extreme.

    A ChoCh is a higher low above prior lows (bullish shift) or lower high below
    prior highs (bearish shift), confirming a reversal in the established trend.
    This is strictly a swing-extreme break detector: if the EMA stack was down
    (ema_short < ema_long), a ChoCh fires on a break above the prior N-bar high.
    Conversely, if the stack was up, a ChoCh fires on a break below the prior
    N-bar low.

    Args:
        c, h, l: close, high, low arrays.
        ema_short, ema_long: fast and slow EMA to determine prior trend direction.
        swing_bars: lookback window for the swing extreme (typically 5).

    Returns:
        Boolean array: True where a ChoCh occurs (a swing-extreme break in the
        opposite direction from the prior EMA trend).
    """
    n = len(c)
    choch = np.zeros(n, dtype=bool)
    if n < swing_bars + 1:
        return choch

    for i in range(swing_bars, n):
        if np.isnan(ema_short[i]) or np.isnan(ema_long[i]):
            continue

        prior_up = ema_short[i - 1] > ema_long[i - 1]
        swing_high = np.max(h[i - swing_bars:i])
        swing_low = np.min(l[i - swing_bars:i])

        if prior_up and l[i] < swing_low:
            choch[i] = True
        elif not prior_up and h[i] > swing_high:
            choch[i] = True

    return choch


# ---------------------------------------------------------------------------
# Feature frame
# ---------------------------------------------------------------------------


def build_features(rates: np.ndarray) -> Dict[str, np.ndarray]:
    c = rates["close"].astype(float)
    f: Dict[str, np.ndarray] = {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": c,
        "spread": rates["spread"].astype(float),
        "volume": rates["tick_volume"].astype(float),
        "atr14": atr(rates, 14),
        "adx14": adx(rates, 14),
        "ema20": ema(c, 20),
        "ema50": ema(c, 50),
        "ema200": ema(c, 200),
        "rsi14": rsi(c, 14),
        "er20": efficiency_ratio(c, 20),
    }
    # ATR as a percentile of its own trailing year, so "high volatility" is
    # defined relative to the regime rather than as a fixed dollar figure.
    a = f["atr14"]
    pct = np.full(len(a), np.nan)
    win = 96 * 250  # ~1 year of M15 bars
    for i in range(win, len(a)):
        if not np.isnan(a[i]):
            hist = a[i - win:i]
            hist = hist[~np.isnan(hist)]
            if len(hist):
                pct[i] = (hist < a[i]).mean()
    f["atr_pct"] = pct

    ist_hour = np.array([
        (datetime.fromtimestamp(int(t), tz=timezone.utc).astimezone(IST).hour +
         datetime.fromtimestamp(int(t), tz=timezone.utc).astimezone(IST).minute / 60.0)
        for t in f["time"]
    ])
    f["ist_hour"] = ist_hour
    f["weekday"] = np.array([
        datetime.fromtimestamp(int(t), tz=timezone.utc).astimezone(IST).weekday()
        for t in f["time"]
    ])
    return f


def session_mask(ist_hour: np.ndarray, session: Tuple[float, float]) -> np.ndarray:
    """Bars inside a session window, expressed in fractional IST hours.

    This is the single canonical implementation; `src/research/screener.py` and
    the tier-2 scripts import it rather than keeping private copies, because the
    private copies are exactly what drifted.

    Two spellings of a wraparound session exist in this codebase and both must
    work, because getting either wrong fails *silently* -- the mask simply comes
    back with fewer bars and the caller reports a smaller trade count:

      * `(21.5, 26.5)`  -- end expressed past 24, as `SESSIONS` does
      * `(21.5, 11.5)`  -- end wrapped to a real clock hour, so `b < a`

    The pre-Phase-6 copies branched only on `b <= 24.0` and then, in the wrap
    branch, compared `ist_hour < b - 24.0`. For the `(21.5, 11.5)` spelling that
    branch was never reached: `b <= 24` sent it down the plain path,
    `(h >= 21.5) & (h < 11.5)`, which is empty for every bar. Overnight sessions
    silently produced zero trades. Fixed 2026-09-01 (Phase 6).
    """
    ist_hour = np.asarray(ist_hour, dtype=float)
    a, b = float(session[0]), float(session[1])
    if b > 24.0:
        b -= 24.0          # normalise the past-midnight spelling to a clock hour
    elif b > a:
        return (ist_hour >= a) & (ist_hour < b)   # ordinary same-day window
    if b == a:
        # a full 24h window written as (h, h); treat it as everything
        return np.ones(len(ist_hour), dtype=bool)
    return (ist_hour >= a) | (ist_hour < b)


def session_of(ist_hour: np.ndarray) -> np.ndarray:
    out = np.full(len(ist_hour), "LATE", dtype=object)
    for name, sess in SESSIONS.items():
        out[session_mask(ist_hour, sess)] = name
    return out


# ---------------------------------------------------------------------------
# Null baselines -- what the instrument does with no signal
# ---------------------------------------------------------------------------


def excursion_baseline(f: Dict[str, np.ndarray], horizon_bars: int = 32,
                       sample: int = 6000, seed: int = 11) -> Dict[str, Any]:
    """MFE/MAE profile of a random entry, in ATR units.

    This is the null every candidate is measured against. If a setup's average
    MFE is 0.9 ATR and a coin flip also gets 0.9 ATR, the setup has found
    nothing.
    """
    rng = np.random.default_rng(seed)
    n = len(f["close"])
    valid = np.nonzero(~np.isnan(f["atr14"]))[0]
    valid = valid[(valid > 250) & (valid < n - horizon_bars - 1)]
    if len(valid) == 0:
        return {}
    idx = rng.choice(valid, size=min(sample, len(valid)), replace=False)

    hi, lo, op, a = f["high"], f["low"], f["open"], f["atr14"]
    long_mfe, long_mae = [], []
    for i in idx:
        entry = op[i + 1]
        atr_i = a[i]
        if atr_i <= 0:
            continue
        window_hi = hi[i + 1:i + 1 + horizon_bars].max()
        window_lo = lo[i + 1:i + 1 + horizon_bars].min()
        long_mfe.append((window_hi - entry) / atr_i)
        long_mae.append((entry - window_lo) / atr_i)

    lm, la = np.array(long_mfe), np.array(long_mae)
    return {
        "horizon_bars": horizon_bars,
        "n": int(len(lm)),
        "mfe_atr_mean": round(float(lm.mean()), 4),
        "mfe_atr_median": round(float(np.median(lm)), 4),
        "mae_atr_mean": round(float(la.mean()), 4),
        "mae_atr_median": round(float(np.median(la)), 4),
        # Symmetric by construction for a driftless series; any asymmetry is drift.
        "mfe_minus_mae_mean": round(float((lm - la).mean()), 4),
    }


def barrier_baseline(f: Dict[str, np.ndarray], tp_atr: float, sl_atr: float,
                     max_bars: int = 192, sample: int = 4000,
                     seed: int = 13) -> Dict[str, Any]:
    """Probability a random long hits +tp_atr before -sl_atr.

    A driftless random walk gives sl/(sl+tp). Anything above that is drift or
    autocorrelation; anything at it is noise. This is what makes the wide-target
    results interpretable.
    """
    rng = np.random.default_rng(seed)
    n = len(f["close"])
    valid = np.nonzero(~np.isnan(f["atr14"]))[0]
    valid = valid[(valid > 250) & (valid < n - max_bars - 1)]
    idx = rng.choice(valid, size=min(sample, len(valid)), replace=False)

    hi, lo, op, a = f["high"], f["low"], f["open"], f["atr14"]
    wins = losses = timeouts = 0
    for i in idx:
        entry, atr_i = op[i + 1], a[i]
        if atr_i <= 0:
            continue
        tp, sl = entry + tp_atr * atr_i, entry - sl_atr * atr_i
        hit = None
        for j in range(i + 1, min(i + 1 + max_bars, n)):
            if lo[j] <= sl:
                hit = "L"
                break
            if hi[j] >= tp:
                hit = "W"
                break
        if hit == "W":
            wins += 1
        elif hit == "L":
            losses += 1
        else:
            timeouts += 1
    decided = wins + losses
    theoretical = sl_atr / (sl_atr + tp_atr)
    observed = wins / decided if decided else float("nan")
    return {
        "tp_atr": tp_atr, "sl_atr": sl_atr,
        "wins": wins, "losses": losses, "timeouts": timeouts,
        "observed_win_rate": round(observed, 4),
        "random_walk_win_rate": round(theoretical, 4),
        "excess": round(observed - theoretical, 4),
        "expectancy_R": round(observed * (tp_atr / sl_atr) - (1 - observed), 4)
        if decided else None,
    }


def follow_through(f: Dict[str, np.ndarray], move_atr: float = 1.0,
                   look_bars: int = 16) -> Dict[str, Any]:
    """After price travels `move_atr` in one direction, does it continue or revert?

    Trend-continuation and mean-reversion families make opposite claims about
    this number. Measuring it says which family gold actually supports.
    """
    c, a = f["close"], f["atr14"]
    n = len(c)
    cont = rev = 0
    fwd: List[float] = []
    i = 250
    while i < n - look_bars - 1:
        if np.isnan(a[i]) or a[i] <= 0:
            i += 1
            continue
        move = (c[i] - c[i - 4]) / a[i]
        if abs(move) >= move_atr:
            nxt = (c[i + look_bars] - c[i]) / a[i]
            fwd.append(nxt * np.sign(move))
            if nxt * np.sign(move) > 0:
                cont += 1
            else:
                rev += 1
            i += look_bars  # non-overlapping
        else:
            i += 1
    arr = np.array(fwd) if fwd else np.array([0.0])
    return {
        "trigger_move_atr": move_atr,
        "lookahead_bars": look_bars,
        "n": cont + rev,
        "continuation_rate": round(cont / (cont + rev), 4) if (cont + rev) else None,
        "mean_forward_atr": round(float(arr.mean()), 4),
        "median_forward_atr": round(float(np.median(arr)), 4),
    }


def autocorrelation(f: Dict[str, np.ndarray], lags=(1, 2, 4, 8, 16, 32)) -> Dict[str, float]:
    """Serial correlation of M15 returns. Positive = momentum, negative = reversion."""
    r = np.diff(np.log(f["close"]))
    out = {}
    for lag in lags:
        if len(r) > lag + 10:
            a_, b_ = r[:-lag], r[lag:]
            out[f"lag_{lag}"] = round(float(np.corrcoef(a_, b_)[0, 1]), 5)
    return out


def by_bucket(f: Dict[str, np.ndarray], key: np.ndarray,
              labels: Optional[List] = None) -> Dict[str, Dict[str, float]]:
    """Volatility, range, spread and efficiency grouped by an arbitrary key."""
    r = np.abs(np.diff(np.log(f["close"]))) * 1e4  # bp per bar
    rng_ = (f["high"] - f["low"])[1:]
    er = f["er20"][1:]
    sp = f["spread"][1:]
    k = key[1:]
    out: Dict[str, Dict[str, float]] = {}
    for lab in (labels if labels is not None else sorted(set(k.tolist()))):
        m = k == lab
        if m.sum() < 30:
            continue
        out[str(lab)] = {
            "bars": int(m.sum()),
            "mean_abs_return_bp": round(float(np.nanmean(r[m])), 2),
            "mean_range_usd": round(float(np.nanmean(rng_[m])), 3),
            "mean_efficiency": round(float(np.nanmean(er[m])), 4),
            "mean_spread_pts": round(float(np.nanmean(sp[m])), 1),
        }
    return out
