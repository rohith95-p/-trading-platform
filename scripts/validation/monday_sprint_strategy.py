"""Backtest the Monday Battle Plan's ACTUAL proposed entry rule.

The earlier analysis (MONDAY_PLAN_ANALYSIS_2026-09-06.md) tested the plan's
sprint *mechanics* -- the $30 target / $20 halt barriers -- against 355 real
days, and found it hits the halt more often than the target. What it did NOT
test was the plan's proposed entry logic itself, because that logic is a new
hybrid that exists nowhere in the codebase. This closes that gap.

Implemented exactly as the plan's pseudocode specifies:
  session   11:30-21:30 IST
  trend     EMA20 > EMA50 > EMA200 (buys) / EMA20 < EMA50 < EMA200 (sells)
  trigger   rejection wick where wick > (wick + body) * 0.60, and the candle
            reaches the EMA50 (low <= ema50 for buys, high >= ema50 for sells)
  stops     SL 0.75x ATR, TP 3.0x ATR

NOTE ON AN INCONSISTENCY IN THE PLAN: its prose says "wait for a pullback to
the EMA 20", but its pseudocode tests `last_candle.low <= ema50`. Those are
different rules. The pseudocode is the executable spec, so that is what is
implemented here; the EMA20 variant is also run for completeness.

    python -m scripts.validation.monday_sprint_strategy
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.market_study import build_features, session_mask
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)

SESSION = (11.5, 21.5)          # owner's window
WICK_FRAC = 0.60
SIMS = 10000
DAYS = 505


class MondaySprint(BaseStrategy):
    """The plan's rule, as written in its pseudocode."""
    name = "MONDAY_SPRINT"
    magic = 3099
    session = SESSION
    sl_atr_mult = 0.75
    tp_atr_mult = 3.0
    execute_immediately = True
    edge_trigger = False
    _min_bars = 250
    pullback_ref = "ema50"      # or "ema20" for the prose variant

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        i = -2                                   # last closed bar
        if not bool(session_mask(f["ist_hour"], self.session)[i]):
            return None

        e20, e50, e200 = f["ema20"][i], f["ema50"][i], f["ema200"][i]
        if not np.isfinite([e20, e50, e200]).all():
            return None
        bull = e20 > e50 > e200
        bear = e20 < e50 < e200
        if not (bull or bear):
            return None

        o, h, l, c = (float(f["open"][i]), float(f["high"][i]),
                      float(f["low"][i]), float(f["close"][i]))
        body = abs(c - o)
        upper = h - max(c, o)
        lower = min(c, o) - l
        ref = e50 if self.pullback_ref == "ema50" else e20

        if bull:
            # lower wick rejects the reference EMA from below
            if (lower + body) <= 0 or lower <= (lower + body) * WICK_FRAC:
                return None
            if not (l <= ref):
                return None
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)

        if (upper + body) <= 0 or upper <= (upper + body) * WICK_FRAC:
            return None
        if not (h >= ref):
            return None
        return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                      magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


def mc(pl: np.ndarray) -> dict:
    if len(pl) < 2:
        return {}
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((SIMS, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    return dict(p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2),
                maxdd_p95=round(float(np.percentile(dd, 95)), 1))


def main():
    bars = _bars()
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    out = {}
    print(f"Monday Sprint entry rule, holdout {HOLDOUT_START} -> {HOLDOUT_END}, "
          f"1 position, 0.01 lot\n")
    print(f"{'variant':<28} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>7} {'$/day':>7} {'P(ruin)':>8} {'I.1':>5}")
    print("-" * 100)

    for ref in ("ema50", "ema20"):
        strat = MondaySprint()
        strat.pullback_ref = ref
        res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, [strat])
        s = stats(res.trades)
        v = verdict(s)
        pl = np.array([t.net_pl for t in res.trades])
        m = mc(pl)
        s["usd_per_day"] = round(s.get("net", 0) / DAYS, 2) if s.get("n") else 0.0
        out[ref] = dict(stats=s, verdict=v, montecarlo=m)
        label = f"pseudocode ({ref})" if ref == "ema50" else f"prose variant ({ref})"
        print(f"{label:<28} {s.get('n',0):>5} {s.get('win_rate',0):>6.1f} "
              f"{s.get('profit_factor','-'):>7} {s.get('net','-'):>9} "
              f"{s.get('min_balance','-'):>8} {s.get('max_drawdown_pct','-'):>6}% "
              f"{s['usd_per_day']:>7} {m.get('p_ruin_pct','-'):>7}% "
              f"{'PASS' if v['passed'] else 'FAIL':>5}")

    print("\nBenchmark -- the configuration the evidence already favours:")
    print(f"{'FVG_NY alone (HYP-055)':<28} {990:>5} {23.5:>6.1f} {1.5004:>7} "
          f"{1477.18:>9} {104.2:>8} {35.69:>6}% {2.92:>7} {8.59:>7}% {'PASS':>5}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/monday_sprint_strategy.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("\n--> research/validation/monday_sprint_strategy.json")


if __name__ == "__main__":
    main()
