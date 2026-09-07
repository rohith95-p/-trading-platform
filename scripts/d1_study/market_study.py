"""Phase 1 -- the D1 gold market study. The GO/NO-GO for the whole project.

Measures, on 26 years of daily data, whether gold carries ANY real, repeatable
edge on the daily timeframe -- BEFORE any strategy exists.

    python -m scripts.d1_study.market_study > docs/research/D1_MARKET_STUDY.txt

Reads research/data/d1_study/master.csv (run scripts.d1_study.fetch first).
"""
import os
import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "research", "data", "d1_study", "master.csv")
df = pd.read_csv(DATA, index_col=0, parse_dates=True)
g = df["gold"].dropna()
r = np.log(g).diff().dropna()          # daily log returns
YR = 252

def _stats(daily_ret):
    eq = (1 + daily_ret).cumprod()
    yrs = len(daily_ret) / YR
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1)
    sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(YR)
    mar = cagr / abs(dd.min()) if dd.min() < 0 else np.inf
    # longest underwater (days)
    uw = (eq < eq.cummax())
    longest = 0; cur = 0
    for v in uw:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return dict(cagr=cagr, maxdd=dd.min(), sharpe=sharpe, mar=mar, underwater_days=longest)

print("=" * 72)
print("D1 GOLD MARKET STUDY  |  GC=F  2000-08 -> 2026-09  (26 years, 6527 days)")
print("=" * 72)

# ---------------------------------------------------------------------------
print("\n## 1. BUY-AND-HOLD GOLD  (the bar every strategy must beat)")
bh = _stats(g.pct_change().dropna())
print(f"  CAGR              {bh['cagr']*100:6.2f}%")
print(f"  max drawdown      {bh['maxdd']*100:6.2f}%")
print(f"  Sharpe            {bh['sharpe']:6.2f}")
print(f"  MAR (CAGR/maxDD)  {bh['mar']:6.2f}")
print(f"  longest underwater {bh['underwater_days']} trading days "
      f"(~{bh['underwater_days']/YR:.1f} yr)")
yearly = g.resample("Y").last().pct_change().dropna()
print(f"  worst year        {yearly.min()*100:6.1f}%  ({yearly.idxmin().year})")
print(f"  best year         {yearly.max()*100:6.1f}%  ({yearly.idxmax().year})")
print(f"  positive years    {int((yearly>0).sum())}/{len(yearly)}")

# ---------------------------------------------------------------------------
print("\n## 2. RANDOM-ENTRY CONTROL  (the noise floor)")
rng = np.random.default_rng(11)
for hold in (5, 10, 20, 40):
    pfs, dds = [], []
    for _ in range(500):
        n = len(r) - hold
        idx = rng.integers(0, n, size=300)
        side = rng.choice([-1, 1], size=300)
        pnl = np.array([side[k] * r.values[i:i+hold].sum() for k, i in enumerate(idx)])
        w, l = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
        pfs.append(w / l if l > 0 else np.nan)
    pfs = np.array(pfs)
    print(f"  hold {hold:2}d : random PF  mean {np.nanmean(pfs):.3f}   "
          f"95th pct {np.nanpercentile(pfs,95):.3f}   "
          f"(a real edge must clear the 95th)")

# ---------------------------------------------------------------------------
print("\n## 3. RETURN AUTOCORRELATION  (M15 was ~0 -- is D1 different?)")
for lag in (1, 2, 3, 5, 10, 20, 40, 60):
    ac = r.autocorr(lag)
    star = " *" if abs(ac) > 2 / np.sqrt(len(r)) else ""
    print(f"  lag {lag:2}d : {ac:+.4f}{star}")
print(f"  (|value| > {2/np.sqrt(len(r)):.4f} = significant at 2 s.e.)")

# ---------------------------------------------------------------------------
print("\n## 4. TIME-SERIES MOMENTUM  (does past return predict future return?)")
print("     regress next-21d return on past-Nd return, by lookback:")
fwd = np.log(g).shift(-21) - np.log(g)          # next ~1mo
for look in (21, 63, 126, 252):
    past = np.log(g) - np.log(g).shift(look)
    d = pd.concat([past, fwd], axis=1).dropna()
    d.columns = ["past", "fwd"]
    x, y = d["past"].values, d["fwd"].values
    b1 = np.cov(x, y)[0, 1] / np.var(x)
    b0 = y.mean() - b1 * x.mean()
    resid = y - (b0 + b1 * x)
    se = np.sqrt((resid @ resid) / (len(x) - 2) / (np.var(x) * len(x)))
    t = b1 / se
    # sign-agreement: does past-up predict fwd-up?
    agree = np.mean(np.sign(x) == np.sign(y))
    print(f"  past {look:3}d : beta {b1:+.4f}  t-stat {t:+5.2f}   "
          f"sign-agreement {agree*100:4.1f}%   {'MOMENTUM' if t>2 else 'reversion' if t<-2 else 'noise'}")

