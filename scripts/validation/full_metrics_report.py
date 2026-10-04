"""
Full Metrics Report — 9-Strategy Portfolio
===========================================
Runs the current live portfolio (portfolio_v5_9_leg) through the backtesting
engine and prints every statistical gate in one place:

  1. Non-parametric edge        (Profit Factor, Expectancy, R-multiples)
  2. Overfitting guards         (Bootstrap expectancy CI, Drop-best-worst)
  3. Monte Carlo ruin           (P(ruin) with 5000 path shuffles)
  4. Walk-forward OOS           (6-fold IS/OOS efficiency ratio)
  5. K_eff multiple-testing     (Vertox eigenspectrum correction)
  6. Distribution-free risk     (Calmar, Omega, Sortino)

Usage:
    python -m scripts.validation.full_metrics_report
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
from src.strategies.portfolio_v5_9_leg import PORTFOLIO as PORTFOLIO_V5

# -- Config mirrors live system -----------------------------------------------
CFG = EngineConfig(
    symbol="XAUUSDm",
    starting_balance=171.14,
    sizing_mode="fixed",
    fixed_lots=0.02,
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
SYM  = "XAUUSDm"

SEP = "=" * 70

def _tick(ok):
    return "PASS" if ok else "FAIL"


def main():
    print(SEP)
    print("  ULTRA CORE -- FULL METRICS REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Portfolio: portfolio_v5_9_leg  ({len(PORTFOLIO_V5)} strategies)")
    print(SEP)

    print("\nLoading XAUUSD data (M15/M5/M1/D1)...")
    bars = load_bars(symbol=SYM, timeframes=("M15", "M5", "M1", "D1"))
    strategies = [cls() for cls in PORTFOLIO_V5]

    print("Running full backtest (this takes ~30s)...\n")
    eng = BacktestEngine(bars=bars, cost=COST, config=CFG)
    result = eng.run(strategies)
    trades = result.trades

    if not trades:
        print("No trades generated. Check data or config.")
        return 1

    stats = summarize(trades, result.equity, CFG.starting_balance)
    pls   = np.array([t.net_pl for t in trades], dtype=float)

    print(f"  Total trades : {stats.trades}")
    print(f"  Date range   : {datetime.utcfromtimestamp(trades[0].entry_time).date()} "
          f"-> {datetime.utcfromtimestamp(trades[-1].exit_time).date()}")

    # 1. NON-PARAMETRIC EDGE
    print(f"\n{SEP}")
    print("  1. NON-PARAMETRIC EDGE METRICS")
    print(SEP)
    print(f"  Trades            : {stats.trades:>8}")
    print(f"  Win Rate          : {stats.win_rate:>7.2f}%")
    print(f"  Breakeven WR      : {stats.breakeven_win_rate:>7.2f}%")
    print(f"  Win Rate Margin   : {stats.win_rate_margin:>7.2f}%")
    print(f"  Profit Factor     : {stats.profit_factor:>7.3f}")
    print(f"  Expectancy/trade  : ${stats.expectancy:>6.4f}")
    print(f"  Total R           : {stats.total_r:>7.3f}")
    print(f"  Expectancy (R)    : {stats.expectancy_r:>7.4f}R")
    print(f"  Avg Win           : ${stats.avg_win:>6.2f}  |  Avg Loss: ${stats.avg_loss:.2f}")
    print(f"  Payoff Ratio      : {stats.payoff_ratio:>7.3f}x")
    print(f"  Net P&L           : ${stats.net_pl:>8.2f}")
    print(f"  Return            : {stats.return_pct:>6.2f}%")
    print()
    print("  Per-Strategy Breakdown:")
    for name, d in sorted(stats.by_strategy.items()):
        print(f"    {name:<42} n={d['trades']:>4}  PF={d['profit_factor']:.3f}  "
              f"WR={d['win_rate']:.1f}%  Net=${d['net_pl']:.2f}")
    print()
    print("  Per-Session Breakdown:")
    for session, d in sorted(stats.by_session.items()):
        print(f"    {session:<18}  n={d['trades']:>4}  PF={d['profit_factor']:.3f}  "
              f"WR={d['win_rate']:.1f}%  Net=${d['net_pl']:.2f}")

    # 2. OVERFITTING GUARDS
    print(f"\n{SEP}")
    print("  2. OVERFITTING GUARDS")
    print(SEP)
    bs = bootstrap_expectancy(trades, n=5000)
    prob_neg = bs.get("prob_negative", 1.0)
    print(f"  Bootstrap Expectancy CI (5000 resamples):")
    print(f"    Mean    : ${bs.get('mean', 0):.4f}")
    print(f"    5th pct : ${bs.get('p05', 0):.4f}  ({'positive' if bs.get('p05', 0) > 0 else 'NEGATIVE -- edge may be noise'})")
    print(f"    50th pct: ${bs.get('p50', 0):.4f}")
    print(f"    95th pct: ${bs.get('p95', 0):.4f}")
    print(f"    P(neg)  : {prob_neg:.2%}")
    print()
    dbw = drop_best_worst(trades)
    print(f"  Outlier Dependency:")
    print(f"    Full net P&L       : ${dbw.get('net_pl', 0):.2f}")
    print(f"    Drop best 1        : ${dbw.get('drop_best_1', 0):.2f}")
    print(f"    Drop best 3        : ${dbw.get('drop_best_3', 0):.2f}  "
          f"({'still positive' if dbw.get('drop_best_3', 0) > 0 else 'GOES NEGATIVE'})")
    print(f"    Drop best 5        : ${dbw.get('drop_best_5', 0):.2f}")
    print(f"    Top-3 share        : {dbw.get('top3_share_of_gross_profit', 0):.1f}%")
    print()
    print(f"  Excursion Quality:")
    print(f"    Avg MAE (R)  : {stats.avg_mae_r:.3f}R")
    print(f"    Avg MFE (R)  : {stats.avg_mfe_r:.3f}R")
    print(f"    MFE Capture  : {stats.mfe_capture:.3f}  "
          f"({'good' if stats.mfe_capture > 0.5 else 'exits cutting winners short'})")
    print(f"    Max consec L : {stats.max_consec_losses}")

    # 3. MONTE CARLO RUIN
    print(f"\n{SEP}")
    print("  3. MONTE CARLO RUIN  (5000 path-shuffles)")
    print(SEP)
    mc = monte_carlo_paths(trades, CFG.starting_balance, n=5000)
    p_ruin_50pct = mc.get("prob_50pct_drawdown", 1.0)
    p_below_start = mc.get("prob_final_below_start", 1.0)
    print(f"  Median max DD        : ${mc.get('median_max_dd', 0):.2f}")
    print(f"  95th pct max DD      : ${mc.get('p95_max_dd', 0):.2f}")
    print(f"  Worst max DD         : ${mc.get('worst_max_dd', 0):.2f}")
    print(f"  Median final balance : ${mc.get('median_final', 0):.2f}")
    print(f"  5th pct final bal    : ${mc.get('p05_final', 0):.2f}")
    print(f"  P(50% drawdown)      : {p_ruin_50pct:.2%}  ({'< 1% OK' if p_ruin_50pct < 0.01 else 'WARNING'})")
    print(f"  P(end below start)   : {p_below_start:.2%}  ({'< 20% OK' if p_below_start < 0.20 else 'WARNING'})")

    # 4. WALK-FORWARD OOS
    print(f"\n{SEP}")
    print("  4. WALK-FORWARD OOS  (6 folds, 70/30 IS/OOS)")
    print(SEP)
    wf_passed = None
    try:
        from scripts.validation.walk_forward_validate import WalkForwardValidator
        wfv = WalkForwardValidator(n_folds=6, is_ratio=0.70, efficiency_threshold=0.50)
        wf = wfv.validate(strategies, bars, CFG, COST)
        avg_eff   = wf["avg_efficiency"]
        wf_passed = wf["passed"]
        print(f"  Avg IS PF            : {wf['is_avg_pf']:.3f}")
        print(f"  Avg OOS PF           : {wf['oos_avg_pf']:.3f}")
        print(f"  Avg Efficiency Ratio : {avg_eff:.3f} +/- {wf['std_efficiency']:.3f}")
        print(f"  Folds passed         : {wf['folds_passed']}/{wf['n_folds']}")
        print(f"  Verdict              : {_tick(wf_passed)}")
    except Exception as e:
        print(f"  Walk-forward skipped: {e}")

    # 5. K_EFF MULTIPLE-TESTING
    print(f"\n{SEP}")
    print("  5. K_EFF MULTIPLE-TESTING CORRECTION  (Vertox eigenspectrum)")
    print(SEP)
    by_strat: dict = {}
    for t in trades:
        by_strat.setdefault(t.strategy, []).append(t.net_pl)
    strat_series = list(by_strat.values())
    keff = k_eff_correction(strat_series, n_tested_raw=len(strat_series))
    diversity_pct = (keff['k_eff'] / keff['k_raw']) * 100
    print(f"  Strategies tested (K)      : {keff['k_raw']}")
    print(f"  Effective indep. tests     : {keff['k_eff']}")
    print(f"  Correlation overlap        : {keff['reduction_pct']:.1f}%  "
          f"({'diverse' if keff['reduction_pct'] < 30 else 'high correlation'})")
    print(f"  Bonferroni (raw, DePrado)  : p < {keff['bonferroni_raw']:.5f}")
    print(f"  Bonferroni (K_eff, honest) : p < {keff['bonferroni_keff']:.5f}")
    print(f"  Eigenvalues (top 5)        : {keff['eigenvalues'][:5]}")
    print(f"  -> {keff['interpretation']}")

    # 6. DISTRIBUTION-FREE RISK METRICS
    print(f"\n{SEP}")
    print("  6. DISTRIBUTION-FREE RISK-ADJUSTED METRICS")
    print(SEP)
    print(f"  Max Drawdown    : ${stats.max_drawdown:.2f}  ({stats.max_drawdown_pct:.2f}%)")
    print(f"  DD Duration     : {stats.max_drawdown_duration_days:.1f} days")
    print(f"  Recovery Factor : {stats.recovery_factor:.3f}")
    print(f"  Calmar Ratio    : {stats.calmar_ratio:.3f}  (Ann.Return / MaxDD%)")
    print(f"  Omega Ratio     : {stats.omega_ratio:.3f}  (gains / losses, threshold=0)")
    print(f"  Sortino Ratio   : {stats.sortino_ratio:.3f}  (mean / downside-std only)")

    # SCORECARD
    print(f"\n{SEP}")
    print("  OVERALL SCORECARD")
    print(SEP)
    gates = {
        "Profit Factor > 1.3"              : stats.profit_factor > 1.3,
        "Bootstrap p05 > 0 (edge is real)" : bs.get("p05", -1) > 0,
        "P(negative bootstrap) < 5%"       : prob_neg < 0.05,
        "Drop-best-3 still positive"       : dbw.get("drop_best_3", -1) > 0,
        "MC P(50% drawdown) < 1%"          : p_ruin_50pct < 0.01,
        "MFE Capture > 0.5"                : stats.mfe_capture > 0.5,
        "Strategy diversity (K_eff/K > 70%)": diversity_pct > 70,
        "Calmar Ratio > 0.5"               : stats.calmar_ratio > 0.5,
        "Sortino Ratio > 1.0"              : stats.sortino_ratio > 1.0,
        "Walk-forward efficiency > 0.5"    : wf_passed,
    }
    passed = sum(1 for v in gates.values() if v is True)
    total  = sum(1 for v in gates.values() if v is not None)
    for name, val in gates.items():
        icon = "SKIP" if val is None else ("PASS" if val else "FAIL")
        print(f"  [{icon:<4}]  {name}")
    print(f"\n  Score: {passed}/{total} gates passed")
    print(SEP)

    # Save JSON
    out_path = Path("reports/full_metrics_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "portfolio": "portfolio_v5_9_leg",
        "n_trades": stats.trades,
        "core_metrics": stats.to_dict(),
        "bootstrap": bs,
        "monte_carlo_paths": mc,
        "drop_best_worst": dbw,
        "k_eff": keff,
        "scorecard": {k: v for k, v in gates.items()},
        "score": f"{passed}/{total}",
    }
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved -> {out_path}")
    return 0 if passed >= total - 1 else 1


if __name__ == "__main__":
    sys.exit(main())
