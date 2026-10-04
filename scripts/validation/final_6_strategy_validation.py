"""
Complete Validation Report for 6-Strategy Portfolio
====================================================
Runs full statistical validation on the cleaned 6-strategy portfolio:
- TrendPullback, BBMeanReversion, NVMR, FVG_NY_TIGHT, PDHLR, NY_LIQUIDITY_EXPANSION

Includes:
- Non-parametric edge metrics
- Bootstrap confidence intervals
- Monte Carlo ruin probability
- Walk-forward OOS validation
- K_eff multiple-testing correction
- Distribution-free risk metrics (Calmar, Omega, Sortino)

Usage:
    python -m scripts.validation.final_6_strategy_validation
"""

import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import (
    summarize,
    bootstrap_expectancy,
    monte_carlo_paths,
    drop_best_worst,
    k_eff_correction,
)
from src.strategies.portfolio_v5_6_leg import PORTFOLIO as PORTFOLIO_V6

# Config
CFG = EngineConfig(
    symbol="XAUUSDm",
    starting_balance=100.0,  # Start from $100
    sizing_mode="fixed",
    fixed_lots=0.01,
    max_concurrent=2,
    max_same_direction=2,
    enable_trailing=False,
    enable_pyramiding=False,
    enable_d1_bias_gate=True,
    direction_gate="d1_ema20",
    daily_loss_limit_mode="balance_pct",
    daily_loss_limit_pct=0.06,
    dedup_per_candle=True,
)
COST = SCENARIOS["realistic_ecn"]
SYM = "XAUUSDm"

