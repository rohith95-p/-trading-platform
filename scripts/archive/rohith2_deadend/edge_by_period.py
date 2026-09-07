"""LOOP iteration 3 -- does portfolio_v4 have an edge in ANY period, or was the
2026-05..08 selection window a one-off?

Runs the FROZEN config (d1_ema20, fixed TP, no trail, 4 legs, 0.01 lots) on
consecutive ~6-month chunks across all available M15 history. If PF is < 1 in
every chunk except the selection window, the edge is an artifact. If it clears
1.2 in several independent chunks, there is something real to salvage.

    python -m scripts.edge_by_period
"""
from datetime import datetime, timezone, timedelta
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
BAL = 105.74

# 6-month chunks from mid-2022 to the selection window
CHUNKS = [
    ("2022-07-01", "2023-01-01"),
    ("2023-01-01", "2023-07-01"),
    ("2023-07-01", "2024-01-01"),
    ("2024-01-01", "2024-07-01"),
    ("2024-07-01", "2025-01-01"),
    ("2025-01-01", "2025-07-01"),
    ("2025-07-01", "2026-01-01"),
    ("2026-01-01", "2026-05-21"),
    ("2026-05-21", "2026-08-29"),   # THE SELECTION WINDOW
]

print("portfolio_v4 FROZEN config, per 6-month chunk (M15 fidelity)\n")
print(f"{'period':<24} {'trades':>7} {'WR':>6} {'PF':>7} {'net$':>9} {'maxDD%':>7}")
print("-" * 66)

for a, b in CHUNKS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, direction_gate="d1_ema20",
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(a), end_ts=_ts(b))
    pl = np.array([t.net_pl for t in res.trades])
    tag = "  <- SELECTION WINDOW" if a == "2026-05-21" else ""
    if not len(pl):
        print(f"{a}..{b[5:]:<14} {'0':>7}{tag}")
        continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else 99.0
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{a}..{b[5:]:<14} {len(pl):>7} {len(w)/len(pl)*100:>5.1f}% {pf:>7.3f} "
          f"{pl.sum():>9.2f} {dd:>6.1f}%{tag}")
