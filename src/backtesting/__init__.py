"""Execution-realistic backtesting for Ultra Core.

Design rule that governs this package:

    The simulator must never re-implement live trading logic.

Strategy signals come from `src.strategies.*` and stop/size/trail decisions come
from `src.core.risk_manager.RiskManager` -- the same modules the live bot runs.
Anything this package computes itself (fills, spread, intrabar path) is
execution mechanics that MT5 owns in production and that must therefore be
modelled here explicitly rather than assumed away.
"""

from src.backtesting.costs import CostModel
from src.backtesting.data import BarSet, DataManifest, load_bars
from src.backtesting.metrics import TradeStats, summarize

__all__ = [
    "BarSet",
    "CostModel",
    "DataManifest",
    "TradeStats",
    "load_bars",
    "summarize",
]
