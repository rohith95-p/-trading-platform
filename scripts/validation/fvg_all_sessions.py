"""Full-history, all-sessions backtest: does NY actually stand out, or was
that an arbitrary inherited choice?

Two stages:
  1. BASELINE FVG (candidate_id XAU-092, sl=0.5xATR/tp=2.5xATR -- FVGNYTight's
     own tight-risk config, unchanged) run separately in EVERY session, over
     the FULL available history (2022-08-01 -> 2026-09-04, leaving warmup
     buffer from the data's actual start of 2022-06-13). This answers "which
     session does this edge actually live in" from scratch, not by assumption.
  2. The liquidity-filter variants (sweep / void / sweep_or_void), run on
     whichever session(s) show a real baseline edge in stage 1 -- over the
     SAME full history. This is the real out-of-sample check for last
     session's finding: it was discovered on 2025-2026 only; this tests it
     against 2022-2024, which it has never seen.

Run through the real engine (M1 fidelity where available, M15 fallback
otherwise -- same convention as every other holdout test this session).

    python -m scripts.validation.fvg_all_sessions
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
    START_BAL, live_config, run_window, _bars, stats, verdict, _ts)
from scripts.validation.liquidity_filter import liquidity_state, _atr as _atr_local

# Owner decision (2026-09-06, reaffirmed 2026-09-07): 2-year standard, not
# 4-year. Same holdout window used throughout this session -- excludes the
# 2026-05-21..08-29 selection window so the strategy isn't scored on its own
# training data.
FULL_START, FULL_END = "2025-01-01", "2026-05-20"
DAYS_FULL = max(1, (_ts(FULL_END) - _ts(FULL_START)) // 86400)

SESSIONS = {
    "ASIA (02:30-11:30)": (2.5, 11.5),
    "LONDON (11:30-15:30)": (11.5, 15.5),
    "OVERLAP (15:30-17:30)": (15.5, 17.5),
    "NY (17:30-21:30)": (17.5, 21.5),
    "LATE (21:30-02:30)": (21.5, 26.5),
    "ALL DAY (no session gate)": (0.0, 24.0),
}

SIMS = 10000


class FVGSession(FVGNYTight):
    """FVG_NY's exact rule/stops, session made configurable."""
    session = (0.0, 24.0)


class FVGSessionLiquidity(FVGSession):
    mode = "baseline"
    void_mult = 1.0

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
            a200 = _atr_local(hi, lo, cl, 200)[i]
            if not np.isfinite(a200):
                return None
            gap = (lo[i] - h2) if bull else (l2 - hi[i])
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
            a200 = _atr_local(hi, lo, cl, 200)[i]
            gap = (lo[i] - h2) if bull else (l2 - hi[i])
            big = np.isfinite(a200) and gap > a200 * self.void_mult
            bs, ss = liquidity_state(hi, lo, cl)
            swept = bs[i] if bull else ss[i]
            if not (big or swept):
                return None

        return Signal(direction=mt5.ORDER_TYPE_BUY if bull else mt5.ORDER_TYPE_SELL,
                      strategy_name=self.name, magic=self.magic, is_buy=bool(bull))


def mc_ruin(pl: np.ndarray) -> float:
    if len(pl) < 2:
        return float("nan")
    rng = np.random.default_rng(11)
    paths = pl[rng.integers(0, len(pl), size=(SIMS, len(pl)))]
    eq = START_BAL + np.cumsum(paths, axis=1)
    return round(float((eq <= START_BAL * 0.20).any(axis=1).mean() * 100), 2)


def run_one(bars, cfg, strat, start, end, days, label, results, trade_log=None):
    res = run_window(bars, cfg, start, end, [strat])
    st = stats(res.trades)
    v = verdict(st)
    pl = np.array([t.net_pl for t in res.trades])
    ruin = mc_ruin(pl)
    per_day = round(st.get("net", 0) / days, 2) if st.get("n") else 0.0
    results[label] = dict(stats=st, verdict=v, p_ruin_pct=ruin, usd_per_day=per_day)
    print(f"{label:<40} {st.get('n',0):>5} {st.get('win_rate',0):>6.1f} "
          f"{st.get('profit_factor','-'):>7} {st.get('net','-'):>9} "
          f"{st.get('min_balance','-'):>9} {st.get('max_drawdown_pct','-'):>7}% "
          f"{ruin:>8} {per_day:>7} {'PASS' if v['passed'] else 'FAIL':>5}")
    if trade_log is not None:
        for t in sorted(res.trades, key=lambda x: x.entry_time):
            trade_log.append(dict(
                session=label, entry_time=t.entry_time, exit_time=t.exit_time,
                is_buy=t.is_buy, entry_price=t.entry_price, exit_price=t.exit_price,
                net_pl=round(t.net_pl, 2), r_multiple=round(t.r_multiple, 3)))
    return results[label]


def main():
    bars = _bars()
    cfg = live_config(max_concurrent=1, max_same_direction=1)
    all_results = {}
    trade_log = []

    print(f"STAGE 1 -- baseline FVG (no filter), every session, FULL history "
          f"{FULL_START} -> {FULL_END} ({DAYS_FULL}d)\n")
    print(f"{'session':<40} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>8} {'P(ruin)':>8} {'$/day':>7} {'I.1':>5}")
    print("-" * 116)
    stage1 = {}
    for label, sess in SESSIONS.items():
        s_ = FVGSession()
        s_.session = sess
        run_one(bars, cfg, s_, FULL_START, FULL_END, DAYS_FULL,
               f"baseline: {label}", stage1, trade_log)
    all_results["stage1_baseline_all_sessions"] = stage1

    # Which sessions show a real, tradeable edge worth taking further?
    candidates = [(label, sess) for label, sess in SESSIONS.items()
                  if stage1[f"baseline: {label}"]["stats"].get("n", 0) >= 100
                  and (stage1[f"baseline: {label}"]["stats"].get("profit_factor") or 0) > 1.0]
    print(f"\nSessions clearing n>=100 and PF>1.0 on full history: "
          f"{[c[0] for c in candidates] or 'NONE'}")

    print(f"\nSTAGE 2 -- liquidity filter variants, on sessions that showed an edge, "
          f"full history\n")
    print(f"{'variant':<40} {'n':>5} {'WR%':>6} {'PF':>7} {'net$':>9} "
          f"{'minBal':>9} {'maxDD':>8} {'P(ruin)':>8} {'$/day':>7} {'I.1':>5}")
    print("-" * 116)
    stage2 = {}
    for sess_label, sess in candidates:
        for mode, vm, mode_label in [("baseline", 1.0, "no filter"),
                                     ("sweep", 1.0, "liquidity sweep"),
                                     ("void", 0.5, "void >0.5xATR200"),
                                     ("sweep_or_void", 0.5, "sweep OR void")]:
            s_ = FVGSessionLiquidity()
            s_.session = sess
            s_.mode = mode
            s_.void_mult = vm
            run_one(bars, cfg, s_, FULL_START, FULL_END, DAYS_FULL,
                   f"{sess_label} | {mode_label}", stage2, trade_log)
    all_results["stage2_liquidity_by_session"] = stage2

    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/fvg_all_sessions.json", "w", encoding="utf-8") as fh:
        json.dump(all_results, fh, indent=2, default=str)
    with open("research/validation/fvg_all_sessions_trades.json", "w", encoding="utf-8") as fh:
        json.dump(trade_log, fh, indent=2, default=str)
    print(f"\n{len(trade_log)} total trades logged.")
    print("--> research/validation/fvg_all_sessions.json (+ _trades.json)")


if __name__ == "__main__":
    main()
