"""
Compare 5-Strategy vs 6-Strategy Portfolio Performance
========================================================
Runs two backtests starting from $100:
1. 5 strategies (WITHOUT TrendPullback)
2. 6 strategies (WITH TrendPullback)

Outputs detailed CSV files with:
- Every trade
- Profit/Loss per trade
- Running account balance after each trade
- Strategy name, entry/exit times, prices

Usage:
    python -m scripts.validation.compare_5_vs_6_strategies
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize

# Import strategy classes
from src.strategies.portfolio_v5_6_leg import (
    TrendPullbackV5,
    BBMeanReversionV5,
    NVMRPortfolioV5,
    FVGNYTightV5,
    PDHLRStrategyV5,
    NYLiquidityExpansionV5
)

# --- Config mirrors live system -----------------------------------------------
BASE_CONFIG = {
    "symbol": "XAUUSDm",
    "starting_balance": 100.0,  # $100 starting capital
    "sizing_mode": "fixed",
    "fixed_lots": 0.01,  # Smaller lots for $100 account
    "max_concurrent": 2,
    "max_same_direction": 2,
    "enable_trailing": False,
    "enable_pyramiding": False,
    "enable_d1_bias_gate": True,
    "direction_gate": "d1_ema20",
    "daily_loss_limit_mode": "balance_pct",
    "daily_loss_limit_pct": 0.06,
    "dedup_per_candle": True,
}

COST = SCENARIOS["realistic_ecn"]
SYM = "XAUUSDm"
SEP = "=" * 80

def write_detailed_csv(trades, equity, starting_balance, output_file):
    """
    Write detailed CSV with running balance after each trade.
    
    Columns:
    - trade_num
    - strategy
    - direction (BUY/SELL)
    - entry_time
    - exit_time
    - entry_price
    - exit_price
    - profit_loss ($)
    - account_balance ($)
    - duration_minutes
    - exit_reason
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'trade_num',
            'strategy',
            'direction',
            'entry_time',
            'exit_time',
            'entry_price',
            'exit_price',
            'profit_loss',
            'account_balance',
            'duration_minutes',
            'exit_reason'
        ])
        
        balance = starting_balance
        for idx, trade in enumerate(trades, start=1):
            balance += trade.net_pl
            
            entry_dt = datetime.utcfromtimestamp(trade.entry_time).strftime('%Y-%m-%d %H:%M:%S')
            exit_dt = datetime.utcfromtimestamp(trade.exit_time).strftime('%Y-%m-%d %H:%M:%S')
            direction = "BUY" if trade.is_buy else "SELL"
            duration_min = (trade.exit_time - trade.entry_time) / 60.0
            
            writer.writerow([
                idx,
                trade.strategy,
                direction,
                entry_dt,
                exit_dt,
                f"{trade.entry_price:.3f}",
                f"{trade.exit_price:.3f}",
                f"{trade.net_pl:.2f}",
                f"{balance:.2f}",
                f"{duration_min:.1f}",
                trade.exit_reason
            ])
    
    print(f"  ✅ Detailed CSV saved: {output_file}")
    print(f"     {len(trades)} trades logged")
    print(f"     Starting balance: ${starting_balance:.2f}")
    print(f"     Ending balance: ${balance:.2f}")
    print(f"     Net P&L: ${balance - starting_balance:.2f}\n")


def run_backtest(strategies, config_dict, label):
    """Run backtest and return results."""
    print(f"\n{SEP}")
    print(f"  RUNNING: {label}")
    print(SEP)
    print(f"  Strategies: {len(strategies)}")
    for strat_cls in strategies:
        strat = strat_cls()
        print(f"    - {strat.name}")
    print(f"  Starting balance: ${config_dict['starting_balance']:.2f}")
    print(f"  Fixed lots: {config_dict['fixed_lots']}")
    print()
    
    # Load data
    print("  Loading XAUUSD data (M15/M5/M1/D1)...")
    bars = load_bars(symbol=SYM, timeframes=("M15", "M5", "M1", "D1"))
    
    # Create config
    cfg = EngineConfig(**config_dict)
    
    # Instantiate strategies
    strategy_instances = [cls() for cls in strategies]
    
    # Run backtest
    print("  Running backtest (30-60 seconds)...\n")
    eng = BacktestEngine(bars=bars, cost=COST, config=cfg)
    result = eng.run(strategy_instances)
    
    if not result.trades:
        print("  ❌ No trades generated!")
        return None
    
    # Calculate metrics
    stats = summarize(result.trades, result.equity, cfg.starting_balance)
    
    print(f"  RESULTS:")
    print(f"    Total trades:     {stats.trades}")
    print(f"    Win rate:         {stats.win_rate:.2f}%")
    print(f"    Profit Factor:    {stats.profit_factor:.3f}")
    print(f"    Net P&L:          ${stats.net_pl:.2f}")
    print(f"    Return:           {stats.return_pct:.2f}%")
    print(f"    Max Drawdown:     ${stats.max_drawdown:.2f} ({stats.max_drawdown_pct:.2f}%)")
    print(f"    Expectancy/trade: ${stats.expectancy:.4f}")
    print(f"    Calmar Ratio:     {stats.calmar_ratio:.3f}")
    print(f"    Omega Ratio:      {stats.omega_ratio:.3f}")
    print(f"    Sortino Ratio:    {stats.sortino_ratio:.3f}")
    
    print(f"\n  Per-Strategy Breakdown:")
    for name, d in sorted(stats.by_strategy.items(), key=lambda x: x[1]['net_pl'], reverse=True):
        print(f"    {name:<35} n={d['trades']:>4}  PF={d['profit_factor']:.3f}  Net=${d['net_pl']:>7.2f}")
    
    return {
        'trades': result.trades,
        'equity': result.equity,
        'stats': stats,
        'config': cfg
    }


