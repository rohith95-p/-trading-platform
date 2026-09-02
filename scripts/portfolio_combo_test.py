"""Task 1: does combining the best validated strategy from each non-overlapping
session into one real portfolio close any of the gap to $20/day? Tested as one
actual engine.run() call (not summed separately) so the shared daily breaker,
shared account balance, and margin all interact realistically.
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy

def _ts(d): return int(datetime.strptime(d,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
lib = {c.id: c for c in build_library()}

legs = [
    ("squeeze_ASIA", lib["XAU-062"].rule, (2.5, 11.5), 2.0, 4.0, 4001),
    ("emastack_LONDON", lib["XAU-005"].rule, (11.5, 15.5), 1.5, 2.0, 4002),
    ("fvg_NY", lib["XAU-092"].rule, (17.5, 21.5), 0.5, 1.5, 4003),
]

class Leg(TightStopStrategy):
    def __init__(self, name, rule, sess, magic):
        super().__init__(name, magic, rule, sess)

strategies = [Leg(n, r, s, m) for (n, r, s, sl, tp, m) in legs]
# tp/sl differ per leg but EngineConfig is global -- run each leg's window
# through its OWN tp/sl by patching per-candle isn't possible with one shared
# config, so this proves the SESSION-additivity/breaker-interaction question
# using each leg's own dedicated single-strategy run compared to a shared-
# account sequential simulation instead.
print("NOTE: EngineConfig's tp/sl are global, so a true single mixed-tp/sl")
print("multi-strategy run needs per-leg config, not supported by this engine")
print("as built. Testing shared-account sequential interaction another way:")
print()

# Simulate shared-account interaction properly: run all three sequentially
# over the SAME balance, session-gated, using the best common tp/sl compromise
# isn't honest either. Instead: run the whole window with all three sessions'
# entries pooled under ONE tp/sl (the closest shared config) to see true
# daily-breaker interaction, then report separately what the isolated per-leg
# numbers already showed for context.
cfg = EngineConfig(symbol="XAUUSDm", starting_balance=105.74, sizing_mode="fixed",
    fixed_lots=0.01, dedup_per_candle=True, max_concurrent=3, max_same_direction=3,
    enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
    history_bars=900, warmup_bars=950, daily_loss_limit_mode="balance_pct",
    daily_loss_limit_pct=0.06, tp_atr_mult=2.5, sl_atr_mult_override=1.2)

bars = load_bars("XAUUSDm", timeframes=("M15","M5","M1","D1"))
eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
res = eng.run(strategies, start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
t = res.trades
if not t:
    print("NO TRADES"); raise SystemExit
net = np.array([x.net_pl for x in t])
wins, losses = net[net>0], net[net<0]
pf = wins.sum()/-losses.sum() if len(losses) else float("inf")
bal = np.concatenate([[105.74],[x.balance_after for x in t]])
print(f"COMBINED PORTFOLIO (shared account, all 3 sessions, common tp=2.5/sl=1.2 compromise):")
print(f"  trades={len(t)} WR={len(wins)/len(net)*100:.1f}% PF={pf:.3f} net=${net.sum():.0f} "
      f"min_bal=${bal.min():.0f} end_bal=${bal[-1]:.0f}")
by_strat = {}
for x in t:
    by_strat.setdefault(x.strategy, []).append(x.net_pl)
for name, pls in by_strat.items():
    print(f"    {name}: n={len(pls)} net=${sum(pls):.0f}")
