"""The control experiment: do the entry rules add anything at all?

The exit sweep found that profit factor rises monotonically with take-profit
width and never turns over, reaching ~1.2 at 12xATR. Two explanations fit that
equally well:

  (a) The entry signals have an edge that wider targets let run.
  (b) Nothing. With a wide target and a tight stop, the win rate converges on the
      random-walk barrier ratio SL/(SL+TP), and any upward drift in the
      underlying tips the result above break-even. Gold rose 41.5% across this
      window.

This script decides between them by replacing the entry signal with a coin flip
-- same instrument, same sessions, same stops, same exits, same costs, same
number of trades -- and comparing. If random entries score like the strategies,
the strategies are contributing nothing and the result is drift, not alpha.

    python -m scripts.random_entry_control
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.metrics import bootstrap_expectancy, summarize
from src.strategies.base_strategy import Signal
from scripts.run_backtest import build_strategies

RUNS_ROOT = os.path.join("research", "runs")
IST = timezone(timedelta(hours=5, minutes=30))


class RandomEntry:
    """A strategy-shaped object that fires at random with no reference to price.

    It keeps the parts of the real strategies that are not the edge -- the
    session window and the trading cadence -- so the only thing removed is the
    signal itself.
    """

    magic = 9999

    def __init__(self, name: str, rate: float, seed: int,
                 session: tuple = (11.5, 21.5), long_prob: float = 0.5):
        self.name = name
        self.rate = rate
        self.session = session
        self.long_prob = long_prob
        self._rng = np.random.default_rng(seed)

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 3:
            return None
        ts = int(m15_rates[-2]["time"])
        ist = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(IST)
        tv = ist.hour + ist.minute / 60.0
        if not (self.session[0] <= tv < self.session[1]):
            return None
        if self._rng.random() > self.rate:
            return None
        is_buy = bool(self._rng.random() < self.long_prob)
        return Signal(direction=0 if is_buy else 1, strategy_name=self.name,
                      magic=self.magic, is_buy=is_buy)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        return None


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _run(bars, strategies, tp, cost, balance, start, end) -> Dict[str, Any]:
    cfg = EngineConfig(starting_balance=balance, sizing_mode="fixed",
                       dedup_per_candle=True, enable_trailing=False,
                       enable_pyramiding=False, tp_atr_mult=tp)
    eng = BacktestEngine(bars, SCENARIOS[cost], cfg)
    res = eng.run(strategies, _ts(start), _ts(end))
    s = summarize(res.trades, res.equity, cfg.starting_balance)
    b = bootstrap_expectancy(res.trades)
    longs = [t for t in res.trades if t.is_buy]
    shorts = [t for t in res.trades if not t.is_buy]
    return {
        "stats": s, "bootstrap": b,
        "long_net": round(sum(t.net_pl for t in longs), 2), "long_n": len(longs),
        "short_net": round(sum(t.net_pl for t in shorts), 2), "short_n": len(shorts),
    }


def _fmt(label: str, r: Dict[str, Any]) -> str:
    s = r["stats"]
    pf = "inf" if s.profit_factor == float("inf") else f"{s.profit_factor:.3f}"
    pn = f"{r['bootstrap']['prob_negative']:.0%}" if r["bootstrap"] else "-"
    return (f"{label:<28}{s.trades:>6}{s.win_rate:>8.2f}{pf:>8}{s.net_pl:>11,.2f}"
            f"{s.expectancy:>9.3f}{pn:>9}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-03")
    ap.add_argument("--end", default="2026-08-29")
    ap.add_argument("--cost", default="realistic")
    ap.add_argument("--balance", type=float, default=100000.0)
    ap.add_argument("--tps", nargs="*", type=float, default=[3.0, 12.0])
    ap.add_argument("--seeds", nargs="*", type=int, default=[1, 2, 3, 4, 5])
    args = ap.parse_args()

    bars = load_bars("XAUUSDm")
    print(f"data {bars.hash_key()}  {args.start} -> {args.end}  costs={args.cost}")
    print("Entries replaced with a coin flip. Everything else held identical.\n")

    hdr = (f"{'entry source':<28}{'n':>6}{'WR%':>8}{'PF':>8}{'net $':>11}"
           f"{'exp $':>9}{'P(e<=0)':>9}")
    out: List[Dict[str, Any]] = []

    for tp in args.tps:
        print(f"\n===== take-profit {tp}xATR, no trailing =====")
        print(hdr)
        print("-" * len(hdr))

        real = _run(bars, build_strategies(
            ["morning_momentum", "ema_pullback", "asian_sweep"]),
            tp, args.cost, args.balance, args.start, args.end)
        print(_fmt("REAL strategies", real), flush=True)
        out.append({"tp": tp, "kind": "real", **{k: v for k, v in real.items()
                                                 if k != "stats"},
                    "stats": real["stats"].to_dict()})

        # Match the real trade count so the comparison is like-for-like.
        target = real["stats"].trades
        rate = min(1.0, target / 9000.0)

        pfs, nets = [], []
        for seed in args.seeds:
            rnd = _run(bars, [RandomEntry("RANDOM", rate, seed)],
                       tp, args.cost, args.balance, args.start, args.end)
            print(_fmt(f"  random seed {seed}", rnd), flush=True)
            pf = rnd["stats"].profit_factor
            if pf != float("inf"):
                pfs.append(pf)
            nets.append(rnd["stats"].net_pl)
            out.append({"tp": tp, "kind": f"random_{seed}",
                        **{k: v for k, v in rnd.items() if k != "stats"},
                        "stats": rnd["stats"].to_dict()})

        if pfs:
            print(f"  {'random mean':<26}{'':>6}{'':>8}{np.mean(pfs):>8.3f}"
                  f"{np.mean(nets):>11,.2f}")
            print(f"\n  REAL PF {real['stats'].profit_factor:.3f} vs "
                  f"RANDOM PF {np.mean(pfs):.3f} "
                  f"(sd {np.std(pfs):.3f}, range {min(pfs):.3f}-{max(pfs):.3f})")
            edge = real["stats"].profit_factor - float(np.mean(pfs))
            z = edge / np.std(pfs) if np.std(pfs) > 0 else float("nan")
            print(f"  entry contribution: {edge:+.3f} PF  ({z:+.2f} sd of the random spread)")
        print(f"\n  REAL   long {real['long_n']:>5} = ${real['long_net']:>10,.2f}   "
              f"short {real['short_n']:>5} = ${real['short_net']:>10,.2f}")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_random_control"
    d = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "control.json"), "w", encoding="utf-8") as fh:
        json.dump({"window": {"start": args.start, "end": args.end},
                   "cost": args.cost, "data_hash": bars.hash_key(), "rows": out},
                  fh, indent=2, default=str)
    print(f"\nwritten to {d}")


if __name__ == "__main__":
    main()
