"""
Risk management - position limits, leverage limits, Kelly criterion
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RiskCheckResult:
    """Result of risk check"""
    approved: bool
    reason: str
    suggested_size: Optional[float] = None

class RiskManager:
    """Manage trading risk"""
    
    def __init__(self, position_limit: float = 0.10, exposure_limit: float = 0.50, leverage_limit: float = 10.0):
        """
        Initialize risk manager
        
        Args:
            position_limit: Max position size as % of portfolio (default 10%)
            exposure_limit: Max total exposure as % of portfolio (default 50%)
            leverage_limit: Max leverage (default 10x)
        """
        self.position_limit = position_limit
        self.exposure_limit = exposure_limit
        self.leverage_limit = leverage_limit
    
    def check_position_size(self, portfolio_value: float, position_size: float) -> RiskCheckResult:
        """Check if position size is within limits"""
        max_position = portfolio_value * self.position_limit
        
        if position_size > max_position:
            return RiskCheckResult(
                approved=False,
                reason=f"Position size {position_size} exceeds limit {max_position}",
                suggested_size=max_position
            )
        
        return RiskCheckResult(approved=True, reason="Position size within limits")
    
    def check_total_exposure(self, portfolio_value: float, current_exposure: float, new_position: float) -> RiskCheckResult:
        """Check if total exposure is within limits"""
        max_exposure = portfolio_value * self.exposure_limit
        total_exposure = current_exposure + new_position
        
        if total_exposure > max_exposure:
            return RiskCheckResult(
                approved=False,
                reason=f"Total exposure {total_exposure} exceeds limit {max_exposure}",
                suggested_size=max_exposure - current_exposure
            )
        
        return RiskCheckResult(approved=True, reason="Total exposure within limits")
    
    def check_leverage(self, notional_value: float, collateral: float) -> RiskCheckResult:
        """Check if leverage is within limits"""
        leverage = notional_value / collateral if collateral > 0 else 0
        
        if leverage > self.leverage_limit:
            return RiskCheckResult(
                approved=False,
                reason=f"Leverage {leverage:.2f}x exceeds limit {self.leverage_limit}x"
            )
        
        return RiskCheckResult(approved=True, reason="Leverage within limits")
    
    def kelly_criterion(self, win_probability: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly criterion position size
        
        Args:
            win_probability: Probability of winning (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            
        Returns:
            Fraction of capital to risk
        """
        if avg_win <= 0 or avg_loss <= 0:
            return 0.0
        
        kelly = (win_probability * avg_win - (1 - win_probability) * avg_loss) / avg_win
        
        # Bound Kelly fraction between -1 and 1
        return max(-1.0, min(1.0, kelly))
