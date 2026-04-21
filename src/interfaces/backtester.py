"""
Backtester interface - for backtesting engines
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BacktestTrade:
    """Trade in backtest"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float

@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float

@dataclass
class BacktestResult:
    """Complete backtest result"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    metrics: BacktestMetrics
    trades: List[BacktestTrade]
    equity_curve: List[float]

class Backtester(ABC):
    """
    Abstract base class for backtesting engines.
    All backtester implementations must inherit from this class.
    """
    
    def __init__(self, name: str):
        """
        Initialize backtester
        
        Args:
            name: Backtester name (e.g., 'pandas', 'vectorbt')
        """
        self.name = name
    
    @abstractmethod
    def backtest(
        self,
        strategy_name: str,
        historical_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> BacktestResult:
        """
        Run backtest
        
        Args:
            strategy_name: Name of strategy to backtest
            historical_data: List of OHLCV data
            config: Backtest configuration
            
        Returns:
            BacktestResult object
        """
        pass
    
    @abstractmethod
    def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
        """
        Compute performance metrics
        
        Args:
            trades: List of trades
            
        Returns:
            BacktestMetrics object
        """
        pass
