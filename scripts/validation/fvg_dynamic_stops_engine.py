"""Dynamic stop placement for FVG_NY -- run through the REAL engine.

Supersedes fvg_dynamic_stops.py, which was invalid: it resolved trades on M15
high/low and assumed SL-before-TP whenever a bar straddled both levels. With a
~$4.34 stop against M15 bars that routinely range $9+, that assumption turned
real winners into losses wholesale -- its "current baseline" came out at
PF 0.56 / -$3,080 where the engine gives PF 1.5004 / +$1,477 for the identical
strategy and window. The engine walks M1 sub-bars for exactly this reason
(COR-001). Lesson kept, harness discarded.

Here each scheme is a strategy subclass that sets its OWN sl_atr_mult (and a
matching tp_atr_mult) on each signal, which the engine then reads per-trade --
so stop placement is genuinely dynamic while fills stay M1-accurate.

Schemes (signal identical throughout; only the stop moves):
  A  static 0.5x ATR                 -- current live behaviour
  B  static 0.75 / 1.0 / 1.25x ATR   -- "just bigger", for reference
  C  structure: beyond the gap's own fill level (setup objectively dead there)
  D  noise-floor aware: at least k x rolling median true range
  E  gap-proportional: k x the gap that created the signal
  F  regime adaptive: multiplier keyed to ATR's own recent percentile

    python -m scripts.validation.fvg_dynamic_stops_engine [start] [end]
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import numpy as np

from src.strategies.portfolio_v4 import FVGNYTight
from src.research.market_study import build_features, session_mask
from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, START_BAL, live_config, run_window, _bars,
    stats, verdict)

SIMS = 10000
RR = 5.0          # TP = 5x whatever the stop turns out to be (current R:R)
MIN_MULT, MAX_MULT = 0.2, 3.0


def _clamp(x):
    return float(min(max(x, MIN_MULT), MAX_MULT))


class DynamicFVG(FVGNYTight):
    """FVG_NY with a per-signal stop multiplier. `scheme` picks the rule."""
    scheme = ("static", 0.5)

    def evaluate(self, m15_rates, m5_rates: Optional[np.ndarray] = None):
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        i = -2
        if not bool(session_mask(f["ist_hour"], self.session)[i]):
            return None

        hi, lo, cl = f["high"], f["low"], f["close"]
        a = float(f["atr14"][i])
        if not np.isfinite(a) or a <= 0:
            return None

        h2, l2 = float(hi[i - 2]), float(lo[i - 2])
        bull = h2 < float(lo[i])
        bear = l2 > float(hi[i])
        if not (bull or bear):
            return None

        entry = float(cl[i])
        gap = (float(lo[i]) - h2) if bull else (l2 - float(hi[i]))
        kind, p = self.scheme

        if kind == "static":
            mult = p
        elif kind == "structure":
            lvl = h2 if bull else l2
            mult = abs(entry - lvl) / a + p
        elif kind == "noise":
            tr = np.maximum(hi[1:] - lo[1:],
                            np.maximum(np.abs(hi[1:] - cl[:-1]), np.abs(lo[1:] - cl[:-1])))
            w = tr[-97:-1]
            w = w[np.isfinite(w)]
            med = float(np.median(w)) if len(w) > 10 else a * 0.5
            mult = max(0.5, p * med / a)
        elif kind == "gap":
            mult = max(p * gap / a, 0.25)
        elif kind == "regime":
            aw = f["atr14"][-481:-1]
            aw = aw[np.isfinite(aw)]
            if len(aw) < 50:
                return None
            q = float((aw < a).mean())
            mult = (1.0 - q) * abs(p) + 0.4 if p > 0 else q * abs(p) + 0.4
        else:
            return None

        # The engine reads these off the strategy when opening the trade.
        self.sl_atr_mult = _clamp(mult)
        self.tp_atr_mult = _clamp(self.sl_atr_mult * RR) if self.sl_atr_mult * RR <= MAX_MULT * RR else self.sl_atr_mult * RR

        from src.strategies.base_strategy import Signal, mt5
        return Signal(direction=mt5.ORDER_TYPE_BUY if bull else mt5.ORDER_TYPE_SELL,
                      strategy_name=self.name, magic=self.magic, is_buy=bool(bull))


def mc(pl: np.ndarray) -> float:
    if len(pl) < 2:
        return float("nan")
    rng = np.random.default_rng(11)
    paths = pl[rng.integers(0, len(pl), size=(SIMS, len(pl)))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    return round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2)


def main():
    start = sys.argv[1] if len(sys.argv) > 2 else HOLDOUT_START
    end = sys.argv[2] if len(sys.argv) > 2 else HOLDOUT_END
    from scripts.validation.part1_suite import _ts
    days = max(1, (_ts(end) - _ts(start)) // 86400)

    bars = _bars()
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    results = {}

    print(f"FVG_NY dynamic stops via REAL engine (M1 fidelity) | {start} -> {end} "
          f"({days}d) | TP = {RR}x stop\n")
    print(f"{'stop scheme':<38} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>8} {'maxDD':>7} {'P(ruin)':>8} {'$/day':>7} {'I.1':>5}")
    print("-" * 112)

    schemes = [("A static 0.5xATR (current)", ("static", 0.5))]
    schemes += [(f"B static {k}xATR", ("static", k)) for k in (0.75, 1.0, 1.25)]
    schemes += [(f"C structure +{b}xATR", ("structure", b)) for b in (0.0, 0.25)]
    schemes += [(f"D noise-floor {k}x medTR", ("noise", k)) for k in (1.0, 1.5)]
    schemes += [(f"E gap-proportional {k}x", ("gap", k)) for k in (1.0, 2.0)]
    schemes += [("F regime (wider-when-calm)", ("regime", 0.8)),
                ("F regime (wider-when-volatile)", ("regime", -0.8))]

    for label, scheme in schemes:
        s_ = DynamicFVG()
        s_.scheme = scheme
        res = run_window(bars, cfg, start, end, [s_])
        st = stats(res.trades)
        v = verdict(st)
        pl = np.array([t.net_pl for t in res.trades])
        ruin = mc(pl)
        per_day = round(st.get("net", 0) / days, 2) if st.get("n") else 0.0
        results[label] = dict(stats=st, verdict=v, p_ruin_pct=ruin, usd_per_day=per_day)
        print(f"{label:<38} {st.get('n',0):>5} {st.get('win_rate',0):>6.1f} "
              f"{st.get('profit_factor','-'):>7} {st.get('net','-'):>9} "
              f"{st.get('min_balance','-'):>8} {st.get('max_drawdown_pct','-'):>6}% "
              f"{ruin:>8} {per_day:>7} {'PASS' if v['passed'] else 'FAIL':>5}")

    os.makedirs("research/validation", exist_ok=True)
    with open(f"research/validation/fvg_dynamic_stops_engine_{start}_{end}.json",
              "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\n--> saved")


if __name__ == "__main__":
    main()
