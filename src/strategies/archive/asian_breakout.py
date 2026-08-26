"""
AsianBreakout — Asian session range breakout strategy.

Calculates the Asian session high/low (00:00–08:00 UTC) and
trades the breakout during the London open (08:00–10:00 UTC).
"""

import numpy as np
from typing import Optional
from datetime import datetime, timezone
from src.strategies.base_strategy import BaseStrategy, Signal, mt5


class AsianBreakout(BaseStrategy):
    name = "ASIAN_BREAKOUT"
    magic = 2003

    def __init__(self):
        self._asian_high: Optional[float] = None
        self._asian_low: Optional[float] = None

    def set_asian_range(self, rates: np.ndarray):
        """Pre-compute the Asian session high/low from overnight data."""
        if rates is None or len(rates) == 0:
            self._asian_high = None
            self._asian_low = None
            return

        self._asian_high = float(np.max(rates["high"]))
        self._asian_low = float(np.min(rates["low"]))

    def evaluate(self, rates: np.ndarray) -> Optional[Signal]:
        """Evaluate breakout against the pre-set Asian range.

        `rates` here should be the latest 3 M15 candles for the breakout check.
        """
        if self._asian_high is None or self._asian_low is None:
            return None
        if rates is None or len(rates) < 3:
            return None

        now_utc = datetime.now(timezone.utc)
        if not (8 <= now_utc.hour < 10):
            return None

        asian_range = self._asian_high - self._asian_low
        if asian_range > 50.0:
            return None

        p_close = rates[-3]["close"]
        c_close = rates[-2]["close"]

        if p_close <= self._asian_high and c_close > self._asian_high:
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )
        elif p_close >= self._asian_low and c_close < self._asian_low:
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )
        return None

    def get_structural_sl(self, signal: Signal) -> Optional[float]:
        """Return a structure-based SL (Asian range low for BUY, high for SELL)."""
        if self._asian_high is None or self._asian_low is None:
            return None
        asian_range = self._asian_high - self._asian_low
        if signal.is_buy:
            return self._asian_low if asian_range <= 25.0 else self._asian_low + (asian_range / 2)
        else:
            return self._asian_high if asian_range <= 25.0 else self._asian_high - (asian_range / 2)
