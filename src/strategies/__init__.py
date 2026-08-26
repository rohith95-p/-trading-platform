"""Strategy package.

ACTIVE: MorningMomentum (strict 4-condition winner).
ARCHIVED: KeltnerBreakout, MACDCross, AsianBreakout, PDHLBreakout
          (saved in src/strategies/archive/ -- NOT deleted).
"""

from src.strategies.base_strategy import BaseStrategy, Signal
from src.strategies.morning_momentum import MorningMomentum
from src.strategies.ema_pullback import EMAPullback
from src.strategies.asian_sweep import AsianSweep

__all__ = [
    "BaseStrategy",
    "Signal",
    "MorningMomentum",
    "EMAPullback",
    "AsianSweep",
]
