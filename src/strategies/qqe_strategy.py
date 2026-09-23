import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional
import MetaTrader5 as mt5

from src.strategies.base_strategy import BaseStrategy, Signal

def calc_qqe_loop(rsi_ma, dar):
    n = len(rsi_ma)
    longband = np.zeros(n)
    shortband = np.zeros(n)
    trend = np.ones(n)
    
    newshortband = rsi_ma + dar
    newlongband = rsi_ma - dar
    
    for i in range(1, n):
        if rsi_ma[i-1] > longband[i-1] and rsi_ma[i] > longband[i-1]:
            longband[i] = max(longband[i-1], newlongband[i])
        else:
            longband[i] = newlongband[i]
            
        if rsi_ma[i-1] < shortband[i-1] and rsi_ma[i] < shortband[i-1]:
            shortband[i] = min(shortband[i-1], newshortband[i])
        else:
            shortband[i] = newshortband[i]
            
        if rsi_ma[i-1] <= shortband[i-1] and rsi_ma[i] > shortband[i-1]:
            trend[i] = 1
        elif rsi_ma[i-1] >= longband[i-1] and rsi_ma[i] < longband[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
            
    return trend, longband, shortband

class QQEStrategy(BaseStrategy):
    def __init__(self, session_mask=(11.5, 15.5)):
        self.name = "QQE"
        self.magic = 9999
        self.session_mask = session_mask
        self.sl_atr_mult = 2.0
        self.tp_atr_mult = 3.0
        
    def evaluate(self, rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if rates is None or len(rates) < 260:
            return None
            
        df = pd.DataFrame(rates)
        
        # Check session on the last completed candle (index -2)
        t = datetime.fromtimestamp(df['time'].iloc[-2], tz=timezone.utc)
        hr = (t.hour + t.minute/60.0 + 5.5) % 24
        if not (self.session_mask[0] <= hr < self.session_mask[1]):
            return None
            
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Smooth RSI
        df['rsi_ma'] = df['rsi'].ewm(span=5, adjust=False).mean()
        
        # ATR of RSI
        df['atr_rsi'] = abs(df['rsi_ma'].shift(1) - df['rsi_ma'])
        df['ma_atr_rsi'] = df['atr_rsi'].ewm(span=27, adjust=False).mean()
        df['dar'] = df['ma_atr_rsi'].ewm(span=27, adjust=False).mean() * 4.238
        
        rsi_ma_arr = df['rsi_ma'].fillna(0).values
        dar_arr = df['dar'].fillna(0).values
        
        trend, _, _ = calc_qqe_loop(rsi_ma_arr, dar_arr)
        
        # We look at the crossover on the last completed candle (-2)
        if trend[-2] == 1 and trend[-3] != 1:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name, magic=self.magic, is_buy=True)
        elif trend[-2] == -1 and trend[-3] != -1:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=False)
            
        return None
