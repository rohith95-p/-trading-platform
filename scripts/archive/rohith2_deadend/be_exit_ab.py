"""Breakeven-move exit test.

The user's concern: price runs most of the way to TP, then reverts to the stop
and a near-win becomes a full loss. A ONE-SHOT breakeven move (not continuous
trailing) removes that case without capping the upside.

  baseline        : frozen -- fixed SL/TP only
  be_trigger 1.0  : once MFE reaches 1.0*entry-ATR, stop -> entry + 0.1*ATR (once)
  ...

All 4 legs, one shared account, D1 EMA20 gate.

    python -m scripts.be_exit_ab
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
    ("baseline (fixed SL/TP)",          0.0),
    ("BE move @ 1.0x ATR MFE",          1.0),
    ("BE move @ 1.5x ATR MFE",          1.5),
    ("BE move @ 2.0x ATR MFE",          2.0),
    ("BE move @ 2.5x ATR MFE",          2.5),
]

print(f"{START} -> {END} | ${BAL} | 0.01 | 4 legs + D1 EMA20 | realistic\n")

for label, be in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, direction_gate="d1_ema20",
        be_trigger_atr=be, be_offset_atr=0.1,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))
    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:26s}  NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    be_exits = sum(1 for t in res.trades if getattr(t, "exit_reason", "") in ("SL",) and t.net_pl > -1)
    print(f"{label:26s}  n={len(pl):4d}  WR={len(w)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  DD={dd:5.1f}%  avgL=${l.mean() if len(l) else 0:6.2f}")