# by decade for stability
print("\n     past-252d momentum sign-agreement, by period:")
past252 = (np.log(g) - np.log(g).shift(252))
dd = pd.concat([past252, fwd], axis=1).dropna(); dd.columns = ["past", "fwd"]
for lo, hi in [(2000, 2008), (2008, 2013), (2013, 2018), (2018, 2022), (2022, 2027)]:
    s = dd[(dd.index.year >= lo) & (dd.index.year < hi)]
    if len(s) > 50:
        ag = np.mean(np.sign(s["past"]) == np.sign(s["fwd"]))
        print(f"       {lo}-{hi-1}: {ag*100:4.1f}%  (n={len(s)})")

# ---------------------------------------------------------------------------
print("\n## 5. DXY RELATIONSHIP")
if "dxy" in df:
    dxret = np.log(df["dxy"]).diff()
    both = pd.concat([r, dxret], axis=1).dropna(); both.columns = ["gold", "dxy"]
    print(f"  full-sample corr(gold ret, dxy ret): {both['gold'].corr(both['dxy']):+.3f}")
    roll = both["gold"].rolling(63).corr(both["dxy"]).dropna()
    print(f"  rolling 63d corr: mean {roll.mean():+.3f}  min {roll.min():+.3f}  "
          f"max {roll.max():+.3f}  std {roll.std():.3f}")
    print(f"  % of time corr < -0.3: {(roll < -0.3).mean()*100:.0f}%   "
          f"% of time corr > 0 (relationship inverts): {(roll > 0).mean()*100:.0f}%")

# ---------------------------------------------------------------------------
print("\n## 6. 10Y YIELD RELATIONSHIP  (proxy for real yields -- nominal only)")
if "y10" in df:
    y = df["y10"].reindex(g.index).ffill()
    ychg = y.diff()
    both = pd.concat([r, ychg], axis=1).dropna(); both.columns = ["gold", "dy"]
    print(f"  corr(gold ret, d 10Y yield): {both['gold'].corr(both['dy']):+.3f}")
    # gold return when yields falling vs rising (20d)
    y20 = y.diff(20).reindex(r.index).ffill()
    fwd5 = r.rolling(5).sum().shift(-5)
    falling = fwd5[y20 < -0.15].mean()
    rising = fwd5[y20 > 0.15].mean()
    print(f"  gold fwd-5d return | 10Y fell >15bp over 20d: {falling*1e4:+.1f} bp")
    print(f"  gold fwd-5d return | 10Y rose >15bp over 20d: {rising*1e4:+.1f} bp")

# ---------------------------------------------------------------------------
print("\n## 7. VOLATILITY REGIMES")
atr = (g.rolling(14).max() - g.rolling(14).min())  # crude 14d range
volpct = atr.rolling(252).apply(lambda w: (w < w.iloc[-1]).mean(), raw=False)
fwd10 = r.rolling(10).sum().shift(-10)
for lo, hi, lbl in [(0, .33, "low vol"), (.33, .67, "mid vol"), (.67, 1.01, "high vol")]:
    m = (volpct >= lo) & (volpct < hi)
    seg = fwd10[m].dropna()
    print(f"  {lbl:8}: fwd-10d mean {seg.mean()*1e4:+6.1f}bp  std {seg.std()*1e4:6.1f}bp  n={len(seg)}")

# ---------------------------------------------------------------------------
print("\n## 8. SEASONALITY")
mret = r.groupby(r.index.month).mean() * 21 * 1e4
print("  mean monthly return (bp):")
for mo in range(1, 13):
    print(f"    {pd.Timestamp(2020, mo, 1).strftime('%b')}: {mret.get(mo, 0):+6.1f}")
dret = r.groupby(r.index.dayofweek).mean() * 1e4
print("  mean by weekday (bp): " + "  ".join(
    f"{d}={dret.get(i,0):+.1f}" for i, d in enumerate(["Mon","Tue","Wed","Thu","Fri"])))

# ---------------------------------------------------------------------------
print("\n## 9. GOLD'S OWN DRAWDOWN ANATOMY  (how wide must a stop be?)")
eq = g / g.iloc[0]
dd = eq / eq.cummax() - 1
troughs = []
in_dd = False; start = None
for dt, v in dd.items():
    if v < -0.01 and not in_dd:
        in_dd = True; start = dt; mn = v
    elif in_dd:
        mn = min(mn, v)
        if v >= -0.001:
            troughs.append((start, dt, mn, (dt - start).days))
            in_dd = False
big = sorted([t for t in troughs if t[2] < -0.10], key=lambda x: x[2])[:8]
print("  worst corrections (>10%):")
for s, e, m, days in big:
    print(f"    {s.date()} -> {e.date()}  {m*100:6.1f}%  {days} days")
print(f"  median daily True Range: ${(g.diff().abs()).median():.2f}   "
      f"90th pct: ${(g.diff().abs()).quantile(.9):.2f}")

print("\n" + "=" * 72)
print("VERDICT NOTES (fill after reading):")
print(" - autocorrelation significant at any lag?  -> momentum family alive/dead")
print(" - TS-momentum t-stat > 2 AND stable by period?  -> H1 viable")
print(" - DXY corr stable & mostly negative?  -> H2 viable")
print(" - yield relationship directional?  -> H3 viable")
print(" - any strategy must clear the section-2 random 95th-pct PF")
print("=" * 72)
