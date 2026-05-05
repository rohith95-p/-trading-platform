"""
Position Sizer - Kelly criterion position sizing with safety cap.
"""

import logging

log = logging.getLogger(__name__)

KELLY_CAP = 0.25  # Quarter-Kelly safety cap


class PositionSizer:
    """
    Calculates position sizes using the Kelly criterion.

    The raw Kelly fraction is capped at 0.25 (quarter-Kelly) to reduce
    variance and protect against estimation errors.
    """

    def __init__(self, kelly_cap: float = KELLY_CAP):
        """
        Args:
            kelly_cap: Maximum allowed Kelly fraction (default 0.25).
        """
        if not (0 < kelly_cap <= 1):
            raise ValueError("kelly_cap must be between 0 (exclusive) and 1 (inclusive)")
        self.kelly_cap = kelly_cap

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """
        Compute the Kelly fraction for a given edge.

        Formula: f* = (win_rate / avg_loss) - ((1 - win_rate) / avg_win)
        Simplified: f* = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        The result is clamped to [0, kelly_cap].

        Args:
            win_rate: Probability of a winning trade (0-1).
            avg_win: Average gain per winning trade (positive).
            avg_loss: Average loss per losing trade (positive magnitude).

        Returns:
            Kelly fraction in [0, kelly_cap].

        Raises:
            ValueError: If inputs are out of valid range.
        """
        if not (0.0 <= win_rate <= 1.0):
            raise ValueError(f"win_rate must be between 0 and 1, got {win_rate}")
        if avg_win <= 0:
            raise ValueError(f"avg_win must be positive, got {avg_win}")
        if avg_loss <= 0:
            raise ValueError(f"avg_loss must be positive, got {avg_loss}")

        # Kelly formula: f* = p/q_loss - (1-p)/q_win  where q = ratio
        # Equivalent: f* = (p * avg_win - (1-p) * avg_loss) / avg_win
        raw_kelly = (win_rate * avg_win - (1.0 - win_rate) * avg_loss) / avg_win

        # Clamp to [0, kelly_cap]
        fraction = max(0.0, min(raw_kelly, self.kelly_cap))
        log.debug(
            f"Kelly: win_rate={win_rate}, avg_win={avg_win}, avg_loss={avg_loss} "
            f"-> raw={raw_kelly:.4f}, capped={fraction:.4f}"
        )
        return fraction

    def calculate_position_size(
        self,
        kelly_fraction: float,
        portfolio_value: float,
        price: float,
    ) -> float:
        """
        Convert a Kelly fraction into a number of units to buy.

        Args:
            kelly_fraction: Fraction of portfolio to risk (0-1).
            portfolio_value: Total portfolio value in base currency.
            price: Current price per unit of the asset.

        Returns:
            Number of units (float, >= 0).

        Raises:
            ValueError: If inputs are invalid.
        """
        if not (0.0 <= kelly_fraction <= 1.0):
            raise ValueError(f"kelly_fraction must be between 0 and 1, got {kelly_fraction}")
        if portfolio_value < 0:
            raise ValueError(f"portfolio_value must be non-negative, got {portfolio_value}")
        if price <= 0:
            raise ValueError(f"price must be positive, got {price}")

        capital_to_deploy = kelly_fraction * portfolio_value
        units = capital_to_deploy / price
        log.debug(
            f"Position size: fraction={kelly_fraction}, portfolio={portfolio_value}, "
            f"price={price} -> units={units:.4f}"
        )
        return units
