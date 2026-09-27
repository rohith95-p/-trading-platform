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
        
        Regression: 2026-09-24 commit b8ab85c silently flipped this to True.
        Reference: HYP-005, HYP-018, HYP-034 in RESEARCH_LEDGER.md
        """
        assert main_loop.ENABLE_TRAILING is False, (
            "ENABLE_TRAILING must be False. "
            "Trailing stops convert 2.5×ATR winners into 0.4×ATR exits. "
            "See RESEARCH_LEDGER.md HYP-005."
        )
    
    def test_pyramiding_must_be_disabled(self):
        """
        CRITICAL: Pyramiding is net-negative (PF 0.592 with trail+pyramid on).
        
        Reference: main_loop.py docstring, REPO_GUIDE.md
        """
        assert main_loop.ENABLE_PYRAMIDING is False, (
            "ENABLE_PYRAMIDING must be False. "
            "Pyramiding adds full-size positions into extended moves."
        )
    
    def test_d1_gate_configuration(self):
        """
        D1 gate status is a deliberate choice with documented trade-offs.
        
        This test documents the current state, not enforces a value.
        If this fails, verify the change is intentional and documented.
        """
        # Current configuration as of 2026-09-24
        assert main_loop.ENABLE_D1_GATE is True, (
            "D1 gate configuration has changed. "
            "Verify this is intentional and documented in RESEARCH_LEDGER.md"
        )


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
        Document the current enforcement status of risk_rules.py circuit breakers.
        
        This is NOT enforcing a value, just making the status visible in tests.
        """
        from src.core import risk_rules
        
        # As of 2026-09-25: shadow mode (tracking but not blocking)
        enforcement_status = getattr(risk_rules, 'ENFORCE', None)
        
        # This test documents the status, doesn't enforce a value
        print(f"\nINFO: risk_rules.ENFORCE = {enforcement_status}")
        print("      (True = blocking trades, False = shadow mode)")


class TestPortfolioConfiguration:
    """Tests for current live portfolio composition."""
    
    def test_portfolio_strategy_count(self):
        """Current portfolio must match documented configuration."""
        from src.strategies.portfolio_v4 import PORTFOLIO_V4
        
        assert len(PORTFOLIO_V4) == 2, (
            f"PORTFOLIO_V4 has {len(PORTFOLIO_V4)} strategies, expected 2. "
            "Current config: NVMR_TARGET_10 + LARS_LONDON"
        )
    
    def test_portfolio_strategy_names(self):
        """Verify expected strategies are in the portfolio."""
        from src.strategies.portfolio_v4 import PORTFOLIO_V4
        
        strategy_names = [cls().name for cls in PORTFOLIO_V4]
        expected = {'NVMR_TARGET_10', 'LARS_LONDON'}
        actual = set(strategy_names)
        
        assert actual == expected, (
            f"Portfolio strategies: {actual}, expected: {expected}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