def main():
    print(f"\n{SEP}")
    print(f"  PORTFOLIO COMPARISON: 5-STRATEGY vs 6-STRATEGY")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Starting Capital: $100")
    print(SEP)
    
    # Define portfolios
    portfolio_5_strategies = [
        BBMeanReversionV5,
        NVMRPortfolioV5,
        FVGNYTightV5,
        PDHLRStrategyV5,
        NYLiquidityExpansionV5
    ]
    
    portfolio_6_strategies = [
        TrendPullbackV5,
        BBMeanReversionV5,
        NVMRPortfolioV5,
        FVGNYTightV5,
        PDHLRStrategyV5,
        NYLiquidityExpansionV5
    ]
    
    # Run 5-strategy backtest
    result_5 = run_backtest(
        strategies=portfolio_5_strategies,
        config_dict=BASE_CONFIG.copy(),
        label="5-STRATEGY PORTFOLIO (NO TrendPullback)"
    )
    
    if result_5:
        csv_path_5 = Path("reports/backtest_5_strategy_trades.csv")
        csv_path_5.parent.mkdir(parents=True, exist_ok=True)
        write_detailed_csv(
            trades=result_5['trades'],
            equity=result_5['equity'],
            starting_balance=result_5['config'].starting_balance,
            output_file=csv_path_5
        )
    
    # Run 6-strategy backtest
    result_6 = run_backtest(
        strategies=portfolio_6_strategies,
        config_dict=BASE_CONFIG.copy(),
        label="6-STRATEGY PORTFOLIO (WITH TrendPullback)"
    )
    
    if result_6:
        csv_path_6 = Path("reports/backtest_6_strategy_trades.csv")
        write_detailed_csv(
            trades=result_6['trades'],
            equity=result_6['equity'],
            starting_balance=result_6['config'].starting_balance,
            output_file=csv_path_6
        )
    
    # Final comparison
    if result_5 and result_6:
        print(f"\n{SEP}")
        print(f"  FINAL COMPARISON")
        print(SEP)
        print(f"\n  {'Metric':<30} {'5-Strategy':<20} {'6-Strategy':<20} {'Winner':<10}")
        print(f"  {'-'*80}")
        
        metrics = [
            ('Total Trades', result_5['stats'].trades, result_6['stats'].trades, 'more'),
            ('Win Rate %', result_5['stats'].win_rate, result_6['stats'].win_rate, 'higher'),
            ('Profit Factor', result_5['stats'].profit_factor, result_6['stats'].profit_factor, 'higher'),
            ('Net P&L $', result_5['stats'].net_pl, result_6['stats'].net_pl, 'higher'),
            ('Return %', result_5['stats'].return_pct, result_6['stats'].return_pct, 'higher'),
            ('Max DD %', result_5['stats'].max_drawdown_pct, result_6['stats'].max_drawdown_pct, 'lower'),
            ('Expectancy/trade $', result_5['stats'].expectancy, result_6['stats'].expectancy, 'higher'),
            ('Calmar Ratio', result_5['stats'].calmar_ratio, result_6['stats'].calmar_ratio, 'higher'),
            ('Omega Ratio', result_5['stats'].omega_ratio, result_6['stats'].omega_ratio, 'higher'),
        ]
        
        for metric_name, val_5, val_6, better in metrics:
            if better == 'higher':
                winner = '5-Strat ✅' if val_5 > val_6 else '6-Strat ✅'
            elif better == 'lower':
                winner = '5-Strat ✅' if val_5 < val_6 else '6-Strat ✅'
            else:  # more
                winner = '5-Strat ✅' if val_5 > val_6 else '6-Strat ✅'
            
            print(f"  {metric_name:<30} {val_5:<20.3f} {val_6:<20.3f} {winner:<10}")
        
        print(f"\n{SEP}")
        print(f"  RECOMMENDATION:")
        print(SEP)
        
        # Decision logic
        pf_improvement = result_5['stats'].profit_factor - result_6['stats'].profit_factor
        profit_loss = result_5['stats'].net_pl - result_6['stats'].net_pl
        trade_count_diff = result_6['stats'].trades - result_5['stats'].trades
        
        if result_5['stats'].profit_factor > 1.4 and pf_improvement > 0.15:
            recommendation = "5-STRATEGY"
            reason = f"PF improvement of {pf_improvement:.3f} is significant, and PF > 1.4 threshold met"
        elif profit_loss > 500:
            recommendation = "5-STRATEGY"
            reason = f"6-strategy gives ${profit_loss:.2f} less profit while adding {trade_count_diff} more trades"
        elif trade_count_diff > 2000 and abs(profit_loss) < 500:
            recommendation = "6-STRATEGY"
            reason = f"Adds {trade_count_diff} more trades for diversification with minimal profit impact"
        else:
            recommendation = "6-STRATEGY"
            reason = "Better diversification and sample size outweigh marginal PF difference"
        
        print(f"\n  ✅ RECOMMENDED: {recommendation}")
        print(f"     Reason: {reason}\n")
        print(f"  CSV Files Generated:")
        print(f"     - reports/backtest_5_strategy_trades.csv")
        print(f"     - reports/backtest_6_strategy_trades.csv\n")
        print(SEP)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
