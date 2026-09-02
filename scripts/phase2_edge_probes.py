"""Phase 2b - adversarial probes of the candidate structures found by
phase2_session_microstructure.py.

The descriptive pass turned up five session-localised anomalies.  This script
asks the only question that matters: *is any of them tradeable at 0.01 lot
after $0.28 round-trip cost, and does it survive being split into disjoint
time thirds?*

Design rules enforced here:
  - Signal uses ONLY bars up to and including close[i-1].
  - Entry is open[i] (a real, reachable price), not close[i-1].  The
    close[i-1] -> open[i] gap is reported separately so we can see how much of
    a close-to-close statistic is unreachable.
  - Exit is close[i+h-1].
  - Cost of $0.28 round trip is subtracted from every trade.
  - Every probe is reported on three DISJOINT thirds of the history.  RECENT
    is a subset of FULL, so agreement between those two is not evidence;
    agreement across disjoint thirds is.
  - Every probe is compared against the unconditional "always long" and
    "always short" expectancy over the same bars, because gold rose 1,850 ->
    4,428 across this sample and any long-biased statistic is contaminated by
    that drift.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scripts.phase2_session_microstructure import load, BAR_SEC, COST_USD  # noqa: E402

# Three disjoint thirds, by calendar, of the M15 history (2022-06 -> 2026-08).
THIRDS = [
    ("T1 2022-06..2023-11", "2022-06-01", "2023-11-01"),
    ("T2 2023-11..2025-05", "2023-11-01", "2025-05-01"),
    ("T3 2025-05..2026-09", "2025-05-01", "2026-09-01"),
]


def ts(s):
    y, m, d = (int(x) for x in s.split("-"))
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp())


def tstat(x):
    x = np.asarray(x, float)
    if x.size < 20:
        return float("nan")
    s = x.std(ddof=1)
    return float(x.mean() / (s / math.sqrt(x.size))) if s > 0 else float("nan")


def hour_in(F, lo, hi):
    return (F["ist_hour"] >= lo) & (F["ist_hour"] < hi)


def contiguous(F, i, back, fwd):
    """True where bars i-back .. i+fwd are one unbroken M15 chain."""
    t, n = F["t"], F["n"]
    ok = (i >= back) & (i + fwd < n)
    i = i[ok]
    good = ((t[i] - t[i - back]) == BAR_SEC * back) & ((t[i + fwd] - t[i]) == BAR_SEC * fwd)
    return i[good]


# ---------------------------------------------------------------------------
# probes: each returns (entry_index_array, direction_array, hold_bars)
# ---------------------------------------------------------------------------

def probe_lon_rev(F, mask, mag_atr=0.0, hold=1):
    """LONDON last hour: fade the previous bar."""
    i = np.nonzero(mask & hour_in(F, 14.5, 15.5))[0]
    i = contiguous(F, i, 2, hold)
    mv = F["c"][i - 1] - F["c"][i - 2]
    a = F["atr"][i - 1]
    keep = np.isfinite(a) & (a > 0) & (mv != 0) & (np.abs(mv) >= mag_atr * a)
    return i[keep], -np.sign(mv[keep]), hold, i


def probe_ny_mom(F, mask, mag_atr=0.0, hold=1):
    """NY last hour: follow the previous bar."""
    i = np.nonzero(mask & hour_in(F, 20.5, 21.5))[0]
    i = contiguous(F, i, 2, hold)
    mv = F["c"][i - 1] - F["c"][i - 2]
    a = F["atr"][i - 1]
    keep = np.isfinite(a) & (a > 0) & (mv != 0) & (np.abs(mv) >= mag_atr * a)
    return i[keep], np.sign(mv[keep]), hold, i


def probe_asia_mom(F, mask, mag_atr=0.0, hold=1):
    """ASIA last hour (pre-London): follow the previous bar."""
    i = np.nonzero(mask & hour_in(F, 10.5, 11.5))[0]
    i = contiguous(F, i, 2, hold)
    mv = F["c"][i - 1] - F["c"][i - 2]
    a = F["atr"][i - 1]
    keep = np.isfinite(a) & (a > 0) & (mv != 0) & (np.abs(mv) >= mag_atr * a)
    return i[keep], np.sign(mv[keep]), hold, i


def probe_ovl_zrev(F, mask, thr=2.0, hold=4):
    """OVERLAP: fade a >2-sigma extension of close from its 20-bar mean."""
    i = np.nonzero(mask & hour_in(F, 15.5, 17.5))[0]
    i = contiguous(F, i, 21, hold)
    sd, sma = F["sd20"][i - 1], F["sma20"][i - 1]
    keep = np.isfinite(sd) & (sd > 0)
    i, sd, sma = i[keep], sd[keep], sma[keep]
    z = (F["c"][i - 1] - sma) / sd
    sel = np.abs(z) > thr
    return i[sel], -np.sign(z[sel]), hold, i


def probe_ny_break(F, mask, N=20, hold=8):
    """NY: long a close above the prior 20-bar high (decided at bar i-1's
    close, entered at bar i's open -- no look-ahead into the breakout bar)."""
    i = np.nonzero(mask & hour_in(F, 17.5, 21.5))[0]
    i = contiguous(F, i, N + 1, hold)
    ph = np.array([F["h"][k - 1 - N:k - 1].max() for k in i]) if i.size else np.array([])
    sel = F["c"][i - 1] > ph
    return i[sel], np.ones(sel.sum()), hold, i


def probe_lon_break_dn(F, mask, N=20, hold=8):
    """LONDON: short a close below the prior 20-bar low."""
    i = np.nonzero(mask & hour_in(F, 11.5, 15.5))[0]
    i = contiguous(F, i, N + 1, hold)
    pl = np.array([F["l"][k - 1 - N:k - 1].min() for k in i]) if i.size else np.array([])
    sel = F["c"][i - 1] < pl
    return i[sel], -np.ones(sel.sum()), hold, i


PROBES = {
    "LON_REV  fade prev bar, IST 14:30-15:30, hold 1": lambda F, m: probe_lon_rev(F, m),
    "LON_REV+ same, |prev|>0.5xATR": lambda F, m: probe_lon_rev(F, m, 0.5),
    "LON_REV++ same, |prev|>1.0xATR": lambda F, m: probe_lon_rev(F, m, 1.0),
    "NY_MOM   follow prev bar, IST 20:30-21:30, hold 1": lambda F, m: probe_ny_mom(F, m),
    "NY_MOM+  same, |prev|>0.5xATR": lambda F, m: probe_ny_mom(F, m, 0.5),
    "ASIA_MOM follow prev bar, IST 10:30-11:30, hold 1": lambda F, m: probe_asia_mom(F, m),
    "ASIA_MOM+ same, |prev|>0.5xATR": lambda F, m: probe_asia_mom(F, m, 0.5),
    "OVL_ZREV fade |z|>2, IST 15:30-17:30, hold 4": lambda F, m: probe_ovl_zrev(F, m, 2.0),
    "OVL_ZREV+ fade |z|>2.5, hold 4": lambda F, m: probe_ovl_zrev(F, m, 2.5),
    "NY_BRK   long 20-bar break, IST 17:30-21:30, hold 8": lambda F, m: probe_ny_break(F, m),
    "LON_BRKD short 20-bar break, IST 11:30-15:30, hold 8": lambda F, m: probe_lon_break_dn(F, m),
}


def evaluate(F, idx, direction, hold):
    """P/L in USD per 0.01 lot: direction x (close[i+hold-1] - open[i]) - cost.

    Also reported in ATR units, because true range roughly doubled across the
    sample: a probe can look like it "improves" in the last third purely
    because every bar got bigger.
    """
    if idx.size == 0:
        return None
    entry = F["o"][idx]
    exit_ = F["c"][idx + hold - 1]
    gross = direction * (exit_ - entry)
    pl = gross - COST_USD
    a = F["atr"][idx - 1]
    ok = np.isfinite(a) & (a > 0)
    return {
        "n": int(idx.size),
        "gross_mean": gross.mean(),
        "gross_atr": float((gross[ok] / a[ok]).mean()) if ok.any() else float("nan"),
        "mean": pl.mean(),
        "median": float(np.median(pl)),
        "hit": float((pl > 0).mean()),
        "t": tstat(pl),
        "total": pl.sum(),
        "long_frac": float((direction > 0).mean()),
    }


def unconditional(F, universe_idx, hold, long_frac):
    """Drift control.  Gold went 1,850 -> 4,428 over this sample, so a
    long-biased probe earns money for reasons that have nothing to do with the
    signal.  This is the expectancy of taking EVERY bar in the probe's
    candidate universe (not just the selected ones) at the probe's own long/
    short mix -- i.e. what the same directional bias earns with no selection.
    """
    if universe_idx.size == 0:
        return float("nan")
    mv = F["c"][universe_idx + hold - 1] - F["o"][universe_idx]
    return float(mv.mean() * (2.0 * long_frac - 1.0))


def gap_check(F):
    """How much of a close-to-close statistic is unreachable? Measure the
    close[i-1] -> open[i] jump."""
    g = F["o"][1:] - F["c"][:-1]
    g = g[F["cont"][1:]]
    return {"n": int(g.size), "mean_abs": float(np.abs(g).mean()),
            "p50_abs": float(np.median(np.abs(g))), "p90_abs": float(np.percentile(np.abs(g), 90))}


def main():
    F = load()
    print("close[i-1] -> open[i] gap (USD):", {k: round(v, 4) for k, v in gap_check(F).items()})
    print(f"\ncost per trade = ${COST_USD:.2f} round trip, 0.01 lot\n")

    masks = []
    for lab, a, b in THIRDS:
        m = (F["t"] >= ts(a)) & (F["t"] < ts(b))
        masks.append((lab, m))
    masks.append(("ALL 2022-06..2026-08", np.ones(F["n"], bool)))

    hdr = (f"{'probe':40}{'window':22}{'n':>7}{'gross$':>9}{'grossATR':>10}{'net$':>9}"
           f"{'med$':>8}{'hit':>7}{'t':>7}{'tot$':>9}{'drift$':>9}{'excess$':>9}")
    print(hdr)
    print("-" * len(hdr))
    for name, fn in PROBES.items():
        for lab, m in masks:
            idx, d, hold, uni = fn(F, m)
            r = evaluate(F, idx, d, hold)
            if r is None or r["n"] < 30:
                print(f"{name:40}{lab:22}{(0 if r is None else r['n']):>7}   (too few)")
                continue
            drift = unconditional(F, uni, hold, r["long_frac"])
            print(f"{name:40}{lab:22}{r['n']:>7}{r['gross_mean']:>9.3f}{r['gross_atr']:>10.4f}"
                  f"{r['mean']:>9.3f}{r['median']:>8.3f}{r['hit']:>7.3f}{r['t']:>7.2f}"
                  f"{r['total']:>9.1f}{drift:>9.3f}{r['gross_mean'] - drift:>9.3f}")
        print()

    tail_decomposition(F)


def tail_decomposition(F):
    """Where does the session autocorrelation actually live?

    Pearson rho is dominated by the largest observations, and gold's M15
    returns have excess kurtosis of 20-300.  If Pearson rho is large but
    Spearman (rank) rho and the winsorised rho are near zero, the "edge" is a
    handful of extreme bar-pairs, not a property a sign-based rule can harvest.
    """
    print("\n\nAUTOCORRELATION: TAILS vs BODY (lag 1, close-to-close M15)")
    print("Pearson uses raw returns; Spearman uses ranks; winsorised clips at "
          "the 1st/99th pct.\n")
    windows = [
        ("LONDON last hr  IST 14:30-15:30", 14.5, 15.5),
        ("LONDON all      IST 11:30-15:30", 11.5, 15.5),
        ("NY last hr      IST 20:30-21:30", 20.5, 21.5),
        ("ASIA last hr    IST 10:30-11:30", 10.5, 11.5),
        ("OVERLAP last hr IST 16:30-17:30", 16.5, 17.5),
        ("POSTNY first hr IST 00:00-01:00", 0.0, 1.0),
    ]
    print(f"{'window':34}{'n':>7}{'pearson':>10}{'z':>8}{'spearman':>10}{'z':>8}"
          f"{'winsor':>9}{'z':>8}")
    for lab, lo, hi in windows:
        m = hour_in(F, lo, hi)
        i = np.nonzero(m & np.isfinite(F["ret"]))[0]
        i = i[(i + 1 < F["n"])]
        ok = m[i + 1] & np.isfinite(F["ret"][i + 1]) & ((F["t"][i + 1] - F["t"][i]) == BAR_SEC)
        a, b = F["ret"][i[ok]], F["ret"][i[ok] + 1]
        if a.size < 200:
            continue
        pear = np.corrcoef(a, b)[0, 1]
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        spear = np.corrcoef(ra, rb)[0, 1]
        lo1, hi1 = np.percentile(np.concatenate([a, b]), [1, 99])
        wa, wb = np.clip(a, lo1, hi1), np.clip(b, lo1, hi1)
        wins = np.corrcoef(wa, wb)[0, 1]
        s = math.sqrt(a.size)
        print(f"{lab:34}{a.size:>7}{pear:>10.4f}{pear*s:>8.2f}{spear:>10.4f}"
              f"{spear*s:>8.2f}{wins:>9.4f}{wins*s:>8.2f}")

    slot_scan(F)
    atr_bucket_scan(F)
    dst_test(F)
    regime_confound(F)


def dst_test(F):
    """Falsification test for the 'LBMA AM auction' explanation of the London
    reversal.

    The LBMA gold benchmark AM auction is fixed to the LONDON clock (10:30
    London).  If the reversal is auction-driven, the hot 15-minute slot must
    move by a full hour in UTC between BST (Apr-Sep) and GMT (Nov-Feb).  If it
    stays at the same UTC time, the auction hypothesis is dead.
    """
    print("\n\nDST FALSIFICATION TEST - winsorised lag-1 rho by slot, BST vs GMT")
    mon = np.array([datetime.utcfromtimestamp(int(x)).month for x in F["t"]])
    bst, gmt = np.isin(mon, [4, 5, 6, 7, 8, 9]), np.isin(mon, [11, 12, 1, 2])

    def wr(m):
        i = np.nonzero(m & np.isfinite(F["ret"]))[0]
        i = i[i + 1 < F["n"]]
        ok = np.isfinite(F["ret"][i + 1]) & ((F["t"][i + 1] - F["t"][i]) == BAR_SEC)
        a, b = F["ret"][i[ok]], F["ret"][i[ok] + 1]
        if a.size < 120:
            return None
        lo, hi = np.percentile(np.concatenate([a, b]), [1, 99])
        w = np.corrcoef(np.clip(a, lo, hi), np.clip(b, lo, hi))[0, 1]
        return a.size, w, w * math.sqrt(a.size)

    print(f"{'IST':8}{'UTC':8}{'nBST':>6}{'rhoBST':>9}{'zBST':>7}{'nGMT':>6}{'rhoGMT':>9}{'zGMT':>7}")
    for k in range(54, 68):
        lo = k * 0.25
        m = (F["ist_hour"] >= lo) & (F["ist_hour"] < lo + 0.25)
        rb, rg = wr(m & bst), wr(m & gmt)
        if rb is None or rg is None:
            continue
        u = (lo - 5.5) % 24
        print(f"{int(lo):02d}:{int((lo%1)*60):02d}   {int(u):02d}:{int((u%1)*60):02d}   "
              f"{rb[0]:>6}{rb[1]:>9.4f}{rb[2]:>7.2f}{rg[0]:>6}{rg[1]:>9.4f}{rg[2]:>7.2f}")


def regime_confound(F):
    """Is 'the London fade works when ATR is high' the same statement as 'the
    London fade only worked in 2025-2026'?  Almost entirely, yes."""
    print("\n\nREGIME CONFOUND - what fraction of each ATR bucket comes from T3?")
    idx, d, hold, _ = probe_lon_rev(F, np.ones(F["n"], bool), 0.5)
    a = F["atr"][idx - 1]
    g = d * (F["c"][idx + hold - 1] - F["o"][idx])
    t3 = F["t"][idx] >= ts("2025-05-01")
    for lo, hi in [(0, 4), (4, 8), (8, 1e9)]:
        s = (a >= lo) & (a < hi)
        print(f"  ATR {lo}-{hi:g}: n={int(s.sum()):5d}  from T3 = {t3[s].mean():.1%}")
    for lab, sub, buckets in (("T3 ONLY (2025-05 ->)", t3, [(0, 6), (6, 9), (9, 1e9)]),
                              ("T1+T2 ONLY (2022-06 -> 2025-05)", ~t3, [(0, 3), (3, 1e9)])):
        print(f"\n  {lab}:")
        for lo, hi in buckets:
            s = sub & (a >= lo) & (a < hi)
            if s.sum() < 30:
                continue
            pl = g[s] - COST_USD
            print(f"    ATR {lo}-{hi:g}: n={int(s.sum()):4d} gross={g[s].mean():+.3f} "
                  f"grossATR={(g[s]/a[s]).mean():+.4f} net={pl.mean():+.3f} t={tstat(pl):+.2f}")


def slot_scan(F):
    """Winsorised lag-1 autocorrelation at 15-minute resolution, IST 11:30-17:30.

    Locates the London reversal precisely.  Note the LBMA gold benchmark AM
    auction runs at 10:30 London = 09:30 UTC = 15:00 IST in BST, 10:30 UTC =
    16:00 IST in GMT -- so a real auction-related effect should appear as two
    adjacent hot slots that swap with the DST changeover, not one.
    """
    print("\n\nWINSORISED LAG-1 AUTOCORRELATION BY 15-MIN SLOT (IST 11:30-17:45)")
    print(f"{'IST slot':12}{'n':>7}{'pearson':>10}{'winsor':>10}{'z_win':>8}"
          f"{'contRate':>10}{'z_cont':>8}")
    for k in range(46, 72):
        lo = k * 0.25
        if lo < 11.5 or lo >= 18.0:
            continue
        m = (F["ist_hour"] >= lo) & (F["ist_hour"] < lo + 0.25)
        i = np.nonzero(m & np.isfinite(F["ret"]))[0]
        i = i[i + 1 < F["n"]]
        ok = np.isfinite(F["ret"][i + 1]) & ((F["t"][i + 1] - F["t"][i]) == BAR_SEC)
        a, b = F["ret"][i[ok]], F["ret"][i[ok] + 1]
        if a.size < 200:
            continue
        pear = np.corrcoef(a, b)[0, 1]
        lo1, hi1 = np.percentile(np.concatenate([a, b]), [1, 99])
        wins = np.corrcoef(np.clip(a, lo1, hi1), np.clip(b, lo1, hi1))[0, 1]
        nz = (a != 0) & (b != 0)
        same = int((np.sign(a[nz]) == np.sign(b[nz])).sum())
        cr = same / nz.sum()
        zc = (same - nz.sum() / 2) / math.sqrt(nz.sum() / 4)
        hh, mm = int(lo), int((lo % 1) * 60)
        print(f"{hh:02d}:{mm:02d}->next{'':1}{a.size:>7}{pear:>10.4f}{wins:>10.4f}"
              f"{wins*math.sqrt(a.size):>8.2f}{cr:>10.4f}{zc:>8.2f}")


def atr_bucket_scan(F):
    """Does the London fade ever clear the fixed $0.28 cost?

    The gross edge scales with ATR; the cost does not.  So the only regime in
    which a sub-ATR edge can pay is high volatility.  Split the London-fade
    trades by the ATR at entry and check.
    """
    print("\n\nLONDON FADE (IST 14:30-15:30, |prev|>0.5xATR, hold 1) BY ATR BUCKET")
    idx, d, hold, _ = probe_lon_rev(F, np.ones(F["n"], bool), 0.5)
    a = F["atr"][idx - 1]
    gross = d * (F["c"][idx + hold - 1] - F["o"][idx])
    edges = [0, 2, 4, 6, 8, 12, 1e9]
    print(f"{'ATR bucket':14}{'n':>7}{'grossUSD':>10}{'grossATR':>10}{'net$':>9}"
          f"{'t':>7}{'hit':>7}{'cost/ATR':>10}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (a >= lo) & (a < hi)
        if s.sum() < 40:
            continue
        g = gross[s]
        pl = g - COST_USD
        lbl = f"{lo:g}-{hi:g}" if hi < 1e8 else f">{lo:g}"
        print(f"{lbl:14}{int(s.sum()):>7}{g.mean():>10.3f}{(g/a[s]).mean():>10.4f}"
              f"{pl.mean():>9.3f}{tstat(pl):>7.2f}{(pl>0).mean():>7.3f}"
              f"{(COST_USD/a[s]).mean():>10.4f}")


if __name__ == "__main__":
    main()
