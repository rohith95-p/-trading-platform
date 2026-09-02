"""
MorningMomentum -- Smart Re-Entry Momentum Strategy.

Entry Conditions (ALL must be TRUE for BUY):
  1. TREND:       M15 Close > 20-period EMA
  2. BREAKOUT:    Current M15 High > Previous M15 High
  3. MOMENTUM:    RSI(14) between 45 and 65
  4. EXHAUSTION:  Price NOT extended > 1.5x ATR beyond EMA (move exhausted)
  5. DIRECTION RESET: If last signal was also BUY, RSI must have dipped
                      below 55 on at least one candle since last signal
                      (proves market "reset" and this is a NEW move, not FOMO)

Entry Conditions (ALL must be TRUE for SELL — mirror):
  1. TREND:       M15 Close < 20-period EMA
  2. BREAKOUT:    Current M15 Low < Previous M15 Low
  3. MOMENTUM:    RSI(14) between 35 and 55
  4. EXHAUSTION:  Price NOT extended > 1.5x ATR below EMA
  5. DIRECTION RESET: If last signal was also SELL, RSI must have risen
                      above 45 on at least one candle since last signal

Session Priority:
  - 10:00 - 18:00 IST (London & early NY): Execute IMMEDIATELY on signal.
  - Other sessions: Wait for next M15 candle to confirm breakout holds.
"""

import numpy as np
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# STRATEGY PARAMETERS
# ---------------------------------------------------------------------------
EMA_PERIOD = 20
RSI_PERIOD = 14
ATR_PERIOD = 14
VOLUME_AVG_PERIOD = 20
EXHAUSTION_ATR_MULT = 1.5
USE_VOLUME_FILTER = False

RSI_LONG_MIN = 45.0
RSI_LONG_MAX = 65.0
RSI_SHORT_MIN = 35.0
RSI_SHORT_MAX = 55.0


class MorningMomentum(BaseStrategy):
    """15-minute candle momentum strategy with smart re-entry and exhaustion filters."""

    name = "MORNING_MOMENTUM"
    magic = 2005

    def __init__(self):
        # Pending signal for non-core sessions (wait for confirmation)
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None
        
        # Smart re-entry state
        self._last_direction: Optional[str] = None
        self._last_signal_candle_idx: int = -999
        self._direction_has_reset: bool = True

    def evaluate(
        self,
        m15_rates: np.ndarray,
        m5_rates: Optional[np.ndarray] = None,
    ) -> Optional[Signal]:
        """Evaluate a BUY or SELL signal."""
        if m15_rates is None or len(m15_rates) < 100:
            return None

        # Session filter: 10:00 to 18:00 IST
        latest_time = datetime.fromtimestamp(int(m15_rates[-2]["time"]), tz=timezone.utc).astimezone(IST)
        ist_tv = latest_time.hour + latest_time.minute / 60.0

        if not (10.0 <= ist_tv <= 18.0):
            return None

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]

        # --- Indicators on M15 ---
        ema20 = self.ema(closes, EMA_PERIOD)
        rsi_vals = self.rsi(closes, RSI_PERIOD)

        # Use the last *completed* candle (index -2) for signals.
        curr_close = closes[-2]
        prev_high = highs[-3]
        prev_low = lows[-3]
        curr_high = highs[-2]
        curr_low = lows[-2]
        curr_ema = ema20[-2]
        curr_rsi = rsi_vals[-2]

        if np.isnan(curr_ema) or np.isnan(curr_rsi):
            return None

        # --- Direction Reset Check ---
        # Did the market "reset" since the last trade in this direction?
        current_idx = len(m15_rates) - 1
        if self._last_direction is not None and not self._direction_has_reset:
            # Look from the candle AFTER the last signal up to the current forming candle
            start_scan = max(0, self._last_signal_candle_idx + 1)
            end_scan = len(rsi_vals) - 1
            for i in range(start_scan, end_scan):
                if np.isnan(rsi_vals[i]):
                    continue
                if self._last_direction == "BUY" and rsi_vals[i] < 55:
                    self._direction_has_reset = True
                    break
                elif self._last_direction == "SELL" and rsi_vals[i] > 45:
                    self._direction_has_reset = True
                    break

        # --- Exhaustion Check (ATR) ---
        atr_vals = self.atr(highs, lows, closes, ATR_PERIOD)
        curr_atr = atr_vals[-2]
        if not np.isnan(curr_atr):
            price_extension = abs(curr_close - curr_ema)
            if price_extension > (EXHAUSTION_ATR_MULT * curr_atr):
                return None  # Move is too extended, wait for pullback

        # --- Volume check (optional) ---
        volume_ok = True
        if USE_VOLUME_FILTER:
            if m5_rates is not None and len(m5_rates) >= VOLUME_AVG_PERIOD + 1:
                volumes = m5_rates["tick_volume"].astype(float)
                curr_vol = volumes[-2]
                avg_vol = np.mean(volumes[-VOLUME_AVG_PERIOD - 1: -1])
            else:
                volumes = m15_rates["tick_volume"].astype(float)
                curr_vol = volumes[-2]
                avg_vol = np.mean(volumes[-VOLUME_AVG_PERIOD - 1: -1])
            volume_ok = curr_vol > avg_vol

        if not volume_ok:
            return None

        # --- LONG conditions ---
        if (
            curr_close > curr_ema
            and curr_high > prev_high
            and RSI_LONG_MIN <= curr_rsi <= RSI_LONG_MAX
        ):
            if self._last_direction == "BUY" and not self._direction_has_reset:
                return None  # Block FOMO consecutive buys without a pullback

            self._last_direction = "BUY"
            self._last_signal_candle_idx = current_idx
            self._direction_has_reset = False

            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )

        # --- SHORT conditions ---
        if (
            curr_close < curr_ema
            and curr_low < prev_low
            and RSI_SHORT_MIN <= curr_rsi <= RSI_SHORT_MAX
        ):
            if self._last_direction == "SELL" and not self._direction_has_reset:
                return None

            self._last_direction = "SELL"
            self._last_signal_candle_idx = current_idx
            self._direction_has_reset = False

            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )

        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        if self._pending_signal is None:
            return None

        if m15_rates is None or len(m15_rates) < 3:
            self._pending_signal = None
            return None

        latest_time = int(m15_rates[-2]["time"])
        if latest_time <= (self._pending_candle_time or 0):
            return None

        closes = m15_rates["close"]
        ema20 = self.ema(closes, EMA_PERIOD)
        sig = self._pending_signal

        if sig.is_buy:
            if closes[-2] > ema20[-2]:
                confirmed = sig
                self._pending_signal = None
                return confirmed
        else:
            if closes[-2] < ema20[-2]:
                confirmed = sig
                self._pending_signal = None
                return confirmed

        self._pending_signal = None
        return None

    def set_pending(self, signal: Signal, candle_time: int):
        self._pending_signal = signal
        self._pending_candle_time = candle_time
