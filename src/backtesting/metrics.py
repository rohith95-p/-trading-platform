"""
Standalone metrics computation module for backtesting.
"""

import math
from typing import List, Any


def compute_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Compute annualised Sharpe ratio.

    Args:
        returns: List of period returns (e.g. daily pct returns as decimals).
        risk_free_rate: Risk-free rate per period (default 0.0).

    Returns:
        Sharpe ratio, or 0.0 when it cannot be computed.
    """
    if not returns:
        return 0.0

    n = len(returns)
    mean = sum(returns) / n - risk_free_rate
    if n < 2:
        return 0.0

    variance = sum((r - (sum(returns) / n)) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(variance)

    if std == 0.0:
        return 0.0

    return (mean / std) * math.sqrt(252)


def compute_max_drawdown(equity_curve: List[float]) -> float:
    """
    Compute maximum drawdown from an equity curve.

    Returns:
        Maximum drawdown as a non-positive fraction (e.g. -0.25 = -25%).
        Returns 0.0 for empty or single-element curves.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd

    return max_dd


def compute_win_rate(trades: List[Any]) -> float:
    """
    Compute win rate from a list of trades or pnl values.

    Returns:
        Win rate in [0, 1]. Returns 0.0 for empty list.
    """
    if not trades:
        return 0.0

    def _pnl(t: Any) -> float:
        return t.pnl if hasattr(t, "pnl") else float(t)

    wins = sum(1 for t in trades if _pnl(t) > 0)
    return wins / len(trades)


def compute_profit_factor(trades: List[Any]) -> float:
    """
    Compute profit factor (gross profit / gross loss).

    Returns:
        Profit factor >= 0. Returns 0.0 when there are no losing trades.
    """
    if not trades:
        return 0.0

    def _pnl(t: Any) -> float:
        return t.pnl if hasattr(t, "pnl") else float(t)

    gross_profit = sum(_pnl(t) for t in trades if _pnl(t) > 0)
    gross_loss = abs(sum(_pnl(t) for t in trades if _pnl(t) < 0))

    if gross_loss == 0.0:
        return 0.0

    return gross_profit / gross_loss


def compute_annual_return(total_return: float, n_days: int) -> float:
    """
    Annualise a total return over n_days using CAGR formula.

    Returns:
        Annualised return as a fraction. Returns 0.0 for n_days <= 0.
    """
    if n_days <= 0:
        return 0.0

    growth = 1.0 + total_return
    if growth <= 0:
        return -1.0

    return growth ** (365.0 / n_days) - 1.0
