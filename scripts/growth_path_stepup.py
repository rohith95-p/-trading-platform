"""Step-up policy simulation for the path-to-$20/day report.

Consumes scratch_base_trades.json (the real 0.01-lot portfolio_v4 trade
sequence from growth_path_sweep2.py) and replays it under fixed-lots and
under 3 lot-step-up policies, scaling each trade's $ P&L linearly by
(policy_lots / 0.01) -- validated as the right approximation by the direct
0.01/0.02/0.05 fixed-lot reruns in growth_path_sweep2.py (commission and
swap are exactly linear in lots; gross P&L is exactly linear in lots for a
fixed entry/exit price pair; the only nonlinearity is margin gating, which
this script checks explicitly with a real margin formula each trade).

The daily 6% breaker is re-evaluated per policy (not reused from the 0.01
baseline) because a bigger multiplier changes which days breach.
"""
import json
import math
from datetime import datetime, timezone

IST_OFFSET = 5.5 * 3600
START_BAL = 105.74
GOLD_PRICE = 4428.0   # approx, per user-supplied context; margin check is a
                       # reasonable-order-of-magnitude flag, not a precise backtest
LEVERAGE = 200.0
CONTRACT = 100.0
LOT_STEP = 0.01


def margin_for(lots):
    return CONTRACT * GOLD_PRICE * lots / LEVERAGE


def snap_lots(x):
    """Snap to the broker's 0.01 lot step, minimum 0.01."""
    steps = max(1, round(x / LOT_STEP))
    return round(steps * LOT_STEP, 2)


with open("scratch_base_trades.json") as f:
    trades = json.load(f)
# already chronological by exit_ts

# ---------------------------------------------------------------------------
# Policy lot functions: given current balance, return lots (pre-snap)
# ---------------------------------------------------------------------------

def policy_fixed(balance):
    return 0.01


def policy_double_on_double(balance):
    """Lot size doubles every time balance doubles from the $105.74 start."""
    ratio = balance / START_BAL
    if ratio < 1:
        return 0.01
    doublings = math.floor(math.log2(ratio))
    return snap_lots(0.01 * (2 ** doublings))


MILESTONES = [
    (105.74, 0.01),
    (200, 0.02),
    (400, 0.03),
    (800, 0.05),
    (1600, 0.08),
    (3200, 0.15),
    (6400, 0.30),
    (12800, 0.60),
]

def policy_milestones(balance):
    lots = 0.01
    for m, l in MILESTONES:
        if balance >= m:
            lots = l
    return lots


TARGET_MARGIN_FRACTION = 0.20  # keep margin locked ~20% of balance (what 0.01 lot was at $105.74 start)

def policy_constant_margin_fraction(balance):
    target_margin = balance * TARGET_MARGIN_FRACTION
    lots = target_margin * LEVERAGE / (CONTRACT * GOLD_PRICE)
    return snap_lots(max(0.01, lots))


POLICIES = {
    "fixed_0.01": policy_fixed,
    "double_on_double": policy_double_on_double,
    "fixed_milestones": policy_milestones,
    "constant_margin_frac_20pct": policy_constant_margin_fraction,
}


def simulate(policy_fn, recheck_every_n_trades=1):
    balance = START_BAL
    min_bal = START_BAL
    peak = START_BAL
    max_dd = 0.0
    daily_pl, daily_start_bal = {}, {}
    shutdown_days = set()
    margin_blocked = 0
    current_lots = 0.01
    milestone_log = []
    last_lots = None
    day_first_daily_rate = {}
    rows = []
    for i, t in enumerate(trades):
        if i % recheck_every_n_trades == 0:
            current_lots = policy_fn(balance)
        day = t["day"]
        if day not in daily_start_bal:
            daily_start_bal[day] = balance
        if day in shutdown_days:
            continue
        # margin check (approximate, single-position-at-a-time per leg is the
        # real engine's constraint; this checks the trade in isolation)
        req_margin = margin_for(current_lots)
        if req_margin > balance * 0.9:
            margin_blocked += 1
            continue
        mult = current_lots / 0.01
        pl = t["pl_001"] * mult
        balance += pl
        min_bal = min(min_bal, balance)
        peak = max(peak, balance)
        dd = (peak - balance) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
        daily_pl[day] = daily_pl.get(day, 0.0) + pl
        if daily_pl[day] < -0.06 * daily_start_bal[day]:
            shutdown_days.add(day)
        if last_lots != current_lots:
            milestone_log.append({"trade_idx": i, "entry_ts": t["entry_ts"], "day": day,
                                   "balance": round(balance, 2), "new_lots": current_lots})
            last_lots = current_lots
        rows.append({"day": day, "entry_ts": t["entry_ts"], "lots": current_lots,
                      "pl": round(pl, 2), "balance": round(balance, 2)})

    days_sorted = sorted(daily_pl.keys())
    span = (datetime.strptime(days_sorted[-1], "%Y-%m-%d").date()
            - datetime.strptime(days_sorted[0], "%Y-%m-%d").date()).days + 1 if days_sorted else 0
    # trailing 10-trading-day $/day at the end (the "natural" run-rate at final lot size)
    tail_days = days_sorted[-10:] if len(days_sorted) >= 10 else days_sorted
    tail_pl = sum(daily_pl[d] for d in tail_days)
    tail_rate = tail_pl / len(tail_days) if tail_days else 0.0

    return {
        "end_balance": round(balance, 2),
        "min_balance": round(min_bal, 2),
        "max_dd_pct": round(max_dd, 2),
        "breach_days": len(shutdown_days),
        "n_trading_days": len(daily_pl),
        "calendar_span_days": span,
        "overall_per_day_avg": round(sum(daily_pl.values()) / span, 3) if span else 0,
        "final_lots": current_lots,
        "tail_10day_per_day_rate": round(tail_rate, 3),
        "margin_blocked_trades": margin_blocked,
        "milestone_log": milestone_log,
        "rows": rows,
    }


results = {}
for name, fn in POLICIES.items():
    res = simulate(fn)
    results[name] = res
    print(f"\n=== {name} ===")
    print(f"  end_balance=${res['end_balance']}  min_bal=${res['min_balance']}  "
          f"max_dd={res['max_dd_pct']}%  breach_days={res['breach_days']}/{res['n_trading_days']}  "
          f"span={res['calendar_span_days']}d")
    print(f"  overall_avg=${res['overall_per_day_avg']}/day  final_lots={res['final_lots']}  "
          f"tail_10day_rate=${res['tail_10day_rate' if False else 'tail_10day_per_day_rate']}/day  "
          f"margin_blocked={res['margin_blocked_trades']}")
    print(f"  lot changes: {len(res['milestone_log'])}")
    for m in res["milestone_log"][:20]:
        print(f"    -> {m['new_lots']} lots at balance=${m['balance']} (day {m['day']})")

with open("scratch_stepup_results.json", "w") as f:
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in results.items()},
              f, indent=2, default=str)
print("\nsaved scratch_stepup_results.json")
