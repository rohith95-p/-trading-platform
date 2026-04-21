"""
Core interfaces for pluggable architecture
"""

from .exchange_connector import ExchangeConnector, Order, Trade, Position, Balance
from .strategy_executor import StrategyExecutor, Signal, MarketData
from .backtester import Backtester, BacktestTrade, BacktestMetrics, BacktestResult
from .drl_agent import DRLAgent, State, Action, Experience

__all__ = [
    # Interfaces
    "ExchangeConnector",
    "StrategyExecutor",
    "Backtester",
    "DRLAgent",
    # ExchangeConnector data classes
    "Order",
    "Trade",
    "Position",
    "Balance",
    # StrategyExecutor data classes
    "Signal",
    "MarketData",
    # Backtester data classes
    "BacktestTrade",
    "BacktestMetrics",
    "BacktestResult",
    # DRLAgent data classes
    "State",
    "Action",
    "Experience",
]
