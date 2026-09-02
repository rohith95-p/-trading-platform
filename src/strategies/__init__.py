"""Strategy package.

ACTIVE: EMAStack (best candidate found to date; see docs/STRATEGY_REGISTRY.md).
ARCHIVED (2026-09-01, rohith phase 3): MorningMomentum, EMAPullback, AsianSweep,
KeltnerBreakout, MACDCross, AsianBreakout, PDHLBreakout, LondonBot
          (saved in src/strategies/archive/ -- NOT deleted).
"""

from src.strategies.base_strategy import BaseStrategy, Signal
from src.strategies.ema_stack import EMAStack

__all__ = [
    "BaseStrategy",
    "Signal",
    "EMAStack",
]
