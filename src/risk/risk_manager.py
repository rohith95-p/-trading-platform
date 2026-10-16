"""Compatibility alias forwarding to src.core.risk_manager.

RiskBudget / DailyMetrics never existed in src.core.risk_manager, so the old import failed on load;
only the names that really exist are re-exported.
"""
from src.core.risk_manager import RiskManager, StopLevels

__all__ = ["RiskManager", "StopLevels"]
