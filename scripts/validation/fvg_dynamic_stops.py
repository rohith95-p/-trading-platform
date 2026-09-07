"""Dynamic stop placement for FVG_NY, instead of the static 0.5x ATR.

The problem being solved: FVG_NY's stop is 0.5 x ATR (~$5), and NY's measured
median adverse excursion is $8.69. The stop sits BELOW the session's own noise
floor, so a share of losses are noise rather than the setup failing. Simply
widening the multiplier was already tested and did not reliably help -- so
this tests stops that adapt to conditions instead of a bigger constant.

Schemes tested (all keep the SAME signal, only stop placement changes):

  A  static 0.5x ATR                  -- current live behaviour, the baseline
  B  static 0.75x / 1.0x / 1.25x ATR  -- "just make it bigger", for reference
  C  STRUCTURE: the gap's own invalidation level. A bullish FVG means
     high[i-2] < low[i]; if price falls back through high[i-2] the gap is
     filled and the setup is objectively dead. Stop goes just beyond that,
     with a small ATR buffer. Naturally dynamic -- it scales with the actual
     impulse that created the gap, not with a constant.
  D  NOISE-FLOOR AWARE: stop = max(0.5x ATR, k x rolling median true range).
     Guarantees the stop always sits above what the market is currently
     wiggling, measured live rather than assumed.
  E  GAP-PROPORTIONAL: stop = k x gap size. A bigger gap implies a stronger
     impulse and gets more room.
  F  ATR-REGIME ADAPTIVE: multiplier varies with where current ATR sits in its
     own recent percentile distribution (tight stops in calm, wide in volatile
     -- and the inverse, since which direction helps is an empirical question).

Take profit is held at 5x the actual risk for every scheme, so R:R is constant
and the ONLY thing being compared is where the stop goes. A second pass holds
TP at a fixed 2.5x ATR (current behaviour) so R:R floats.

    python -m scripts.validation.fvg_dynamic_stops [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features

START_BAL = 105.74
COST_PER_TRADE = 2.80
SESSION = (17.5, 21.5)        # FVG_NY's own session
MAX_HOLD = 96
SIMS = 5000


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def rolling_median_tr(high, low, close, window=96):
    n = len(high)
    tr = np.full(n, np.nan)
    tr[1:] = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
    out = np.full(n, np.nan)
    for i in range(window, n):
        out[i] = np.nanmedian(tr[i - window:i])
    return out


def atr_percentile(atr, window=480):
    """Where current ATR sits within its own recent distribution, 0..1."""
    n = len(atr)
    out = np.full(n, np.nan)
    for i in range(window, n):
        w = atr[i - window:i]
        w = w[np.isfinite(w)]
        if len(w) > 10 and np.isfinite(atr[i]):
            out[i] = float((w < atr[i]).mean())
    return out


def summarize(trades, label, days):
    if len(trades) < 5:
        print(f"{label:<40} {len(trades):>5}  (too few)")
        return dict(n=len(trades))
    pls = np.array([t[0] for t in trades], float)
    risks = np.array([t[1] for t in trades], float)
    w, l = pls[pls > 0], pls[pls < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = START_BAL + np.cumsum(pls)
    peak = np.maximum.accumulate(np.concatenate(([START_BAL], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    # ruin probability via bootstrap
    rng = np.random.default_rng(11)
    paths = pls[rng.integers(0, len(pls), size=(SIMS, len(pls)))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    ruin = float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100)
    out = dict(n=int(len(pls)), win_rate=round(float(len(w) / len(pls) * 100), 1),
               profit_factor=round(pf, 4), net=round(float(pls.sum()), 2),
               min_balance=round(float(bal.min()), 2),
               max_drawdown_pct=round(dd, 1),
               avg_risk_usd=round(float(risks.mean()), 2),
               p_ruin_pct=round(ruin, 2),
               usd_per_day=round(float(pls.sum()) / days, 2))
    print(f"{label:<40} {out['n']:>5} {out['win_rate']:>6.1f} {out['profit_factor']:>7} "
          f"{out['net']:>9} {out['min_balance']:>8} {out['max_drawdown_pct']:>7}% "
          f"{out['avg_risk_usd']:>8} {out['p_ruin_pct']:>8} {out['usd_per_day']:>7}")
    return out


def simulate(idx, high, low, close, atr, med_tr, atr_pct, scheme, rr_mode, days, label, results):
    trades = []
    for i in idx:
        if not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        h2, l2 = high[i - 2], low[i - 2]
        bull = h2 < low[i]
        bear = l2 > high[i]
        if not (bull or bear):
            continue
        entry = close[i]
        gap = (low[i] - h2) if bull else (l2 - high[i])
        a = atr[i]

        kind, p = scheme
        if kind == "static":
            risk = p * a
        elif kind == "structure":
            # stop just beyond the gap's origin -- where the setup is invalid
            lvl = h2 if bull else l2
            risk = abs(entry - lvl) + p * a
        elif kind == "noise":
            m = med_tr[i]
            risk = max(0.5 * a, p * m) if np.isfinite(m) else 0.5 * a
        elif kind == "gap":
            risk = max(p * gap, 0.25 * a)
        elif kind == "regime":
            q = atr_pct[i]
            if not np.isfinite(q):
                continue
            # p>0: wider when calm, tighter when volatile;  p<0: the inverse
            mult = (1.0 - q) * abs(p) + 0.4 if p > 0 else q * abs(p) + 0.4
            risk = mult * a
        else:
            continue

        if risk <= 0 or not np.isfinite(risk):
            continue
        reward = 5.0 * risk if rr_mode == "rr5" else 2.5 * a

        sl = entry - risk if bull else entry + risk
        tp = entry + reward if bull else entry - reward
        for j in range(i + 1, min(i + 1 + MAX_HOLD, len(close))):
            if bull:
                if low[j] <= sl:
                    trades.append((-risk - COST_PER_TRADE, risk)); break
                if high[j] >= tp:
                    trades.append((reward - COST_PER_TRADE, risk)); break
            else:
                if high[j] >= sl:
                    trades.append((-risk - COST_PER_TRADE, risk)); break
                if low[j] <= tp:
                    trades.append((reward - COST_PER_TRADE, risk)); break
    results[label] = summarize(trades, label, days)


def main():
    start = sys.argv[1] if len(sys.argv) > 2 else "2025-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-05-20"
    days = max(1, (_ts(end) - _ts(start)) // 86400)

    bars = load_bars("XAUUSDm", timeframes=("M15",))
    m15 = bars.m15
    f = build_features(m15)
    high = np.asarray(m15["high"], float)
    low = np.asarray(m15["low"], float)
    close = np.asarray(m15["close"], float)
    atr = f["atr14"]
    ist_hour = f["ist_hour"]
    med_tr = rolling_median_tr(high, low, close)
    apct = atr_percentile(atr)

    in_sess = (ist_hour >= SESSION[0]) & (ist_hour < SESSION[1])
    idx = np.nonzero((m15["time"] >= _ts(start)) & (m15["time"] < _ts(end)) & in_sess)[0]
    idx = idx[idx > 2]

    for rr_mode in ("rr5", "fixed_tp"):
        tp_desc = "TP = 5x risk (R:R fixed)" if rr_mode == "rr5" else "TP = 2.5x ATR (current)"
        print(f"\nFVG_NY dynamic stops | {start} -> {end} ({days}d) | {tp_desc}\n")
        print(f"{'stop scheme':<40} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
              f"{'minBal':>8} {'maxDD':>8} {'avgRisk':>8} {'P(ruin)':>8} {'$/day':>7}")
        print("-" * 122)
        results = {}
        simulate(idx, high, low, close, atr, med_tr, apct, ("static", 0.5), rr_mode, days,
                 "A static 0.5xATR (current)", results)
        for k in (0.75, 1.0, 1.25):
            simulate(idx, high, low, close, atr, med_tr, apct, ("static", k), rr_mode, days,
                     f"B static {k}xATR", results)
        for buf in (0.0, 0.25, 0.5):
            simulate(idx, high, low, close, atr, med_tr, apct, ("structure", buf), rr_mode, days,
                     f"C structure (gap fill) +{buf}xATR", results)
        for k in (1.0, 1.5, 2.0):
            simulate(idx, high, low, close, atr, med_tr, apct, ("noise", k), rr_mode, days,
                     f"D noise-floor {k}x medTR", results)
        for k in (1.0, 2.0):
            simulate(idx, high, low, close, atr, med_tr, apct, ("gap", k), rr_mode, days,
                     f"E gap-proportional {k}x gap", results)
        for p in (0.8, -0.8):
            direction = "wider-when-calm" if p > 0 else "wider-when-volatile"
            simulate(idx, high, low, close, atr, med_tr, apct, ("regime", p), rr_mode, days,
                     f"F regime adaptive ({direction})", results)

        os.makedirs("research/validation", exist_ok=True)
        with open(f"research/validation/fvg_dynamic_stops_{rr_mode}.json", "w",
                  encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, default=str)
    print("\n--> research/validation/fvg_dynamic_stops_*.json")


if __name__ == "__main__":
    main()
