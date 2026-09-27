import numpy as np
from typing import Optional

from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.market_study import atr as _atr, build_features, session_mask

class LondonJudasSwing(BaseStrategy):
    """
    Setup 1: London Judas Swing
    Sweeps the Asian range high/low, rejects back inside, displaces.
    """
    execute_immediately = True
    edge_trigger = False
    _min_bars = 250

    def __init__(
        self,
        penetration_atr: float = 0.1,
        displacement_body_atr: float = 0.3,
        min_range_atr: float = 0.5,
        sl_atr_mult: float = 1.2,
        tp_atr_mult: float = 2.5,
        session: tuple = (12.5, 15.5),
        magic: int = 91001,
        name: str = "LONDON_JUDAS",
    ):
        self.penetration_atr = penetration_atr
        self.displacement_body_atr = displacement_body_atr
        self.min_range_atr = min_range_atr
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.session = session
        self.magic = magic
        self.name = name

    def _in_asian_session(self, ts: int) -> bool:
        hr = (int(ts) + 19800) % 86400 / 3600.0
        return 2.5 <= hr < 11.5

    def _in_london_session(self, ts: int) -> bool:
        hr = (int(ts) + 19800) % 86400 / 3600.0
        a, b = self.session
        return a <= hr < b

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None

        h = m15_rates["high"].astype(float)
        l = m15_rates["low"].astype(float)
        c = m15_rates["close"].astype(float)
        o = m15_rates["open"].astype(float)
        t = m15_rates["time"].astype(np.int64)

        if not self._in_london_session(t[-2]):
            return None

        atr_14 = _atr(m15_rates, 14)
        a = atr_14[-2]
        if not np.isfinite(a) or a <= 0:
            return None

        # 1. Asian Range Extraction
        # Look back from -3 to find the most recent Asian session bars
        asian_high = -np.inf
        asian_low = np.inf
        found_asian = False
        
        # We need to find the *current day's* Asian session.
        # We walk backwards. Once we hit Asian hours, we record. 
        # Once we leave Asian hours (going backwards into the previous NY session), we stop.
        in_asia = False
        for i in range(len(m15_rates) - 3, -1, -1):
            if self._in_asian_session(t[i]):
                in_asia = True
                found_asian = True
                asian_high = max(asian_high, h[i])
                asian_low = min(asian_low, l[i])
            elif in_asia:
                # We were in Asia, now we're out (going backwards). Stop.
                break

        if not found_asian:
            return None

        asian_range = asian_high - asian_low
        if asian_range < self.min_range_atr * a:
            return None

        # 3. Judas Sweep Detection (bar -2)
        bull_sweep = l[-2] < (asian_low - self.penetration_atr * a)
        bear_sweep = h[-2] > (asian_high + self.penetration_atr * a)

        if not (bull_sweep or bear_sweep):
            return None

        # 4. MSS / Rejection Confirmation
        # 5. Displacement Strength
        body = abs(c[-2] - o[-2])
        has_displacement = body >= self.displacement_body_atr * a

        if bull_sweep and c[-2] > asian_low and c[-2] > o[-2] and has_displacement:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name, magic=self.magic, is_buy=True)
            
        if bear_sweep and c[-2] < asian_high and c[-2] < o[-2] and has_displacement:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=False)

        return None


class LondonOTEReentry(BaseStrategy):
    """
    Setup 2: London OTE Re-entry
    Wait for London impulse, re-enter at 61.8-78.6% Fib retracement if there's an FVG.
    """
    execute_immediately = True
    edge_trigger = False
    _min_bars = 250

    def __init__(
        self,
        fvg_lookback: int = 8,
        sl_atr_mult: float = 1.0,
        tp_atr_mult: float = 2.0,
        session: tuple = (17.0, 18.5),
        magic: int = 91002,
        name: str = "LONDON_OTE",
    ):
        self.fvg_lookback = fvg_lookback
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.session = session
        self.magic = magic
        self.name = name

    def _in_london_killzone(self, ts: int) -> bool:
        hr = (int(ts) + 19800) % 86400 / 3600.0
        return 12.5 <= hr < 15.5

    def _in_ote_window(self, ts: int) -> bool:
        hr = (int(ts) + 19800) % 86400 / 3600.0
        a, b = self.session
        return a <= hr < b

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None

        t = m15_rates["time"].astype(np.int64)
        
        if not self._in_ote_window(t[-2]):
            return None

        h = m15_rates["high"].astype(float)
        l = m15_rates["low"].astype(float)
        c = m15_rates["close"].astype(float)

        # 1. London Swing Detection
        london_high = -np.inf
        london_low = np.inf
        london_close = None
        london_open = None
        found_london = False
        
        in_london = False
        for i in range(len(m15_rates) - 3, -1, -1):
            if self._in_london_killzone(t[i]):
                if not in_london:
                    # First bar found going backwards = most recent London bar = session close
                    london_close = c[i]
                in_london = True
                found_london = True
                london_high = max(london_high, h[i])
                london_low = min(london_low, l[i])
                london_open = m15_rates["open"][i]  # Overwrites to earliest London bar's open
            elif in_london:
                break

        if not found_london or london_open is None or london_close is None:
            return None

        london_range = london_high - london_low
        if london_range <= 0:
            return None
            
        is_london_bull = london_close > london_open
        is_london_bear = london_close < london_open
        
        if not (is_london_bull or is_london_bear):
             return None

        # 3. OTE Zone Check
        if is_london_bull:
            ote_high = london_high - 0.618 * london_range
            ote_low = london_high - 0.786 * london_range
            in_ote = ote_low <= c[-2] <= ote_high
        else:
            ote_low = london_low + 0.618 * london_range
            ote_high = london_low + 0.786 * london_range
            in_ote = ote_low <= c[-2] <= ote_high

        if not in_ote:
            return None

        # 4. Reversal Candle Confluence (loosened from strict FVG)
        # Enter if we close a candle in the direction of the London trend while in the OTE zone.
        o_minus_2 = m15_rates["open"][-2]
        
        if is_london_bull and c[-2] > o_minus_2:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name, magic=self.magic, is_buy=True)
            
        if is_london_bear and c[-2] < o_minus_2:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name, magic=self.magic, is_buy=False)

        return None
