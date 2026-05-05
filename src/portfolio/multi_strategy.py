"""
Multi-Strategy Portfolio Management.
"""

import copy
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)


class MultiStrategyPortfolio:
    """
    Manages a portfolio of named strategies with target allocation percentages.
    """

    def __init__(self, total_capital: float = 100_000.0):
        self.total_capital = total_capital
        self._strategies: Dict[str, Dict[str, Any]] = {}

    def add_strategy(self, name: str, allocation_pct: float, config: Optional[Dict] = None) -> None:
        """Add a strategy with a target allocation percentage (0-1)."""
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' already exists")
        if not 0.0 < allocation_pct <= 1.0:
            raise ValueError("allocation_pct must be between 0 and 1 (exclusive/inclusive)")

        total_alloc = sum(s["allocation_pct"] for s in self._strategies.values()) + allocation_pct
        if total_alloc > 1.0 + 1e-9:
            raise ValueError(f"Total allocation {total_alloc:.2%} would exceed 100%")

        self._strategies[name] = {
            "allocation_pct": allocation_pct,
            "value": allocation_pct * self.total_capital,
            "pnl": 0.0,
            "config": config or {},
        }

    def remove_strategy(self, name: str) -> None:
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")
        del self._strategies[name]

    def rebalance(self) -> Dict[str, float]:
        """Rebalance all strategies to their target allocations."""
        total_value = self._total_value()
        adjustments: Dict[str, float] = {}
        for name, strategy in self._strategies.items():
            target_value = strategy["allocation_pct"] * total_value
            delta = target_value - strategy["value"]
            strategy["value"] = target_value
            adjustments[name] = delta
        return adjustments

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        total_value = self._total_value()
        allocations: Dict[str, Any] = {}
        pnl_by_strategy: Dict[str, float] = {}
        for name, strategy in self._strategies.items():
            actual_pct = strategy["value"] / total_value if total_value > 0 else 0.0
            allocations[name] = {
                "target_pct": strategy["allocation_pct"],
                "actual_pct": actual_pct,
                "value": strategy["value"],
            }
            pnl_by_strategy[name] = strategy["pnl"]
        return {
            "total_value": total_value,
            "total_pnl": sum(s["pnl"] for s in self._strategies.values()),
            "strategy_count": len(self._strategies),
            "allocations": allocations,
            "pnl_by_strategy": pnl_by_strategy,
        }

    def clone_strategy(self, source_name: str, new_name: str) -> None:
        if source_name not in self._strategies:
            raise KeyError(f"Source strategy '{source_name}' not found")
        if new_name in self._strategies:
            raise ValueError(f"Strategy '{new_name}' already exists")
        source = self._strategies[source_name]
        self._strategies[new_name] = {
            "allocation_pct": source["allocation_pct"],
            "value": source["allocation_pct"] * self.total_capital,
            "pnl": 0.0,
            "config": copy.deepcopy(source["config"]),
        }

    def update_strategy_value(self, name: str, new_value: float) -> None:
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")
        strategy = self._strategies[name]
        initial_value = strategy["allocation_pct"] * self.total_capital
        strategy["value"] = new_value
        strategy["pnl"] = new_value - initial_value

    def _total_value(self) -> float:
        return sum(s["value"] for s in self._strategies.values())

    def __len__(self) -> int:
        return len(self._strategies)

    def __contains__(self, name: str) -> bool:
        return name in self._strategies
