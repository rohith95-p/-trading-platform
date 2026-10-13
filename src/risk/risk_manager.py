"""Compatibility alias forwarding to src.core.risk_manager."""
from src.core.risk_manager import RiskManager, RiskBudget, DailyMetrics

__all__ = ["RiskManager", "RiskBudget", "DailyMetrics"]
