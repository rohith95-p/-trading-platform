"""Direction-gate A/B: does BigBeluga M15 structure trend beat the D1 EMA20 gate?

Context: on 2026-09-02 the D1 EMA20 gate stayed BEARISH all day and blocked every
long through the entire NY reversal. The M15 structure trend flipped BULL at
17:15 -- right as the reversal started. This tests whether a structure-based gate
would actually have helped over the 100-day window, or just added noise.

All 4 portfolio_v4 legs, one shared account, frozen exit config.

    python -m scripts.direction_gate_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2026-05-21", "2026-08-29", 105.74

VARIANTS = [
    ("D1 EMA20  (current live)",     True,  "d1_ema20"),
    ("D1 EMA10  (faster daily)",     True,  "d1_ema10"),
    ("M15 structure trend (len 10)", True,  "structure"),
    ("D1 EMA20 AND structure agree", True,  "both"),
    ("no gate (both directions)",    False, "d1_ema20"),
]

print(f"{START} -> {END} | ${BAL} | 0.01 lots | realistic | 6% breaker | fixed per-leg TP\n")

for label, gate_on, mode in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=gate_on, direction_gate=mode,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))

    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:32s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    blocked = res.diag.get("entries_blocked_d1_bias", "?") if hasattr(res, "diag") else "?"
    print(f"{label:32s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  DD={dd:5.1f}%  blocked={blocked}")
