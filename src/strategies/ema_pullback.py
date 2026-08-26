"""
EMA Pullback Continuation Strategy.

Captures trend continuations during the NY and Overlap sessions (15:30 - 21:30 IST).
Checks for EMA alignment (50 > 200), a pullback to the 20 EMA, and a confirmed rejection.
"""

import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

IST = timezone(timedelta(hours=5, minutes=30))

class EMAPullback(BaseStrategy):
    """EMA Pullback trend continuation strategy."""

    name = "EMA_PULLBACK"
    magic = 2006

    def __init__(self):
        # Pending signal not heavily used here since we execute on close,
        # but required by the interface for compatibility.
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(
        self,
        m15_rates: np.ndarray,
        m5_rates: Optional[np.ndarray] = None,
    ) -> Optional[Signal]:
        
        if m15_rates is None or len(m15_rates) < 200:
            return None

        # Session filter: NY + Overlap (15:30 - 21:30 IST)
        latest_time = datetime.fromtimestamp(int(m15_rates[-2]["time"]), tz=timezone.utc).astimezone(IST)
        ist_tv = latest_time.hour + latest_time.minute / 60.0

        if not (15.5 <= ist_tv < 21.5):
            return None

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]

        ema20 = self.ema(closes, 20)
        ema50 = self.ema(closes, 50)
        ema200 = self.ema(closes, 200)
        rsi_vals = self.rsi(closes, 14)

        if np.isnan(ema200[-2]) or np.isnan(rsi_vals[-2]):
            return None

        # Volume filter (relax to 0.8x average)
        if m5_rates is not None and len(m5_rates) >= 21:
            volumes = m5_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])
        else:
            volumes = m15_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])

        if curr_vol <= avg_vol * 0.8:
            return None

        # Trend conditions
        trend_bullish = closes[-2] > ema50[-2] and ema50[-2] > ema200[-2]
        trend_bearish = closes[-2] < ema50[-2] and ema50[-2] < ema200[-2]

        rsi_ok = 35 <= rsi_vals[-2] <= 65

        # BUY: Uptrend, pulled back to touch/near 20-EMA, closed above 20-EMA
        if (trend_bullish
            and lows[-3] <= ema20[-3] * 1.001
            and closes[-2] > ema20[-2]
            and rsi_ok):
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )

        # SELL: Downtrend, pulled back to touch/near 20-EMA, closed below 20-EMA
        if (trend_bearish
            and highs[-3] >= ema20[-3] * 0.999
            and closes[-2] < ema20[-2]
            and rsi_ok):
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )

        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        """EMA Pullback executes immediately upon the M15 close."""
        return None

    def set_pending(self, signal: Signal, candle_time: int):
        self._pending_signal = signal
        self._pending_candle_time = candle_time
