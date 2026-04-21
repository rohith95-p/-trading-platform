"""
Pandas-based vectorized backtester
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from src.interfaces import Backtester
from src.interfaces.backtester import BacktestResult, BacktestMetrics, BacktestTrade

class PandasBacktester(Backtester):
    """Vectorized backtester using pandas"""
    
    def __init__(self):
        super().__init__("pandas")
    
    def backtest(self, strategy_name: str, historical_data: List[Dict[str, Any]], config: Dict[str, Any]) -> BacktestResult:
        """Run backtest"""
        df = pd.DataFrame(historical_data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        
        # Generate signals (placeholder)
        df['signal'] = 0
        df.loc[df.index[::10], 'signal'] = 1  # Buy every 10 bars
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # Calculate equity curve
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        equity_curve = df['cumulative_returns'].tolist()
        
        # Generate trades
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        
        for idx, row in df.iterrows():
            if row['signal'] == 1 and not in_position:
                in_position = True
                entry_price = row['close']
                entry_time = row['datetime']
            elif row['signal'] == 0 and in_position:
                in_position = False
                exit_price = row['close']
                pnl = exit_price - entry_price
                pnl_percent = (pnl / entry_price) * 100
                
                trades.append(BacktestTrade(
                    entry_time=entry_time,
                    exit_time=row['datetime'],
                    entry_price=entry_price,
                    exit_price=exit_price,
                    size=1.0,
                    pnl=pnl,
                    pnl_percent=pnl_percent
                ))
        
        # Compute metrics
        metrics = self.compute_metrics(trades)
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=df['datetime'].iloc[0],
            end_date=df['datetime'].iloc[-1],
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
    
    def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
        """Compute performance metrics"""
        if not trades:
            return BacktestMetrics(
                total_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                trades_count=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0.0,
                avg_loss=0.0
            )
        
        pnls = [t.pnl for t in trades]
        total_return = sum(pnls)
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = sum([t.pnl for t in winning_trades]) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum([t.pnl for t in losing_trades]) / len(losing_trades)) if losing_trades else 0
        
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = np.array([t.pnl_percent for t in trades])
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Max drawdown
        cumulative = np.cumprod(1 + returns / 100)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        return BacktestMetrics(
            total_return=total_return,
            annual_return=total_return * 252 / len(trades) if trades else 0,
            sharpe_ratio=float(sharpe_ratio),
            max_drawdown=float(max_drawdown),
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades_count=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss
        )
