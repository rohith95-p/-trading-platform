"""Phase 2 - session-by-session market microstructure characterisation for XAUUSDm.

Primary data: broker M15 bars (research/data/XAUUSDm_M15.npy), 100k bars,
2022-06-07 -> 2026-08-31.  Bar timestamps are UTC (verified: the 75-minute daily
gold break lands at 21:00-22:15 UTC in DST and 22:00-23:15 UTC in winter, which
is 17:00 ET in both cases).  IST = UTC + 5:30.

Everything here is descriptive / null-testing.  No look-ahead: every conditional
statistic uses only bars strictly before the decision bar, and every forward
measurement starts at the bar after the decision bar.

Two windows are reported everywhere:
  FULL   = all 100k M15 bars
  RECENT = last ~2 years (2024-09-01 onward), the regime that matters because
           mean true range roughly doubled across the history.

Output: JSON to reports/session_microstructure.json plus a printed text report.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.research.market_study import atr, adx, ema, rsi, true_range  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "research", "data", "XAUUSDm_M15.npy")
OUT_JSON = os.path.join(ROOT, "reports", "session_microstructure.json")

POINT = 0.001          # 1 point = $0.001 on XAUUSDm
COST_USD = 0.28        # $0.26 spread + $0.02 slippage, round trip, 0.01 lot
BAR_SEC = 900

# Sessions in IST hours.  The project's canonical labels.  POSTNY is added
# because IST 00:00-02:30 (= UTC 18:30-21:00) is otherwise unlabelled and is
# ~10% of all bars -- and it is the genuinely dead window, which matters a lot
# for a $100 account whose risk IS its stop distance.
SESSIONS = {
    "ASIA":    (2.5, 11.5),
    "LONDON":  (11.5, 15.5),
    "OVERLAP": (15.5, 17.5),
    "NY":      (17.5, 21.5),
    "LATE":    (21.5, 24.0),
    "POSTNY":  (0.0, 2.5),
}
ORDER = ["ASIA", "LONDON", "OVERLAP", "NY", "LATE", "POSTNY"]

# Sub-windows: (label, lo, hi) in IST hours.
SUBWINDOWS = {
    "ASIA":    [("first_1h", 2.5, 3.5), ("middle", 3.5, 10.5), ("last_1h", 10.5, 11.5)],
    "LONDON":  [("first_1h", 11.5, 12.5), ("middle", 12.5, 14.5), ("last_1h", 14.5, 15.5)],
    "OVERLAP": [("first_1h", 15.5, 16.5), ("last_1h", 16.5, 17.5)],
    "NY":      [("first_1h", 17.5, 18.5), ("middle", 18.5, 20.5), ("last_1h", 20.5, 21.5)],
    "LATE":    [("first_1h", 21.5, 22.5), ("middle", 22.5, 23.5), ("last_30m", 23.5, 24.0)],
    "POSTNY":  [("first_1h", 0.0, 1.0), ("rest", 1.0, 2.5)],
}

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def pct(a, q):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.percentile(a, q)) if a.size else float("nan")


def r3(x):
    try:
        return round(float(x), 3)
    except Exception:
        return None


def r4(x):
    try:
        return round(float(x), 4)
    except Exception:
        return None


def skew(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return float("nan")
    m, s = x.mean(), x.std(ddof=0)
    return float(((x - m) ** 3).mean() / s ** 3) if s > 0 else float("nan")


def exkurt(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 4:
        return float("nan")
    m, s = x.mean(), x.std(ddof=0)
    return float(((x - m) ** 4).mean() / s ** 4 - 3.0) if s > 0 else float("nan")


def binom_z(k, n, p=0.5):
    """z-statistic for k successes in n trials against P=p."""
    if n < 20:
        return float("nan")
    return float((k - n * p) / math.sqrt(n * p * (1 - p)))


def mean_z(x):
    """z-statistic that mean(x) differs from zero (iid assumption -- optimistic)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 20:
        return float("nan")
    s = x.std(ddof=1)
    return float(x.mean() / (s / math.sqrt(x.size))) if s > 0 else float("nan")


def acorr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 50:
        return float("nan"), 0
    a, b = a[m], b[m]
    if a.std() == 0 or b.std() == 0:
        return float("nan"), int(m.sum())
    return float(np.corrcoef(a, b)[0, 1]), int(m.sum())


# ---------------------------------------------------------------------------
# load + features
# ---------------------------------------------------------------------------

