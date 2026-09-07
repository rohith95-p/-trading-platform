"""LuxAlgo Buyside/Sellside Liquidity as a CONTEXT FILTER on FVG_NY.

Owner's framing (correct, and the reason this is worth testing at all): this is
not an execution strategy, it is market context -- does knowing where liquidity
sits improve the quality of trades we already take? Every trend indicator
tested has died here; liquidity/orderflow is the one family with a measured
edge (FVG), so a liquidity-context filter is testing in the right direction.

Two ideas are extracted from the Pine script, both used as filters on the
EXISTING FVG signal, never as triggers:

  1. LIQUIDITY LEVEL SWEEP. The script finds pivot clusters -- 3+ pivot
     highs (or lows) sitting within atr/margin of each other -- and calls the
     level "breached" when price trades through it. The trading idea: a gap
     that forms just AFTER liquidity was swept is a gap created by real
     forced flow (stops being run), not by drift. Tested as: was a level
     breached within the last N bars, in the same direction?

  2. LIQUIDITY VOID. The script's own definition:
         bull = low - high[2] > atr(200)  and  low > high[2]  and  close[1] > high[2]
     That is literally an FVG with a size threshold of ATR(200) -- a
     principled version of the "minimum gap size" idea (V.1) that earlier used
     an arbitrary % of price. Worth testing precisely because the threshold
     comes from the market's own long-run volatility rather than a number
     someone picked.

Run through the real engine (M1 fidelity), not a hand-rolled resolver.

    python -m scripts.validation.liquidity_filter [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import numpy as np

from src.strategies.portfolio_v4 import FVGNYTight
from src.research.market_study import build_features, session_mask
from src.strategies.base_strategy import Signal, mt5
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict, _ts)

SIMS = 10000
PIVOT_LEN = 7          # script default "Detection Length"
LIQ_MARGIN = 10 / 6.9  # script default margin -> atr / liqMar
MIN_CLUSTER = 3        # script requires count > 2


def _atr(high, low, close, period):
    n = len(high)
    tr = np.full(n, np.nan)
    tr[1:] = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
    out = np.full(n, np.nan)
    if n > period:
        out[period] = np.nanmean(tr[1:period + 1])
        for i in range(period + 1, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def liquidity_state(high, low, close, lookback_breach=12):
    """Returns (buy_swept, sell_swept): bool arrays -- was a clustered
    liquidity level breached within the last `lookback_breach` bars.

    Faithful to the script's structure: confirmed pivots (length 7, right
    offset 1), clustered when 3+ sit within atr/margin, breached when price
    trades beyond the cluster band. Strictly backward-looking -- a pivot at
    bar p is only known at p + PIVOT_LEN + 1.
    """
    n = len(high)
    atr10 = _atr(high, low, close, 10)
    ph_idx, pl_idx = [], []
    for i in range(PIVOT_LEN + 1, n - 1):
        w_h = high[i - PIVOT_LEN:i + 2]
        if high[i] == w_h.max() and np.argmax(w_h) == PIVOT_LEN:
            ph_idx.append(i)
        w_l = low[i - PIVOT_LEN:i + 2]
        if low[i] == w_l.min() and np.argmin(w_l) == PIVOT_LEN:
            pl_idx.append(i)

    buy_swept = np.zeros(n, dtype=bool)
    sell_swept = np.zeros(n, dtype=bool)

    def build(pivots, prices, is_buy):
        # confirmed only after PIVOT_LEN+1 bars
        levels = []          # (confirm_bar, band_lo, band_hi)
        for k, p in enumerate(pivots):
            confirm = p + PIVOT_LEN + 1
            if confirm >= n or not np.isfinite(atr10[confirm]):
                continue
            band = atr10[confirm] / LIQ_MARGIN
            cluster = [prices[q] for q in pivots[max(0, k - 20):k + 1]
                       if abs(prices[q] - prices[p]) <= band]
            if len(cluster) >= MIN_CLUSTER:
                mid = float(np.mean([min(cluster), max(cluster)]))
                levels.append((confirm, mid - band, mid + band))
        for confirm, lo_b, hi_b in levels:
            for j in range(confirm, min(confirm + 500, n)):
                if is_buy and high[j] > hi_b:
                    buy_swept[j:min(j + lookback_breach, n)] = True
                    break
                if (not is_buy) and low[j] < lo_b:
                    sell_swept[j:min(j + lookback_breach, n)] = True
                    break

    build(ph_idx, high, True)
    build(pl_idx, low, False)
    return buy_swept, sell_swept


class FVGLiquidity(FVGNYTight):
    """FVG_NY filtered by liquidity context. mode selects which filter."""
    mode = "baseline"
    void_mult = 1.0
    _cache = None

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        i = -2
        if not bool(session_mask(f["ist_hour"], self.session)[i]):
            return None
        hi = np.asarray(f["high"], float)
        lo = np.asarray(f["low"], float)
        cl = np.asarray(f["close"], float)

        h2, l2 = hi[i - 2], lo[i - 2]
        bull = h2 < lo[i]
        bear = l2 > hi[i]
        if not (bull or bear):
            return None

        if self.mode == "void":
            a200 = _atr(hi, lo, cl, 200)[i]
            if not np.isfinite(a200):
                return None
            gap = (lo[i] - h2) if bull else (l2 - hi[i])
            # script also requires close[1] beyond the gap origin
            confirm = (cl[i - 1] > h2) if bull else (cl[i - 1] < l2)
            if gap <= a200 * self.void_mult or not confirm:
                return None
        elif self.mode == "sweep":
            bs, ss = liquidity_state(hi, lo, cl)
            if bull and not bs[i]:
                return None
            if bear and not ss[i]:
                return None
        elif self.mode == "sweep_or_void":
            a200 = _atr(hi, lo, cl, 200)[i]
            gap = (lo[i] - h2) if bull else (l2 - hi[i])
            big = np.isfinite(a200) and gap > a200 * self.void_mult
            bs, ss = liquidity_state(hi, lo, cl)
            swept = bs[i] if bull else ss[i]
            if not (big or swept):
                return None

        return Signal(direction=mt5.ORDER_TYPE_BUY if bull else mt5.ORDER_TYPE_SELL,
                      strategy_name=self.name, magic=self.magic, is_buy=bool(bull))


def mc(pl):
    if len(pl) < 2:
        return float("nan")
    rng = np.random.default_rng(11)
    paths = pl[rng.integers(0, len(pl), size=(SIMS, len(pl)))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    return round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2)


def main():
    start = sys.argv[1] if len(sys.argv) > 2 else HOLDOUT_START
    end = sys.argv[2] if len(sys.argv) > 2 else HOLDOUT_END
    days = max(1, (_ts(end) - _ts(start)) // 86400)
    bars = _bars()
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    results = {}

    print(f"LuxAlgo liquidity as a FILTER on FVG_NY | {start} -> {end} ({days}d) | "
          f"real engine, M1 fidelity\n")
    print(f"{'variant':<40} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>7} {'P(ruin)':>8} {'$/day':>7} {'I.1':>5}")
    print("-" * 114)

    variants = [("baseline FVG (no filter)", "baseline", 1.0),
                ("liquidity VOID (gap > 1.0x ATR200)", "void", 1.0),
                ("liquidity VOID (gap > 0.5x ATR200)", "void", 0.5),
                ("liquidity VOID (gap > 1.5x ATR200)", "void", 1.5),
                ("after liquidity SWEEP", "sweep", 1.0),
                ("sweep OR void", "sweep_or_void", 1.0)]

    for label, mode, vm in variants:
        s_ = FVGLiquidity()
        s_.mode = mode
        s_.void_mult = vm
        res = run_window(bars, cfg, start, end, [s_])
        st = stats(res.trades)
        v = verdict(st)
        pl = np.array([t.net_pl for t in res.trades])
        ruin = mc(pl)
        per_day = round(st.get("net", 0) / days, 2) if st.get("n") else 0.0
        results[label] = dict(stats=st, verdict=v, p_ruin_pct=ruin, usd_per_day=per_day)
        print(f"{label:<40} {st.get('n',0):>5} {st.get('win_rate',0):>6.1f} "
              f"{st.get('profit_factor','-'):>7} {st.get('net','-'):>9} "
              f"{st.get('min_balance','-'):>8} {st.get('max_drawdown_pct','-'):>6}% "
              f"{ruin:>8} {per_day:>7} {'PASS' if v['passed'] else 'FAIL':>5}")

    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/liquidity_filter_{start}_{end}.json", "w",
              encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\n--> saved")


if __name__ == "__main__":
    main()
