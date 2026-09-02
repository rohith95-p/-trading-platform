"""LuxAlgo Fair Value Gap (FVG) - Reference Implementation

Status: RESEARCH ONLY / FOR UNDERSTANDING
Not actively imported by main_loop. 

This is a direct Python port of the LuxAlgo Fair Value Gap PineScript.
It tracks unmitigated FVGs dynamically. It does not blindly fire signals on gap 
creation (unlike the basic FVG momentum strategy). Instead, it maintains a state 
of active gaps and can be used to filter trades, find confluence, or trade bounces.
"""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass
import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5

@dataclass
class FVGBox:
    max_price: float
    min_price: float
    is_bull: bool
    creation_time: int


class LuxAlgoFVG(BaseStrategy):
    """
    Tracks Unmitigated Fair Value Gaps.
    
    A Bullish FVG forms when:
      - Current Low > High of 2 bars ago
      - Previous Close > High of 2 bars ago
      - Gap size exceeds a threshold
      
    It becomes "mitigated" (filled) and is removed when price closes below the gap minimum.
    """

    name = "LUXALGO_FVG"
    magic = 3099

    def __init__(self, threshold_pct: float = 0.0, use_auto_threshold: bool = False):
        self.threshold_pct = threshold_pct
        self.use_auto_threshold = use_auto_threshold
        
        # State tracking (matching LuxAlgo's dynamic arrays)
        self.unmitigated_fvgs: List[FVGBox] = []
        
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 3:
            return None

        # 1. Calculate Threshold (Auto vs Manual)
        if self.use_auto_threshold:
            # cumulative average of (high-low)/low
            high_arr = m15_rates['high']
            low_arr = m15_rates['low']
            hl_pct = (high_arr - low_arr) / np.maximum(low_arr, 1e-9)
            threshold = float(np.mean(hl_pct)) # Approximate "ta.cum / bar_index" over the window
        else:
            threshold = self.threshold_pct / 100.0

        # We evaluate the most recently closed candle (-2)
        # i-0 is the forming candle, i-1 is the closed candle, i-2 is previous, i-3 is the one before that.
        # So in PineScript: low > high[2] maps to: closed_low > high_of_3_bars_ago
        
        curr_bar = m15_rates[-2] 
        prev_bar = m15_rates[-3]
        two_bars_ago = m15_rates[-4]

        # 2. FVG Detection Logic
        # Bull FVG: low > high[2] AND close[1] > high[2] AND gap % > threshold
        bull_fvg = (curr_bar['low'] > two_bars_ago['high']) and \
                   (prev_bar['close'] > two_bars_ago['high']) and \
                   ((curr_bar['low'] - two_bars_ago['high']) / two_bars_ago['high'] > threshold)
                   
        # Bear FVG: high < low[2] AND close[1] < low[2] AND gap % > threshold
        bear_fvg = (curr_bar['high'] < two_bars_ago['low']) and \
                   (prev_bar['close'] < two_bars_ago['low']) and \
                   ((two_bars_ago['low'] - curr_bar['high']) / curr_bar['high'] > threshold)

        # 3. Add to Unmitigated State
        if bull_fvg:
            self.unmitigated_fvgs.append(
                FVGBox(
                    max_price=curr_bar['low'], 
                    min_price=two_bars_ago['high'], 
                    is_bull=True, 
                    creation_time=int(curr_bar['time'])
                )
            )
        elif bear_fvg:
            self.unmitigated_fvgs.append(
                FVGBox(
                    max_price=two_bars_ago['low'], 
                    min_price=curr_bar['high'], 
                    is_bull=False, 
                    creation_time=int(curr_bar['time'])
                )
            )

        # 4. Mitigation Logic (Remove filled gaps)
        # LuxAlgo tests for mitigation backwards through the array. 
        # A bull FVG is mitigated if close < min. A bear FVG is mitigated if close > max.
        
        still_unmitigated = []
        for box in self.unmitigated_fvgs:
            if box.is_bull:
                if curr_bar['close'] < box.min_price:
                    continue # Mitigated! (Dropped)
            else:
                if curr_bar['close'] > box.max_price:
                    continue # Mitigated! (Dropped)
                    
            still_unmitigated.append(box)
            
        self.unmitigated_fvgs = still_unmitigated

        # 5. Signal Generation (Optional)
        # As requested: "not for a signal, just for a better understanding of the trade"
        # We do not fire blindly. We return None so the bot does not trade this directly.
        # You can read `self.unmitigated_fvgs` from other strategies as a confluence filter.
        
        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        return None

    def set_pending(self, signal: Signal, candle_time: int) -> None:
        self._pending_signal = signal
        self._pending_candle_time = candle_time
