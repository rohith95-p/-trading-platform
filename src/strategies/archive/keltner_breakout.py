"""
KeltnerBreakout — ATR Keltner Channel breakout strategy.

Fires when price closes above the upper Keltner Channel (BUY)
or below the lower channel (SELL) on the M15 timeframe.
"""

import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.core.risk_manager import RiskManager


class KeltnerBreakout(BaseStrategy):
    name = "ATR_KELTNER"
    magic = 2001

    def evaluate(self, rates: np.ndarray) -> Optional[Signal]:
        if rates is None or len(rates) < 100:
            return None

        closes = rates["close"]
        ema20 = self.ema(closes, 20)
        atr = RiskManager.calc_atr(rates, 14)

        # Use the previous-completed candle (index -2) vs the one before (-3)
        p_close = closes[-3]
        c_close = closes[-2]

        p_kc_up = ema20[-3] + (2 * atr[-3])
        p_kc_lo = ema20[-3] - (2 * atr[-3])
        c_kc_up = ema20[-2] + (2 * atr[-2])
        c_kc_lo = ema20[-2] - (2 * atr[-2])

        if p_close <= p_kc_up and c_close > c_kc_up:
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )
        elif p_close >= p_kc_lo and c_close < c_kc_lo:
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )
        return None
