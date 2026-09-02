"""Honest portfolio combination: run each leg independently at its OWN real
best config (not a compromise), then merge trades chronologically and replay
the shared-account daily-loss-breaker interaction manually. This is what
portfolio_combo_test.py's single-shared-config approach could not test fairly.
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
bars = load_bars("XAUUSDm", timeframes=("M15","M5","M1","D1"))

legs = [
    ("fvg_NY_tight", "XAU-092", (17.5,21.5), 0.5, 2.5),
    ("emastack_LONDON_tight", "XAU-005", (11.5,15.5), 0.75, 3.0),
    ("rangerejection_NY_tight", "XAU-049", (17.5,21.5), 0.75, 2.25),
]

all_trades = []
for name, cid, sess, sl, tp in legs:
    cfg = EngineConfig(symbol="XAUUSDm", starting_balance=105.74, sizing_mode="fixed",
        fixed_lots=0.01, dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
        enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
        history_bars=900, warmup_bars=950, daily_loss_limit_mode="off",  # replay breaker manually below
        tp_atr_mult=tp, sl_atr_mult_override=sl)
    strat = TightStopStrategy(name, hash(name) % 9000, lib[cid].rule, sess)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([strat], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
    for t in res.trades:
        all_trades.append((t.entry_time, t.exit_time, name, t.net_pl))
    print(f"{name}: {len(res.trades)} trades at its own real config (isolated, breaker off)")

all_trades.sort(key=lambda x: x[1])  # replay in exit-time order

# Replay with ONE shared account and the real 6% daily breaker, IST calendar day
START_BAL = 105.74
IST_OFFSET = 5.5 * 3600
balance = START_BAL
min_bal = START_BAL
peak = START_BAL
max_dd = 0.0
daily_pl = {}
daily_start_bal = {}
shutdown_days = set()
kept = []
blocked = 0

for entry_ts, exit_ts, name, pl in all_trades:
    day = datetime.fromtimestamp(entry_ts + IST_OFFSET, tz=timezone.utc).date()
    if day not in daily_start_bal:
        daily_start_bal[day] = balance
    if day in shutdown_days:
        blocked += 1
        continue
    balance += pl
    min_bal = min(min_bal, balance)
    peak = max(peak, balance)
    max_dd = max(max_dd, (peak - balance) / peak * 100 if peak > 0 else 0)
    daily_pl[day] = daily_pl.get(day, 0.0) + pl
    kept.append((entry_ts, name, pl, balance))
    if daily_pl[day] < -0.06 * daily_start_bal[day]:
        shutdown_days.add(day)

net = np.array([k[2] for k in kept])
wins, losses = net[net>0], net[net<0]
pf = wins.sum()/-losses.sum() if len(losses) else float("inf")
print()
print(f"MERGED PORTFOLIO (each leg's own real config, shared account, real daily breaker):")
print(f"  trades kept={len(kept)} blocked_by_breaker={blocked}")
print(f"  WR={len(wins)/len(net)*100:.1f}% PF={pf:.3f} net=${net.sum():.0f} "
      f"min_bal=${min_bal:.0f} max_dd={max_dd:.1f}% end_bal=${balance:.2f}")
print(f"  days with breach: {len(shutdown_days)} / {len(daily_pl)} trading days")
