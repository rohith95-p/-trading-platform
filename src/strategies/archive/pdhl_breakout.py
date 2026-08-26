"""
PDHLBreakout — Previous Day High/Low breakout strategy.

BUY when price closes above yesterday's high.
SELL when price closes below yesterday's low.
ATR-based stops applied via the RiskManager.
"""

import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5


class PDHLBreakout(BaseStrategy):
    name = "PDHL_BREAKOUT"
    magic = 2004

    def __init__(self):
        self.pd_high: Optional[float] = None
        self.pd_low: Optional[float] = None

    def set_previous_day(self, d1_rates: np.ndarray):
        """Pre-compute previous day's high and low from D1 data."""
        if d1_rates is None or len(d1_rates) < 2:
            self.pd_high = None
            self.pd_low = None
            return

        prev_day = d1_rates[-2]
        self.pd_high = float(prev_day["high"])
        self.pd_low = float(prev_day["low"])

    def evaluate(self, rates: np.ndarray) -> Optional[Signal]:
        """Evaluate breakout against previous day's high/low.

        `rates` should be the latest M15 candles (at least 3).
        """
        if self.pd_high is None or self.pd_low is None:
            return None
        if rates is None or len(rates) < 3:
            return None

        p_close = rates[-3]["close"]
        c_close = rates[-2]["close"]

        if p_close <= self.pd_high and c_close > self.pd_high:
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )
        elif p_close >= self.pd_low and c_close < self.pd_low:
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )
        return None
