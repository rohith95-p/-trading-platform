"""New-class edge screen: time-of-day drift, H1/H4 trend, D1 momentum.

Hypotheses are fixed in advance (small grid). Parameters/signs are chosen on the
in-sample half only (2021/22 -> 2024-12); the out-of-sample half (2025-01 ->) is
the judge. Net of spread (one spread per round trip). $ figures are per 0.01 lot
(1 oz): $1 per $1 of price move.
"""
import os, sys, datetime as dt, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
SPLIT = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp())
PT = 0.001

def load(tf): return np.load(f"research/data/XAUUSDm_{tf}.npy")

def stats(pnl, label, extra=""):
    pnl = np.asarray(pnl, float)
    if len(pnl) < 5: return f"{label:44s} n={len(pnl):5d} (too few)"
    w, l = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    pf = w / l if l > 0 else float("inf")
    t = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl))) if pnl.std() > 0 else 0
    return f"{label:44s} n={len(pnl):5d} win={np.mean(pnl>0)*100:4.1f}% PF={pf:5.2f} mean=${pnl.mean():7.3f} net=${pnl.sum():9.1f} t={t:5.2f} {extra}"

def split(times, pnl):
    m = times >= SPLIT
    return pnl[~m], pnl[m]

# ---- A. time-of-day drift on M15 --------------------------------------------
def tod():
    r = load("M15"); t = r["time"].astype("int64"); o = r["open"].astype(float)
    sp = r["spread"].astype(float) * PT
    ist = ((t % 86400) + 19800) % 86400
    bucket = ist // 1800
    print("\n== A. Time-of-day drift (buckets=30min IST, entry open[i], exit open[i+h]) ==")
    picked = []
    for h in (2, 4, 8):
        n = len(o) - h
        ret = o[h:h + n] - o[:n]                   # long return in $
        valid = (t[h:h + n] - t[:n]) == 900 * h    # no gaps
        for b in range(48):
            idx = np.nonzero((bucket[:n] == b) & valid & (t[:n] < SPLIT))[0]
            if len(idx) < 150: continue
            x = ret[idx]; tt = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
            if abs(tt) >= 2.5: picked.append((h, b, np.sign(tt), tt))
    print(f"IS buckets with |t|>=2.5: {len(picked)} of {3*48} tests (chance ~{0.0124*144:.1f})")
    allo = []
    for h, b, s, tt in picked:
        n = len(o) - h
        ret = o[h:h + n] - o[:n]; valid = (t[h:h + n] - t[:n]) == 900 * h
        idx = np.nonzero((bucket[:n] == b) & valid & (t[:n] >= SPLIT))[0]
        pnl = s * ret[idx] - sp[idx]
        allo.extend(pnl)
        print(stats(pnl, f"h={h*15:3d}m bucket {b//2:02d}:{'30' if b%2 else '00'} IST dir={'L' if s>0 else 'S'} (IS t={tt:+.1f})", ""))
    if allo: print(stats(allo, "ALL picked, OOS pooled"))

# ---- B. H4 / H1 trend ---------------------------------------------------------
def donchian(tf, n_in, n_out, split_label):
    r = load(tf); t = r["time"].astype("int64"); h = r["high"].astype(float); l = r["low"].astype(float)
    c = r["close"].astype(float); sp = r["spread"].astype(float) * PT
    pos = 0; entry = 0; et = 0; pnl = []; times = []
    for i in range(max(n_in, n_out) + 1, len(c) - 1):
        hh = h[i - n_in:i].max(); ll = l[i - n_in:i].min()
        xh = h[i - n_out:i].max(); xl = l[i - n_out:i].min()
        if pos == 1 and c[i] < xl:
            pnl.append(c[i] - entry - sp[i]); times.append(et); pos = 0
        elif pos == -1 and c[i] > xh:
            pnl.append(entry - c[i] - sp[i]); times.append(et); pos = 0
        if pos == 0:
            if c[i] > hh: pos, entry, et = 1, c[i], t[i]
            elif c[i] < ll: pos, entry, et = -1, c[i], t[i]
    return np.array(pnl), np.array(times)

def trend():
    print("\n== B. Donchian trend (close-break entry, opposite n_out exit, both sides) ==")
    for tf, ni, no in (("H4", 20, 10), ("H4", 55, 20), ("H1", 100, 50), ("H1", 200, 100)):
        p, tm = donchian(tf, ni, no, "")
        a, b = split(tm, p)
        print(stats(a, f"{tf} Donchian {ni}/{no} IS")); print(stats(b, f"{tf} Donchian {ni}/{no} OOS"))

# ---- C. D1 time-series momentum ----------------------------------------------
def d1mom():
    r = load("D1"); t = r["time"].astype("int64"); c = r["close"].astype(float)
    o = r["open"].astype(float); sp = r["spread"].astype(float) * PT
    print("\n== C. D1 time-series momentum (sign of N-day return at close, hold 1 day) ==")
    for N in (20, 60, 120):
        sig = np.zeros(len(c)); sig[N:] = np.sign(c[N:] - c[:-N])
        # decide at close[i], hold close[i]->close[i+1]
        day = (c[1:] - c[:-1]) * sig[:-1]
        chg = np.abs(np.diff(sig, prepend=0))[:-1] > 0
        day = day - sp[:-1] * chg                      # pay spread when position flips
        tm = t[:-1]
        a, b = split(tm, day)
        print(stats(a, f"D1 TSMOM N={N} IS")); print(stats(b, f"D1 TSMOM N={N} OOS"))
        lo = day[(sig[:-1] > 0)]; 
    m = t[:-1] >= SPLIT
    bh = (c[1:] - c[:-1])
    print(stats(bh[~m], "Buy&hold daily IS (benchmark)")); print(stats(bh[m], "Buy&hold daily OOS (benchmark)"))
    print("OOS price move: $%.0f -> $%.0f" % (c[t >= SPLIT][0], c[-1]))

if __name__ == "__main__":
    tod(); trend(); d1mom()
