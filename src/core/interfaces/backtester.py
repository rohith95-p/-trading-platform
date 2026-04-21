"""
Backtester Interface

Enables pluggable backtesting engines with consistent APIs for strategy validation.

Implements Requirement 1 (Pluggable Architecture) and Requirement 8 (Vectorized Backtesting)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class BacktestMetrics:
    """Performance metrics from a backtest run"""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: float
    profit_factor: float


class Backtester(ABC):
    """Abstract base class for backtesting engines"""
    
    def __init__(self, backtester_type: str):
        """
        Initialize backtester
        
        Args:
            backtester_type: Type of backtester ('event-driven' or 'vectorized')
        """
        self.type = backtester_type
    
    @abstractmethod
    def run(self, strategy: Any, data: Any, params: Dict) -> Dict:
        """
        Run backtest and return results
        
        Args:
            strategy: Strategy implementation to backtest
            data: Historical price data
            params: Strategy parameters
            
        Returns:
            Dictionary containing backtest results with metrics and trades
        """
        pass
    
    @abstractmethod
    def optimize(self, strategy: Any, data: Any, param_grid: Dict) -> Dict:
        """
        Optimize strategy parameters
        
        Args:
            strategy: Strategy implementation to optimize
            data: Historical price data
            param_grid: Grid of parameters to test
            
        Returns:
            Dictionary containing optimization results with best parameters
        """
        pass
    
    @abstractmethod
    def get_metrics(self, result: Dict) -> BacktestMetrics:
        """
        Compute performance metrics from backtest result
        
        Args:
            result: Backtest result dictionary
            
        Returns:
            BacktestMetrics object with computed metrics
        """
        pass
