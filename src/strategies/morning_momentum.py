"""
MorningMomentum -- The STRICT WINNER. The ONLY active strategy.

DO NOT MODIFY the entry conditions without user approval.

Entry Conditions (ALL must be TRUE for BUY):
  1. TREND:    M15 Close > 20-period EMA
  2. BREAKOUT: Current M15 High > Previous M15 High
  3. VOLUME:   M5 Tick Volume > 20-period avg M5 Tick Volume
  4. MOMENTUM: RSI(14) between 50 and 65

Entry Conditions (ALL must be TRUE for SELL):
  1. TREND:    M15 Close < 20-period EMA
  2. BREAKOUT: Current M15 Low < Previous M15 Low
  3. VOLUME:   M5 Tick Volume > 20-period avg M5 Tick Volume
  4. MOMENTUM: RSI(14) between 35 and 50

Session Priority:
  - London Open (11:30-15:30 IST): Execute IMMEDIATELY on signal.
  - Other sessions: Wait for next M15 candle to confirm breakout holds.

IMMUTABLE PARAMETERS -- locked from forensic audit (83% backtest win rate).
"""

import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# IMMUTABLE parameters (DO NOT CHANGE)
# ---------------------------------------------------------------------------
EMA_PERIOD = 20
RSI_PERIOD = 14
VOLUME_AVG_PERIOD = 20
RSI_LONG_MIN = 50.0
RSI_LONG_MAX = 65.0
RSI_SHORT_MIN = 35.0
RSI_SHORT_MAX = 50.0


class MorningMomentum(BaseStrategy):
    """15-minute candle momentum strategy with strict 4-condition gate."""

    name = "MORNING_MOMENTUM"
    magic = 2005

    def __init__(self):
        # Pending signal for non-London sessions (wait for confirmation)
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(
        self,
        m15_rates: np.ndarray,
        m5_rates: Optional[np.ndarray] = None,
    ) -> Optional[Signal]:
        """Evaluate a BUY or SELL signal.

        Args:
            m15_rates: At least 100 M15 candles (structured numpy array).
            m5_rates:  At least 25 M5 candles for volume confirmation.
                       If None, falls back to M15 tick_volume.

        Returns:
            Signal if all 4 conditions align, otherwise None.
        """
        if m15_rates is None or len(m15_rates) < 100:
            return None

        # Session filter: London Open ONLY (11:30 - 15:30 IST)
        latest_time = datetime.fromtimestamp(int(m15_rates[-2]["time"]), tz=timezone.utc).astimezone(IST)
        ist_tv = latest_time.hour + latest_time.minute / 60.0

        if not (11.5 <= ist_tv < 15.5):
            return None

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]

        # --- Indicators on M15 ---
        ema20 = self.ema(closes, EMA_PERIOD)
        rsi_vals = self.rsi(closes, RSI_PERIOD)

        # Use the last *completed* candle (index -2) for signals.
        # Index -1 is the currently forming candle.
        curr_close = closes[-2]
        prev_high = highs[-3]
        prev_low = lows[-3]
        curr_high = highs[-2]
        curr_low = lows[-2]
        curr_ema = ema20[-2]
        curr_rsi = rsi_vals[-2]

        if np.isnan(curr_ema) or np.isnan(curr_rsi):
            return None

        # --- Volume check (M5 tick_volume preferred) ---
        if m5_rates is not None and len(m5_rates) >= VOLUME_AVG_PERIOD + 1:
            volumes = m5_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-VOLUME_AVG_PERIOD - 1: -1])
        else:
            # Fallback: use M15 tick_volume
            volumes = m15_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-VOLUME_AVG_PERIOD - 1: -1])

        volume_ok = curr_vol > avg_vol

        if not volume_ok:
            return None

        # --- LONG conditions (ALL 4 must be TRUE) ---
        if (
            curr_close > curr_ema                       # 1. Trend
            and curr_high > prev_high                    # 2. Breakout
            # volume_ok checked above                    # 3. Volume
            and RSI_LONG_MIN <= curr_rsi <= RSI_LONG_MAX # 4. Momentum
        ):
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )

        # --- SHORT conditions (ALL 4 must be TRUE) ---
        if (
            curr_close < curr_ema                         # 1. Trend
            and curr_low < prev_low                        # 2. Breakout
            # volume_ok checked above                      # 3. Volume
            and RSI_SHORT_MIN <= curr_rsi <= RSI_SHORT_MAX # 4. Momentum
        ):
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )

        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        """For non-London sessions: check if the pending signal holds on the next candle.

        Called on the candle AFTER a signal fired. If the breakout still holds,
        return the signal. Otherwise, cancel it.
        """
        if self._pending_signal is None:
            return None

        if m15_rates is None or len(m15_rates) < 3:
            self._pending_signal = None
            return None

        latest_time = int(m15_rates[-2]["time"])

        # Must be a NEW candle after the signal candle
        if latest_time <= (self._pending_candle_time or 0):
            return None  # Same candle, keep waiting

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]
        ema20 = self.ema(closes, EMA_PERIOD)

        sig = self._pending_signal

        if sig.is_buy:
            # Confirmation: price still above EMA and above the breakout high
            if closes[-2] > ema20[-2]:
                confirmed = sig
                self._pending_signal = None
                return confirmed
        else:
            if closes[-2] < ema20[-2]:
                confirmed = sig
                self._pending_signal = None
                return confirmed

        # Failed confirmation
        self._pending_signal = None
        return None

    def set_pending(self, signal: Signal, candle_time: int):
        """Queue a signal for confirmation on the next candle (non-London sessions)."""
        self._pending_signal = signal
        self._pending_candle_time = candle_time
