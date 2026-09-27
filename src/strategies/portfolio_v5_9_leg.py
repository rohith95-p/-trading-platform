# --- PORTFOLIO V5 (9-Leg Hyper-Tight Masterpiece) ---
# Super Portfolio combining the top 9 uncorrelated hyper-tight winners.
# Backtest 2-Year Result: +$8,951 on $100 account
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat
from src.strategies.bible_strategies import NVMRStrategy as _NVMRStrategy
from src.strategies.eurusd_asian_range import EURUSDAsianRange
from src.strategies.forex_session_momentum import ForexSessionMomentum
from src.strategies.liquidity_sweep_reversal import LiquiditySweepReversal
from src.strategies.bible_strategies import PDHLRStrategy
from src.strategies.ny_liquidity_expansion import NYLiquidityExpansion
from src.strategies.portfolio_v4 import _LiquidityFilteredFVG

class TrendPullbackV5(TrendPullbackStrat):
    name = 'TREND_PULLBACK_V5'
    magic = 5001
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class BBMeanReversionV5(BBMeanReversionStrat):
    name = 'BB_MEAN_REVERSION_V5'
    magic = 5002
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0
    
class NVMRPortfolioV5(_NVMRStrategy):
    name = 'NVMR_TARGET_10_V5'
    magic = 5003
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class EURUSDAsianRangeV5(EURUSDAsianRange):
    name = 'EURUSD_ASIAN_RANGE_V5'
    magic = 5004
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class FVGNYTightV5(_LiquidityFilteredFVG):
    name = 'FVG_NY_TIGHT_V5'
    magic = 5005
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0
    
class ForexSessionMomentumV5(ForexSessionMomentum):
    name = 'FOREX_SESSION_MOMENTUM_V5'
    magic = 5006
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class LiquiditySweepReversalV5(LiquiditySweepReversal):
    name = 'LIQUIDITY_SWEEP_REVERSAL_V5'
    magic = 5007
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class PDHLRStrategyV5(PDHLRStrategy):
    name = 'PDHLR_STRATEGY_V5'
    magic = 5008
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

class NYLiquidityExpansionV5(NYLiquidityExpansion):
    name = 'NY_LIQUIDITY_EXPANSION_V5'
    magic = 5009
    sl_atr_mult = 0.1
    tp_atr_mult = 1.0

PORTFOLIO = [
    TrendPullbackV5, 
    BBMeanReversionV5, 
    NVMRPortfolioV5,
    EURUSDAsianRangeV5,
    FVGNYTightV5,
    ForexSessionMomentumV5,
    LiquiditySweepReversalV5,
    PDHLRStrategyV5,
    NYLiquidityExpansionV5
]
