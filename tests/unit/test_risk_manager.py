"""
Property-based and unit tests for the Risk Management layer.

Tests:
- RiskManager: position limit, exposure limit, leverage limit
- PositionSizer: Kelly fraction always in [0, 0.25]
- CircuitBreaker: triggers at correct thresholds
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from dataclasses import dataclass
from datetime import datetime

from src.interfaces.exchange_connector import Order, Position
from src.risk.manager import RiskManager
from src.risk.position_sizer import PositionSizer
from src.risk.circuit_breaker import CircuitBreaker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_position(
    symbol: str = "BTC",
    size: float = 1.0,
    entry_price: float = 100.0,
    current_price: float = 100.0,
    pnl: float = 0.0,
    pnl_percent: float = 0.0,
) -> Position:
    return Position(
        id="pos-1",
        symbol=symbol,
        side="long",
        size=size,
        entry_price=entry_price,
        current_price=current_price,
        pnl=pnl,
        pnl_percent=pnl_percent,
    )


def make_order(
    symbol: str = "ETH",
    size: float = 1.0,
    price: float = 100.0,
    leverage: float = 1.0,
) -> Order:
    return Order(
        symbol=symbol,
        side="buy",
        type="limit",
        size=size,
        price=price,
        leverage=leverage,
    )


# ===========================================================================
# RiskManager Unit Tests
# ===========================================================================


class TestRiskManagerUnit:
    """Concrete unit tests for RiskManager."""

    def test_valid_order_passes(self):
        """A small order well within limits should not raise."""
        rm = RiskManager()
        order = make_order(size=1.0, price=50.0)  # notional=50, 5% of 1000
        rm.validate_order(order, portfolio_value=1000.0, current_positions=[])

    def test_position_limit_exceeded(self):
        """Order exceeding 10% of portfolio should raise ValueError."""
        rm = RiskManager()
        order = make_order(size=1.0, price=150.0)  # notional=150, 15% of 1000
        with pytest.raises(ValueError, match="exceeds"):
            rm.validate_order(order, portfolio_value=1000.0, current_positions=[])

    def test_exposure_limit_exceeded(self):
        """Adding an order that pushes total exposure above 50% should raise."""
        rm = RiskManager()
        # Existing position: 45% of portfolio
        existing = make_position(size=1.0, current_price=450.0)
        # New order: 9% of portfolio (within position limit but pushes total over 50%)
        order = make_order(size=1.0, price=90.0)
        with pytest.raises(ValueError, match="exposure"):
            rm.validate_order(order, portfolio_value=1000.0, current_positions=[existing])

    def test_leverage_limit_exceeded(self):
        """Order with leverage > 10x should raise ValueError."""
        rm = RiskManager()
        order = make_order(size=1.0, price=50.0, leverage=11.0)
        with pytest.raises(ValueError, match="[Ll]everage"):
            rm.validate_order(order, portfolio_value=1000.0, current_positions=[])

    def test_leverage_at_limit_passes(self):
        """Order with exactly 10x leverage should pass."""
        rm = RiskManager()
        order = make_order(size=1.0, price=50.0, leverage=10.0)
        rm.validate_order(order, portfolio_value=1000.0, current_positions=[])

    def test_check_limits_empty_portfolio(self):
        """check_limits with no positions should return safe status."""
        rm = RiskManager()
        result = rm.check_limits([], portfolio_value=1000.0)
        assert result["exposure_ok"] is True
        assert result["total_exposure"] == 0.0
        assert result["exposure_pct"] == 0.0

    def test_check_limits_with_positions(self):
        """check_limits should correctly compute exposure percentage."""
        rm = RiskManager()
        pos = make_position(size=2.0, current_price=100.0)  # notional=200, 20% of 1000
        result = rm.check_limits([pos], portfolio_value=1000.0)
        assert result["exposure_ok"] is True
        assert abs(result["exposure_pct"] - 0.20) < 1e-9

    def test_invalid_portfolio_value(self):
        """validate_order with portfolio_value <= 0 should raise."""
        rm = RiskManager()
        order = make_order()
        with pytest.raises(ValueError):
            rm.validate_order(order, portfolio_value=0.0, current_positions=[])


# ===========================================================================
# RiskManager Property-Based Tests
# ===========================================================================


class TestRiskManagerProperties:
    """
    **Validates: Requirements 11.2**

    Property: position limit and total exposure limit are never exceeded
    when orders are validated through RiskManager.
    """

    @given(
        portfolio_value=st.floats(min_value=1000.0, max_value=1_000_000.0),
        order_size=st.floats(min_value=0.01, max_value=100.0),
        order_price=st.floats(min_value=1.0, max_value=10_000.0),
    )
    @settings(max_examples=200)
    def test_position_limit_never_exceeded(
        self, portfolio_value: float, order_size: float, order_price: float
    ):
        """
        **Validates: Requirements 11.2**

        Property: If validate_order does NOT raise, the order notional
        must be <= 10% of portfolio value.
        """
        rm = RiskManager()
        order = make_order(size=order_size, price=order_price)
        notional = order_size * order_price

        try:
            rm.validate_order(order, portfolio_value=portfolio_value, current_positions=[])
            # If no exception, notional must be within limit
            assert notional / portfolio_value <= rm.max_position_pct + 1e-9
        except ValueError:
            # Exception is expected when limit is exceeded - that's correct behaviour
            pass

    @given(
        portfolio_value=st.floats(min_value=1000.0, max_value=1_000_000.0),
        existing_notional=st.floats(min_value=0.0, max_value=400.0),
        order_size=st.floats(min_value=0.01, max_value=10.0),
        order_price=st.floats(min_value=1.0, max_value=100.0),
    )
    @settings(max_examples=200)
    def test_total_exposure_limit_enforced(
        self,
        portfolio_value: float,
        existing_notional: float,
        order_size: float,
        order_price: float,
    ):
        """
        **Validates: Requirements 11.2**

        Property: If validate_order does NOT raise, total exposure
        (existing + new) must be <= 50% of portfolio value.
        """
        rm = RiskManager()
        # Build an existing position with the given notional
        existing = make_position(size=existing_notional, current_price=1.0)
        order = make_order(size=order_size, price=order_price)
        new_notional = order_size * order_price

        try:
            rm.validate_order(
                order, portfolio_value=portfolio_value, current_positions=[existing]
            )
            total_exposure = existing_notional + new_notional
            assert total_exposure / portfolio_value <= rm.max_exposure_pct + 1e-9
        except ValueError:
            pass  # Correct: limit would be breached

    @given(leverage=st.floats(min_value=0.1, max_value=50.0))
    @settings(max_examples=100)
    def test_leverage_limit_enforced(self, leverage: float):
        """
        **Validates: Requirements 11.2**

        Property: If validate_order does NOT raise, leverage must be <= 10x.
        """
        rm = RiskManager()
        order = make_order(size=1.0, price=50.0, leverage=leverage)  # 5% notional

        try:
            rm.validate_order(order, portfolio_value=1000.0, current_positions=[])
            assert leverage <= rm.max_leverage + 1e-9
        except ValueError:
            pass  # Correct: leverage exceeded


# ===========================================================================
# PositionSizer Unit Tests
# ===========================================================================


class TestPositionSizerUnit:
    """Concrete unit tests for PositionSizer."""

    def test_kelly_positive_edge(self):
        """Positive edge should produce a positive fraction."""
        ps = PositionSizer()
        fraction = ps.kelly_criterion(win_rate=0.6, avg_win=1.0, avg_loss=1.0)
        assert fraction > 0.0

    def test_kelly_no_edge(self):
        """Zero edge (win_rate=0.5, equal win/loss) should produce 0."""
        ps = PositionSizer()
        fraction = ps.kelly_criterion(win_rate=0.5, avg_win=1.0, avg_loss=1.0)
        assert fraction == 0.0

    def test_kelly_negative_edge_clamped_to_zero(self):
        """Negative edge should be clamped to 0."""
        ps = PositionSizer()
        fraction = ps.kelly_criterion(win_rate=0.3, avg_win=1.0, avg_loss=2.0)
        assert fraction == 0.0

    def test_kelly_capped_at_quarter(self):
        """Very high edge should be capped at 0.25."""
        ps = PositionSizer()
        fraction = ps.kelly_criterion(win_rate=0.99, avg_win=10.0, avg_loss=1.0)
        assert fraction == pytest.approx(0.25)

    def test_calculate_position_size(self):
        """Position size should equal (fraction * portfolio) / price."""
        ps = PositionSizer()
        units = ps.calculate_position_size(
            kelly_fraction=0.10, portfolio_value=10_000.0, price=100.0
        )
        assert units == pytest.approx(10.0)

    def test_zero_kelly_fraction_gives_zero_units(self):
        """Zero Kelly fraction should result in zero units."""
        ps = PositionSizer()
        units = ps.calculate_position_size(
            kelly_fraction=0.0, portfolio_value=10_000.0, price=100.0
        )
        assert units == 0.0

    def test_invalid_win_rate_raises(self):
        with pytest.raises(ValueError):
            PositionSizer().kelly_criterion(win_rate=1.5, avg_win=1.0, avg_loss=1.0)

    def test_invalid_avg_win_raises(self):
        with pytest.raises(ValueError):
            PositionSizer().kelly_criterion(win_rate=0.6, avg_win=0.0, avg_loss=1.0)

    def test_invalid_avg_loss_raises(self):
        with pytest.raises(ValueError):
            PositionSizer().kelly_criterion(win_rate=0.6, avg_win=1.0, avg_loss=-1.0)


# ===========================================================================
# PositionSizer Property-Based Tests
# ===========================================================================


class TestPositionSizerProperties:
    """
    **Validates: Requirements 11.3**

    Property: Kelly fraction is always between 0 and 0.25.
    """

    @given(
        win_rate=st.floats(min_value=0.0, max_value=1.0),
        avg_win=st.floats(min_value=0.01, max_value=100.0),
        avg_loss=st.floats(min_value=0.01, max_value=100.0),
    )
    @settings(max_examples=500)
    def test_kelly_fraction_always_in_range(
        self, win_rate: float, avg_win: float, avg_loss: float
    ):
        """
        **Validates: Requirements 11.3**

        Property: kelly_criterion always returns a value in [0, 0.25].
        """
        ps = PositionSizer()
        fraction = ps.kelly_criterion(win_rate=win_rate, avg_win=avg_win, avg_loss=avg_loss)
        assert 0.0 <= fraction <= ps.kelly_cap + 1e-12

    @given(
        kelly_fraction=st.floats(min_value=0.0, max_value=0.25),
        portfolio_value=st.floats(min_value=100.0, max_value=1_000_000.0),
        price=st.floats(min_value=0.01, max_value=100_000.0),
    )
    @settings(max_examples=200)
    def test_position_size_non_negative(
        self, kelly_fraction: float, portfolio_value: float, price: float
    ):
        """
        **Validates: Requirements 11.3**

        Property: calculate_position_size always returns a non-negative number.
        """
        ps = PositionSizer()
        units = ps.calculate_position_size(
            kelly_fraction=kelly_fraction,
            portfolio_value=portfolio_value,
            price=price,
        )
        assert units >= 0.0


# ===========================================================================
# CircuitBreaker Unit Tests
# ===========================================================================


class TestCircuitBreakerUnit:
    """Concrete unit tests for CircuitBreaker."""

    def test_not_triggered_initially(self):
        cb = CircuitBreaker()
        assert cb.is_triggered() is False

    def test_position_loss_below_threshold(self):
        """Position with 10% loss should NOT trigger (threshold=20%)."""
        cb = CircuitBreaker()
        pos = make_position(entry_price=100.0, current_price=90.0, pnl=-10.0, pnl_percent=-10.0)
        assert cb.check_position_loss(pos) is False

    def test_position_loss_at_threshold(self):
        """Position with exactly 20% loss should trigger."""
        cb = CircuitBreaker()
        pos = make_position(entry_price=100.0, current_price=80.0, pnl=-20.0, pnl_percent=-20.0)
        assert cb.check_position_loss(pos) is True

    def test_position_loss_above_threshold(self):
        """Position with 30% loss should trigger."""
        cb = CircuitBreaker()
        pos = make_position(entry_price=100.0, current_price=70.0, pnl=-30.0, pnl_percent=-30.0)
        assert cb.check_position_loss(pos) is True

    def test_daily_drawdown_below_threshold(self):
        """5% daily loss should NOT halt trading (threshold=10%)."""
        cb = CircuitBreaker()
        assert cb.check_daily_drawdown(daily_pnl=-50.0, portfolio_value=1000.0) is False
        assert cb.is_triggered() is False

    def test_daily_drawdown_at_threshold(self):
        """Exactly 10% daily loss should halt trading."""
        cb = CircuitBreaker()
        assert cb.check_daily_drawdown(daily_pnl=-100.0, portfolio_value=1000.0) is True
        assert cb.is_triggered() is True

    def test_daily_drawdown_above_threshold(self):
        """15% daily loss should halt trading."""
        cb = CircuitBreaker()
        assert cb.check_daily_drawdown(daily_pnl=-150.0, portfolio_value=1000.0) is True

    def test_reset_clears_state(self):
        """reset() should clear triggered flag and daily P&L."""
        cb = CircuitBreaker()
        cb.check_daily_drawdown(daily_pnl=-200.0, portfolio_value=1000.0)
        assert cb.is_triggered() is True
        cb.reset()
        assert cb.is_triggered() is False
        assert cb.daily_pnl == 0.0

    def test_record_trade_accumulates_pnl(self):
        """record_trade should accumulate daily P&L."""
        cb = CircuitBreaker()
        cb.record_trade(100.0)
        cb.record_trade(-50.0)
        assert cb.daily_pnl == pytest.approx(50.0)
        assert cb.trade_count == 2

    def test_positive_pnl_does_not_trigger(self):
        """Positive daily P&L should never trigger the circuit breaker."""
        cb = CircuitBreaker()
        assert cb.check_daily_drawdown(daily_pnl=500.0, portfolio_value=1000.0) is False


# ===========================================================================
# CircuitBreaker Property-Based Tests
# ===========================================================================


class TestCircuitBreakerProperties:
    """
    **Validates: Requirements 11.4**

    Property: circuit breaker triggers at correct thresholds.
    """

    @given(
        loss_pct=st.floats(min_value=0.0, max_value=1.0),
        portfolio_value=st.floats(min_value=100.0, max_value=1_000_000.0),
    )
    @settings(max_examples=300)
    def test_daily_drawdown_triggers_correctly(
        self, loss_pct: float, portfolio_value: float
    ):
        """
        **Validates: Requirements 11.4**

        Property: check_daily_drawdown returns True iff loss_pct >= threshold.
        """
        cb = CircuitBreaker()
        threshold = cb.daily_drawdown_threshold
        daily_pnl = -loss_pct * portfolio_value

        result = cb.check_daily_drawdown(daily_pnl, portfolio_value)

        if loss_pct >= threshold:
            assert result is True
        else:
            assert result is False

    @given(
        pnl_percent=st.floats(min_value=-100.0, max_value=100.0),
    )
    @settings(max_examples=300)
    def test_position_loss_triggers_correctly(self, pnl_percent: float):
        """
        **Validates: Requirements 11.4**

        Property: check_position_loss returns True iff pnl_percent <= -threshold*100.
        """
        cb = CircuitBreaker()
        threshold = cb.position_loss_threshold  # 0.20
        pos = make_position(
            entry_price=100.0,
            current_price=max(0.01, 100.0 * (1 + pnl_percent / 100.0)),
            pnl=pnl_percent,
            pnl_percent=pnl_percent,
        )

        result = cb.check_position_loss(pos)
        loss_fraction = -pnl_percent / 100.0

        if loss_fraction >= threshold:
            assert result is True
        else:
            assert result is False
