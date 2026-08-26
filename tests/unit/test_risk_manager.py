"""
Unit tests for RiskManager v3 (ATR-dynamic, zero hardcoded limits).
"""

import pytest
import numpy as np
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from src.core.risk_manager import RiskManager, StopLevels

IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def risk():
    with patch("builtins.open", side_effect=FileNotFoundError):
        return RiskManager()


@pytest.fixture
def sample_rates():
    """Low-volatility synthetic M15 data (ATR ~4-5 points)."""
    n = 30
    np.random.seed(42)
    base = 4600.0
    dtype = np.dtype([
        ("time", "i8"), ("open", "f8"), ("high", "f8"),
        ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"),
        ("spread", "i4"), ("real_volume", "i8"),
    ])
    rates = np.zeros(n, dtype=dtype)
    for i in range(n):
        o = base + np.random.uniform(-2, 2)
        h = o + np.random.uniform(0.5, 3)
        l = o - np.random.uniform(0.5, 3)
        c = o + np.random.uniform(-1, 1)
        rates[i] = (i, o, h, l, c, 1000, 100, 0)
    return rates


@pytest.fixture
def d1_rates():
    """Synthetic D1 data for drawdown cap testing."""
    n = 20
    np.random.seed(99)
    base = 4600.0
    dtype = np.dtype([
        ("time", "i8"), ("open", "f8"), ("high", "f8"),
        ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"),
        ("spread", "i4"), ("real_volume", "i8"),
    ])
    rates = np.zeros(n, dtype=dtype)
    for i in range(n):
        o = base + np.random.uniform(-10, 10)
        h = o + np.random.uniform(5, 15)
        l = o - np.random.uniform(5, 15)
        c = o + np.random.uniform(-5, 5)
        rates[i] = (i, o, h, l, c, 50000, 50, 0)
    return rates


class TestSessionMultiplier:
    def test_london_open_returns_1_5(self, risk):
        t = datetime(2026, 8, 25, 12, 0, tzinfo=IST)  # noon IST
        assert risk.get_session_multiplier(t) == 1.5

    def test_ny_morning_returns_1_5(self, risk):
        t = datetime(2026, 8, 25, 18, 0, tzinfo=IST)  # 6 PM IST
        assert risk.get_session_multiplier(t) == 1.5

    def test_asia_returns_2_0(self, risk):
        t = datetime(2026, 8, 25, 23, 0, tzinfo=IST)  # 11 PM IST
        assert risk.get_session_multiplier(t) == 2.0

    def test_early_morning_returns_2_0(self, risk):
        t = datetime(2026, 8, 25, 6, 0, tzinfo=IST)  # 6 AM IST
        assert risk.get_session_multiplier(t) == 2.0

    def test_boundary_11_30_returns_1_5(self, risk):
        t = datetime(2026, 8, 25, 11, 30, tzinfo=IST)
        assert risk.get_session_multiplier(t) == 1.5

    def test_boundary_21_30_returns_2_0(self, risk):
        t = datetime(2026, 8, 25, 21, 30, tzinfo=IST)
        assert risk.get_session_multiplier(t) == 2.0


class TestSessionName:
    def test_london_open(self, risk):
        t = datetime(2026, 8, 25, 13, 0, tzinfo=IST)
        assert risk.get_session_name(t) == "LONDON_OPEN"

    def test_ny_morning(self, risk):
        t = datetime(2026, 8, 25, 19, 0, tzinfo=IST)
        assert risk.get_session_name(t) == "NY_MORNING"

    def test_asia(self, risk):
        t = datetime(2026, 8, 25, 23, 0, tzinfo=IST)
        assert risk.get_session_name(t) == "ASIA_OVERNIGHT"


class TestATRStops:
    def test_buy_stops_correct_direction(self, risk, sample_rates):
        stops = risk.calculate_atr_stops(4600.0, is_buy=True, m15_rates=sample_rates, multiplier=1.5)
        assert stops is not None
        assert stops.sl < 4600.0
        assert stops.tp > 4600.0

    def test_sell_stops_correct_direction(self, risk, sample_rates):
        stops = risk.calculate_atr_stops(4600.0, is_buy=False, m15_rates=sample_rates, multiplier=1.5)
        assert stops is not None
        assert stops.sl > 4600.0
        assert stops.tp < 4600.0

    def test_rr_ratio_is_2(self, risk, sample_rates):
        stops = risk.calculate_atr_stops(4600.0, is_buy=True, m15_rates=sample_rates, multiplier=1.5)
        if stops:
            rr = stops.tp_distance / stops.sl_distance
            assert abs(rr - 2.0) < 0.01

    def test_wider_stops_for_asia(self, risk, sample_rates):
        london = risk.calculate_atr_stops(4600.0, True, sample_rates, 1.5)
        asia = risk.calculate_atr_stops(4600.0, True, sample_rates, 2.0)
        assert asia.sl_distance > london.sl_distance

    def test_returns_trail_params(self, risk, sample_rates):
        stops = risk.calculate_atr_stops(4600.0, True, sample_rates, 1.5)
        assert stops.trail_activation > 0
        assert stops.trail_distance > 0
        assert stops.trail_activation > stops.trail_distance


class TestDailyDrawdown:
    def test_allows_trading_when_no_losses(self, risk, d1_rates):
        assert risk.check_daily_drawdown(d1_rates, 0.0) == True

    def test_allows_trading_when_profitable(self, risk, d1_rates):
        assert risk.check_daily_drawdown(d1_rates, 50.0) == True

    def test_allows_trading_when_loss_below_limit(self, risk, d1_rates):
        assert risk.check_daily_drawdown(d1_rates, -5.0) == True

    def test_blocks_when_loss_exceeds_limit(self, risk, d1_rates):
        # D1 ATR with this data should be ~20-30, so limit = 30-45
        # Use a massive loss to guarantee it triggers
        assert risk.check_daily_drawdown(d1_rates, -500.0) == False


class TestPyramiding:
    def test_pyramid_triggers_when_profitable(self, risk):
        assert risk.check_pyramid_condition(4600.0, 4605.0, 8.0, is_buy=True) == True

    def test_pyramid_does_not_trigger_early(self, risk):
        assert risk.check_pyramid_condition(4600.0, 4602.0, 8.0, is_buy=True) == False

    def test_pyramid_sell(self, risk):
        assert risk.check_pyramid_condition(4600.0, 4595.0, 8.0, is_buy=False) == True

    def test_pyramid_sell_does_not_trigger_early(self, risk):
        assert risk.check_pyramid_condition(4600.0, 4598.0, 8.0, is_buy=False) == False


class TestConsolidation:
    def test_no_exit_when_insufficient_data(self, risk):
        dtype = np.dtype([
            ("time", "i8"), ("open", "f8"), ("high", "f8"),
            ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"),
            ("spread", "i4"), ("real_volume", "i8"),
        ])
        rates = np.zeros(5, dtype=dtype)
        for i in range(5):
            rates[i] = (i, 4600, 4602, 4598, 4600, 1000, 50, 0)
        assert risk.should_exit_consolidation(rates) == False
