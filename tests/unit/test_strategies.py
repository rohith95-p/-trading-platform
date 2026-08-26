"""
Unit tests for MorningMomentum strategy (the ONLY active strategy).
"""

import pytest
import numpy as np


def make_rates(n=100, base=4600.0, trend=0.0, volatility=5.0, seed=42):
    """Generate synthetic structured OHLCV data."""
    np.random.seed(seed)
    dtype = np.dtype([
        ("time", "i8"), ("open", "f8"), ("high", "f8"),
        ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"),
        ("spread", "i4"), ("real_volume", "i8"),
    ])
    rates = np.zeros(n, dtype=dtype)
    price = base
    for i in range(n):
        price += trend + np.random.uniform(-volatility, volatility)
        o = price
        h = o + np.random.uniform(0.5, volatility)
        l = o - np.random.uniform(0.5, volatility)
        c = o + np.random.uniform(-2, 2)
        vol = int(np.random.uniform(500, 3000))
        rates[i] = (i * 900, o, h, l, c, vol, 100, 0)
    return rates


class TestMorningMomentum:
    def test_returns_none_on_insufficient_data(self):
        from src.strategies.morning_momentum import MorningMomentum
        strat = MorningMomentum()
        rates = make_rates(10)
        assert strat.evaluate(rates) is None

    def test_no_signal_on_low_volume(self):
        """Volume condition must reject low-volume candles."""
        from src.strategies.morning_momentum import MorningMomentum
        strat = MorningMomentum()
        rates = make_rates(100, trend=1.0)
        rates["tick_volume"][-2] = 1  # Very low volume
        sig = strat.evaluate(rates)
        assert sig is None

    def test_buy_signal_possible_on_strong_uptrend(self):
        """With a strong uptrend + high volume, a BUY is possible."""
        from src.strategies.morning_momentum import MorningMomentum
        strat = MorningMomentum()
        rates = make_rates(100, trend=1.5, volatility=3.0, seed=99)
        rates["tick_volume"][-2] = 5000
        rates["tick_volume"][-3] = 500
        sig = strat.evaluate(rates)
        assert sig is None or sig.is_buy

    def test_accepts_m5_volume_data(self):
        """Strategy should accept separate M5 data for volume confirmation."""
        from src.strategies.morning_momentum import MorningMomentum
        strat = MorningMomentum()
        m15 = make_rates(100, trend=1.0)
        m5 = make_rates(25, trend=0.5, seed=77)
        m5["tick_volume"][-2] = 5000
        # Should not crash with m5 data
        sig = strat.evaluate(m15, m5)
        assert sig is None or sig.strategy_name == "MORNING_MOMENTUM"

    def test_pending_signal_mechanism(self):
        """Pending signal should work without crashing."""
        from src.strategies.morning_momentum import MorningMomentum
        from src.strategies.base_strategy import Signal
        import MetaTrader5 as _mt5
        from typing import Any
        mt5: Any = _mt5

        strat = MorningMomentum()
        sig = Signal(
            direction=0,  # placeholder
            strategy_name="MORNING_MOMENTUM",
            magic=2005,
            is_buy=True,
        )
        strat.set_pending(sig, 12345)
        assert strat._pending_signal is not None
        assert strat._pending_candle_time == 12345

    def test_confirmation_returns_none_without_new_candle(self):
        from src.strategies.morning_momentum import MorningMomentum
        from src.strategies.base_strategy import Signal

        strat = MorningMomentum()
        rates = make_rates(100, trend=1.0)
        sig = Signal(direction=0, strategy_name="MORNING_MOMENTUM", magic=2005, is_buy=True)
        candle_time = int(rates[-2]["time"])
        strat.set_pending(sig, candle_time)
        # Same candle time -- should not confirm
        result = strat.check_pending_confirmation(rates)
        assert result is None
