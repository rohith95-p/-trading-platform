"""
Asian Range Liquidity Sweep Strategy.

Captures liquidity sweeps during the London Open (11:30 - 14:30 IST).
Checks for a sweep of the Asian Range (5:30 - 11:30 IST) high/low, followed by a confirmed rejection.
"""

import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

IST = timezone(timedelta(hours=5, minutes=30))

class AsianSweep(BaseStrategy):
    """Asian Range Sweep-and-Reverse strategy."""

    name = "ASIAN_SWEEP"
    magic = 2007

    def __init__(self):
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(
        self,
        m15_rates: np.ndarray,
        m5_rates: Optional[np.ndarray] = None,
    ) -> Optional[Signal]:
        
        if m15_rates is None or len(m15_rates) < 50:
            return None

        # Session filter: London Open (11:30 - 14:30 IST)
        latest_time = datetime.fromtimestamp(int(m15_rates[-2]["time"]), tz=timezone.utc).astimezone(IST)
        ist_tv = latest_time.hour + latest_time.minute / 60.0

        if not (11.5 <= ist_tv < 14.5):
            return None

        # Find Asian Range (5:30 - 11:30 IST) for today
        asian_high = -np.inf
        asian_low = np.inf
        found_candles = 0
        today_date = latest_time.date()

        for i in range(len(m15_rates) - 1, max(-1, len(m15_rates) - 50), -1):
            dt = datetime.fromtimestamp(int(m15_rates[i]["time"]), tz=timezone.utc).astimezone(IST)
            if dt.date() != today_date:
                continue
            h_tv = dt.hour + dt.minute / 60.0
            if 5.5 <= h_tv < 11.5:
                found_candles += 1
                asian_high = max(asian_high, float(m15_rates[i]["high"]))
                asian_low = min(asian_low, float(m15_rates[i]["low"]))

        if found_candles < 4:
            return None

        asian_range = asian_high - asian_low
        if asian_range < 5 or asian_range > 35:
            return None

        # Volume filter
        if m5_rates is not None and len(m5_rates) >= 21:
            volumes = m5_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])
        else:
            volumes = m15_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])

        if curr_vol <= avg_vol:
            return None

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]

        # BUY: Candle N-1 swept below Asian Low and closed below it, Candle N closed above it
        if (lows[-3] < asian_low
            and closes[-3] < asian_low
            and closes[-2] > asian_low):
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )

        # SELL: Candle N-1 swept above Asian High and closed above it, Candle N closed below it
        if (highs[-3] > asian_high
            and closes[-3] > asian_high
            and closes[-2] < asian_high):
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )

        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        return None

    def set_pending(self, signal: Signal, candle_time: int):
        self._pending_signal = signal
        self._pending_candle_time = candle_time
