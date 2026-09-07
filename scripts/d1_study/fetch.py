"""Phase 0 -- data foundation for the D1 gold study.

Pulls 20+ years of daily data from Yahoo Finance and caches it as CSV in
research/data/d1_study/. Gold via GC=F (COMEX front-month futures); the broker
XAUUSDm spot only goes back ~4 years, GC=F to 2000 and tracks spot within a few
dollars -- fine for measuring statistical relationships.

    python -m scripts.d1_study.fetch
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "research", "data", "d1_study")
os.makedirs(OUT, exist_ok=True)

TICKERS = {
    "gold":  "GC=F",        # COMEX gold front-month
    "dxy":   "DX-Y.NYB",    # US Dollar Index
    "y10":   "^TNX",        # 10Y nominal Treasury yield (x10)
    "vix":   "^VIX",        # equity vol
    "spx":   "^GSPC",       # S&P 500
    "gld":   "GLD",         # gold ETF -- spot proxy cross-check
}

frames = {}
for name, tkr in TICKERS.items():
    h = yf.Ticker(tkr).history(period="max", interval="1d", auto_adjust=False)
    if h.empty:
        print(f"  {name:5} ({tkr}): EMPTY -- skipped")
        continue
    h = h[["Open", "High", "Low", "Close"]].copy()
    h.columns = ["open", "high", "low", "close"]
    h.index = h.index.tz_localize(None).normalize()
    h = h[~h.index.duplicated(keep="last")].sort_index()
    # integrity: drop rows with non-positive or absurd prices
    bad = (h[["open", "high", "low", "close"]] <= 0).any(axis=1)
    if bad.any():
        print(f"  {name}: dropped {int(bad.sum())} bad-price rows")
        h = h[~bad]
    path = os.path.join(OUT, f"{name}.csv")
    h.to_csv(path)
    frames[name] = h
    print(f"  {name:5} ({tkr:10}) {len(h):>6} rows  {h.index[0].date()} -> {h.index[-1].date()}")

# aligned master frame on gold's trading days
g = frames["gold"]
master = pd.DataFrame(index=g.index)
master["gold"] = g["close"]
for name in ("dxy", "y10", "vix", "spx", "gld"):
    if name in frames:
        master[name] = frames[name]["close"].reindex(g.index).ffill()
master["gold_ret"] = np.log(master["gold"]).diff()
master = master.dropna(subset=["gold"])
master.to_csv(os.path.join(OUT, "master.csv"))
print(f"\nmaster.csv: {len(master)} rows {master.index[0].date()} -> {master.index[-1].date()}")
print(f"columns: {list(master.columns)}")
print(f"gold NaN in returns: {master['gold_ret'].isna().sum()}")
