"""
Constitutional Guardrails for DRL agents.

Enforces hard safety rules that override agent actions when necessary.
Implements Requirement 7 (PPO Reinforcement Learning Agent) - constitutional guardrails.
"""

import logging
from typing import Dict, Any

import numpy as np

log = logging.getLogger(__name__)

HOLD = 0
BUY = 1
SELL = 2

ACTION_NAMES = {HOLD: "hold", BUY: "buy", SELL: "sell"}


class ConstitutionalGuardrails:
    """
    Hard safety rules that can override DRL agent actions.

    Rules enforced:
    - Never exceed leverage limits
    - Never trade when circuit breaker is triggered
    """

    def __init__(self, max_leverage: float = 10.0):
        self.max_leverage = max_leverage
        self._override_count = 0

    def check(self, action: int, state: np.ndarray, context: Dict[str, Any]) -> int:
        """
        Validate an action against constitutional rules.

        Args:
            action: Proposed action (0=hold, 1=buy, 2=sell).
            state: Current market state array.
            context: Runtime context dict. Recognised keys:
                - ``circuit_breaker_triggered`` (bool): halt trading flag.
                - ``current_leverage`` (float): current portfolio leverage.

        Returns:
            Possibly overridden action (0=hold if a rule fires).
        """
        # Rule 1: circuit breaker
        if context.get("circuit_breaker_triggered", False):
            if action != HOLD:
                return self.override_action(action, "circuit breaker is triggered")

        # Rule 2: leverage limit
        current_leverage = context.get("current_leverage", 0.0)
        if current_leverage > self.max_leverage and action == BUY:
            return self.override_action(
                action,
                f"leverage {current_leverage:.1f}x exceeds limit {self.max_leverage:.1f}x",
            )

        return action

    def override_action(self, action: int, reason: str) -> int:
        """Log the override and return HOLD."""
        self._override_count += 1
        log.warning(
            "Guardrail override #%d: action=%s (%d) -> HOLD. Reason: %s",
            self._override_count,
            ACTION_NAMES.get(action, "unknown"),
            action,
            reason,
        )
        return HOLD

    @property
    def override_count(self) -> int:
        """Total number of overrides applied since instantiation."""
        return self._override_count
