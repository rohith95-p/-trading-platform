import numpy as np
from typing import Optional
from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.market_study import atr as _atr

def _ist_hour(rates: np.ndarray) -> np.ndarray:
    ts = rates["time"].astype("int64")
    return ((ts % 86400) + 19800) % 86400 / 3600.0

class ForexSessionMomentum(BaseStrategy):
    """
    Forex Session Momentum (Overlap)
    Trades the London-NY overlap session where volume is highest.
    Looks for a strong trend on M15 and enters on pullbacks.
    """
    execute_immediately = True
    edge_trigger = False
    _min_bars = 200

    def __init__(self, 
                 sl_atr_mult: float = 0.5, 
                 tp_atr_mult: float = 1.0,
                 session: tuple = (18.0, 22.0),
                 magic: int = 5001,
                 name: str = "FX_OVERLAP_MOMENTUM"):
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
        
        i = -2 # last closed bar
        
        # Session gate
        if not (self.session[0] <= ist[i] < self.session[1]):
            return None

        # Momentum: close > close[-20] for buy
        if c[i] > c[i-20] and c[i] > c[i-5]:
            # Bullish trend, enter if pullback (red candle)
            if c[i] < window_rates["open"][i]:
                return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name, magic=self.magic, is_buy=True)
                
        elif c[i] < c[i-20] and c[i] < c[i-5]:
            # Bearish trend, enter if pullback (green candle)
            if c[i] > window_rates["open"][i]:
                return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=False)

        return None
