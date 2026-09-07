"""Can FVG_NY alone be made survivable on a STANDARD account at $100?

Owner constraint (2026-09-06, restated firmly): Standard account only. No Cent
account. So risk-per-trade cannot go below the 0.01-lot floor, and the only
remaining levers are ones that change WHICH trades are taken, not their size.

Baseline to beat: FVG_NY alone, 1 position, Standard 0.01 lot --
  PF 1.5004, net +$1,477, min balance $104.20, maxDD 35.7%, P(ruin) 8.59%.

Three levers, none of which require a different account type:

  1. V.1 FVG MINIMUM GAP SIZE. Currently `_c_fvg` fires on ANY 3-bar gap, which
     SYSTEM_FAULTS.md called out: "~19 signals/day, mostly noise." The LuxAlgo
     test on 2026-09-03 found a ~$4.4 minimum gap took PF 1.66 -> 2.11 and
     drawdown 28.5% -> 19.6%. Never applied. Tested here as a % of price so it
     scales with gold's level.
  2. DAILY LOSS CAP at 3% (Part II.3's early-phase rule) instead of 6%.
     Truncates the bad tail, which is what drives ruin.
  3. VOLATILITY REGIME FILTER. I.6 found the edge bleeds in mid volatility
     (quintile 2, PF 0.979) and earns in high (q3 1.307, q4 1.264).

    python -m scripts.validation.fvg_standard_hardening
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

from src.strategies.portfolio_v4 import FVGNYTight
from src.research.market_study import build_features, session_mask
from src.strategies.base_strategy import Signal, mt5
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)

SIMS = 10000
DAYS = 505


class FVGFiltered(FVGNYTight):
    """FVG_NY with an optional minimum gap size and volatility-regime filter."""
    min_gap_pct = 0.0        # gap must be >= this % of price
    min_atr_pct = 0.0        # ATR must be >= this % of price (vol-regime floor)

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        i = -2
        if not bool(session_mask(f["ist_hour"], self.session)[i]):
            return None

        hi, lo, close = f["high"], f["low"], f["close"]
        px = float(close[i])
        if px <= 0:
            return None

        if self.min_atr_pct > 0:
            a = float(f["atr14"][i])
            if not np.isfinite(a) or (a / px * 100.0) < self.min_atr_pct:
                return None

        # 3-bar fair value gap, strictly backward (same as _c_fvg)
        h2, l2 = float(hi[i - 2]), float(lo[i - 2])
        bull_gap = float(lo[i]) - h2      # >0 means bullish gap
        bear_gap = l2 - float(hi[i])      # >0 means bearish gap
        need = self.min_gap_pct / 100.0 * px

        if bull_gap > 0 and bull_gap >= need:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        if bear_gap > 0 and bear_gap >= need:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                          magic=self.magic, is_buy=False)
        return None


def mc(pl: np.ndarray) -> dict:
    if len(pl) < 2:
        return dict(p_ruin_pct=None, maxdd_p95=None)
    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(SIMS, n))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((SIMS, 1), START_BAL), eq], axis=1), axis=1)
    dd = ((peak[:, 1:] - eq) / peak[:, 1:]).max(axis=1) * 100
    return dict(p_ruin_pct=round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2),
                maxdd_p95=round(float(np.percentile(dd, 95)), 1),
                p_touch_minus50_pct=round(float((eq <= START_BAL * 0.50).any(axis=1).mean() * 100), 2))


def run(bars, label, gap_pct, atr_pct, daily_cap, rows):
    s_ = FVGFiltered()
    s_.min_gap_pct = gap_pct
    s_.min_atr_pct = atr_pct
    cfg = live_config(max_concurrent=1, max_same_direction=1,
                      daily_loss_limit_pct=daily_cap)
    res = run_window(bars, cfg, HOLDOUT_START, HOLDOUT_END, [s_])
    s = stats(res.trades)
    v = verdict(s)
    m = mc(np.array([t.net_pl for t in res.trades]))
    per_day = round(s.get("net", 0) / DAYS, 2) if s.get("n") else 0.0
    rows.append(dict(label=label, gap_pct=gap_pct, atr_pct=atr_pct,
                     daily_cap=daily_cap, stats=s, verdict=v, mc=m,
                     usd_per_day=per_day))
    print(f"{label:<34} {s.get('n',0):>5} {s.get('profit_factor','-'):>7} "
          f"{s.get('net','-'):>9} {s.get('min_balance','-'):>8} "
          f"{s.get('max_drawdown_pct','-'):>6}% {per_day:>7} "
          f"{str(m.get('p_ruin_pct')):>8} {'PASS' if v['passed'] else 'FAIL':>5}")


def main():
    bars = _bars()
    rows = []
    print(f"FVG_NY alone, STANDARD account 0.01 lot, holdout "
          f"{HOLDOUT_START} -> {HOLDOUT_END}\n")
    print(f"{'variant':<34} {'n':>5} {'PF':>7} {'net$':>9} {'minBal':>8} "
          f"{'maxDD':>7} {'$/day':>7} {'P(ruin)':>8} {'I.1':>5}")
    print("-" * 100)

    run(bars, "baseline (no filters, 6% daily)", 0.0, 0.0, 0.06, rows)
    run(bars, "daily cap 3%", 0.0, 0.0, 0.03, rows)
    for g in (0.02, 0.05, 0.10, 0.15):
        run(bars, f"min gap {g}% of price", g, 0.0, 0.06, rows)
    run(bars, "min gap 0.10% + daily 3%", 0.10, 0.0, 0.03, rows)
    run(bars, "min gap 0.10% + ATR>=0.20%", 0.10, 0.20, 0.06, rows)
    run(bars, "gap 0.10% + ATR 0.20% + 3%", 0.10, 0.20, 0.03, rows)

    best = min((r for r in rows if r["stats"].get("n", 0) >= 100
                and r["mc"].get("p_ruin_pct") is not None),
               key=lambda r: r["mc"]["p_ruin_pct"], default=None)
    print()
    if best:
        print(f"LOWEST RUIN (n>=100): {best['label']}")
        print(f"  PF {best['stats'].get('profit_factor')}, "
              f"P(ruin) {best['mc']['p_ruin_pct']}%, "
              f"maxDD {best['stats'].get('max_drawdown_pct')}%, "
              f"${best['usd_per_day']}/day, "
              f"I.1 {'PASS' if best['verdict']['passed'] else 'FAIL'}")

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/fvg_standard_hardening.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)
    print("\n--> research/validation/fvg_standard_hardening.json")


if __name__ == "__main__":
    main()
