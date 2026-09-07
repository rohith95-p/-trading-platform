"""SMC Institutional Clean Wave & Structure PRO -- two distinct signal
families extracted and tested on their own terms.

  1. BOS/CHoCH STRUCTURE BREAK (trend-following): close crosses above/below
     the last CONFIRMED pivot high/low (smc_sens=7, symmetric left/right --
     confirmed sig_sens bars after the pivot bar, never before). Same family
     as every trend-follower already tested tonight (QQE, EMA5/13, UT Bot) --
     all failed. Prediction: this fails too, for the same measured reason
     (M15 gold autocorrelation ~=0).

  2. SWING REVERSAL (mean-reversion): BUY at a confirmed pivot low, SELL at a
     confirmed pivot high (sig_sens=10) -- fade the extremes rather than
     follow them. Genuinely different family from everything else tested
     tonight. Worth an honest test on its own merits.

Both use ATR stops since the Pine script itself defines none (it's a pure
indicator, no strategy.entry calls). Entries at the M15 close of the bar the
signal is CONFIRMED on (not the historical pivot bar -- that would be
lookahead/repaint). Cost and M15-bar SL/TP resolution match the same
convention used for the other indicator tests tonight (qqe_test.py,
ema513_test.py, utbot_test.py) -- SL checked before TP within a straddled bar.

    python -m scripts.validation.smc_wave_structure_test [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.research.market_study import build_features

START_BAL = 105.74
COST_PER_TRADE = 2.80


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def confirmed_pivots(high, low, sens):
    """ta.pivothigh/pivotlow(sens, sens) -- symmetric, confirmed `sens` bars
    after the pivot bar. Returns (ph_confirm_idx -> pivot_price dict-like
    arrays): ph[i] is the confirmed pivot HIGH value known as of bar i (NaN
    otherwise), same for pl[i]."""
    n = len(high)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for p in range(sens, n - sens):
        confirm = p + sens
        if confirm >= n:
            continue
        window_h = high[p - sens:p + sens + 1]
        if high[p] == window_h.max() and np.argmax(window_h) == sens:
            ph[confirm] = high[p]
        window_l = low[p - sens:p + sens + 1]
        if low[p] == window_l.min() and np.argmin(window_l) == sens:
            pl[confirm] = low[p]
    return ph, pl


def summarize(trades, label, days):
    if len(trades) < 2:
        print(f"{label:<44} {len(trades):>5}  (too few)")
        return dict(n=len(trades))
    pls = np.array([t[0] for t in trades], float)
    w, l = pls[pls > 0], pls[pls < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = START_BAL + np.cumsum(pls)
    peak = np.maximum.accumulate(np.concatenate(([START_BAL], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    out = dict(n=int(len(pls)), win_rate=round(float(len(w) / len(pls) * 100), 1),
               profit_factor=round(pf, 4), net=round(float(pls.sum()), 2),
               min_balance=round(float(bal.min()), 2),
               max_drawdown_pct=round(dd, 1),
               usd_per_day=round(float(pls.sum()) / days, 2))
    print(f"{label:<44} {out['n']:>5} {out['win_rate']:>6.1f} {out['profit_factor']:>7} "
          f"{out['net']:>9} {out['min_balance']:>9} {out['max_drawdown_pct']:>8}% "
          f"{out['usd_per_day']:>7}")
    return out


def resolve(entry_idx, is_buy, high, low, sl_d, tp_d, close):
    e = close[entry_idx]
    sl = e - sl_d if is_buy else e + sl_d
    tp = e + tp_d if is_buy else e - tp_d
    for j in range(entry_idx + 1, min(entry_idx + 97, len(close))):
        if is_buy:
            if low[j] <= sl:
                return -sl_d - COST_PER_TRADE
            if high[j] >= tp:
                return tp_d - COST_PER_TRADE
        else:
            if high[j] >= sl:
                return -sl_d - COST_PER_TRADE
            if low[j] <= tp:
                return tp_d - COST_PER_TRADE
    return None


def run_structure(high, low, close, atr, ist_hour, idx, sens, sl_m, tp_m, sess, days, label, results):
    ph, pl = confirmed_pivots(high, low, sens)
    last_ph = last_pl = np.nan
    trades = []
    for i in idx:
        if not np.isfinite(atr[i]):
            continue
        if np.isfinite(ph[i]):
            last_ph = ph[i]
        if np.isfinite(pl[i]):
            last_pl = pl[i]
        if sess is not None and not (sess[0] <= ist_hour[i] < sess[1]):
            continue
        buy = np.isfinite(last_ph) and close[i - 1] < last_ph <= close[i]
        sell = np.isfinite(last_pl) and close[i - 1] > last_pl >= close[i]
        if not (buy or sell):
            continue
        pl_val = resolve(i, buy, high, low, sl_m * atr[i], tp_m * atr[i], close)
        if pl_val is not None:
            trades.append((pl_val,))
        if buy:
            last_ph = np.nan
        else:
            last_pl = np.nan
    results[label] = summarize(trades, label, days)


def run_reversal(high, low, close, atr, ist_hour, idx, sens, sl_m, tp_m, sess, days, label, results):
    ph, pl = confirmed_pivots(high, low, sens)
    trades = []
    for i in idx:
        if not np.isfinite(atr[i]):
            continue
        if sess is not None and not (sess[0] <= ist_hour[i] < sess[1]):
            continue
        buy = np.isfinite(pl[i])   # confirmed swing low -> fade up (BUY)
        sell = np.isfinite(ph[i])  # confirmed swing high -> fade down (SELL)
        if buy and sell:
            continue  # ambiguous same-bar confirmation, skip
        if not (buy or sell):
            continue
        pl_val = resolve(i, buy, high, low, sl_m * atr[i], tp_m * atr[i], close)
        if pl_val is not None:
            trades.append((pl_val,))
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
    idx = np.nonzero((m15["time"] >= _ts(start)) & (m15["time"] < _ts(end)))[0]
    idx = idx[idx > 20]

    print(f"SMC Wave & Structure PRO, {start} -> {end} ({days}d), 0.01 lot, "
          f"cost ${COST_PER_TRADE}/trade\n")

    print("=== 1. BOS/CHoCH structure break (trend-following, smc_sens=7) ===")
    print(f"{'variant':<44} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>8} {'$/day':>7}")
    print("-" * 100)
    r1 = {}
    run_structure(high, low, close, atr, ist_hour, idx, 7, 0.75, 3.0, None, days,
                 "structure, ATR 0.75x/3.0x, all sessions", r1)
    run_structure(high, low, close, atr, ist_hour, idx, 7, 1.0, 2.0, None, days,
                 "structure, ATR 1.0x/2.0x, all sessions", r1)
    run_structure(high, low, close, atr, ist_hour, idx, 7, 0.75, 3.0, (11.5, 21.5), days,
                 "structure, ATR 0.75x/3.0x, 11:30-21:30", r1)

    print("\n=== 2. Swing reversal (mean-reversion, sig_sens=10) ===")
    print(f"{'variant':<44} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>8} {'$/day':>7}")
    print("-" * 100)
    r2 = {}
    run_reversal(high, low, close, atr, ist_hour, idx, 10, 0.75, 3.0, None, days,
                "reversal, ATR 0.75x/3.0x, all sessions", r2)
    run_reversal(high, low, close, atr, ist_hour, idx, 10, 1.0, 1.0, None, days,
                "reversal, ATR 1.0x/1.0x, all sessions", r2)
    run_reversal(high, low, close, atr, ist_hour, idx, 10, 0.5, 1.5, None, days,
                "reversal, ATR 0.5x/1.5x, all sessions", r2)
    run_reversal(high, low, close, atr, ist_hour, idx, 10, 0.75, 3.0, (11.5, 21.5), days,
                "reversal, ATR 0.75x/3.0x, 11:30-21:30", r2)
    run_reversal(high, low, close, atr, ist_hour, idx, 5, 0.75, 3.0, None, days,
                "reversal, sens=5, ATR 0.75x/3.0x, all sessions", r2)

    print("\nBenchmark: FVG_NY_TIGHT alone -- PF 1.5004, +$1,477, maxDD 35.7%")
    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/smc_wave_structure_{start}_{end}.json", "w",
              encoding="utf-8") as fh:
        json.dump(dict(structure=r1, reversal=r2), fh, indent=2, default=str)
    print("--> saved")


if __name__ == "__main__":
    main()
