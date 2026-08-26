"""
MACDCross — MACD crossover + EMA200 trend filter strategy.

BUY when MACD crosses above signal AND price is above EMA200.
SELL when MACD crosses below signal AND price is below EMA200.
"""

import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5


class MACDCross(BaseStrategy):
    name = "MACD_EMA200"
    magic = 2002

    def evaluate(self, rates: np.ndarray) -> Optional[Signal]:
        if rates is None or len(rates) < 300:
            return None

        closes = rates["close"]
        ema200 = self.ema(closes, 200)
        macd_line, sig_line = self.macd(closes)

        c_close = closes[-2]
        c_ema200 = ema200[-2]
        p_macd = macd_line[-3]
        p_sig = sig_line[-3]
        c_macd = macd_line[-2]
        c_sig = sig_line[-2]

        # Check for NaN in MACD values
        if any(np.isnan(v) for v in [p_macd, p_sig, c_macd, c_sig, c_ema200]):
            return None

        if c_close > c_ema200 and p_macd <= p_sig and c_macd > c_sig:
            return Signal(
                direction=mt5.ORDER_TYPE_BUY,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=True,
            )
        elif c_close < c_ema200 and p_macd >= p_sig and c_macd < c_sig:
            return Signal(
                direction=mt5.ORDER_TYPE_SELL,
                strategy_name=self.name,
                magic=self.magic,
                is_buy=False,
            )
        return None
