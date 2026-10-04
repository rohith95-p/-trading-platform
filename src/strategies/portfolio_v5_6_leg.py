# --- PORTFOLIO V5 (6-Leg Validated Core) ---
# Cleaned portfolio with losing strategies removed:
# - REMOVED: EURUSD_ASIAN_RANGE (PF 0.83, -$1,980)
# - REMOVED: LIQUIDITY_SWEEP_REVERSAL (PF 1.001, +$4 essentially random)
# - REMOVED: FOREX_SESSION_MOMENTUM (PF 1.043, +$161 marginal, contributes to overlap losses)
# Expected Performance: PF ~1.40+, Net ~$6,400+
#
# 2026-10-02 SL AUDIT: sl_atr_mult was temporarily raised to 0.5, then REVERTED.
# A/B backtest (scripts/bt_sl_increase_ab.py) proved 0.1x ATR is the correct SL:
#   Control  (sl=0.1): PF 2.67, net $682, max DD 4.4%, avg loss $0.91
#   Treatment(sl=0.5): PF 1.13, net $145, max DD 36.6%, avg loss $4.37 — REJECTED
# The strategy is a high-payoff (19.68x), low-win-rate (12%) system. The tiny SL
# is the mechanism. Widening it makes losses 5x larger, destroying the edge.
# Today's live losses were 5 sequential losers in a bad regime — expected variance,
# not a structural SL flaw. See: research/runs/*_sl_increase_ab/manifest.json
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat
from src.strategies.bible_strategies import NVMRStrategy as _NVMRStrategy
from src.strategies.bible_strategies import PDHLRStrategy
from src.strategies.ny_liquidity_expansion import NYLiquidityExpansion
from src.strategies.portfolio_v4 import _LiquidityFilteredFVG

class TrendPullbackV5(TrendPullbackStrat):
    def __init__(self):
        super().__init__()
        self.name = 'TREND_PULLBACK_V5'
        self.magic = 5001
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0

class BBMeanReversionV5(BBMeanReversionStrat):
    def __init__(self):
        super().__init__()
        self.name = 'BB_MEAN_REVERSION_V5'
        self.magic = 5002
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0
    
class NVMRPortfolioV5(_NVMRStrategy):
    def __init__(self):
        super().__init__()
        self.name = 'NVMR_TARGET_10_V5'
        self.magic = 5003
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0

class FVGNYTightV5(_LiquidityFilteredFVG):
    def __init__(self):
        super().__init__()
        self.name = 'FVG_NY_TIGHT_V5'
        self.magic = 5005
        self.session = (17.5, 21.5)
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0

class PDHLRStrategyV5(PDHLRStrategy):
    def __init__(self):
        super().__init__()
        self.name = 'PDHLR_STRATEGY_V5'
        self.magic = 5008
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0

class NYLiquidityExpansionV5(NYLiquidityExpansion):
    def __init__(self):
        super().__init__()
        self.name = 'NY_LIQUIDITY_EXPANSION_V5'
        self.magic = 5009
        self.sl_atr_mult = 0.1
        self.tp_atr_mult = 2.0

PORTFOLIO = [
    TrendPullbackV5, 
    BBMeanReversionV5, 
    NVMRPortfolioV5,
    FVGNYTightV5,
    PDHLRStrategyV5,
    NYLiquidityExpansionV5
]

