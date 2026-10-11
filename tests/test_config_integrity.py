"""
Critical configuration regression tests.

These tests MUST pass before any deployment. They catch configuration
drift that has caused production issues in the past.
"""
import pytest
from src.core import main_loop


class TestCriticalFlags:
    """Tests for flags that have caused production incidents."""
    
    def test_trailing_stops_must_be_disabled(self):
        """
        CRITICAL: Trailing stops are net-negative (PF 0.592, -$93.59).
        """
        from src.backtesting.engine import EngineConfig
        assert EngineConfig().enable_trailing is False, "ENABLE_TRAILING must be False in EngineConfig."
    
    def test_pyramiding_must_be_disabled(self):
        """
        CRITICAL: Pyramiding is net-negative (PF 0.592 with trail+pyramid on).
        """
        from src.backtesting.engine import EngineConfig
        assert EngineConfig().enable_pyramiding is False, "ENABLE_PYRAMIDING must be False in EngineConfig."
    
    def test_d1_gate_configuration(self):
        """
        D1 gate status is a deliberate choice with documented trade-offs.
        """
        from src.backtesting.engine import EngineConfig
        assert EngineConfig().enable_d1_bias_gate is True, "D1 gate configuration has changed."


class TestPositionLimits:
    """Tests for position sizing and exposure caps."""
    
    def test_fixed_lot_size_documented(self):
        """Current fixed lot size must match documentation."""
        from src.core.execution_handler import FIXED_LOT_SIZE
        
        # As of 2026-09-24: bumped to 0.02 for "$10/day goal"
        assert FIXED_LOT_SIZE == 0.02, (
            f"FIXED_LOT_SIZE is {FIXED_LOT_SIZE}, expected 0.02. "
            "If changed, update REPO_GUIDE.md and README.md"
        )
    
    def test_max_total_exposure(self):
        """Maximum total volume must not exceed small-account limits."""
        from src.core.execution_handler import MAX_TOTAL_VOLUME
        
        assert MAX_TOTAL_VOLUME <= 0.04, (
            f"MAX_TOTAL_VOLUME is {MAX_TOTAL_VOLUME}. "
            "Values > 0.04 not validated for sub-$200 accounts."
        )
    
    def test_max_concurrent_positions(self):
        """Concurrent position limit must match validated config."""
        from src.core.execution_handler import MAX_CONCURRENT_POSITIONS
        
        assert MAX_CONCURRENT_POSITIONS == 2, (
            f"MAX_CONCURRENT_POSITIONS is {MAX_CONCURRENT_POSITIONS}. "
            "Current portfolio validated with 2 positions max."
        )


class TestRiskControls:
    """Tests for risk management configuration."""
    
    def test_daily_loss_limit(self):
        """Daily loss limit must be configured."""
        from src.core.risk_manager import DAILY_LOSS_LIMIT_PCT
        
        assert DAILY_LOSS_LIMIT_PCT == 0.06, (
            f"DAILY_LOSS_LIMIT_PCT is {DAILY_LOSS_LIMIT_PCT}, expected 0.06 (6%)"
        )
    
    def test_risk_rules_enforcement_status(self):
        """
        Risk rules MUST be enforced to prevent bypassing circuit breakers.
        """
        from src.core import risk_rules
        
        assert getattr(risk_rules, 'ENFORCE', False) is True, "Circuit breakers must be enforced, not in shadow mode."


class TestPortfolioConfiguration:
    """Tests for current live portfolio composition."""
    
    def test_portfolio_strategy_count(self):
        """Current portfolio must match documented configuration."""
        from src.strategies.portfolio_v5_6_leg import PORTFOLIO as PORTFOLIO_V5
        
        assert len(PORTFOLIO_V5) == 6, (
            f"PORTFOLIO_V5 has {len(PORTFOLIO_V5)} strategies, expected 6."
        )
    
    def test_portfolio_strategy_names(self):
        """Verify expected strategies are in the portfolio."""
        from src.strategies.portfolio_v5_6_leg import PORTFOLIO as PORTFOLIO_V5
        
        strategy_names = [cls().name for cls in PORTFOLIO_V5]
        expected = {
            'TREND_PULLBACK_V5',
            'BB_MEAN_REVERSION_V5',
            'NVMR_TARGET_10_V5',
            'FVG_NY_TIGHT_V5',
            'PDHLR_STRATEGY_V5',
            'NY_LIQUIDITY_EXPANSION_V5'
        }
        actual = set(strategy_names)
        
        assert actual == expected, (
            f"Portfolio strategies: {actual}, expected: {expected}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
