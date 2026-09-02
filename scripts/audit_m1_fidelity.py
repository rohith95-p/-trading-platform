"""Phase 0 audit: quantify how much the M1 sub-bar walk actually changes results.

The engine falls back to treating a whole M15 bar as one bar when M1 is
absent (engine.py:537-540), resolving ambiguity stop-first. Our M1 cache only
covers 2026-05-20 onward, and last night's tier-2 scripts excluded M1 from
load_bars entirely -- so every number produced then ran at M15 resolution.
This measures the size of that error on the window where M1 does exist.
"""
from __future__ import annotations
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.ema_stack import EMAStack

def _ts(d): return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

CFG = dict(symbol="XAUUSDm", starting_balance=105.74, sizing_mode="fixed", fixed_lots=0.01,
           dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
           enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
           history_bars=900, warmup_bars=950,
           daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06)

for label, tfs in [("WITHOUT M1 (last night's setup)", ("M15","M5","D1")),
                   ("WITH M1 (true sub-bar fidelity)", ("M15","M5","M1","D1"))]:
    bars = load_bars("XAUUSDm", timeframes=tfs)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=EngineConfig(**CFG))
    r = eng.run([EMAStack()], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
    t = r.trades
    if not t:
        print(f"{label}: NO TRADES"); continue
    net = np.array([x.net_pl for x in t]); wins = net[net>0]; losses = net[net<0]
    pf = wins.sum()/-losses.sum() if len(losses) else float('inf')
    amb = sum(1 for x in t if x.intrabar_ambiguous)
    print(f"\n{label}")
    print(f"  trades={len(t)} WR={len(wins)/len(net)*100:.1f}% PF={pf:.3f} "
          f"net=${net.sum():+.2f} end=${t[-1].balance_after:.2f}")
    print(f"  ambiguous trades={amb} ({amb/len(t)*100:.1f}%)  diag_bars_without_m1={r.diagnostics.get('bars_without_m1')}")
