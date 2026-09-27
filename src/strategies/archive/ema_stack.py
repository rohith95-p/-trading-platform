"""EMAStack -- research candidate, NOT approved for live trading.

Status: RESEARCH ONLY. Not imported by `main_loop` and must not be until it has
cleared the remaining gates in docs/research/RESEARCH_LEDGER.md.

The setup is a trend *state*, not a trend *event*: it takes a position whenever
the EMA ribbon is ordered and price is on the correct side of the fast EMA. It
carries no breakout trigger, no volume filter and no oscillator band, because
the screen found those filters subtract from this signal rather than add to it.

Why it is here at all: across 108 screened candidates it was the only base setup
that beat a session- and direction-matched random control across every session
and exit geometry tested, stayed positive across all 45 parameter perturbations,
and was profitable on the short side as well as the long -- which rules out the
gold uptrend as the explanation.

What would falsify it: a regime where the ribbon orders and re-orders rapidly.
Walk-forward fold 3 (2025-10-24 to 2026-02-05) was exactly that and lost.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5

FAST = 20
MID = 50
SLOW = 200


class EMAStack(BaseStrategy):
    """Long while EMA(20) > EMA(50) > EMA(200) and close > EMA(20); short inverted."""

    name = "EMA_STACK"
    magic = 3001

    def __init__(self, fast: int = FAST, mid: int = MID, slow: int = SLOW):
        self.fast, self.mid, self.slow = fast, mid, slow
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(self, m15_rates: np.ndarray,
                 m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        # EMA(200) needs far more than its period to converge. main_loop supplies
        # 250 bars, which is not enough for the slow leg to be meaningful, so the
        # requirement is stated here rather than silently tolerated.
        need = self.slow + 60
        if m15_rates is None or len(m15_rates) < need:
            return None

        closes = m15_rates["close"]
        e_fast = self.ema(closes, self.fast)
        e_mid = self.ema(closes, self.mid)
        e_slow = self.ema(closes, self.slow)

        # index -2 is the last CLOSED candle; -1 is still forming
        c, f_, m_, s_ = closes[-2], e_fast[-2], e_mid[-2], e_slow[-2]
        if np.isnan(f_) or np.isnan(m_) or np.isnan(s_):
            return None

        if f_ > m_ > s_ and c > f_:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        if f_ < m_ < s_ and c < f_:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                          magic=self.magic, is_buy=False)
        return None

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        return None

    def set_pending(self, signal: Signal, candle_time: int) -> None:
        self._pending_signal = signal
        self._pending_candle_time = candle_time
