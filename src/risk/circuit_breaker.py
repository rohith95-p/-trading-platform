"""
Circuit Breaker - auto-close positions on large losses and halt trading on daily drawdown.
"""

from typing import List
from src.interfaces.exchange_connector import Position
import logging

log = logging.getLogger(__name__)

DEFAULT_POSITION_LOSS_THRESHOLD = 0.20   # 20% loss on a single position
DEFAULT_DAILY_DRAWDOWN_THRESHOLD = 0.10  # 10% daily drawdown on portfolio


class CircuitBreaker:
    """
    Monitors trading losses and triggers protective halts.

    Two triggers:
    - Position loss: individual position down >= 20% -> should close
    - Daily drawdown: cumulative daily P&L down >= 10% of portfolio -> halt trading
    """

    def __init__(
        self,
        position_loss_threshold: float = DEFAULT_POSITION_LOSS_THRESHOLD,
        daily_drawdown_threshold: float = DEFAULT_DAILY_DRAWDOWN_THRESHOLD,
    ):
        self.position_loss_threshold = position_loss_threshold
        self.daily_drawdown_threshold = daily_drawdown_threshold
        self._triggered = False
        self._daily_pnl: float = 0.0
        self._trade_history: List[float] = []

    # -------------------------------------------------------------------------
    # Checks
    # -------------------------------------------------------------------------

    def check_position_loss(
        self,
        position: Position,
        threshold: float = DEFAULT_POSITION_LOSS_THRESHOLD,
    ) -> bool:
        """
        Check whether a single position has lost more than the threshold.

        Args:
            position: The position to evaluate.
            threshold: Loss fraction that triggers closure (default 0.20 = 20%).

        Returns:
            True if the position should be closed, False otherwise.
        """
        if position.entry_price <= 0:
            return False

        loss_pct = -position.pnl_percent / 100.0  # pnl_percent is signed; loss is negative
        should_close = loss_pct >= threshold
        if should_close:
            log.warning(
                f"Circuit breaker: position {position.symbol} loss {loss_pct:.1%} "
                f">= threshold {threshold:.1%}"
            )
        return should_close

    def check_daily_drawdown(
        self,
        daily_pnl: float,
        portfolio_value: float,
        threshold: float = DEFAULT_DAILY_DRAWDOWN_THRESHOLD,
    ) -> bool:
        """
        Check whether the daily P&L drawdown exceeds the threshold.

        Args:
            daily_pnl: Cumulative P&L for the current trading day (negative = loss).
            portfolio_value: Portfolio value at the start of the day.
            threshold: Drawdown fraction that halts trading (default 0.10 = 10%).

        Returns:
            True if trading should be halted, False otherwise.
        """
        if portfolio_value <= 0:
            return False

        drawdown_pct = -daily_pnl / portfolio_value  # positive when losing
        should_halt = drawdown_pct >= threshold

        if should_halt:
            self._triggered = True
            log.warning(
                f"Circuit breaker TRIGGERED: daily drawdown {drawdown_pct:.1%} "
                f">= threshold {threshold:.1%}"
            )
        return should_halt

    # -------------------------------------------------------------------------
    # State management
    # -------------------------------------------------------------------------

    def record_trade(self, pnl: float) -> None:
        """
        Record a completed trade's P&L and update the daily running total.

        Args:
            pnl: Profit or loss from the trade (negative = loss).
        """
        self._trade_history.append(pnl)
        self._daily_pnl += pnl
        log.debug(f"Trade recorded: pnl={pnl:.2f}, daily_pnl={self._daily_pnl:.2f}")

    def is_triggered(self) -> bool:
        """Return True if the circuit breaker has been triggered."""
        return self._triggered

    def reset(self) -> None:
        """Reset the circuit breaker state (e.g., at start of new trading day)."""
        self._triggered = False
        self._daily_pnl = 0.0
        self._trade_history = []
        log.info("Circuit breaker reset")

    @property
    def daily_pnl(self) -> float:
        """Current cumulative daily P&L."""
        return self._daily_pnl

    @property
    def trade_count(self) -> int:
        """Number of trades recorded today."""
        return len(self._trade_history)
