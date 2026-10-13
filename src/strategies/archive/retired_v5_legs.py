"""
Retired Portfolio V5 Legs (Pruned from active 4-leg core).

The 6-leg portfolio originally included these two legs:
- PDHLR_STRATEGY_V5 (magic 5008): PF 0.795, -$617.35 net, clogged Asian/London concurrency slots.
- NY_LIQUIDITY_EXPANSION_V5 (magic 5009): PF 0.953, -$39.08 net, sub-1.0 PF drag.

Pruning these 2 legs unlocked NVMR concurrency slots and reduced portfolio max drawdown
by 32% (from 6-leg backtest to 4-leg core: PF 1.141, Net +$4,495.43, Max DD $1,250.45 / 22.44%).
Preserved here for comparative audit and ablation testing.
"""

from src.strategies.bible_strategies import PDHLRStrategy
from src.strategies.ny_liquidity_expansion import NYLiquidityExpansion


class PDHLRStrategyV5(PDHLRStrategy):
    """Previous Day High/Low Reversal - Retired due to net negative performance (PF 0.795)."""
    def __init__(self):
        super().__init__()
        self.name = 'PDHLR_STRATEGY_V5'
        self.magic = 5008
        self.sl_atr_mult = 0.5
        self.tp_atr_mult = 1.5


class NYLiquidityExpansionV5(NYLiquidityExpansion):
    """NY Liquidity Expansion - Retired due to sub-1.0 profit factor (PF 0.953)."""
    def __init__(self):
        super().__init__()
        self.name = 'NY_LIQUIDITY_EXPANSION_V5'
        self.magic = 5009
        self.sl_atr_mult = 0.5
        self.tp_atr_mult = 1.5
