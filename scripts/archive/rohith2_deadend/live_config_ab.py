"""Does the LIVE config (2 concurrent, 2 same-direction, trailing ON,
pyramiding ON) beat the validated one (1/1, both OFF)?

Runs all four portfolio_v4 legs in ONE engine on one shared account -- which is
what the live bot actually does -- instead of the isolated-then-merged approach
portfolio_merge_v4_full.py used. Per-strategy sl/tp multipliers come from the
strategy classes themselves, same as main_loop._execute_signal.

    python -m scripts.live_config_ab
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
    ("VALIDATED   1 pos, no trail, no pyramid", 1, 1, False, False),
    ("LIVE NOW    2 pos, trail ON, pyramid ON", 2, 2, True, True),
    ("trail only  2 pos, trail ON, pyramid off", 2, 2, True, False),
    ("2-pos only  2 pos, no trail, no pyramid", 2, 2, False, False),
    ("1-pos+trail 1 pos, trail ON, no pyramid", 1, 1, True, False),
]

print(f"{START} -> {END} | ${BAL} start | 0.01 lots | realistic costs | 6% daily breaker")
print(f"all 4 legs on ONE shared account (true live simulation)\n")

for label, conc, same, trail, pyr in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=conc, max_same_direction=same,
        enable_pyramiding=pyr, enable_trailing=trail, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))

    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label}:  NO TRADES\n")
        continue
    wins, losses = pl[pl > 0], pl[pl < 0]
    pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    print(f"{label}")
    print(f"   trades={len(pl):4d}  WR={len(wins)/len(pl)*100:5.1f}%  PF={pf:6.3f}  "
          f"net=${pl.sum():8.2f}  end=${bal[-1]:8.2f}  min=${bal.min():7.2f}  maxDD={dd:5.1f}%")
    print()
