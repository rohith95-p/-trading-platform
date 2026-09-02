"""Path-to-$20/day modeling, leaner version. Reruns portfolio_v4's 4 legs at
3 fixed lot sizes (0.01 baseline, 0.02, 0.05) to check linearity + margin
binding, then saves the 0.01-lot trade sequence for step-up simulation.
Unbuffered output (-u) so progress is visible while running.
"""
import sys
import json
import time
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy


def _ts(d):
    return int(datetime.strptime(d, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())


def log(*a):
    print(*a)
    sys.stdout.flush()


lib = {c.id: c for c in build_library()}
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
log("bars loaded")

LEGS = [
    ("squeeze_ASIA", "XAU-062", (2.5, 11.5), 2.0, 4.0),
    ("emastack_LONDON_tight", "XAU-005", (11.5, 15.5), 0.75, 3.0),
    ("fvg_NY_tight", "XAU-092", (17.5, 21.5), 0.5, 2.5),
    ("rangerejection_NY_tight", "XAU-049", (17.5, 21.5), 0.75, 2.25),
]
START_BAL = 105.74
IST_OFFSET = 5.5 * 3600


def run_legs(fixed_lots):
    all_trades = []
    diag_totals = {"entries_blocked_margin": 0}
    for name, cid, sess, sl, tp in LEGS:
        t0 = time.time()
        cfg = EngineConfig(symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed",
                            fixed_lots=fixed_lots, dedup_per_candle=True, max_concurrent=1,
                            max_same_direction=1, enable_pyramiding=False,
                            enable_consolidation_exit=False, enable_trailing=False,
                            history_bars=900, warmup_bars=950, daily_loss_limit_mode="off",
                            tp_atr_mult=tp, sl_atr_mult_override=sl)
        strat = TightStopStrategy(name, hash(name) % 9000, lib[cid].rule, sess)
        eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        res = eng.run([strat], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
        diag_totals["entries_blocked_margin"] += res.diagnostics.get("entries_blocked_margin", 0)
        for t in res.trades:
            all_trades.append((t.entry_time, t.exit_time, name, t.net_pl, t.lots))
        log(f"  leg {name} lots={fixed_lots}: {len(res.trades)} trades, "
            f"{time.time()-t0:.1f}s, margin_blocked={res.diagnostics.get('entries_blocked_margin', 0)}")
    all_trades.sort(key=lambda x: x[1])
    return all_trades, diag_totals


def replay_shared_account(all_trades, start_bal=START_BAL):
    balance = start_bal
    min_bal = start_bal
    peak = start_bal
    max_dd = 0.0
    daily_pl, daily_start_bal = {}, {}
    shutdown_days = set()
    kept = []
    blocked = 0
    for entry_ts, exit_ts, name, pl, lots in all_trades:
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
        kept.append((entry_ts, exit_ts, name, pl, balance, day))
        if daily_pl[day] < -0.06 * daily_start_bal[day]:
            shutdown_days.add(day)
    net = np.array([k[3] for k in kept])
    wins, losses = net[net > 0], net[net < 0]
    pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
    n_days = len(daily_pl)
    span_days = (max(daily_pl.keys()) - min(daily_pl.keys())).days + 1 if daily_pl else 0
    return {
        "trades_kept": len(kept), "blocked_by_breaker": blocked,
        "wr_pct": float(len(wins) / len(net) * 100) if len(net) else 0.0,
        "pf": float(pf), "net": float(net.sum()),
        "min_bal": float(min_bal), "max_dd_pct": float(max_dd),
        "end_bal": float(balance), "n_trading_days": n_days,
        "calendar_span_days": span_days,
        "per_day_avg": float(net.sum() / span_days) if span_days else 0.0,
        "breach_days": len(shutdown_days),
        "kept": kept,
    }


log("=" * 70)
log("Lot-size sweep: 0.01 (base), 0.02, 0.05")
log("=" * 70)
sweep_results = {}
base_kept = None
for lots in (0.01, 0.02, 0.05):
    trades, diag = run_legs(lots)
    rep = replay_shared_account(trades, start_bal=START_BAL)
    sweep_results[lots] = {
        "net": rep["net"], "pf": rep["pf"], "max_dd_pct": rep["max_dd_pct"],
        "min_bal": rep["min_bal"], "trades_kept": rep["trades_kept"],
        "blocked_by_breaker": rep["blocked_by_breaker"],
        "entries_blocked_margin": diag["entries_blocked_margin"],
        "per_day_avg": rep["per_day_avg"], "wr_pct": rep["wr_pct"],
        "calendar_span_days": rep["calendar_span_days"],
    }
    log(f"lots={lots:.2f}  net=${rep['net']:.2f}  pf={rep['pf']:.3f}  "
        f"max_dd={rep['max_dd_pct']:.1f}%  min_bal=${rep['min_bal']:.2f}  "
        f"trades={rep['trades_kept']}  breach_blocked={rep['blocked_by_breaker']}  "
        f"margin_blocked={diag['entries_blocked_margin']}  $/day={rep['per_day_avg']:.2f}")
    if lots == 0.01:
        base_kept = rep["kept"]

with open("scratch_sweep.json", "w") as f:
    json.dump(sweep_results, f, indent=2, default=str)
log("saved scratch_sweep.json")

kept_serializable = [
    {"entry_ts": e, "exit_ts": x, "leg": n, "pl_001": pl, "day": str(d)}
    for (e, x, n, pl, bal, d) in base_kept
]
with open("scratch_base_trades.json", "w") as f:
    json.dump(kept_serializable, f, indent=2)
log(f"saved scratch_base_trades.json ({len(kept_serializable)} trades)")
log("DONE")
