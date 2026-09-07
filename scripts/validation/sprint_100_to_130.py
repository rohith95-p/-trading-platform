"""Does the "$100 -> $130 in a day" sprint plan actually work?

The Monday battle plan proposes: 0.75x ATR stop (~$9), 3.0x ATR target (~$36),
halt the day at $80. Its own arithmetic ("two $9 losses and one $36 win = +$18")
assumes a win arrives. This measures how often one actually did.

No idealised win-rate assumption: it replays the REAL holdout trades grouped
into real IST calendar days, walks each day's actual trade sequence in order,
and asks which barrier the day touched first -- +$30 (target) or -$20 (halt).

    python -m scripts.validation.sprint_100_to_130
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np

from scripts.validation.part1_suite import (
    HOLDOUT_START, HOLDOUT_END, live_config, run_window, _bars)

IST = timezone(timedelta(hours=5, minutes=30))
START = 100.0
TARGET = 130.0     # +$30
HALT = 80.0        # -$20


def main():
    bars = _bars()
    res = run_window(bars, live_config(), HOLDOUT_START, HOLDOUT_END)
    if not res.trades:
        print("no trades"); return

    days = defaultdict(list)
    for t in sorted(res.trades, key=lambda x: x.exit_time):
        d = datetime.fromtimestamp(t.exit_time, tz=timezone.utc).astimezone(IST).date()
        days[d].append(float(t.net_pl))

    hit_target = hit_halt = neither = 0
    end_balances, day_nets = [], []
    for d, pls in sorted(days.items()):
        bal = START
        outcome = None
        for pl in pls:
            bal += pl
            if bal >= TARGET:
                outcome = "target"; break
            if bal <= HALT:
                outcome = "halt"; break
        end_balances.append(bal)
        day_nets.append(bal - START)
        if outcome == "target":
            hit_target += 1
        elif outcome == "halt":
            hit_halt += 1
        else:
            neither += 1

    n = len(days)
    nets = np.array(day_nets)
    print(f"Replayed {n} real trading days from the holdout "
          f"({HOLDOUT_START} -> {HOLDOUT_END}), each starting fresh at ${START:.0f}\n")
    print(f"  hit +$30 target first : {hit_target:4d}  ({hit_target/n*100:5.1f}%)")
    print(f"  hit -$20 halt first   : {hit_halt:4d}  ({hit_halt/n*100:5.1f}%)")
    print(f"  neither (day ended)   : {neither:4d}  ({neither/n*100:5.1f}%)\n")
    print(f"  mean day P&L   : ${nets.mean():+.2f}")
    print(f"  median day P&L : ${np.median(nets):+.2f}")
    print(f"  best / worst   : ${nets.max():+.2f} / ${nets.min():+.2f}")
    print(f"  days profitable: {(nets > 0).sum()}/{n} ({(nets > 0).mean()*100:.1f}%)")

    # What the plan implicitly needs: hitting target far more often than halt.
    ratio = hit_target / hit_halt if hit_halt else float("inf")
    print(f"\n  target:halt ratio = {ratio:.2f}  "
          f"(the sprint only makes sense if this is comfortably > 1)")

    # Expected value of running the sprint repeatedly, day after day.
    ev = hit_target / n * 30 + hit_halt / n * -20 + neither / n * float(
        np.mean([x for x in nets if HALT - START < x < TARGET - START] or [0]))
    print(f"  approx EV per sprint day = ${ev:+.2f}")

    out = dict(days=n, hit_target=hit_target, hit_halt=hit_halt, neither=neither,
               pct_target=round(hit_target / n * 100, 2),
               pct_halt=round(hit_halt / n * 100, 2),
               mean_day=round(float(nets.mean()), 2),
               median_day=round(float(np.median(nets)), 2),
               pct_days_profitable=round(float((nets > 0).mean() * 100), 2),
               target_halt_ratio=round(float(ratio), 3) if hit_halt else None,
               approx_ev_per_day=round(float(ev), 2))
    os.makedirs("research/validation", exist_ok=True)
    with open("research/validation/sprint_100_to_130.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\n--> research/validation/sprint_100_to_130.json")


if __name__ == "__main__":
    main()
