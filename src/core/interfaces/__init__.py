"""
Core interfaces for the Unified Trading Intelligence Platform

This module exports all core interfaces that define the pluggable architecture.
"""

# Python interfaces
from .backtester import Backtester, BacktestMetrics
from .drl_agent import DRLAgent
from .exchange_connector import (
    ExchangeConnector,
    Market,
    OrderBook,
    Ticker,
    Order,
    Trade,
    Position,
    OrderSide,
    OrderType,
    TimeInForce,
    ExchangeType,
)

__all__ = [
    'Backtester',
    'BacktestMetrics',
    'DRLAgent',
    'ExchangeConnector',
    'Market',
    'OrderBook',
    'Ticker',
    'Order',
    'Trade',
    'Position',
    'OrderSide',
    'OrderType',
    'TimeInForce',
    'ExchangeType',
]
