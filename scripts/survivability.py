"""Survivability analysis for a backtest run at fixed 0.01 lot size.

Reports on the account's ability to survive the historical drawdown sequence
at the user's actual operating constraint: 0.01 lots per trade.

    python -m scripts.survivability <run_dir>

Reads backtest.json from run_dir to get the trade sequence and equity curve.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="research/runs/YYYYMMDD-HHMMSS_* directory")
    ap.add_argument("--fixed-lots", type=float, default=0.01,
                    help="Lot size used in the backtest (default 0.01)")
    ap.add_argument("--starting-balance", type=float, default=105.74,
                    help="Starting balance (default 105.74)")
    args = ap.parse_args()

    run_path = Path(args.run_dir)
    if not run_path.is_dir():
        print(f"Error: {run_path} is not a directory")
        return

    backtest_file = run_path / "backtest.json"
    if not backtest_file.exists():
        print(f"Error: {backtest_file} not found")
        return

    with open(backtest_file, "r") as fh:
        data = json.load(fh)

    trades = data.get("trades", [])
    equity = data.get("equity", [])

    if not trades:
        print("No trades to analyze")
        return

    print("\n" + "=" * 80)
    print(f"  SURVIVABILITY ANALYSIS @ {args.fixed_lots} lot size")
    print(f"  Run: {run_path.name}")
    print("=" * 80)

    # --- Key metrics in dollars (not R) ---
    start_bal = args.starting_balance

    # Account drawdown from equity curve
    if equity:
        eq_vals = np.array([e[1] for e in equity])
        peak = np.maximum.accumulate(eq_vals)
        dd_abs = peak - eq_vals
        max_dd_abs = float(np.max(dd_abs))
        max_dd_pct = max_dd_abs / start_bal * 100
    else:
        max_dd_abs = 0.0
        max_dd_pct = 0.0

    # Losing streak metrics
    losses = [t["net_pl"] for t in trades if t["net_pl"] < 0]
    wins = [t["net_pl"] for t in trades if t["net_pl"] > 0]
    n_trades = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)

    if losses:
        max_loss = min(losses)  # most negative
        avg_loss = sum(losses) / len(losses)
    else:
        max_loss = 0.0
        avg_loss = 0.0

    if wins:
        avg_win = sum(wins) / len(wins)
    else:
        avg_win = 0.0

    # Consecutive losing streak (bars, not trades, but proxy to trade count)
    cumulative_pl = 0.0
    streak_start = 0
    max_streak_loss = 0.0
    max_streak_loss_trades = 0
    current_streak_loss = 0.0
    current_streak_trades = 0

    for i, t in enumerate(trades):
        cumulative_pl += t["net_pl"]
        if t["net_pl"] < 0:
            if current_streak_loss == 0.0:
                streak_start = i
            current_streak_loss += t["net_pl"]
            current_streak_trades += 1
        else:
            if current_streak_loss < max_streak_loss:
                max_streak_loss = current_streak_loss
                max_streak_loss_trades = current_streak_trades
            current_streak_loss = 0.0
            current_streak_trades = 0

    if current_streak_loss < max_streak_loss:
        max_streak_loss = current_streak_loss
        max_streak_loss_trades = current_streak_trades

    # Daily loss limit breaches
    daily_pls = {}
    for t in trades:
        exit_date = t["exit_date"] if "exit_date" in t else "unknown"
        if exit_date not in daily_pls:
            daily_pls[exit_date] = 0.0
        daily_pls[exit_date] += t["net_pl"]

    limit_pct = 0.06
    breaches = sum(1 for pl in daily_pls.values() if pl < -limit_pct * start_bal)

    # Trades-to-ruin heuristic: at worst historical streak, how many more would destroy account?
    if max_streak_loss_trades > 0:
        avg_loss_per_trade = max_streak_loss / max_streak_loss_trades
        equity_left = start_bal - max_dd_abs
        if avg_loss_per_trade < 0:
            trades_to_ruin = equity_left / abs(avg_loss_per_trade)
        else:
            trades_to_ruin = float("inf")
    else:
        trades_to_ruin = float("inf")

    # --- Report ---
    print(f"\n  Starting balance:         ${start_bal:.2f}")
    print(f"  Trades:                   {n_trades}")
    print(f"    Wins:                   {n_wins} ({n_wins/n_trades*100:.1f}%)")
    print(f"    Losses:                 {n_losses} ({n_losses/n_trades*100:.1f}%)")
    print(f"\n  Profitability:")
    print(f"    Avg win:                ${avg_win:.2f}")
    print(f"    Avg loss:               ${avg_loss:.2f}")
    print(f"    Win/loss ratio:         {avg_win / abs(avg_loss) if avg_loss else 0:.2f}x")
    print(f"    Total P/L:              ${cumulative_pl:+.2f}")
    print(f"\n  Drawdown (absolute):")
    print(f"    Max drawdown:           ${max_dd_abs:.2f} ({max_dd_pct:.1f}% of start)")
    print(f"  Drawdown (consecutive loss streak):")
    print(f"    Worst streak loss:      ${max_streak_loss:.2f} over {max_streak_loss_trades} trades")
    print(f"\n  Survival metrics:")
    print(f"    Daily loss limit (6%):  breached {breaches} times")
    print(f"    Trades to ruin (at worst streak rate): {trades_to_ruin:.0f}")
    print(f"      (if this is < 20, account is fragile)")
    print(f"\n  Assessment:")
    if max_dd_pct > 50:
        print(f"    ⚠️  HIGH RISK: max drawdown {max_dd_pct:.0f}% of starting balance")
    elif max_dd_pct > 30:
        print(f"    ⚠️  MODERATE RISK: max drawdown {max_dd_pct:.0f}% of starting balance")
    else:
        print(f"    ✓  Drawdown {max_dd_pct:.0f}% is manageable at 0.01 lots")

    if breaches > 0:
        print(f"    ⚠️  Daily limit breached {breaches} times — increase position size or reduce risk")
    else:
        print(f"    ✓  Never hit daily loss limit at 0.01 lots")

    if trades_to_ruin < 50:
        print(f"    ⚠️  Account fragile: {trades_to_ruin:.0f} consecutive losses would wipe it out")
    else:
        print(f"    ✓  Account has buffer for {trades_to_ruin:.0f} consecutive losses")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
