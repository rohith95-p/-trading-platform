"""
ConsensusBuilder - aggregates agent votes via weighted majority.
Weight = confidence score per vote.
"""

from dataclasses import dataclass, field
from typing import List, Dict

from src.simulation.engine import AgentVote, ACTIONS


@dataclass
class ConsensusResult:
    action: str           # BUY | SELL | HOLD
    confidence: float     # 0.0 – 1.0 (weighted fraction of winning action)
    vote_breakdown: Dict[str, float] = field(default_factory=dict)


class ConsensusBuilder:
    """
    Builds consensus from a list of AgentVotes using weighted majority.

    Each vote contributes its confidence as weight to its chosen action.
    The winning action is the one with the highest total weight.
    Returned confidence = winning_weight / total_weight.
    """

    def build(self, votes: List[AgentVote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                action="HOLD",
                confidence=0.0,
                vote_breakdown={a: 0.0 for a in ACTIONS},
            )

        # Accumulate weighted votes
        weights: Dict[str, float] = {a: 0.0 for a in ACTIONS}
        for vote in votes:
            action = vote.action if vote.action in ACTIONS else "HOLD"
            weights[action] += vote.confidence

        total_weight = sum(weights.values())

        if total_weight == 0.0:
            return ConsensusResult(
                action="HOLD",
                confidence=0.0,
                vote_breakdown={a: 0.0 for a in ACTIONS},
            )

        # Winning action
        winning_action = max(weights, key=lambda a: weights[a])
        winning_confidence = round(weights[winning_action] / total_weight, 4)

        # Normalised breakdown
        breakdown = {a: round(weights[a] / total_weight, 4) for a in ACTIONS}

        return ConsensusResult(
            action=winning_action,
            confidence=winning_confidence,
            vote_breakdown=breakdown,
        )
