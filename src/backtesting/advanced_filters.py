"""
Advanced Backtesting Filters and Trade Analytics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def _get_pnl(trade: Any) -> float:
    return trade.pnl if hasattr(trade, "pnl") else float(trade)


def _get_symbol(trade: Any) -> Optional[str]:
    return getattr(trade, "symbol", None)


def _get_entry_time(trade: Any) -> Optional[datetime]:
    return getattr(trade, "entry_time", None)


def _get_exit_time(trade: Any) -> Optional[datetime]:
    return getattr(trade, "exit_time", None)


class BacktestFilter:
    """Provides filtering and analytics utilities for backtest trade lists."""

    def filter_by_date_range(self, trades: List[Any], start: datetime, end: datetime) -> List[Any]:
        """Return trades whose entry_time falls within [start, end] (inclusive)."""
        return [t for t in trades if (e := _get_entry_time(t)) is not None and start <= e <= end]

    def filter_by_min_pnl(self, trades: List[Any], min_pnl: float) -> List[Any]:
        return [t for t in trades if _get_pnl(t) >= min_pnl]

    def filter_by_symbol(self, trades: List[Any], symbols: List[str]) -> List[Any]:
        symbol_set = set(symbols)
        return [t for t in trades if _get_symbol(t) in symbol_set]

    def filter_by_win_loss(self, trades: List[Any], wins_only: bool = True) -> List[Any]:
        if wins_only:
            return [t for t in trades if _get_pnl(t) > 0]
        return [t for t in trades if _get_pnl(t) <= 0]

    def compute_trade_analytics(self, trades: List[Any]) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0, "avg_pnl": 0.0, "total_pnl": 0.0,
                "best_trade": 0.0, "worst_trade": 0.0,
                "avg_duration_seconds": None, "win_count": 0, "loss_count": 0, "win_rate": 0.0,
            }
        pnls = [_get_pnl(t) for t in trades]
        total_pnl = sum(pnls)
        win_count = sum(1 for p in pnls if p > 0)
        durations = []
        for trade in trades:
            entry, exit_ = _get_entry_time(trade), _get_exit_time(trade)
            if entry is not None and exit_ is not None:
                durations.append((exit_ - entry).total_seconds())
        return {
            "total_trades": len(trades),
            "avg_pnl": total_pnl / len(pnls),
            "total_pnl": total_pnl,
            "best_trade": max(pnls),
            "worst_trade": min(pnls),
            "avg_duration_seconds": sum(durations) / len(durations) if durations else None,
            "win_count": win_count,
            "loss_count": len(pnls) - win_count,
            "win_rate": win_count / len(pnls),
        }
