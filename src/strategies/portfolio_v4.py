"""Portfolio v4 -- the best validated combined result of the rohith research
effort (2026-09-01). Four session-specialist strategies sharing one account:

    squeeze_break ASIA   (SL 2.0x / TP 4.0xATR)
    ema_stack     LONDON (SL 0.75x / TP 3.0xATR, tight-risk variant)
    fvg           NY     (SL 0.5x / TP 2.5xATR, tight-risk variant)
    range_rejection NY   (SL 0.75x / TP 2.25xATR, tight-risk variant)

Replayed together on one shared account with the real 6% daily breaker:
PF 1.512, net $703 over ~100 days (~$7.03/day), min balance $106 (never
dropped below the $105.74 start), max drawdown 35.0%.
See docs/research/PHASE3_FULL_SWEEP_RESULTS.md and ledger HYP-036/038.

Each class carries its own sl_atr_mult / tp_atr_mult, read by main_loop.py
and passed through to RiskManager.calculate_atr_stops() via the new
tp_multiplier parameter -- these do NOT match the live system's hardcoded
session multipliers (1.5 London/NY, 2.0 Asia), which is exactly why a
per-strategy override was needed rather than relying on session auto-detect.

Caveats carried forward honestly, not hidden:
- Single ~100-day window (the only period with true M1 data on this broker).
  No holdout validation yet.
- 35% max drawdown is the worst of any portfolio variant tested -- a real
  tradeoff for the higher return, not a free upgrade.
- Under macro-rule "strict short stops" gating (RiskManager._strict_short_stops),
  SHORT signals get a hardcoded 1.0/2.0xATR stop/target regardless of what
  is requested here -- existing live risk control, not overridden by design.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.candidates import build_library
from src.research.market_study import build_features, session_mask

_LIB = {c.id: c for c in build_library()}


class _SessionSpecialist(BaseStrategy):
    """Shared plumbing for the 4 portfolio_v4 legs."""

    candidate_id: str
    session: tuple
    sl_atr_mult: float
    tp_atr_mult: float
    # main_loop.py fetches exactly 250 M15 bars (its documented live history
    # window) -- 260 (copied from EMAStack's own EMA200-convergence margin)
    # silently blocked every evaluate() call forever. Found live: all 4
    # strategies returned None on every check with no error, no log line,
    # nothing to indicate why. Fixed 2026-09-02, see ledger HYP-045.
    _min_bars = 250
    # CRITICAL: the backtest engine that validated every number in this file
    # executes a signal immediately on the bar after it fires -- it has no
    # "queue and confirm next candle" concept. main_loop.py's default path for
    # non-London sessions DOES queue, and check_pending_confirmation() below
    # always returns None, so a queued signal would be silently dropped
    # forever. This flag routes these strategies through the same
    # execute-immediately path London already had, matching what was actually
    # tested. Found by tracing real account history, not by inspection --
    # see docs/research/RESEARCH_LEDGER.md HYP-042.
    execute_immediately = True

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        raw = _LIB[self.candidate_id].rule(f)
        mask = session_mask(f["ist_hour"], self.session)
        sig = np.where(mask, raw, 0)
        s = sig[-2]
        if s == 0 or (isinstance(s, float) and np.isnan(s)):
            return None
        if s > 0:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                      magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


class SqueezeBreakAsia(_SessionSpecialist):
    """Squeeze breakout, ASIA session (02:30-11:30 IST). Isolated PF 1.741."""
    name = "SQUEEZE_ASIA"
    magic = 3011
    candidate_id = "XAU-062"
    session = (2.5, 11.5)
    sl_atr_mult = 2.0
    tp_atr_mult = 4.0


class EMAStackLondonTight(_SessionSpecialist):
    """EMA ribbon, LONDON session (11:30-15:30 IST), tight-risk variant
    (~$6 avg risk, ~$26 avg win). Isolated PF 1.286."""
    name = "EMASTACK_LONDON_TIGHT"
    magic = 3012
    candidate_id = "XAU-005"
    session = (11.5, 15.5)
    sl_atr_mult = 0.75
    tp_atr_mult = 3.0


class FVGNYTight(_SessionSpecialist):
    """Fair value gap, NY session (17:30-21:30 IST), tight-risk variant
    (~$5 avg risk, ~$26 avg win). Isolated PF 1.661 -- the strongest single
    leg in the portfolio."""
    name = "FVG_NY_TIGHT"
    magic = 3013
    candidate_id = "XAU-092"
    session = (17.5, 21.5)
    sl_atr_mult = 0.5
    tp_atr_mult = 2.5


class RangeRejectionNYTight(_SessionSpecialist):
    """Range rejection wick, NY session (17:30-21:30 IST), tight-risk
    variant (~$7 avg risk, ~$22 avg win). Isolated PF 1.726, smaller
    sample (n=26) than the other three legs."""
    name = "RANGEREJECTION_NY_TIGHT"
    magic = 3014
    candidate_id = "XAU-049"
    session = (17.5, 21.5)
    sl_atr_mult = 0.75
    tp_atr_mult = 2.25


PORTFOLIO_V4 = [SqueezeBreakAsia, EMAStackLondonTight, FVGNYTight, RangeRejectionNYTight]
