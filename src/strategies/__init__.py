"""Strategy package.

ACTIVE (live in main_loop): portfolio_v4 -- four session-specialist legs.
  See src/strategies/portfolio_v4.py and docs/research/STRATEGY_REGISTRY.md.

RESEARCH ONLY (not imported by main_loop): ema_stack, trend_sniper_sar,
  luxalgo_fvg, supertrend_ema.

ARCHIVED (2026-09-01, rohith phase 3): MorningMomentum, EMAPullback, AsianSweep,
  KeltnerBreakout, MACDCross, AsianBreakout, PDHLBreakout, LondonBot
  -- all scored below the random-entry control; saved in
  src/strategies/archive/, NOT deleted.
"""

from src.strategies.base_strategy import BaseStrategy, Signal

__all__ = [
    "BaseStrategy",
    "Signal",
]