def load():
    r = np.load(DATA)
    t = r["time"].astype(np.int64)
    o = r["open"].astype(float)
    h = r["high"].astype(float)
    l = r["low"].astype(float)
    c = r["close"].astype(float)
    sp = r["spread"].astype(float) * POINT           # dollars
    vol = r["tick_volume"].astype(float)

    # IST calendar fields, vectorised.
    ist = (t + 5 * 3600 + 1800)
    ist_hour = (ist % 86400) / 3600.0
    # weekday: 1970-01-01 was a Thursday (weekday 3)
    weekday = ((ist // 86400) + 3) % 7

    tr = true_range(h, l, c)
    a14 = atr(r, 14)
    adx14 = adx(r, 14)
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)

    # contiguity: bar i follows bar i-1 with no gap
    cont = np.zeros(len(t), dtype=bool)
    cont[1:] = (t[1:] - t[:-1]) == BAR_SEC

    ret = np.full(len(t), np.nan)                     # log return, contiguous only
    ret[1:] = np.where(cont[1:], np.log(c[1:] / c[:-1]), np.nan)

    rng = h - l
    upper = np.where(rng > 0, (h - np.maximum(o, c)) / rng, np.nan)
    lower = np.where(rng > 0, (np.minimum(o, c) - l) / rng, np.nan)
    body = np.where(rng > 0, np.abs(c - o) / rng, np.nan)

    # rolling 20-bar mean/std of close for the z-score work (strictly trailing,
    # windows [i-20, i-1]).
    n = len(c)
    sma20 = np.full(n, np.nan)
    sd20 = np.full(n, np.nan)
    csum = np.concatenate([[0.0], np.cumsum(c)])
    csum2 = np.concatenate([[0.0], np.cumsum(c * c)])
    w = 20
    idx = np.arange(w, n)
    s1 = csum[idx] - csum[idx - w]
    s2 = csum2[idx] - csum2[idx - w]
    mu = s1 / w
    var = np.maximum(s2 / w - mu * mu, 0.0)
    sma20[idx] = mu
    sd20[idx] = np.sqrt(var)

    return dict(t=t, o=o, h=h, l=l, c=c, spread=sp, vol=vol, tr=tr, atr=a14,
                adx=adx14, ema20=e20, ema50=e50, ema200=e200, cont=cont,
                ret=ret, rng=rng, upper=upper, lower=lower, body=body,
                ist_hour=ist_hour, weekday=weekday, sma20=sma20, sd20=sd20,
                n=len(t))


def session_mask(ist_hour, name):
    lo, hi = SESSIONS[name]
    return (ist_hour >= lo) & (ist_hour < hi)


def window_mask(F, which):
    if which == "FULL":
        return np.ones(F["n"], dtype=bool)
    cutoff = int(datetime(2024, 9, 1, tzinfo=timezone.utc).timestamp())
    return F["t"] >= cutoff


# ---------------------------------------------------------------------------
# per-session blocks
# ---------------------------------------------------------------------------

def basic_block(F, m):
    rng, sp, atr_, vol = F["rng"][m], F["spread"][m], F["atr"][m], F["vol"][m]
    med_rng = float(np.nanmedian(rng))
    return {
        "bars": int(m.sum()),
        "range_mean": r3(np.nanmean(rng)),
        "range_p10": r3(pct(rng, 10)), "range_p25": r3(pct(rng, 25)),
        "range_p50": r3(med_rng), "range_p75": r3(pct(rng, 75)),
        "range_p90": r3(pct(rng, 90)), "range_p99": r3(pct(rng, 99)),
        "atr14_mean": r3(np.nanmean(atr_)), "atr14_p50": r3(np.nanmedian(atr_)),
        "tick_volume_mean": r3(np.nanmean(vol)),
        "spread_mean": r3(np.nanmean(sp)), "spread_p50": r3(np.nanmedian(sp)),
        "spread_p90": r3(pct(sp, 90)), "spread_p99": r3(pct(sp, 99)),
        "spread_pct_of_median_range": r3(100.0 * np.nanmedian(sp) / med_rng) if med_rng > 0 else None,
        "roundtrip_cost_pct_of_median_range": r3(100.0 * COST_USD / med_rng) if med_rng > 0 else None,
    }


def return_block(F, m):
    r = F["ret"][m & np.isfinite(F["ret"])] * 1e4          # basis points
    if r.size < 50:
        return {"n": int(r.size)}
    s = r.std(ddof=1)
    return {
        "n": int(r.size),
        "mean_bp": r4(r.mean()), "std_bp": r3(s),
        "mean_abs_bp": r3(np.abs(r).mean()),
        "skew": r3(skew(r)), "excess_kurtosis": r3(exkurt(r)),
        "p01_bp": r3(pct(r, 1)), "p99_bp": r3(pct(r, 99)),
        "frac_beyond_3sd": r4(float((np.abs(r - r.mean()) > 3 * s).mean())),
        "frac_beyond_5sd": r4(float((np.abs(r - r.mean()) > 5 * s).mean())),
        "drift_z": r3(mean_z(r)),
    }


def autocorr_block(F, m, lags=range(1, 9)):
    """Return autocorrelation at lags 1..8 restricted to bars inside the session.

    A pair (i, i+k) counts only if both bars are in the session AND the k
    intervening steps are gap-free, so weekend/daily-break joins never enter.
    """
    t, ret = F["t"], F["ret"]
    n = F["n"]
    out = {}
    idx = np.nonzero(m & np.isfinite(ret))[0]
    for k in lags:
        j = idx[idx + k < n]
        j2 = j + k
        ok = m[j2] & np.isfinite(ret[j2]) & ((t[j2] - t[j]) == BAR_SEC * k)
        a, b = ret[j[ok]], ret[j2[ok]]
        if a.size < 100:
            out[f"lag{k}"] = {"rho": None, "n": int(a.size), "z": None}
            continue
        rho = float(np.corrcoef(a, b)[0, 1])
        out[f"lag{k}"] = {"rho": r4(rho), "n": int(a.size),
                          "z": r3(rho * math.sqrt(a.size))}
    return out


def vol_cluster_block(F, m):
    """Autocorrelation of |return| at lag 1 and range-persistence probability."""
    t, ret, rng = F["t"], F["ret"], F["rng"]
    n = F["n"]
    idx = np.nonzero(m & np.isfinite(ret))[0]
    j = idx[idx + 1 < n]
    ok = m[j + 1] & np.isfinite(ret[j + 1]) & ((t[j + 1] - t[j]) == BAR_SEC)
    a, b = np.abs(ret[j[ok]]), np.abs(ret[j[ok] + 1])
    rho, nn = acorr(a, b)

    r_in = rng[m]
    p75 = pct(r_in, 75)
    p50 = pct(r_in, 50)
    jj = j[ok]
    hi_now = rng[jj] > p75
    exp_after_hi = float((rng[jj + 1][hi_now] > p50).mean()) if hi_now.sum() > 30 else None
    lo_now = rng[jj] < pct(r_in, 25)
    exp_after_lo = float((rng[jj + 1][lo_now] > p50).mean()) if lo_now.sum() > 30 else None
    return {
        "abs_return_lag1_rho": r4(rho), "n": nn,
        "z": r3(rho * math.sqrt(nn)) if nn else None,
        "P(next_range>median | range>p75)": r4(exp_after_hi),
        "P(next_range>median | range<p25)": r4(exp_after_lo),
        "n_hi": int(hi_now.sum()), "n_lo": int(lo_now.sum()),
    }


def continuation_block(F, m):
    """Sign persistence of consecutive M15 returns inside the session."""
    t, ret = F["t"], F["ret"]
    n = F["n"]
    idx = np.nonzero(m & np.isfinite(ret))[0]
    j = idx[idx + 1 < n]
    ok = m[j + 1] & np.isfinite(ret[j + 1]) & ((t[j + 1] - t[j]) == BAR_SEC)
    a, b = ret[j[ok]], ret[j[ok] + 1]
    nz = (a != 0) & (b != 0)
    a, b = a[nz], b[nz]
    if a.size < 100:
        return {"n": int(a.size)}
    same = int((np.sign(a) == np.sign(b)).sum())
    return {
        "n": int(a.size),
        "continuation_rate": r4(same / a.size),
        "reversal_rate": r4(1 - same / a.size),
        "z_vs_50pct": r3(binom_z(same, a.size)),
    }


def persistence_expectancy(F, m, look=4, fwd=4):
    """E[ forward move x sign(prior move) ] in USD -- the single cleanest test of
    directional persistence at a tradeable horizon.  Uses close[i]-close[i-look]
    as the signal (all information available at bar i's close) and
    close[i+fwd]-close[i] as the outcome.  Gap-free windows only.
    """
    t, c, atr_ = F["t"], F["c"], F["atr"]
    n = F["n"]
    idx = np.nonzero(m)[0]
    idx = idx[(idx >= look) & (idx + fwd < n)]
    ok = ((t[idx] - t[idx - look]) == BAR_SEC * look) & \
         ((t[idx + fwd] - t[idx]) == BAR_SEC * fwd) & np.isfinite(atr_[idx]) & (atr_[idx] > 0)
    idx = idx[ok]
    if idx.size < 100:
        return {"n": int(idx.size)}
    mv = c[idx] - c[idx - look]
    fw = c[idx + fwd] - c[idx]
    sgn = np.sign(mv)
    keep = sgn != 0
    x = fw[keep] * sgn[keep]
    xa = x / atr_[idx][keep]
    win = int((x > 0).sum())
    return {
        "n": int(x.size),
        "mean_usd": r4(x.mean()),
        "median_usd": r4(np.median(x)),
        "mean_atr": r4(xa.mean()),
        "hit_rate": r4(win / x.size),
        "hit_z": r3(binom_z(win, x.size)),
        "mean_z": r3(mean_z(x)),
        "net_of_cost_usd": r4(x.mean() - COST_USD),
    }


def breakout_block(F, m, N=20, k=4, fwd=8):
    """N-bar high/low breaks and their failure rate.

    Break at bar i = high[i] > max(high[i-N:i]) (or low[i] < min(low[i-N:i])).
    FALSE if, within the next k bars, close falls back inside the prior range.
    Forward move measured from close[i] over `fwd` bars, signed by break
    direction.  All windows gap-checked.
    """
    t, h, l, c, atr_ = F["t"], F["h"], F["l"], F["c"], F["atr"]
    n = F["n"]
    idx = np.nonzero(m)[0]
    idx = idx[(idx >= N) & (idx + max(k, fwd) < n)]
    if idx.size == 0:
        return {"n_bars": 0}
    ok = ((t[idx] - t[idx - N]) == BAR_SEC * N) & \
         ((t[idx + max(k, fwd)] - t[idx]) == BAR_SEC * max(k, fwd)) & \
         np.isfinite(atr_[idx]) & (atr_[idx] > 0)
    idx = idx[ok]
    if idx.size < 100:
        return {"n_bars": int(idx.size)}

    ph = np.array([h[i - N:i].max() for i in idx])
    pl = np.array([l[i - N:i].min() for i in idx])
    up = h[idx] > ph
    dn = l[idx] < pl

    res = {"n_bars": int(idx.size),
           "breakout_rate_up": r4(up.mean()), "breakout_rate_dn": r4(dn.mean())}

    for lab, sel, lvl, sign in (("up", up, ph, 1.0), ("dn", dn, pl, -1.0)):
        ii = idx[sel]
        lv = lvl[sel]
        if ii.size < 50:
            res[lab] = {"n": int(ii.size)}
            continue
        # false break: close back inside within k bars
        fail = np.zeros(ii.size, dtype=bool)
        for step in range(0, k + 1):
            cc = c[ii + step]
            fail |= (cc < lv) if sign > 0 else (cc > lv)
        fw = (c[ii + fwd] - c[ii]) * sign
        fa = fw / atr_[ii]
        res[lab] = {
            "n": int(ii.size),
            "false_break_rate": r4(fail.mean()),
            "fwd8_mean_usd": r4(fw.mean()),
            "fwd8_median_usd": r4(np.median(fw)),
            "fwd8_mean_atr": r4(fa.mean()),
            "fwd8_hit_rate": r4(float((fw > 0).mean())),
            "fwd8_hit_z": r3(binom_z(int((fw > 0).sum()), ii.size)),
            "fwd8_mean_z": r3(mean_z(fw)),
            "net_of_cost_usd": r4(fw.mean() - COST_USD),
        }
    return res


def wick_block(F, m):
    u, lo, b = F["upper"][m], F["lower"][m], F["body"][m]
    return {
        "n": int(np.isfinite(u).sum()),
        "upper_wick_frac_mean": r4(np.nanmean(u)),
        "lower_wick_frac_mean": r4(np.nanmean(lo)),
        "body_frac_mean": r4(np.nanmean(b)),
        "body_frac_p50": r4(np.nanmedian(b)),
        "upper_minus_lower": r4(np.nanmean(u) - np.nanmean(lo)),
    }


def zscore_reversion_block(F, m, thr=2.0, fwd=4):
    """Does an extended close revert?  Signal: z = (close - sma20)/sd20 computed
    from bars [i-20, i-1] plus close[i].  Outcome: forward `fwd`-bar move times
    -sign(z).  Positive mean = mean reversion pays.
    """
    t, c, sma, sd, atr_ = F["t"], F["c"], F["sma20"], F["sd20"], F["atr"]
    n = F["n"]
    idx = np.nonzero(m)[0]
    idx = idx[(idx >= 21) & (idx + fwd < n)]
    ok = ((t[idx] - t[idx - 20]) == BAR_SEC * 20) & \
         ((t[idx + fwd] - t[idx]) == BAR_SEC * fwd) & \
         np.isfinite(sd[idx]) & (sd[idx] > 0) & np.isfinite(atr_[idx])
    idx = idx[ok]
    if idx.size < 100:
        return {"n_bars": int(idx.size)}
    z = (c[idx] - sma[idx]) / sd[idx]
    out = {"n_bars": int(idx.size), "z_abs_p90": r3(pct(np.abs(z), 90))}
    for label, sel in (("all", np.ones(z.size, bool)),
                       ("abs_z>2", np.abs(z) > 2.0),
                       ("abs_z>2.5", np.abs(z) > 2.5)):
        ii = idx[sel]
        zz = z[sel]
        if ii.size < 50:
            out[label] = {"n": int(ii.size)}
            continue
        rev = (c[ii + fwd] - c[ii]) * (-np.sign(zz))
        out[label] = {
            "n": int(ii.size),
            "reversion_mean_usd": r4(rev.mean()),
            "reversion_mean_atr": r4((rev / atr_[ii]).mean()),
            "reversion_hit_rate": r4(float((rev > 0).mean())),
            "hit_z": r3(binom_z(int((rev > 0).sum()), ii.size)),
            "mean_z": r3(mean_z(rev)),
            "net_of_cost_usd": r4(rev.mean() - COST_USD),
        }
    return out


def trend_persistence_block(F, m, win_mask):
    """How long does an EMA20>50>200 (or inverse) stack survive once formed?

    Runs are found over the whole (window-masked) series; a run is attributed to
    the session in which it STARTED.  Also reports the one-bar survival
    probability conditional on being aligned inside the session.
    """
    e20, e50, e200 = F["ema20"], F["ema50"], F["ema200"]
    up = (e20 > e50) & (e50 > e200)
    dn = (e20 < e50) & (e50 < e200)
    state = np.where(up, 1, np.where(dn, -1, 0))
    state[~np.isfinite(e200)] = 0
    valid = win_mask & F["cont"]

    # one-bar survival inside the session
    n = F["n"]
    idx = np.nonzero(m & (state != 0))[0]
    idx = idx[idx + 1 < n]
    idx = idx[valid[idx + 1] & m[idx + 1]]
    surv = float((state[idx + 1] == state[idx]).mean()) if idx.size > 100 else None

    # run lengths, attributed to the session of the run's first bar
    runs = []
    i = 0
    while i < n:
        if state[i] == 0 or not win_mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and state[j + 1] == state[i] and F["cont"][j + 1] and win_mask[j + 1]:
            j += 1
        if m[i]:
            runs.append(j - i + 1)
        i = j + 1
    runs = np.array(runs, float)
    return {
        "one_bar_survival": r4(surv), "n_aligned_bars": int(idx.size),
        "runs_started_here": int(runs.size),
        "run_len_mean_bars": r3(runs.mean()) if runs.size else None,
        "run_len_p50_bars": r3(np.median(runs)) if runs.size else None,
        "run_len_p90_bars": r3(pct(runs, 90)) if runs.size else None,
        "frac_aligned": r4(float((state[m] != 0).mean())),
    }


# ---------------------------------------------------------------------------
# hour and weekday tables
# ---------------------------------------------------------------------------

def hour_table(F, win):
    rows = []
    for hh in range(24):
        m = win & (np.floor(F["ist_hour"]) == hh)
        if m.sum() < 200:
            continue
        pe = persistence_expectancy(F, m)
        cb = continuation_block(F, m)
        ac = autocorr_block(F, m, lags=(1,))
        rows.append({
            "ist_hour": hh,
            "session": next((s for s in ORDER
                             if SESSIONS[s][0] <= hh + 0.25 < SESSIONS[s][1]), "?"),
            "bars": int(m.sum()),
            "range_p50": r3(np.nanmedian(F["rng"][m])),
            "spread_p50": r3(np.nanmedian(F["spread"][m])),
            "mean_abs_ret_bp": r3(np.nanmean(np.abs(F["ret"][m])) * 1e4),
            "lag1_rho": ac["lag1"]["rho"], "lag1_z": ac["lag1"]["z"],
            "cont_rate": cb.get("continuation_rate"), "cont_z": cb.get("z_vs_50pct"),
            "persist_mean_usd": pe.get("mean_usd"), "persist_z": pe.get("mean_z"),
            "persist_n": pe.get("n"),
        })
    return rows


def weekday_table(F, win, m_sess):
    rows = []
    for d in range(5):
        m = win & m_sess & (F["weekday"] == d)
        if m.sum() < 150:
            continue
        pe = persistence_expectancy(F, m)
        rows.append({
            "weekday": DOW[d], "bars": int(m.sum()),
            "range_p50": r3(np.nanmedian(F["rng"][m])),
            "mean_ret_bp": r4(np.nanmean(F["ret"][m]) * 1e4),
            "drift_z": r3(mean_z(F["ret"][m] * 1e4)),
            "persist_mean_usd": pe.get("mean_usd"), "persist_z": pe.get("mean_z"),
            "persist_n": pe.get("n"),
        })
    return rows


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def run():
    F = load()
    result = {
        "meta": {
            "source": "research/data/XAUUSDm_M15.npy",
            "bars": F["n"],
            "first": datetime.utcfromtimestamp(int(F["t"][0])).isoformat() + "Z",
            "last": datetime.utcfromtimestamp(int(F["t"][-1])).isoformat() + "Z",
            "timestamp_tz": "UTC (verified via daily gold break at 17:00 ET)",
            "ist_offset_hours": 5.5,
            "cost_usd_roundtrip": COST_USD,
            "recent_cutoff": "2024-09-01",
        },
        "windows": {},
    }

    for wname in ("RECENT", "FULL"):
        win = window_mask(F, wname)
        wblock = {"bars": int(win.sum()), "sessions": {}, "hours": hour_table(F, win)}
        for s in ORDER:
            ms = win & session_mask(F["ist_hour"], s)
            if ms.sum() < 500:
                continue
            blk = {
                "basic": basic_block(F, ms),
                "returns": return_block(F, ms),
                "autocorr": autocorr_block(F, ms),
                "vol_clustering": vol_cluster_block(F, ms),
                "continuation": continuation_block(F, ms),
                "persistence_4x4": persistence_expectancy(F, ms, 4, 4),
                "persistence_8x8": persistence_expectancy(F, ms, 8, 8),
                "breakout_20": breakout_block(F, ms, N=20, k=4, fwd=8),
                "wicks": wick_block(F, ms),
                "zscore_reversion": zscore_reversion_block(F, ms),
                "trend_state": trend_persistence_block(F, ms, win),
                "weekday": weekday_table(F, win, session_mask(F["ist_hour"], s)),
                "subwindows": {},
            }
            for lab, lo, hi in SUBWINDOWS[s]:
                msub = win & (F["ist_hour"] >= lo) & (F["ist_hour"] < hi)
                if msub.sum() < 400:
                    continue
                blk["subwindows"][lab] = {
                    "basic": basic_block(F, msub),
                    "returns": return_block(F, msub),
                    "autocorr_lag1": autocorr_block(F, msub, lags=(1, 2))["lag1"],
                    "continuation": continuation_block(F, msub),
                    "persistence_4x4": persistence_expectancy(F, msub, 4, 4),
                    "wicks": wick_block(F, msub),
                    "zscore_reversion": zscore_reversion_block(F, msub),
                }
            wblock["sessions"][s] = blk
        result["windows"][wname] = wblock

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(result, fh, indent=1)
    return result


def _dash(o):
    """Replace None with '-' so the fixed-width text report never blows up."""
    if isinstance(o, dict):
        return {k: _dash(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_dash(v) for v in o]
    return "-" if o is None else o


def show(res):
    res = _dash(res)
    for wname in ("RECENT", "FULL"):
        W = res["windows"][wname]
        print("\n" + "=" * 100)
        print(f"WINDOW {wname}  bars={W['bars']}")
        print("=" * 100)

        print("\n-- BASIC / SPREAD --")
        print(f"{'sess':8}{'bars':>7}{'rngMean':>9}{'rngP50':>8}{'rngP90':>8}{'ATR':>7}"
              f"{'spMean':>8}{'spP50':>7}{'spP90':>7}{'sp%rng':>8}{'cost%rng':>9}{'vol':>8}")
        for s, b in W["sessions"].items():
            x = b["basic"]
            print(f"{s:8}{x['bars']:>7}{x['range_mean']:>9}{x['range_p50']:>8}{x['range_p90']:>8}"
                  f"{x['atr14_mean']:>7}{x['spread_mean']:>8}{x['spread_p50']:>7}{x['spread_p90']:>7}"
                  f"{x['spread_pct_of_median_range']:>8}{x['roundtrip_cost_pct_of_median_range']:>9}"
                  f"{x['tick_volume_mean']:>8}")

        print("\n-- RETURN DISTRIBUTION (bp per M15 bar) --")
        print(f"{'sess':8}{'n':>7}{'mean':>9}{'std':>8}{'|mean|':>8}{'skew':>8}{'exKurt':>9}"
              f"{'>3sd':>8}{'>5sd':>8}{'driftZ':>8}")
        for s, b in W["sessions"].items():
            x = b["returns"]
            print(f"{s:8}{x['n']:>7}{x['mean_bp']:>9}{x['std_bp']:>8}{x['mean_abs_bp']:>8}"
                  f"{x['skew']:>8}{x['excess_kurtosis']:>9}{x['frac_beyond_3sd']:>8}"
                  f"{x['frac_beyond_5sd']:>8}{x['drift_z']:>8}")

        print("\n-- RETURN AUTOCORRELATION (rho, z in parens) lags 1-8 --")
        print(f"{'sess':8}" + "".join(f"{'lag'+str(k):>16}" for k in range(1, 9)))
        for s, b in W["sessions"].items():
            cells = []
            for k in range(1, 9):
                d = b["autocorr"][f"lag{k}"]
                cells.append(f"{d['rho']}({d['z']})".rjust(16))
            print(f"{s:8}" + "".join(cells))
            print(f"{'':8}n={b['autocorr']['lag1']['n']}")

        print("\n-- CONTINUATION vs REVERSAL (consecutive bar sign) --")
        print(f"{'sess':8}{'n':>8}{'cont':>8}{'rev':>8}{'z':>8}")
        for s, b in W["sessions"].items():
            x = b["continuation"]
            print(f"{s:8}{x['n']:>8}{x['continuation_rate']:>8}{x['reversal_rate']:>8}{x['z_vs_50pct']:>8}")

        print("\n-- DIRECTIONAL PERSISTENCE EXPECTANCY (4 bars back -> 4 bars fwd, USD) --")
        print(f"{'sess':8}{'n':>8}{'meanUSD':>10}{'medUSD':>9}{'meanATR':>9}{'hit':>8}{'hitZ':>8}{'meanZ':>8}{'netCost':>9}")
        for s, b in W["sessions"].items():
            x = b["persistence_4x4"]
            print(f"{s:8}{x['n']:>8}{x['mean_usd']:>10}{x['median_usd']:>9}{x['mean_atr']:>9}"
                  f"{x['hit_rate']:>8}{x['hit_z']:>8}{x['mean_z']:>8}{x['net_of_cost_usd']:>9}")
        print("   (8x8 variant)")
        for s, b in W["sessions"].items():
            x = b["persistence_8x8"]
            print(f"{s:8}{x['n']:>8}{x['mean_usd']:>10}{x['median_usd']:>9}{x['mean_atr']:>9}"
                  f"{x['hit_rate']:>8}{x['hit_z']:>8}{x['mean_z']:>8}{x['net_of_cost_usd']:>9}")

        print("\n-- BREAKOUT (20-bar extreme), false-break within 4 bars, fwd 8 bars --")
        print(f"{'sess':8}{'dir':>5}{'n':>7}{'rate':>8}{'false':>8}{'fwdUSD':>9}{'fwdATR':>9}{'hit':>7}{'hitZ':>7}{'meanZ':>7}{'net':>8}")
        for s, b in W["sessions"].items():
            bo = b["breakout_20"]
            for d in ("up", "dn"):
                x = bo.get(d, {})
                if "false_break_rate" not in x:
                    continue
                print(f"{s:8}{d:>5}{x['n']:>7}{bo['breakout_rate_'+d]:>8}{x['false_break_rate']:>8}"
                      f"{x['fwd8_mean_usd']:>9}{x['fwd8_mean_atr']:>9}{x['fwd8_hit_rate']:>7}"
                      f"{x['fwd8_hit_z']:>7}{x['fwd8_mean_z']:>7}{x['net_of_cost_usd']:>8}")

        print("\n-- WICKS (fraction of bar range) --")
        print(f"{'sess':8}{'n':>8}{'upper':>9}{'lower':>9}{'body':>9}{'bodyP50':>9}{'u-l':>9}")
        for s, b in W["sessions"].items():
            x = b["wicks"]
            print(f"{s:8}{x['n']:>8}{x['upper_wick_frac_mean']:>9}{x['lower_wick_frac_mean']:>9}"
                  f"{x['body_frac_mean']:>9}{x['body_frac_p50']:>9}{x['upper_minus_lower']:>9}")

        print("\n-- Z-SCORE MEAN REVERSION (20-bar z, fwd 4 bars, signed toward mean) --")
        print(f"{'sess':8}{'bucket':>10}{'n':>8}{'USD':>9}{'ATR':>9}{'hit':>8}{'hitZ':>8}{'meanZ':>8}{'net':>9}")
        for s, b in W["sessions"].items():
            zb = b["zscore_reversion"]
            for k in ("all", "abs_z>2", "abs_z>2.5"):
                x = zb.get(k, {})
                if "reversion_mean_usd" not in x:
                    continue
                print(f"{s:8}{k:>10}{x['n']:>8}{x['reversion_mean_usd']:>9}{x['reversion_mean_atr']:>9}"
                      f"{x['reversion_hit_rate']:>8}{x['hit_z']:>8}{x['mean_z']:>8}{x['net_of_cost_usd']:>9}")

        print("\n-- VOLATILITY CLUSTERING --")
        print(f"{'sess':8}{'n':>8}{'|r|rho1':>10}{'z':>8}{'P(hi|hi)':>10}{'P(hi|lo)':>10}")
        for s, b in W["sessions"].items():
            x = b["vol_clustering"]
            print(f"{s:8}{x['n']:>8}{x['abs_return_lag1_rho']:>10}{x['z']:>8}"
                  f"{x['P(next_range>median | range>p75)']:>10}{x['P(next_range>median | range<p25)']:>10}")

        print("\n-- TREND-STATE (EMA20/50/200 stack) PERSISTENCE --")
        print(f"{'sess':8}{'fracAligned':>13}{'1barSurv':>10}{'runs':>7}{'lenMean':>9}{'lenP50':>8}{'lenP90':>8}")
        for s, b in W["sessions"].items():
            x = b["trend_state"]
            print(f"{s:8}{x['frac_aligned']:>13}{x['one_bar_survival']:>10}{x['runs_started_here']:>7}"
                  f"{x['run_len_mean_bars']:>9}{x['run_len_p50_bars']:>8}{x['run_len_p90_bars']:>8}")

        print("\n-- HOUR BY HOUR (IST) --")
        print(f"{'h':>3}{'sess':>9}{'bars':>7}{'rngP50':>8}{'spP50':>7}{'|r|bp':>7}"
              f"{'rho1':>9}{'rhoZ':>7}{'cont':>8}{'contZ':>7}{'persUSD':>9}{'persZ':>7}{'persN':>7}")
        for r in W["hours"]:
            print(f"{r['ist_hour']:>3}{r['session']:>9}{r['bars']:>7}{r['range_p50']:>8}{r['spread_p50']:>7}"
                  f"{r['mean_abs_ret_bp']:>7}{r['lag1_rho']:>9}{r['lag1_z']:>7}{r['cont_rate']:>8}"
                  f"{r['cont_z']:>7}{r['persist_mean_usd']:>9}{r['persist_z']:>7}{r['persist_n']:>7}")

        print("\n-- DAY OF WEEK, per session --")
        print(f"{'sess':8}{'dow':>5}{'bars':>7}{'rngP50':>8}{'retBp':>9}{'driftZ':>8}{'persUSD':>9}{'persZ':>7}{'n':>7}")
        for s, b in W["sessions"].items():
            for r in b["weekday"]:
                print(f"{s:8}{r['weekday']:>5}{r['bars']:>7}{r['range_p50']:>8}{r['mean_ret_bp']:>9}"
                      f"{r['drift_z']:>8}{r['persist_mean_usd']:>9}{r['persist_z']:>7}{r['persist_n']:>7}")

        print("\n-- SUB-WINDOWS --")
        print(f"{'sess':8}{'sub':>10}{'bars':>7}{'rngP50':>8}{'spP50':>7}{'|r|bp':>7}{'rho1':>9}{'rhoZ':>7}"
              f"{'cont':>8}{'contZ':>7}{'persUSD':>9}{'persZ':>7}{'body':>7}{'zRevUSD':>9}{'zRevZ':>7}")
        for s, b in W["sessions"].items():
            for lab, sb in b["subwindows"].items():
                zr = sb["zscore_reversion"].get("abs_z>2", {})
                pe, cn, rt = sb["persistence_4x4"], sb["continuation"], sb["returns"]
                print(f"{s:8}{lab:>10}{sb['basic']['bars']:>7}{sb['basic']['range_p50']:>8}"
                      f"{sb['basic']['spread_p50']:>7}{str(rt.get('mean_abs_bp','-')):>7}"
                      f"{str(sb['autocorr_lag1']['rho']):>9}{str(sb['autocorr_lag1']['z']):>7}"
                      f"{str(cn.get('continuation_rate','-')):>8}{str(cn.get('z_vs_50pct','-')):>7}"
                      f"{str(pe.get('mean_usd','-')):>9}{str(pe.get('mean_z','-')):>7}"
                      f"{sb['wicks']['body_frac_mean']:>7}"
                      f"{str(zr.get('reversion_mean_usd','-')):>9}{str(zr.get('mean_z','-')):>7}")


if __name__ == "__main__":
    show(run())
