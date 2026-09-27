"""
Position sizing ladder for small-account survivability.

Implements the ladder from REAL_MONEY_READINESS.md Part II.2.
"""

from typing import Tuple


class SizingLadder:
    """
    Account-balance-based position sizing with hard floors and caps.
    
    Design principle: Risk per trade decreases as account grows.
    At minimum balance ($100-200), we're forced into 5-8% risk per the
    broker's 0.01 lot minimum. As balance grows, size up in discrete
    steps to keep risk in the 1.5-2.5% range.
    """
    
    # Ladder definition: (balance_threshold, lots_per_order, max_concurrent, max_total_exposure)
    LADDER = [
        # Phase 1: Survival mode (highest risk, most constrained)
        (0.0,    0.01, 1, 0.01),    # < $100: 1 position only, survive
        (100.0,  0.01, 1, 0.01),    # $100-200: still 1 position, 4-9% risk
        
        # Phase 2: Growth begins
        (200.0,  0.01, 2, 0.02),    # $200-400: 2 positions, 2-4% risk
        
        # Phase 3: Scaling
        (400.0,  0.01, 3, 0.03),    # $400-800: 3 positions, 1.5-2.5% risk
        (800.0,  0.02, 2, 0.04),    # $800+: 2×0.02 lots, 1.5-2% risk
        
        # Phase 4: Full scale (requires validation at larger account size)
        (1200.0, 0.02, 3, 0.06),    # $1200+: 3×0.02, ~1% risk per trade
    ]
    
    # Absolute minimum balance to continue trading
    POSITION_FLOOR = 50.0  # Stop trading below $50
    
    @classmethod
    def get_sizing(cls, balance: float) -> Tuple[float, int, float]:
        """
        Get position sizing for current balance.
        
        Args:
            balance: Account balance in USD
            
        Returns:
            (lots_per_order, max_concurrent_positions, max_total_exposure)
            
        Raises:
            ValueError: If balance is below position floor
        """
        if balance < cls.POSITION_FLOOR:
            raise ValueError(
                f"Balance ${balance:.2f} below position floor ${cls.POSITION_FLOOR:.2f}. "
                f"Trading halted."
            )
        
        # Find the appropriate ladder rung
        # Ladder is sorted ascending, so iterate backwards to find highest matching threshold
        for threshold, lots, max_concurrent, max_exposure in reversed(cls.LADDER):
            if balance >= threshold:
                return (lots, max_concurrent, max_exposure)
        
        # Shouldn't reach here if LADDER starts at 0.0
        return cls.LADDER[0][1:]  # Return first rung values
    
    @classmethod
    def get_risk_pct(cls, balance: float, lots: float, stop_distance_usd: float) -> float:
        """
        Calculate actual risk percentage for given position.
        
        Args:
            balance: Account balance
            lots: Position size in lots
            stop_distance_usd: Stop loss distance in USD (not pips)
            
        Returns:
            Risk as percentage of balance (e.g., 0.05 for 5%)
        """
        risk_usd = lots * stop_distance_usd
        return risk_usd / balance if balance > 0 else 0.0
    
    @classmethod
    def is_safe_to_trade(cls, balance: float) -> bool:
        """Check if balance is above position floor."""
        return balance >= cls.POSITION_FLOOR
    
    @classmethod
    def format_sizing_table(cls) -> str:
        """Return formatted sizing ladder for display."""
        lines = ["Position Sizing Ladder:", ""]
        lines.append("Balance Range | Lots/Order | Max Positions | Max Exposure | ~Risk/Trade")
        lines.append("-" * 75)
        
        for i, (threshold, lots, max_concurrent, max_exposure) in enumerate(cls.LADDER):
            if i < len(cls.LADDER) - 1:
                next_threshold = cls.LADDER[i + 1][0]
                balance_range = f"${threshold:.0f}-${next_threshold:.0f}"
            else:
                balance_range = f"${threshold:.0f}+"
            
            # Estimate risk at midpoint of range (using ~$10 ATR stop)
            mid_balance = threshold + 100 if i < len(cls.LADDER) - 1 else threshold + 200
            est_risk_pct = cls.get_risk_pct(mid_balance, lots, 10.0) * 100
            
            lines.append(
                f"{balance_range:16} | {lots:10.2f} | {max_concurrent:13} | "
                f"{max_exposure:12.2f} | ~{est_risk_pct:.1f}%"
            )
        
        lines.append("")
        lines.append(f"Position Floor: ${cls.POSITION_FLOOR:.2f} (trading halts below this)")
        
        return "\n".join(lines)


# Convenience function for main_loop integration
def should_halt_trading(balance: float) -> Tuple[bool, str]:
    """
    Check if trading should be halted due to low balance.
    
    Returns:
        (should_halt, reason)
    """
    if balance < SizingLadder.POSITION_FLOOR:
        return (
            True,
            f"Balance ${balance:.2f} below position floor ${SizingLadder.POSITION_FLOOR:.2f}"
        )
    return (False, "")


if __name__ == "__main__":
    # Display sizing ladder
    print(SizingLadder.format_sizing_table())
    print()
    
    # Test at various balances
    test_balances = [75, 105, 250, 500, 900, 1500]
    print("Examples:")
    print()
    
    for balance in test_balances:
        try:
            lots, max_conc, max_exp = SizingLadder.get_sizing(balance)
            risk_pct = SizingLadder.get_risk_pct(balance, lots, 10.0) * 100
            print(f"Balance ${balance:4.0f}: {lots:.2f} lots, {max_conc} positions, "
                  f"max {max_exp:.2f} exposure → ~{risk_pct:.1f}% risk/trade")
        except ValueError as e:
            print(f"Balance ${balance:4.0f}: HALTED - {e}")
