"""Run the XAUUSD market characterisation and write it to research/.

    python -m scripts.market_study

In-sample window only. The locked holdout is not read.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import (
    autocorrelation,
    barrier_baseline,
    build_features,
    by_bucket,
    excursion_baseline,
    follow_through,
    session_of,
)

OUT_DIR = os.path.join("research", "market")


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    args = ap.parse_args()

    bars = load_bars("XAUUSDm", timeframes=("M15", "D1"))
    t = bars.m15["time"].astype(np.int64)
    m = (t >= _ts(args.start)) & (t <= _ts(args.end))
    rates = bars.m15[m]
    print(f"XAUUSDm M15  {len(rates):,} bars  {args.start} -> {args.end}  "
          f"data {bars.hash_key()}\n")

    f = build_features(rates)
    sess = session_of(f["ist_hour"])
    report = {"window": {"start": args.start, "end": args.end},
              "bars": int(len(rates)), "data_hash": bars.hash_key()}

    # ---- 1. Null baselines -------------------------------------------------
    print("=" * 74)
    print("  NULL BASELINES -- what gold does with no signal at all")
    print("=" * 74)
    exc = excursion_baseline(f)
    report["excursion_baseline"] = exc
    print(f"  random entry, {exc['horizon_bars']} bars ahead (n={exc['n']:,}):")
    print(f"    MFE {exc['mfe_atr_mean']:.3f} ATR   MAE {exc['mae_atr_mean']:.3f} ATR"
          f"   drift {exc['mfe_minus_mae_mean']:+.3f} ATR")
    print("    -> any candidate must beat these excursions to be a signal at all")

    print("\n  barrier hit rates (random long, 192-bar cap):")
    print(f"    {'TP/SL':<14}{'observed':>10}{'random walk':>14}{'excess':>9}{'exp R':>9}")
    bars_rows = []
    for tp, sl in [(1.0, 1.0), (1.5, 1.5), (2.0, 1.5), (3.0, 1.5), (5.0, 1.5), (12.0, 1.5)]:
        b = barrier_baseline(f, tp, sl)
        bars_rows.append(b)
        print(f"    {f'{tp}/{sl}':<14}{b['observed_win_rate']:>10.4f}"
              f"{b['random_walk_win_rate']:>14.4f}{b['excess']:>+9.4f}"
              f"{(b['expectancy_R'] if b['expectancy_R'] is not None else 0):>+9.4f}")
    report["barrier_baseline"] = bars_rows

    # ---- 2. Momentum vs mean reversion -------------------------------------
    print("\n" + "=" * 74)
    print("  DOES GOLD CONTINUE OR REVERT?")
    print("=" * 74)
    ac = autocorrelation(f)
    report["autocorrelation"] = ac
    print("  M15 log-return autocorrelation:")
    print("   ", {k: v for k, v in ac.items()})
    ft_rows = []
    print(f"\n  {'trigger':<12}{'lookahead':>11}{'n':>7}{'continue%':>11}{'mean fwd ATR':>14}")
    for mv in (0.5, 1.0, 1.5, 2.0):
        for lb in (4, 16):
            ft = follow_through(f, mv, lb)
            ft_rows.append(ft)
            if ft["n"]:
                print(f"  {f'{mv} ATR':<12}{lb:>11}{ft['n']:>7}"
                      f"{ft['continuation_rate']*100:>10.1f}%{ft['mean_forward_atr']:>+14.4f}")
    report["follow_through"] = ft_rows

    # ---- 3. Session and hour structure -------------------------------------
    print("\n" + "=" * 74)
    print("  SESSION STRUCTURE (IST)")
    print("=" * 74)
    sb = by_bucket(f, sess, labels=["ASIA", "LONDON", "OVERLAP", "NY", "LATE"])
    report["by_session"] = sb
    print(f"  {'session':<10}{'bars':>8}{'|ret| bp':>11}{'range $':>10}"
          f"{'efficiency':>12}{'spread pts':>12}")
    for k, v in sb.items():
        print(f"  {k:<10}{v['bars']:>8}{v['mean_abs_return_bp']:>11.2f}"
              f"{v['mean_range_usd']:>10.3f}{v['mean_efficiency']:>12.4f}"
              f"{v['mean_spread_pts']:>12.1f}")

    hb = by_bucket(f, np.floor(f["ist_hour"]).astype(int))
    report["by_hour"] = hb
    print(f"\n  {'IST hr':<8}{'bars':>8}{'|ret| bp':>11}{'range $':>10}"
          f"{'efficiency':>12}{'spread':>9}")
    for k in sorted(hb, key=lambda x: int(x)):
        v = hb[k]
        print(f"  {k:0>2}:00   {v['bars']:>8}{v['mean_abs_return_bp']:>11.2f}"
              f"{v['mean_range_usd']:>10.3f}{v['mean_efficiency']:>12.4f}"
              f"{v['mean_spread_pts']:>9.1f}")

    wd = by_bucket(f, f["weekday"])
    report["by_weekday"] = wd
    names = {"0": "Mon", "1": "Tue", "2": "Wed", "3": "Thu", "4": "Fri", "6": "Sun"}
    print(f"\n  {'day':<7}{'bars':>8}{'|ret| bp':>11}{'efficiency':>12}")
    for k in sorted(wd, key=lambda x: int(x)):
        v = wd[k]
        print(f"  {names.get(k, k):<7}{v['bars']:>8}{v['mean_abs_return_bp']:>11.2f}"
              f"{v['mean_efficiency']:>12.4f}")

    # ---- 4. Chop / regime --------------------------------------------------
    print("\n" + "=" * 74)
    print("  CHOP AND REGIME (Part 21)")
    print("=" * 74)
    er, adxv, atrp = f["er20"], f["adx14"], f["atr_pct"]
    ok = ~np.isnan(er) & ~np.isnan(adxv)
    qs = [0, 10, 25, 50, 75, 90, 100]
    print("  efficiency ratio (ER20) percentiles -- the direct chop measure:")
    print("   ", {f"p{q}": round(float(np.percentile(er[ok], q)), 4) for q in qs})
    print("  ADX(14) percentiles (proper Wilder ADX, not the DX the old engine used):")
    print("   ", {f"p{q}": round(float(np.percentile(adxv[ok], q)), 2) for q in qs})
    report["er_percentiles"] = {f"p{q}": float(np.percentile(er[ok], q)) for q in qs}
    report["adx_percentiles"] = {f"p{q}": float(np.percentile(adxv[ok], q)) for q in qs}

    # How much of the sample is genuinely trending?
    for thr in (0.2, 0.3, 0.4, 0.5):
        share = float((er[ok] >= thr).mean())
        print(f"    ER >= {thr}: {share*100:5.1f}% of bars")
        report[f"er_share_ge_{thr}"] = share

    # Does efficiency predict follow-through? If it does, a chop filter has value.
    print("\n  forward 16-bar |move| in ATR, bucketed by current ER20:")
    c, a = f["close"], f["atr14"]
    n = len(c)
    fwd = np.full(n, np.nan)
    fwd[:n - 16] = np.abs(c[16:] - c[:n - 16])
    with np.errstate(invalid="ignore", divide="ignore"):
        fwd_atr = fwd / a
    edges = [0.0, 0.15, 0.25, 0.35, 0.5, 1.01]
    er_rows = {}
    print(f"    {'ER bucket':<16}{'bars':>9}{'fwd |move| ATR':>17}{'fwd signed':>13}")
    signed = np.full(n, np.nan)
    signed[:n - 16] = (c[16:] - c[:n - 16])
    with np.errstate(invalid="ignore", divide="ignore"):
        signed_atr = signed / a
    for lo_, hi_ in zip(edges[:-1], edges[1:]):
        msk = ok & (er >= lo_) & (er < hi_) & ~np.isnan(fwd_atr)
        if msk.sum() < 50:
            continue
        er_rows[f"{lo_}-{hi_}"] = {
            "bars": int(msk.sum()),
            "fwd_abs_move_atr": round(float(np.nanmean(fwd_atr[msk])), 4),
            "fwd_signed_atr": round(float(np.nanmean(signed_atr[msk])), 4),
        }
        print(f"    {f'{lo_:.2f}-{hi_:.2f}':<16}{msk.sum():>9}"
              f"{np.nanmean(fwd_atr[msk]):>17.4f}{np.nanmean(signed_atr[msk]):>+13.4f}")
    report["forward_move_by_er"] = er_rows

    # ---- 5. Spread ---------------------------------------------------------
    print("\n" + "=" * 74)
    print("  SPREAD (the cost that consumed 86% of the old edge)")
    print("=" * 74)
    sp = f["spread"]
    for q in (50, 75, 90, 95, 99, 100):
        print(f"    p{q:<3} {np.percentile(sp, q):>7.0f} pts  = ${np.percentile(sp, q)*0.001:>6.3f}")
    report["spread_percentiles"] = {f"p{q}": float(np.percentile(sp, q))
                                    for q in (50, 75, 90, 95, 99, 100)}
    a_med = float(np.nanmedian(f["atr14"]))
    print(f"    median ATR(14) = ${a_med:.2f};  median spread is "
          f"{np.percentile(sp,50)*0.001/a_med*100:.2f}% of one ATR")
    report["median_atr"] = a_med

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "xauusd_market_study.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"\nwritten to {path}")


if __name__ == "__main__":
    main()
