"""Exit A/B: current fixed TP vs a wide ATR trailing stop (BigBeluga-style).

The 0.7/0.3xATR trail was removed for strangling winners. This tests the other
extreme -- a wide "only exit on a real structure failure" trail -- against the
frozen fixed-TP config. All 4 portfolio_v4 legs on one shared account.

    python -m scripts.exit_trail_ab
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

# (label, enable_trailing, trail_activation_atr, trail_distance_atr, tp_atr_mult)
# tp_atr_mult=None keeps each leg's own TP; a big number effectively disables it
# so the trail is the only exit (BigBeluga has no fixed TP).
VARIANTS = [
    ("FROZEN     fixed per-leg TP, no trail",      False, None, None, None),
    ("trail 2.0x + keep per-leg TP",               True,  1.0,  2.0,  None),
    ("trail 3.0x + keep per-leg TP",               True,  1.0,  3.0,  None),
    ("trail 4.0x + keep per-leg TP",               True,  1.0,  4.0,  None),
    ("trail 3.0x, NO fixed TP (pure BigBeluga)",   True,  0.5,  3.0,  20.0),
    ("trail 4.0x, NO fixed TP (pure BigBeluga)",   True,  0.5,  4.0,  20.0),
]

print(f"{START} -> {END} | ${BAL} start | 0.01 lots | realistic costs | 6% breaker | D1 gate")
print("all 4 legs, one shared account\n")

for label, trail, act, dist, tp in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_consolidation_exit=False,
        enable_trailing=trail, trail_activation_atr=act, trail_distance_atr=dist,
        tp_atr_mult=tp,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))

    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:44s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    avg_w = w.mean() if len(w) else 0
    avg_l = l.mean() if len(l) else 0
    print(f"{label:44s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  DD={dd:5.1f}%  avgW=${avg_w:6.2f}  avgL=${avg_l:6.2f}")
