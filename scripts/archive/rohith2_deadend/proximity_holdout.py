"""Holdout check for the one gate refinement that survived the in-sample screen:
d1_proximity k=0.3 vs the current d1_ema20 gate.

In-sample (100 days, M1): proximity k=0.3 was near-neutral (PF 1.42 vs 1.48,
DD +1.6pp) and caught +36 transition-zone trades. This runs the same A/B on the
OUT-OF-SAMPLE period 2022-06-07 -> 2026-05-20 (~4 years) at M15 fidelity -- no
M1 for that range, so fills are coarser, but the *direction* of the comparison
is what matters.

    python -m scripts.proximity_holdout
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
HOLD_START, HOLD_END, BAL = "2022-06-15", "2026-05-19", 105.74

VARIANTS = [
    ("d1_ema20  (current gate)",   dict(direction_gate="d1_ema20")),
    ("d1_proximity  k=0.3",        dict(direction_gate="d1_proximity", gate_prox_atr=0.3)),
    ("d1_proximity  k=0.5",        dict(direction_gate="d1_proximity", gate_prox_atr=0.5)),
]

print(f"HOLDOUT {HOLD_START} -> {HOLD_END} | M15 fidelity (no M1) | ${BAL} | 0.01 | 4 legs\n")

for label, extra in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, **extra,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(HOLD_START), end_ts=_ts(HOLD_END))
    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:26s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{label:26s}  n={len(pl):5d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():9.2f}  minBal=${bal.min():8.2f}  DD={dd:5.1f}%")