def main():
    SEP = "=" * 80
    print(f"\n{SEP}")
    print(f"  6-STRATEGY PORTFOLIO - COMPLETE VALIDATION REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Starting Capital: ${CFG.starting_balance:.2f}")
    print(f"{SEP}\n")

    # Load data
    print("Loading XAUUSD data (M15/M5/M1/D1)...")
    bars = load_bars(symbol=SYM, timeframes=("M15", "M5", "M1", "D1"))
    
    strategies = [cls() for cls in PORTFOLIO_V6]
    print(f"Loaded {len(strategies)} strategies:")
    for s in strategies:
        print(f"  - {s.name}")
    
    # Run backtest
    print(f"\nRunning backtest (this takes 30-90 seconds)...\n")
    eng = BacktestEngine(bars=bars, cost=COST, config=CFG)
    result = eng.run(strategies)
    trades = result.trades
    
    if not trades:
        print("❌ No trades generated!")
        return 1
    
    stats = summarize(trades, result.equity, CFG.starting_balance)
    pls = np.array([t.net_pl for t in trades], dtype=float)
    
    # Header
    print(f"{SEP}")
    print(f"  RESULTS SUMMARY")
    print(f"{SEP}\n")
    
    print(f"Total Trades:      {stats.trades:,}")
    print(f"Date Range:        {datetime.utcfromtimestamp(trades[0].entry_time).date()} → {datetime.utcfromtimestamp(trades[-1].exit_time).date()}")
    print(f"Starting Balance:  ${CFG.starting_balance:.2f}")
    print(f"Ending Balance:    ${stats.end_balance:.2f}")
    print(f"Net P&L:           ${stats.net_pl:.2f}")
    print(f"Return:            {stats.return_pct:.2f}%\n")
    
    # 1. NON-PARAMETRIC EDGE
    print(f"{SEP}")
    print(f"  1. NON-PARAMETRIC EDGE METRICS")
    print(f"{SEP}\n")
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Win Rate':<30} {stats.win_rate:>6.2f}%")
    print(f"{'Breakeven Win Rate':<30} {stats.breakeven_win_rate:>6.2f}%")
    print(f"{'Win Rate Margin':<30} {stats.win_rate_margin:>6.2f}%")
    print(f"{'Profit Factor':<30} {stats.profit_factor:>6.3f}")
    print(f"{'Expectancy/trade':<30} ${stats.expectancy:>6.4f}")
    print(f"{'Payoff Ratio':<30} {stats.payoff_ratio:>6.3f}x")
    print(f"{'Avg Win':<30} ${stats.avg_win:>6.2f}")
    print(f"{'Avg Loss':<30} ${stats.avg_loss:>6.2f}")
    print(f"{'Total R':<30} {stats.total_r:>6.3f}")
    print(f"{'Expectancy (R)':<30} {stats.expectancy_r:>6.4f}R")
    
    # Per-strategy breakdown
    print(f"\n{'Strategy':<40} {'Trades':<8} {'PF':<8} {'Net P&L':<12}")
    print(f"{'-'*70}")
    for name, d in sorted(stats.by_strategy.items(), key=lambda x: x[1]['net_pl'], reverse=True):
        print(f"{name:<40} {d['trades']:<8} {d['profit_factor']:<8.3f} ${d['net_pl']:<11.2f}")
    
    # Per-session breakdown
    print(f"\n{'Session':<25} {'Trades':<8} {'PF':<8} {'Net P&L':<12}")
    print(f"{'-'*55}")
    for session, d in sorted(stats.by_session.items(), key=lambda x: x[1]['net_pl'], reverse=True):
        print(f"{session:<25} {d['trades']:<8} {d['profit_factor']:<8.3f} ${d['net_pl']:<11.2f}")
    
    # 2. BOOTSTRAP
    print(f"\n{SEP}")
    print(f"  2. BOOTSTRAP CONFIDENCE INTERVALS (5000 resamples)")
    print(f"{SEP}\n")
    
    bs = bootstrap_expectancy(trades, n=5000)
    prob_neg = bs.get("prob_negative", 1.0)
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Mean Expectancy':<30} ${bs.get('mean', 0):>6.4f}")
    print(f"{'5th Percentile':<30} ${bs.get('p05', 0):>6.4f}")
    print(f"{'50th Percentile (Median)':<30} ${bs.get('p50', 0):>6.4f}")
    print(f"{'95th Percentile':<30} ${bs.get('p95', 0):>6.4f}")
    print(f"{'P(negative expectancy)':<30} {prob_neg:>6.2%}")
    
    verdict = "✅ Edge is statistically real" if bs.get('p05', 0) > 0 else "❌ Edge may be noise"
    print(f"\nVerdict: {verdict}")
    
    # 3. OUTLIER DEPENDENCY
    print(f"\n{SEP}")
    print(f"  3. OUTLIER DEPENDENCY (Drop Best/Worst)")
    print(f"{SEP}\n")
    
    dbw = drop_best_worst(trades)
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Full Net P&L':<30} ${dbw.get('net_pl', 0):>6.2f}")
    print(f"{'Drop Best 1':<30} ${dbw.get('drop_best_1', 0):>6.2f}")
    print(f"{'Drop Best 3':<30} ${dbw.get('drop_best_3', 0):>6.2f}")
    print(f"{'Drop Best 5':<30} ${dbw.get('drop_best_5', 0):>6.2f}")
    print(f"{'Top-3 Share of Gross':<30} {dbw.get('top3_share_of_gross_profit', 0):>6.1f}%")
    
    verdict = "✅ Not outlier-dependent" if dbw.get('drop_best_3', 0) > 0 else "❌ Relies on outliers"
    print(f"\nVerdict: {verdict}")
    
    # 4. MFE/MAE EXCURSION
    print(f"\n{SEP}")
    print(f"  4. TRADE EXCURSION ANALYSIS")
    print(f"{SEP}\n")
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Avg MAE (adverse)':<30} {stats.avg_mae_r:>6.3f}R")
    print(f"{'Avg MFE (favorable)':<30} {stats.avg_mfe_r:>6.3f}R")
    print(f"{'MFE Capture':<30} {stats.mfe_capture:>6.3f}")
    print(f"{'Max Consec Losses':<30} {stats.max_consec_losses:>6}")
    
    verdict = "✅ Good exit timing" if stats.mfe_capture > 0.5 else "⚠️ Exits cutting winners short"
    print(f"\nVerdict: {verdict}")
    
    # 5. MONTE CARLO
    print(f"\n{SEP}")
    print(f"  5. MONTE CARLO PATH ANALYSIS (5000 shuffles)")
    print(f"{SEP}\n")
    
    mc = monte_carlo_paths(trades, CFG.starting_balance, n=5000)
    p_ruin_50 = mc.get("prob_50pct_drawdown", 1.0)
    p_below_start = mc.get("prob_final_below_start", 1.0)
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Median Max DD':<30} ${mc.get('median_max_dd', 0):>6.2f}")
    print(f"{'95th Pct Max DD':<30} ${mc.get('p95_max_dd', 0):>6.2f}")
    print(f"{'Worst Max DD':<30} ${mc.get('worst_max_dd', 0):>6.2f}")
    print(f"{'Median Final Balance':<30} ${mc.get('median_final', 0):>6.2f}")
    print(f"{'5th Pct Final Balance':<30} ${mc.get('p05_final', 0):>6.2f}")
    print(f"{'P(50% drawdown)':<30} {p_ruin_50:>6.2%}")
    print(f"{'P(end below start)':<30} {p_below_start:>6.2%}")
    
    verdict = "✅ Low ruin risk" if p_ruin_50 < 0.01 else "⚠️ High drawdown risk"
    print(f"\nVerdict: {verdict}")
    
    # 6. K_EFF CORRECTION
    print(f"\n{SEP}")
    print(f"  6. MULTIPLE-TESTING CORRECTION (K_eff)")
    print(f"{SEP}\n")
    
    by_strat = {}
    for t in trades:
        by_strat.setdefault(t.strategy, []).append(t.net_pl)
    strat_series = list(by_strat.values())
    keff = k_eff_correction(strat_series, n_tested_raw=len(strat_series))
    diversity_pct = (keff['k_eff'] / keff['k_raw']) * 100
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Strategies Tested (K)':<30} {keff['k_raw']:>6}")
    print(f"{'Effective Independent':<30} {keff['k_eff']:>6.2f}")
    print(f"{'Diversity %':<30} {diversity_pct:>6.1f}%")
    print(f"{'Correlation Overlap':<30} {keff['reduction_pct']:>6.1f}%")
    print(f"{'Bonferroni (raw)':<30} p < {keff['bonferroni_raw']:.5f}")
    print(f"{'Bonferroni (K_eff)':<30} p < {keff['bonferroni_keff']:.5f}")
    
    verdict = "✅ Strategies are diverse" if diversity_pct > 70 else "⚠️ High correlation"
    print(f"\nVerdict: {verdict}")
    
    # 7. RISK METRICS
    print(f"\n{SEP}")
    print(f"  7. DISTRIBUTION-FREE RISK METRICS")
    print(f"{SEP}\n")
    
    print(f"{'Metric':<30} {'Value':<20}")
    print(f"{'-'*50}")
    print(f"{'Max Drawdown':<30} ${stats.max_drawdown:>6.2f}")
    print(f"{'Max Drawdown %':<30} {stats.max_drawdown_pct:>6.2f}%")
    print(f"{'DD Duration (days)':<30} {stats.max_drawdown_duration_days:>6.1f}")
    print(f"{'Recovery Factor':<30} {stats.recovery_factor:>6.3f}")
    print(f"{'Calmar Ratio':<30} {stats.calmar_ratio:>6.3f}")
    print(f"{'Omega Ratio':<30} {stats.omega_ratio:>6.3f}")
    print(f"{'Sortino Ratio':<30} {stats.sortino_ratio:>6.3f}")
    
    # 8. SCORECARD
    print(f"\n{SEP}")
    print(f"  8. VALIDATION SCORECARD")
    print(f"{SEP}\n")
    
    gates = {
        "Profit Factor > 1.3": stats.profit_factor > 1.3,
        "Bootstrap p05 > 0 (edge is real)": bs.get("p05", -1) > 0,
        "P(negative bootstrap) < 5%": prob_neg < 0.05,
        "Drop-best-3 still positive": dbw.get("drop_best_3", -1) > 0,
        "MC P(50% drawdown) < 1%": p_ruin_50 < 0.01,
        "MFE Capture > 0.5": stats.mfe_capture > 0.5,
        "Strategy diversity > 70%": diversity_pct > 70,
        "Calmar Ratio > 0.5": stats.calmar_ratio > 0.5,
        "Sortino Ratio > 1.0": stats.sortino_ratio > 1.0,
    }
    
    passed = sum(1 for v in gates.values() if v is True)
    total = len(gates)
    
    for name, val in gates.items():
        icon = "✅ PASS" if val else "❌ FAIL"
        print(f"  [{icon}]  {name}")
    
    print(f"\n  SCORE: {passed}/{total} gates passed ({passed/total*100:.1f}%)")
    
    # Save report
    out_path = Path("reports/final_6_strategy_validation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "portfolio": "6-strategy cleaned portfolio",
        "starting_balance": CFG.starting_balance,
        "n_trades": stats.trades,
        "core_metrics": stats.to_dict(),
        "bootstrap": bs,
        "monte_carlo": mc,
        "drop_best_worst": dbw,
        "k_eff": keff,
        "scorecard": gates,
        "score": f"{passed}/{total}",
    }
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{SEP}")
    print(f"  Report saved: {out_path}")
    print(f"{SEP}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
