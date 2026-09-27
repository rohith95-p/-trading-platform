# --- PORTFOLIO V5 (3-Leg Hyper-Tight Masterpiece) ---
# Super Portfolio combining the top 3 uncorrelated hyper-tight winners.
# Backtest 2-Year Result: +$4,821 on $100 account
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat
from src.strategies.bible_strategies import NVMRStrategy as _NVMRStrategy

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

PORTFOLIO = [TrendPullbackV5, BBMeanReversionV5, NVMRPortfolioV5]
