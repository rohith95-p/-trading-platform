"""Tier-2 survivability test for EMA_STACK at the REAL account size.

Every prior EMA_STACK measurement (stack_single, stack_research) used a
$100,000 synthetic balance with the daily-loss breaker OFF, specifically to
isolate the entry edge from account-size effects. That is the right test for
"does this signal have edge" and the wrong test for "will this survive at
0.01 lots on $105.74" -- which is the user's actual operating constraint.

This script runs the identical strategy and cost model at:
  - starting_balance = 105.74 (real)
  - daily_loss_limit_mode = "balance_pct" (the live breaker, on)
  - sizing_mode = "fixed", fixed_lots = 0.01 (the only lot size ever traded)

and reports survivability in dollars: max drawdown, worst losing streak,
daily-limit breach count, trades-to-ruin -- the same shape of report already
produced for the SAR candidates in scripts/tier2_ema_sar_simple.py, so the
two are directly comparable.

    python -m scripts.tier2_ema_stack_survivability
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.ema_stack import EMAStack

RUNS_ROOT = os.path.join("research", "runs")


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _survivability(trades, start_bal: float) -> dict:
    if not trades:
        print("  NO TRADES")
        return {}

    net = np.array([t.net_pl for t in trades])
    bal_after = np.array([t.balance_after for t in trades])
    balances = np.concatenate([[start_bal], bal_after])
    peak = np.maximum.accumulate(balances)
    dd_abs = peak - balances
    dd_pct_of_peak = np.divide(dd_abs, peak, out=np.zeros_like(dd_abs), where=peak > 0)
    max_dd_abs = float(dd_abs.max())
    max_dd_pct_of_start = max_dd_abs / start_bal * 100
    max_dd_pct_of_peak = float(dd_pct_of_peak.max()) * 100

    wins = net[net > 0]
    losses = net[net < 0]
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0

    # worst consecutive-loss streak, in dollars
    max_streak_loss = 0.0
    max_streak_n = 0
    cur_loss = 0.0
    cur_n = 0
    for pl in net:
        if pl < 0:
            cur_loss += pl
            cur_n += 1
            if cur_loss < max_streak_loss:
                max_streak_loss = cur_loss
                max_streak_n = cur_n
        else:
            cur_loss = 0.0
            cur_n = 0

    # daily P/L breaches: 6% of the balance the account actually had that
    # morning, not 6% of the starting balance -- matches how the live/engine
    # breaker actually computes it as the account compounds.
    daily_pl: dict = {}
    daily_start_bal: dict = {}
    running_bal = start_bal
    for t in trades:
        d = datetime.fromtimestamp(t.exit_time, tz=timezone.utc).date().isoformat()
        if d not in daily_start_bal:
            daily_start_bal[d] = running_bal
        daily_pl[d] = daily_pl.get(d, 0.0) + t.net_pl
        running_bal = t.balance_after
    breaches = sum(1 for d, pl in daily_pl.items() if pl < -0.06 * daily_start_bal[d])

    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    exp_r = float(np.mean([t.r_multiple for t in trades]))

    end_bal = bal_after[-1]
    min_bal = float(balances.min())
    min_bal_idx = int(balances.argmin())
    print(f"  Trades:                  {len(trades)}")
    print(f"  Lowest balance reached:  ${min_bal:.2f} (after trade #{min_bal_idx})")
    print(f"  Win rate:                {len(wins)/len(net)*100:.1f}%")
    print(f"  Profit factor:           {pf:.3f}   expectancy {exp_r:+.4f}R")
    print(f"  Avg win / avg loss:      ${avg_win:.2f} / ${avg_loss:.2f}")
    print(f"  Net P/L:                 ${net.sum():+.2f}")
    print(f"  Start -> end balance:    ${start_bal:.2f} -> ${end_bal:.2f}")
    print(f"  Max drawdown:            ${max_dd_abs:.2f} ({max_dd_pct_of_start:.1f}% of start, {max_dd_pct_of_peak:.1f}% of peak)")
    print(f"  Worst losing streak:     ${max_streak_loss:.2f} over {max_streak_n} trades")
    print(f"  Days breaching 6% limit: {breaches} / {len(daily_pl)} trading days")
    if end_bal <= 5.0:
        print("  ACCOUNT RUINED (hit min_tradeable_balance floor)")

    return {
        "trades": len(trades), "win_rate": len(wins) / len(net) * 100,
        "profit_factor": pf, "expectancy_r": exp_r,
        "net_pl": float(net.sum()), "start_balance": start_bal, "end_balance": end_bal,
        "min_balance": min_bal, "min_balance_after_trade": min_bal_idx,
        "max_dd_abs": max_dd_abs, "max_dd_pct_of_start": max_dd_pct_of_start,
        "max_dd_pct_of_peak": max_dd_pct_of_peak,
        "worst_streak_loss": max_streak_loss, "worst_streak_trades": max_streak_n,
        "daily_limit_breaches": breaches, "trading_days": len(daily_pl),
    }


def run() -> None:
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "D1"))
    print(f"Data hash: {bars.hash_key()}\n")

    cfg = EngineConfig(
        symbol="XAUUSDm",
        starting_balance=105.74,
        sizing_mode="fixed",
        fixed_lots=0.01,
        dedup_per_candle=True,
        max_concurrent=1,
        max_same_direction=1,
        enable_pyramiding=False,
        enable_consolidation_exit=False,
        enable_trailing=False,
        history_bars=900,
        warmup_bars=950,
        daily_loss_limit_mode="balance_pct",
        daily_loss_limit_pct=0.06,
    )

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_ema_stack_survivability"
    out_dir = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out_dir, exist_ok=True)

    windows = [
        ("in_sample", "IN-SAMPLE (2025-04-03 to 2026-08-29)", "2025-04-03", "2026-08-29"),
        ("holdout", "LOCKED HOLDOUT (2022-06-08 to 2025-04-02)", "2022-06-08", "2025-04-02"),
    ]
    summary = {"data_hash": bars.hash_key(), "engine_config": {**cfg.__dict__}, "windows": {}}

    for key, label, start, end in windows:
        print("=" * 86)
        print(f"  EMA_STACK @ $105.74 / 0.01 lots / daily breaker ON -- {label}")
        print("=" * 86)
        engine = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
        result = engine.run([EMAStack()], start_ts=_ts(start), end_ts=_ts(end))
        stats = _survivability(result.trades, cfg.starting_balance)
        summary["windows"][key] = stats
        with open(os.path.join(out_dir, f"trades_{key}.json"), "w", encoding="utf-8") as fh:
            json.dump([asdict(t) for t in result.trades], fh, indent=1, default=str)
        print()

    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print(f"written to {out_dir}")


if __name__ == "__main__":
    run()
