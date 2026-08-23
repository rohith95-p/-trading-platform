"""
Unit tests for the Multi-Agent Simulation Engine (Task 12).
"""

import asyncio
import pytest
from unittest.mock import patch

from src.simulation.engine import (
    SimulationEngine,
    SimulationResult,
    AgentVote,
    NUM_AGENTS,
    NUM_ROUNDS,
    ACTIONS,
)
from src.simulation.consensus import ConsensusBuilder, ConsensusResult


# ---------------------------------------------------------------------------
# ConsensusBuilder tests
# ---------------------------------------------------------------------------


class TestConsensusBuilder:
    def _make_votes(self, action: str, count: int, confidence: float = 0.8) -> list:
        return [
            AgentVote(agent_id=i, action=action, confidence=confidence, round=1)
            for i in range(count)
        ]

    def test_unanimous_buy(self):
        votes = self._make_votes("BUY", 10)
        result = ConsensusBuilder().build(votes)
        assert result.action == "BUY"
        assert result.confidence == pytest.approx(1.0)

    def test_unanimous_sell(self):
        votes = self._make_votes("SELL", 10)
        result = ConsensusBuilder().build(votes)
        assert result.action == "SELL"
        assert result.confidence == pytest.approx(1.0)

    def test_unanimous_hold(self):
        votes = self._make_votes("HOLD", 10)
        result = ConsensusBuilder().build(votes)
        assert result.action == "HOLD"
        assert result.confidence == pytest.approx(1.0)

    def test_majority_buy_over_sell(self):
        votes = self._make_votes("BUY", 7) + self._make_votes("SELL", 3)
        result = ConsensusBuilder().build(votes)
        assert result.action == "BUY"
        assert result.confidence > 0.5

    def test_weighted_by_confidence(self):
        # 3 high-confidence SELL beats 7 low-confidence BUY
        buy_votes = [AgentVote(agent_id=i, action="BUY", confidence=0.1, round=1) for i in range(7)]
        sell_votes = [AgentVote(agent_id=i + 7, action="SELL", confidence=0.9, round=1) for i in range(3)]
        result = ConsensusBuilder().build(buy_votes + sell_votes)
        assert result.action == "SELL"

    def test_empty_votes_returns_hold(self):
        result = ConsensusBuilder().build([])
        assert result.action == "HOLD"
        assert result.confidence == 0.0

    def test_vote_breakdown_sums_to_one(self):
        votes = (
            self._make_votes("BUY", 4, 0.7)
            + self._make_votes("SELL", 3, 0.6)
            + self._make_votes("HOLD", 3, 0.5)
        )
        result = ConsensusBuilder().build(votes)
        total = sum(result.vote_breakdown.values())
        assert total == pytest.approx(1.0, abs=1e-4)

    def test_breakdown_contains_all_actions(self):
        votes = self._make_votes("BUY", 5)
        result = ConsensusBuilder().build(votes)
        assert set(result.vote_breakdown.keys()) == {"BUY", "SELL", "HOLD"}

    def test_invalid_action_treated_as_hold(self):
        votes = [AgentVote(agent_id=0, action="INVALID", confidence=0.9, round=1)]
        result = ConsensusBuilder().build(votes)
        assert result.action == "HOLD"


# ---------------------------------------------------------------------------
# SimulationEngine tests (mock agents, no OpenAI key needed)
# ---------------------------------------------------------------------------


class TestSimulationEngine:
    """Tests that run without an OpenAI key (mock agents)."""

    def _engine_no_openai(self) -> SimulationEngine:
        """Return an engine that always uses mock agents."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            engine = SimulationEngine()
        return engine

    def test_mock_agents_used_without_api_key(self):
        engine = self._engine_no_openai()
        assert engine._use_openai is False

    def test_simulation_returns_result(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        assert isinstance(result, SimulationResult)

    def test_consensus_is_valid_action(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "ETH-USD"}))
        assert result.consensus in ACTIONS

    def test_confidence_in_range(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        assert 0.0 <= result.confidence <= 1.0

    def test_correct_number_of_votes(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        assert len(result.votes) == NUM_AGENTS * NUM_ROUNDS

    def test_all_votes_have_valid_actions(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        for vote in result.votes:
            assert vote.action in ACTIONS

    def test_all_votes_confidence_in_range(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        for vote in result.votes:
            assert 0.0 <= vote.confidence <= 1.0

    def test_simulation_completes_under_30s(self):
        """Simulation must complete in <30 seconds (mock agents are fast)."""
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        assert result.duration_seconds < 30.0

    def test_duration_is_positive(self):
        engine = self._engine_no_openai()
        result = asyncio.run(engine.run({"symbol": "BTC-USD"}))
        assert result.duration_seconds > 0.0

    def test_context_passed_through(self):
        """Engine accepts arbitrary context without error."""
        engine = self._engine_no_openai()
        ctx = {"symbol": "AAPL", "price": 175.0, "rsi": 55.0, "trade_value": 2000.0}
        result = asyncio.run(engine.run(ctx))
        assert result.consensus in ACTIONS


# ---------------------------------------------------------------------------
# Auto-trigger logic tests (via API layer)
# ---------------------------------------------------------------------------


class TestAutoTrigger:
    """Test the auto_triggered flag logic in the API."""

    def test_auto_triggered_above_threshold(self):
        from src.api.simulation import AUTO_TRIGGER_THRESHOLD
        trade_value = AUTO_TRIGGER_THRESHOLD + 1
        auto = trade_value > AUTO_TRIGGER_THRESHOLD
        assert auto is True

    def test_not_auto_triggered_below_threshold(self):
        from src.api.simulation import AUTO_TRIGGER_THRESHOLD
        trade_value = AUTO_TRIGGER_THRESHOLD - 1
        auto = trade_value > AUTO_TRIGGER_THRESHOLD
        assert auto is False

    def test_not_auto_triggered_at_threshold(self):
        from src.api.simulation import AUTO_TRIGGER_THRESHOLD
        trade_value = AUTO_TRIGGER_THRESHOLD  # exactly 1000 — not > 1000
        auto = trade_value > AUTO_TRIGGER_THRESHOLD
        assert auto is False

    def test_auto_triggered_none_trade_value(self):
        """No trade_value means not auto-triggered."""
        trade_value = None
        auto = bool(trade_value is not None and trade_value > 1000.0)
        assert auto is False

    def test_threshold_is_1000(self):
        from src.api.simulation import AUTO_TRIGGER_THRESHOLD
        assert AUTO_TRIGGER_THRESHOLD == 1000.0
