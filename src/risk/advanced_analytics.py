"""
Advanced Risk Analytics - VaR, CVaR, Beta, Correlation, Sortino.
"""

import math
import logging
from typing import Dict, List

log = logging.getLogger(__name__)


class AdvancedRiskAnalytics:
    """Computes advanced risk metrics for portfolio analysis."""

    def compute_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Historical Value at Risk at the given confidence level."""
        if len(returns) < 2:
            return 0.0
        sorted_returns = sorted(returns)
        index = max(0, min(int((1.0 - confidence) * len(sorted_returns)), len(sorted_returns) - 1))
        return -sorted_returns[index]

    def compute_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Conditional Value at Risk (Expected Shortfall)."""
        if len(returns) < 2:
            return 0.0
        sorted_returns = sorted(returns)
        cutoff_index = max(1, int((1.0 - confidence) * len(sorted_returns)))
        tail = sorted_returns[:cutoff_index]
        if not tail:
            return 0.0
        return -sum(tail) / len(tail)

    def compute_beta(self, returns: List[float], market_returns: List[float]) -> float:
        """Compute beta relative to a market benchmark."""
        n = min(len(returns), len(market_returns))
        if n < 2:
            return 0.0
        r, m = returns[:n], market_returns[:n]
        mean_r, mean_m = sum(r) / n, sum(m) / n
        cov = sum((r[i] - mean_r) * (m[i] - mean_m) for i in range(n)) / (n - 1)
        var_m = sum((m[i] - mean_m) ** 2 for i in range(n)) / (n - 1)
        return 0.0 if var_m == 0.0 else cov / var_m

    def compute_correlation_matrix(self, returns_dict: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """Compute pairwise Pearson correlation matrix."""
        names = list(returns_dict.keys())
        matrix: Dict[str, Dict[str, float]] = {name: {} for name in names}
        for i, name_a in enumerate(names):
            for j, name_b in enumerate(names):
                if i == j:
                    matrix[name_a][name_b] = 1.0
                elif name_b not in matrix[name_a]:
                    corr = self._pearson(returns_dict[name_a], returns_dict[name_b])
                    matrix[name_a][name_b] = corr
                    matrix[name_b][name_a] = corr
        return matrix

    def compute_sortino_ratio(self, returns: List[float], target_return: float = 0.0) -> float:
        """Compute the annualised Sortino ratio."""
        if len(returns) < 2:
            return 0.0
        n = len(returns)
        mean_r = sum(returns) / n
        excess = mean_r - target_return
        downside_sq = [(min(r - target_return, 0.0)) ** 2 for r in returns]
        downside_var = sum(downside_sq) / (n - 1)
        downside_std = math.sqrt(downside_var)
        return 0.0 if downside_std == 0.0 else (excess / downside_std) * math.sqrt(252)

    def _pearson(self, a: List[float], b: List[float]) -> float:
        n = min(len(a), len(b))
        if n < 2:
            return 0.0
        a, b = a[:n], b[:n]
        mean_a, mean_b = sum(a) / n, sum(b) / n
        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
        std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))
        denom = std_a * std_b
        return 0.0 if denom == 0.0 else cov / denom
