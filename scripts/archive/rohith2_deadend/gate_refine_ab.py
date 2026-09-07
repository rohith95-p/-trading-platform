"""Gate refinements: keep the D1 gate but stop it strangling transition setups.

  d1_ema20     : current live (baseline)
  d1_proximity : allow BOTH directions when D1 close is within k*D1_ATR of the
                 EMA20 (the "macro might be flipping" zone)
  h4_structure : structure trend on H4 bars (faster than D1, less noisy than M15)
  d1_choch     : D1 gate, but a fresh H4 CHoCH in the signal direction overrides
                 the daily block

All 4 legs, one shared account, frozen exit config.

    python -m scripts.gate_refine_ab
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
START, END, BAL = "2026-05-21", "2026-08-29", 105.74

VARIANTS = [
    ("d1_ema20  (BASELINE / live)",        dict(direction_gate="d1_ema20")),
    ("d1_proximity  k=0.3",                dict(direction_gate="d1_proximity", gate_prox_atr=0.3)),
    ("d1_proximity  k=0.5",                dict(direction_gate="d1_proximity", gate_prox_atr=0.5)),
    ("d1_proximity  k=0.75",               dict(direction_gate="d1_proximity", gate_prox_atr=0.75)),
    ("h4_structure  (len 10)",             dict(direction_gate="h4_structure")),
    ("d1_choch  H4 lookback 2",            dict(direction_gate="d1_choch", choch_lookback_h4=2)),
    ("d1_choch  H4 lookback 3",            dict(direction_gate="d1_choch", choch_lookback_h4=3)),
    ("d1_choch  H4 lookback 4",            dict(direction_gate="d1_choch", choch_lookback_h4=4)),
]

print(f"{START} -> {END} | ${BAL} | 0.01 | 4 legs | fixed per-leg TP | realistic\n")

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
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))
    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:30s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{label:30s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  DD={dd:5.1f}%")
