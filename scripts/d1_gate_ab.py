"""A/B: portfolio_v4 with the D1 bias gate ON vs OFF, same 100-day window.

Clones portfolio_merge_v4_full.py exactly (each leg at its own real config,
merged on one shared account with the real 6% IST daily breaker) and runs it
twice -- enable_d1_bias_gate True then False -- so the only thing that changes
is the gate.

    python -m scripts.d1_gate_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


lib = {c.id: c for c in build_library()}
bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))

LEGS = [
    ("squeeze_ASIA", "XAU-062", (2.5, 11.5), 2.0, 4.0),
    ("emastack_LONDON_tight", "XAU-005", (11.5, 15.5), 0.75, 3.0),
    ("fvg_NY_tight", "XAU-092", (17.5, 21.5), 0.5, 2.5),
    ("rangerejection_NY_tight", "XAU-049", (17.5, 21.5), 0.75, 2.25),
]
START = "2026-05-21"
END = "2026-08-29"
START_BAL = 105.74


def run(gate_on: bool):
    all_trades = []
    per_leg = {}
    for name, cid, sess, sl, tp in LEGS:
        cfg = EngineConfig(
            symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed",
            fixed_lots=0.01, dedup_per_candle=True, max_concurrent=1,
            max_same_direction=1, enable_pyramiding=False,
            enable_consolidation_exit=False, enable_trailing=False,
            history_bars=900, warmup_bars=950, daily_loss_limit_mode="off",
            tp_atr_mult=tp, sl_atr_mult_override=sl,
            enable_d1_bias_gate=gate_on,
        )
        strat = TightStopStrategy(name, hash(name) % 9000, lib[cid].rule, sess)
        eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        res = eng.run([strat], start_ts=_ts(START), end_ts=_ts(END))
        per_leg[name] = len(res.trades)
        for t in res.trades:
            all_trades.append((t.entry_time, t.exit_time, name, t.net_pl))

    all_trades.sort(key=lambda x: x[1])

    IST = 5.5 * 3600
    balance = min_bal = peak = START_BAL
    max_dd = 0.0
    daily_pl, daily_start = {}, {}
    shutdown_days = set()
    kept, blocked = [], 0
    for entry_ts, exit_ts, name, pl in all_trades:
        day = datetime.fromtimestamp(entry_ts + IST, tz=timezone.utc).date()
        daily_start.setdefault(day, balance)
        if day in shutdown_days:
            blocked += 1
            continue
        balance += pl
        min_bal = min(min_bal, balance)
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100 if peak > 0 else 0)
        daily_pl[day] = daily_pl.get(day, 0.0) + pl
        kept.append(pl)
        if daily_pl[day] < -0.06 * daily_start[day]:
            shutdown_days.add(day)

    net = np.array(kept)
    wins, losses = net[net > 0], net[net < 0]
    pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
    return {
        "per_leg": per_leg, "n": len(net), "blocked_breaker": blocked,
        "wr": len(wins) / len(net) * 100 if len(net) else 0,
        "pf": pf, "net": net.sum(), "min_bal": min_bal, "max_dd": max_dd,
        "end_bal": balance, "breach_days": len(shutdown_days),
        "trading_days": len(daily_pl),
    }


print(f"Window {START} -> {END} | start ${START_BAL} | 0.01 lots | realistic costs\n")
for label, on in [("D1 GATE ON  (current live config)", True),
                  ("D1 GATE OFF (both directions)", False)]:
    r = run(on)
    print(f"=== {label} ===")
    print(f"  per leg: {r['per_leg']}")
    print(f"  trades={r['n']}  WR={r['wr']:.1f}%  PF={r['pf']:.3f}  "
          f"net=${r['net']:.2f}  end=${r['end_bal']:.2f}")
    print(f"  min_bal=${r['min_bal']:.2f}  max_dd={r['max_dd']:.1f}%  "
          f"breaker_days={r['breach_days']}/{r['trading_days']}  "
          f"blocked_by_breaker={r['blocked_breaker']}")
    print()
