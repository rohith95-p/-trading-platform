import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.market_study import atr as _atr, ema as _ema

def _ist_hour(rates: np.ndarray) -> np.ndarray:
    ts = rates["time"].astype("int64")
    return ((ts % 86400) + 19800) % 86400 / 3600.0

class EURUSDAsianRange(BaseStrategy):
    """
    Asian Range Mean Reversion for EURUSD
    Targets the quiet Asian session where EURUSD usually ranges.
    Fades moves that deviate too far from the EMA.
    """
    execute_immediately = True
    edge_trigger = False
    _min_bars = 200

    def __init__(self, 
                 sl_atr_mult: float = 1.5, 
                 tp_atr_mult: float = 1.0,
                 session: tuple = (2.0, 9.0), # 2 AM to 9 AM IST
                 magic: int = 5002,
                 name: str = "EURUSD_ASIAN_RANGE"):
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.session = session
        self.magic = magic
        self.name = name

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None

        # Fix O(N^2) by using only last 100 bars
        window_rates = m15_rates[-100:]
        c = window_rates["close"].astype(float)
        
        ist = _ist_hour(window_rates)
        atr14 = _atr(window_rates, 14)
        ema20 = _ema(c, 20)
        
        i = -2 # last closed bar
        
        if not (self.session[0] <= ist[i] < self.session[1]):
            return None

        cur_atr = atr14[i]
        if cur_atr <= 0:
            return None

        deviation = c[i] - ema20[i]
        
        # If price stretches more than 1.0 ATR above EMA, sell it back
        if deviation > 1.0 * cur_atr:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=False)
            
        # If price stretches more than 1.0 ATR below EMA, buy it back
        elif deviation < -1.0 * cur_atr:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name, magic=self.magic, is_buy=True)

        return None
