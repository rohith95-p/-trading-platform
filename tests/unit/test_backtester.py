"""
Property-based tests for backtesting metrics.

**Validates: Requirements 14.4, 14.8**
"""

import math
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.backtesting.metrics import (
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_win_rate,
    compute_profit_factor,
    compute_annual_return,
)

finite_floats = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
positive_floats = st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False)
non_empty_returns = st.lists(finite_floats, min_size=2, max_size=200)
non_empty_equity = st.lists(positive_floats, min_size=2, max_size=200)
non_empty_pnls = st.lists(finite_floats, min_size=1, max_size=200)


@given(returns=non_empty_returns)
@settings(max_examples=200)
def test_sharpe_ratio_is_finite(returns):
    """Sharpe ratio must be finite for any non-empty returns list."""
    result = compute_sharpe_ratio(returns)
    assert math.isfinite(result), f"Sharpe ratio was not finite: {result}"


def test_sharpe_ratio_empty_returns():
    assert compute_sharpe_ratio([]) == 0.0


def test_sharpe_ratio_constant_returns():
    result = compute_sharpe_ratio([0.01] * 50)
    assert math.isfinite(result)


@given(equity=non_empty_equity)
@settings(max_examples=200)
def test_max_drawdown_non_positive(equity):
    """Maximum drawdown must always be <= 0."""
    result = compute_max_drawdown(equity)
    assert result <= 0.0, f"max_drawdown was positive: {result}"


def test_max_drawdown_monotone_increasing():
    equity = [float(i) for i in range(1, 101)]
    assert compute_max_drawdown(equity) == 0.0


def test_max_drawdown_empty():
    assert compute_max_drawdown([]) == 0.0


@given(pnls=non_empty_pnls)
@settings(max_examples=200)
def test_win_rate_in_unit_interval(pnls):
    """Win rate must always be in [0, 1]."""
    result = compute_win_rate(pnls)
    assert 0.0 <= result <= 1.0, f"win_rate out of [0,1]: {result}"


def test_win_rate_all_wins():
    assert compute_win_rate([1.0, 2.0, 3.0]) == 1.0


def test_win_rate_all_losses():
    assert compute_win_rate([-1.0, -2.0]) == 0.0


def test_win_rate_empty():
    assert compute_win_rate([]) == 0.0


@given(pnls=non_empty_pnls)
@settings(max_examples=200)
def test_profit_factor_non_negative(pnls):
    """Profit factor must always be >= 0."""
    result = compute_profit_factor(pnls)
    assert result >= 0.0, f"profit_factor was negative: {result}"


def test_profit_factor_no_losses():
    assert compute_profit_factor([1.0, 2.0, 3.0]) == 0.0


def test_profit_factor_no_wins():
    assert compute_profit_factor([-1.0, -2.0]) == 0.0


def test_profit_factor_mixed():
    result = compute_profit_factor([2.0, -1.0])
    assert result == pytest.approx(2.0)


def test_annual_return_zero_days():
    assert compute_annual_return(0.25, 0) == 0.0


def test_annual_return_one_year():
    result = compute_annual_return(0.10, 365)
    assert result == pytest.approx(0.10, rel=1e-6)


def test_annual_return_negative_total():
    result = compute_annual_return(-1.0, 365)
    assert result == -1.0
