"""
Risk Manager - enforces position, exposure, and leverage limits.
"""

from typing import Dict, List
from src.interfaces.exchange_connector import Order, Position
import logging

log = logging.getLogger(__name__)

# Default risk limits
MAX_POSITION_PCT = 0.10   # 10% of portfolio per position
MAX_EXPOSURE_PCT = 0.50   # 50% total portfolio exposure
MAX_LEVERAGE = 10.0       # 10x leverage cap


class RiskManager:
    """
    Validates orders and monitors portfolio risk limits.

    Limits enforced:
    - Single position: max 10% of portfolio value
    - Total exposure: max 50% of portfolio value
    - Leverage: max 10x
    """

    def __init__(
        self,
        max_position_pct: float = MAX_POSITION_PCT,
        max_exposure_pct: float = MAX_EXPOSURE_PCT,
        max_leverage: float = MAX_LEVERAGE,
    ):
        self.max_position_pct = max_position_pct
        self.max_exposure_pct = max_exposure_pct
        self.max_leverage = max_leverage

    # -------------------------------------------------------------------------
    # Order validation
    # -------------------------------------------------------------------------

    def validate_order(
        self,
        order: Order,
        portfolio_value: float,
        current_positions: List[Position],
    ) -> None:
        """
        Validate an order against risk limits.

        Args:
            order: The order to validate.
            portfolio_value: Current total portfolio value.
            current_positions: List of currently open positions.

        Raises:
            ValueError: If any risk limit would be breached.
        """
        if portfolio_value <= 0:
            raise ValueError("Portfolio value must be positive")

        # Determine order notional value
        price = order.price if order.price else 0.0
        notional = order.size * price

        # Leverage check
        leverage = order.leverage or 1.0
        if leverage > self.max_leverage:
            raise ValueError(
                f"Leverage {leverage}x exceeds maximum allowed {self.max_leverage}x"
            )

        # Position size check (notional / portfolio)
        if portfolio_value > 0 and notional > 0:
            position_pct = notional / portfolio_value
            if position_pct > self.max_position_pct:
                raise ValueError(
                    f"Order notional {notional:.2f} is {position_pct:.1%} of portfolio, "
                    f"exceeds {self.max_position_pct:.0%} limit"
                )

        # Total exposure check (existing + new order)
        current_exposure = sum(
            abs(p.size * p.current_price) for p in current_positions
        )
        new_exposure = current_exposure + notional
        exposure_pct = new_exposure / portfolio_value if portfolio_value > 0 else 0.0

        if exposure_pct > self.max_exposure_pct:
            raise ValueError(
                f"Total exposure {new_exposure:.2f} ({exposure_pct:.1%}) would exceed "
                f"{self.max_exposure_pct:.0%} limit"
            )

        log.info(
            f"Order validated: {order.symbol} {order.side} {order.size} "
            f"(notional={notional:.2f}, exposure={exposure_pct:.1%})"
        )

    # -------------------------------------------------------------------------
    # Limit status
    # -------------------------------------------------------------------------

    def check_limits(
        self,
        positions: List[Position],
        portfolio_value: float,
    ) -> Dict[str, object]:
        """
        Return current limit utilisation for all open positions.

        Args:
            positions: List of open positions.
            portfolio_value: Current total portfolio value.

        Returns:
            Dict with limit status information.
        """
        if portfolio_value <= 0:
            return {
                "portfolio_value": portfolio_value,
                "total_exposure": 0.0,
                "exposure_pct": 0.0,
                "exposure_limit": self.max_exposure_pct,
                "exposure_ok": True,
                "positions": [],
                "max_position_pct": self.max_position_pct,
                "max_leverage": self.max_leverage,
            }

        position_details = []
        total_exposure = 0.0

        for pos in positions:
            notional = abs(pos.size * pos.current_price)
            pct = notional / portfolio_value
            total_exposure += notional
            position_details.append(
                {
                    "symbol": pos.symbol,
                    "notional": notional,
                    "pct_of_portfolio": pct,
                    "within_limit": pct <= self.max_position_pct,
                }
            )

        exposure_pct = total_exposure / portfolio_value

        return {
            "portfolio_value": portfolio_value,
            "total_exposure": total_exposure,
            "exposure_pct": exposure_pct,
            "exposure_limit": self.max_exposure_pct,
            "exposure_ok": exposure_pct <= self.max_exposure_pct,
            "positions": position_details,
            "max_position_pct": self.max_position_pct,
            "max_leverage": self.max_leverage,
        }
