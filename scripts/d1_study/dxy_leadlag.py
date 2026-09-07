"""H2 decision test: does DXY LEAD gold, or only move opposite it?

D1_MARKET_STUDY.txt section 5 measured contemporaneous correlation (-0.397,
stable) -- which is real but not tradeable on its own. A same-day inverse
relationship tells you nothing about what happens NEXT unless the DXY move
comes first. This is the regression that decides whether H2 (and therefore
Phase 1 of D1_SYSTEM_PLAN.md) is a GO or a NO-GO.

Pre-registered before running (per Rule 2 of the plan's four rules):
  PASS  : |t-stat| > 2 on prior-DXY-move -> forward-gold-return, with the
          expected NEGATIVE sign, stable in sign across decade sub-samples.
  FAIL  : t-stat inside +/-2, or sign flips by period -> DXY is coincident,
          not predictive; H2 dies and Phase 1 returns NO-GO overall.

    python -m scripts.d1_study.dxy_leadlag
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

CSV = os.path.join("research", "data", "d1_study", "master.csv")
LOOKBACKS = (1, 3, 5, 10, 20)     # prior DXY move, trading days
FORWARDS = (1, 5, 10, 20)         # forward gold return, trading days


def ols_t(x: np.ndarray, y: np.ndarray):
    """beta, t-stat for y ~ a + b*x."""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 30:
        return np.nan, np.nan, n
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (n - 2)
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(s2 * xtx_inv[1, 1])
    return float(beta[1]), float(beta[1] / se) if se > 0 else np.nan, n


def main():
    df = pd.read_csv(CSV, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
    df = df.dropna(subset=["gold", "dxy"]).reset_index(drop=True)
    gold, dxy, dates = df["gold"].to_numpy(float), df["dxy"].to_numpy(float), df["Date"]
    print(f"H2 LEAD/LAG TEST  |  {dates.iloc[0].date()} -> {dates.iloc[-1].date()}  n={len(df)}\n")

    print("PRIOR DXY move (rows) -> FORWARD gold return (cols).  cell = beta / t-stat")
    print(f"{'prior DXY':>10} | " + " | ".join(f"fwd {f:>2}d" for f in FORWARDS))
    print("-" * 62)

    grid = {}
    for lb in LOOKBACKS:
        dxy_prior = np.full(len(dxy), np.nan)
        dxy_prior[lb:] = dxy[lb:] / dxy[:-lb] - 1.0
        cells = []
        for fw in FORWARDS:
            g_fwd = np.full(len(gold), np.nan)
            g_fwd[:-fw] = gold[fw:] / gold[:-fw] - 1.0
            b, t, n = ols_t(dxy_prior, g_fwd)
            grid[(lb, fw)] = (b, t, n)
            cells.append(f"{b:+.3f}/{t:+5.2f}" if np.isfinite(t) else "   n/a   ")
        print(f"{lb:>9}d | " + " | ".join(cells))

    # Contemporaneous benchmark -- what section 5 already knew.
    g_ret = np.full(len(gold), np.nan); g_ret[1:] = gold[1:] / gold[:-1] - 1.0
    d_ret = np.full(len(dxy), np.nan); d_ret[1:] = dxy[1:] / dxy[:-1] - 1.0
    b_c, t_c, _ = ols_t(d_ret, g_ret)
    print(f"\n(benchmark) SAME-DAY dxy ret -> gold ret: beta {b_c:+.3f}  t {t_c:+.2f}"
          f"   <- known, not tradeable")

    # Best predictive cell, and its stability by era.
    best = max((v for v in grid.items() if np.isfinite(v[1][1])),
               key=lambda kv: abs(kv[1][1]), default=None)
    if not best:
        print("\nVERDICT: no computable predictive relationship -> H2 FAILS")
        return
    (lb, fw), (b, t, n) = best
    print(f"\nstrongest predictive cell: prior {lb}d DXY -> fwd {fw}d gold  "
          f"beta {b:+.4f}  t {t:+.2f}  n={n}")

    print("\nstability by era (same cell):")
    dxy_prior = np.full(len(dxy), np.nan); dxy_prior[lb:] = dxy[lb:] / dxy[:-lb] - 1.0
    g_fwd = np.full(len(gold), np.nan); g_fwd[:-fw] = gold[fw:] / gold[:-fw] - 1.0
    years = dates.dt.year.to_numpy()
    signs = []
    for lo, hi in [(2000, 2007), (2008, 2012), (2013, 2017), (2018, 2021), (2022, 2026)]:
        m = (years >= lo) & (years <= hi)
        bb, tt, nn = ols_t(dxy_prior[m], g_fwd[m])
        if np.isfinite(tt):
            signs.append(np.sign(bb))
            print(f"  {lo}-{hi}: beta {bb:+.4f}  t {tt:+5.2f}  n={nn}")

    stable = len(set(signs)) == 1 if signs else False
    significant = abs(t) > 2
    negative = b < 0
    passed = significant and negative and stable
    print(f"\nPRE-REGISTERED CRITERIA:")
    print(f"  |t| > 2                : {significant}  (t = {t:+.2f})")
    print(f"  expected negative sign : {negative}  (beta = {b:+.4f})")
    print(f"  sign stable by era     : {stable}")
    print(f"\nVERDICT: H2 {'PASSES -- DXY leads gold, Phase 1 is a GO' if passed else 'FAILS -- DXY is coincident, not predictive'}")
    if not passed:
        print("  -> All four pre-registered hypotheses (H1-H4) are now rejected.")
        print("  -> D1_SYSTEM_PLAN.md Phase 1 gate returns NO-GO as written.")


if __name__ == "__main__":
    main()
