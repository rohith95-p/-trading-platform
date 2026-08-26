import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5

# IMMUTABLE parameters
EMA_PERIOD = 200
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

class SupertrendEMA(BaseStrategy):
    """Supertrend strategy filtered by a 200 EMA for trend direction."""

    name = "SUPERTREND_EMA"
    magic = 2006

    def __init__(self):
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    @staticmethod
    def tr(highs, lows, closes):
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        tr = np.zeros_like(highs)
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(highs)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
            
        return tr

    @staticmethod
    def atr(highs, lows, closes, period):
        true_range = SupertrendEMA.tr(highs, lows, closes)
        atr = np.zeros_like(true_range)
        if len(atr) < period:
            return atr
            
        atr[period-1] = np.mean(true_range[:period])
        for i in range(period, len(true_range)):
            # RMA (smma) is usually used for ATR
            atr[i] = (atr[i-1] * (period - 1) + true_range[i]) / period
            
        return atr

    def evaluate(
        self,
        m15_rates: np.ndarray,
        m5_rates: Optional[np.ndarray] = None,
    ) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < max(EMA_PERIOD, SUPERTREND_PERIOD) + 2:
            return None

        closes = m15_rates["close"]
        highs = m15_rates["high"]
        lows = m15_rates["low"]

        # Calculate EMA
        ema200 = self.ema(closes, EMA_PERIOD)

        # Calculate ATR
        atr_vals = self.atr(highs, lows, closes, SUPERTREND_PERIOD)

        # Calculate Supertrend
        hl2 = (highs + lows) / 2.0
        
        basic_upperband = hl2 + (SUPERTREND_MULTIPLIER * atr_vals)
        basic_lowerband = hl2 - (SUPERTREND_MULTIPLIER * atr_vals)
        
        final_upperband = np.zeros_like(basic_upperband)
        final_lowerband = np.zeros_like(basic_lowerband)
        supertrend = np.zeros_like(closes)
        direction = np.zeros_like(closes) # 1 for up, -1 for down

        # Initialize first values
        final_upperband[0] = basic_upperband[0]
        final_lowerband[0] = basic_lowerband[0]
        supertrend[0] = final_upperband[0]
        direction[0] = -1

        for i in range(1, len(closes)):
            # Final Upper Band
            if basic_upperband[i] < final_upperband[i-1] or closes[i-1] > final_upperband[i-1]:
                final_upperband[i] = basic_upperband[i]
            else:
                final_upperband[i] = final_upperband[i-1]
                
            # Final Lower Band
            if basic_lowerband[i] > final_lowerband[i-1] or closes[i-1] < final_lowerband[i-1]:
                final_lowerband[i] = basic_lowerband[i]
            else:
                final_lowerband[i] = final_lowerband[i-1]
                
            # Supertrend
            if supertrend[i-1] == final_upperband[i-1]:
                if closes[i] <= final_upperband[i]:
                    supertrend[i] = final_upperband[i]
                    direction[i] = -1
                else:
                    supertrend[i] = final_lowerband[i]
                    direction[i] = 1
            elif supertrend[i-1] == final_lowerband[i-1]:
                if closes[i] >= final_lowerband[i]:
                    supertrend[i] = final_lowerband[i]
                    direction[i] = 1
                else:
                    supertrend[i] = final_upperband[i]
                    direction[i] = -1

        # Evaluate last completed candle (index -2)
        curr_close = closes[-2]
        curr_ema = ema200[-2]
        curr_direction = direction[-2]
        prev_direction = direction[-3]
        
        if np.isnan(curr_ema):
            return None

        # --- LONG condition ---
        # Trend is UP (close > EMA), and Supertrend just flipped to UP
        if curr_close > curr_ema and curr_direction == 1 and prev_direction == -1:
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )

        # --- SHORT condition ---
        # Trend is DOWN (close < EMA), and Supertrend just flipped to DOWN
        if curr_close < curr_ema and curr_direction == -1 and prev_direction == 1:
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )

        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        """Check if pending signal is valid on the next candle."""
        if self._pending_signal is None:
            return None

        if m15_rates is None or len(m15_rates) < 3:
            self._pending_signal = None
            return None

        latest_time = int(m15_rates[-2]["time"])

        if latest_time <= (self._pending_candle_time or 0):
            return None 

        closes = m15_rates["close"]
        ema200 = self.ema(closes, EMA_PERIOD)
        
        sig = self._pending_signal

        # Simply confirm price is still on the correct side of the EMA
        if sig.is_buy and closes[-2] > ema200[-2]:
            confirmed = sig
            self._pending_signal = None
            return confirmed
        elif not sig.is_buy and closes[-2] < ema200[-2]:
            confirmed = sig
            self._pending_signal = None
            return confirmed

        self._pending_signal = None
        return None

    def set_pending(self, signal: Signal, candle_time: int):
        self._pending_signal = signal
        self._pending_candle_time = candle_time
