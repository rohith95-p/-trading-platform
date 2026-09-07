"""'Buy Sell Signal' (Pine v6) -- EMA 5/13 crossover with ATR stops, tested.

Faithful port of the script's trading logic (the plotting/table code has no
bearing on results):

    emaFast = ema(close, 5); emaSlow = ema(close, 13); atr = atr(14)
    bullTrend    = emaFast > emaSlow
    trendChange  = bullTrend != bullTrend[1]
    buySignal    = bullTrend and trendChange and close > open   (confirmCandle)
    sellSignal   = bearTrend and trendChange and close < open
    entry  = close
    SL     = low  - atr*0.5   (long)   /  high + atr*0.5  (short)
    risk   = |entry - SL|
    TP     = entry +/- risk * 3.0
    an opposite signal INVALIDATES the open position (closes it and flips)

Note the stop is anchored to the signal candle's low/high, not to entry, so
risk-per-trade varies with candle size -- that matters on a $100 account and
is measured below (avg risk in $).

Simulated directly on M15 bars with realistic cost, rather than through our
engine, so none of our own SL/TP conventions colour the result.

    python -m scripts.validation.ema513_test
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features

IST = timezone(timedelta(hours=5, minutes=30))
START_BAL = 105.74
HOLDOUT_START, HOLDOUT_END = "2025-01-01", "2026-05-20"
DAYS = 505
COST_PER_TRADE = 2.80        # ~260pt spread + slippage at 0.01 lot
MAX_HOLD_BARS = 96


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _ema(a, period):
    out = np.full(len(a), np.nan)
    k = 2.0 / (period + 1.0)
    s = None
    for i, v in enumerate(a):
        if not np.isfinite(v):
            continue
        s = v if s is None else (v - s) * k + s
        out[i] = s
    return out


def summarize(trades, label):
    if len(trades) < 2:
        print(f"{label:<46} {len(trades):>5}  (too few)")
        return dict(n=len(trades))
    pls = np.array([t[0] for t in trades], dtype=float)
    risks = np.array([t[1] for t in trades], dtype=float)
    w, l = pls[pls > 0], pls[pls < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = START_BAL + np.cumsum(pls)
    peak = np.maximum.accumulate(np.concatenate(([START_BAL], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    out = dict(n=len(pls), win_rate=round(float(len(w) / len(pls) * 100), 1),
               profit_factor=round(pf, 4), net=round(float(pls.sum()), 2),
               min_balance=round(float(bal.min()), 2),
               max_drawdown_pct=round(dd, 2),
               avg_risk_usd=round(float(risks.mean()), 2),
               usd_per_day=round(float(pls.sum()) / DAYS, 2))
    print(f"{label:<46} {out['n']:>5} {out['win_rate']:>6.1f} "
          f"{out['profit_factor']:>7} {out['net']:>9} {out['min_balance']:>8} "
          f"{out['max_drawdown_pct']:>7.1f}% {out['avg_risk_usd']:>8} "
          f"{out['usd_per_day']:>7}")
    return out


def run(m15, idx, atr, ist_hour, confirm, rr, sl_mult, sess, label, results):
    o = np.asarray(m15["open"], float)
    h = np.asarray(m15["high"], float)
    lo_ = np.asarray(m15["low"], float)
    c = np.asarray(m15["close"], float)
    ef, es = _ema(c, 5), _ema(c, 13)

    bull = ef > es
    trades = []
    open_pos = None      # (dir, entry, sl, tp, risk)

    for i in idx:
        if not (np.isfinite(ef[i]) and np.isfinite(es[i]) and np.isfinite(atr[i])):
            continue
        # resolve an open position on THIS bar first (SL checked before TP)
        if open_pos is not None:
            d, entry, sl, tp, risk = open_pos
            hit = None
            if d > 0:
                if lo_[i] <= sl:
                    hit = -(entry - sl)
                elif h[i] >= tp:
                    hit = tp - entry
            else:
                if h[i] >= sl:
                    hit = -(sl - entry)
                elif lo_[i] <= tp:
                    hit = entry - tp
            if hit is not None:
                trades.append((hit - COST_PER_TRADE, risk))
                open_pos = None

        change = bull[i] != bull[i - 1]
        if not change:
            continue
        buy = bull[i] and (c[i] > o[i] if confirm else True)
        sell = (not bull[i]) and (c[i] < o[i] if confirm else True)
        if not (buy or sell):
            continue
        if sess is not None and not (sess[0] <= ist_hour[i] < sess[1]):
            continue

        # invalidation: opposite signal closes the open position at market
        if open_pos is not None:
            d, entry, sl, tp, risk = open_pos
            trades.append((d * (c[i] - entry) - COST_PER_TRADE, risk))
            open_pos = None

        entry = c[i]
        if buy:
            sl = lo_[i] - atr[i] * sl_mult
            risk = entry - sl
            if risk <= 0:
                continue
            open_pos = (1, entry, sl, entry + risk * rr, risk)
        else:
            sl = h[i] + atr[i] * sl_mult
            risk = sl - entry
            if risk <= 0:
                continue
            open_pos = (-1, entry, sl, entry - risk * rr, risk)

    results[label] = summarize(trades, label)


def main():
    import sys
    global DAYS
    start = sys.argv[1] if len(sys.argv) > 2 else HOLDOUT_START
    end = sys.argv[2] if len(sys.argv) > 2 else HOLDOUT_END
    DAYS = max(1, (_ts(end) - _ts(start)) // 86400)

    bars = load_bars("XAUUSDm", timeframes=("M15",))
    m15 = bars.m15
    f = build_features(m15)
    atr, ist_hour = f["atr14"], f["ist_hour"]
    lo, hi = _ts(start), _ts(end)
    idx = np.nonzero((m15["time"] >= lo) & (m15["time"] < hi))[0]
    idx = idx[idx > 1]

    print(f"EMA 5/13 'Buy Sell Signal', {start} -> {end} ({DAYS} days), "
          f"0.01 lot, cost ${COST_PER_TRADE}/trade\n")
    print(f"{'variant':<46} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>8} {'avgRisk':>8} {'$/day':>7}")
    print("-" * 118)

    r = {}
    run(m15, idx, atr, ist_hour, True, 3.0, 0.5, None, "as-written (confirm, R:R 3, SL 0.5xATR)", r)
    run(m15, idx, atr, ist_hour, False, 3.0, 0.5, None, "no candle confirmation", r)
    run(m15, idx, atr, ist_hour, True, 3.0, 0.5, (11.5, 21.5), "as-written, 11:30-21:30 IST", r)
    run(m15, idx, atr, ist_hour, True, 2.0, 0.5, None, "R:R 2.0", r)
    run(m15, idx, atr, ist_hour, True, 1.5, 0.5, None, "R:R 1.5", r)
    run(m15, idx, atr, ist_hour, True, 3.0, 1.0, None, "SL 1.0xATR (wider)", r)
    run(m15, idx, atr, ist_hour, True, 3.0, 1.5, None, "SL 1.5xATR (wider still)", r)

    print()
    print("Benchmark: FVG_NY alone -- n=990 WR 23.5% PF 1.5004 net $1477 "
          "minBal $104.20 maxDD 35.7% $2.93/day")

    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/ema513_test_{start}_{end}.json", "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=2, default=str)
    print("\n--> saved")


if __name__ == "__main__":
    main()
