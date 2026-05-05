"""
Multi-Agent Simulation Engine
10 agents, 5 rounds, <30s execution via asyncio.gather
Uses OpenAI gpt-4o-mini if OPENAI_API_KEY is set, otherwise mock agents.
"""

import asyncio
import os
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)

ACTIONS = ["BUY", "SELL", "HOLD"]

NUM_AGENTS = 10
NUM_ROUNDS = 5


@dataclass
class AgentVote:
    agent_id: int
    action: str          # BUY | SELL | HOLD
    confidence: float    # 0.0 – 1.0
    round: int
    reasoning: str = ""


@dataclass
class SimulationResult:
    consensus: str           # BUY | SELL | HOLD
    confidence: float        # 0.0 – 1.0
    votes: List[AgentVote] = field(default_factory=list)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Agent personas for richer mock / prompt diversity
# ---------------------------------------------------------------------------

_AGENT_PERSONAS = [
    "momentum trader",
    "value investor",
    "technical analyst",
    "macro economist",
    "sentiment analyst",
    "risk manager",
    "quantitative analyst",
    "contrarian investor",
    "fundamental analyst",
    "algorithmic trader",
]


# ---------------------------------------------------------------------------
# Mock agent (no API key required)
# ---------------------------------------------------------------------------

async def _mock_agent_vote(agent_id: int, context: Dict[str, Any], round_num: int) -> AgentVote:
    """Deterministic-ish mock vote based on context hash + agent_id."""
    # Simulate a tiny async delay (realistic without being slow)
    await asyncio.sleep(random.uniform(0.01, 0.05))

    seed = hash(str(context)) ^ (agent_id * 31) ^ (round_num * 7)
    rng = random.Random(seed)

    action = rng.choice(ACTIONS)
    confidence = round(rng.uniform(0.4, 0.95), 3)
    persona = _AGENT_PERSONAS[agent_id % len(_AGENT_PERSONAS)]

    return AgentVote(
        agent_id=agent_id,
        action=action,
        confidence=confidence,
        round=round_num,
        reasoning=f"Mock {persona} analysis",
    )


# ---------------------------------------------------------------------------
# OpenAI agent
# ---------------------------------------------------------------------------

async def _openai_agent_vote(
    agent_id: int,
    context: Dict[str, Any],
    round_num: int,
    client,
) -> AgentVote:
    """Call OpenAI gpt-4o-mini to get a trading vote."""
    persona = _AGENT_PERSONAS[agent_id % len(_AGENT_PERSONAS)]
    symbol = context.get("symbol", "UNKNOWN")

    prompt = (
        f"You are a {persona} evaluating a trade for {symbol}.\n"
        f"Context: {context}\n"
        f"Round: {round_num}/{NUM_ROUNDS}\n"
        "Respond with exactly one JSON object: "
        '{"action": "BUY"|"SELL"|"HOLD", "confidence": 0.0-1.0, "reasoning": "brief reason"}'
    )

    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=80,
                    temperature=0.7,
                ),
            ),
            timeout=20.0,
        )

        import json
        text = response.choices[0].message.content.strip()
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        action = data.get("action", "HOLD").upper()
        if action not in ACTIONS:
            action = "HOLD"
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        reasoning = str(data.get("reasoning", ""))

        return AgentVote(
            agent_id=agent_id,
            action=action,
            confidence=confidence,
            round=round_num,
            reasoning=reasoning,
        )

    except Exception as exc:
        log.warning(f"OpenAI agent {agent_id} round {round_num} failed: {exc}. Using mock fallback.")
        return await _mock_agent_vote(agent_id, context, round_num)


# ---------------------------------------------------------------------------
# SimulationEngine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Runs a multi-agent simulation with NUM_AGENTS agents over NUM_ROUNDS rounds.
    All agents in a round run in parallel via asyncio.gather.
    Total execution target: <30 seconds.
    """

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        self._use_openai = bool(api_key)
        self._client = None

        if self._use_openai:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key)
                log.info("SimulationEngine: using OpenAI gpt-4o-mini")
            except ImportError:
                log.warning("openai package not installed; falling back to mock agents")
                self._use_openai = False

        if not self._use_openai:
            log.info("SimulationEngine: using mock agents (no OPENAI_API_KEY)")

    async def _run_round(
        self, round_num: int, context: Dict[str, Any]
    ) -> List[AgentVote]:
        """Run all agents in parallel for a single round."""
        if self._use_openai and self._client:
            tasks = [
                _openai_agent_vote(agent_id, context, round_num, self._client)
                for agent_id in range(NUM_AGENTS)
            ]
        else:
            tasks = [
                _mock_agent_vote(agent_id, context, round_num)
                for agent_id in range(NUM_AGENTS)
            ]

        return await asyncio.gather(*tasks)

    async def run(self, context: Dict[str, Any]) -> SimulationResult:
        """
        Run the full simulation.

        Args:
            context: Dict with at minimum {"symbol": str}. May include
                     price, volume, indicators, news_sentiment, etc.

        Returns:
            SimulationResult with consensus action, confidence, all votes,
            and wall-clock duration.
        """
        start = time.monotonic()

        all_votes: List[AgentVote] = []

        # Run rounds sequentially (each round is internally parallel)
        for round_num in range(1, NUM_ROUNDS + 1):
            round_votes = await self._run_round(round_num, context)
            all_votes.extend(round_votes)

        from src.simulation.consensus import ConsensusBuilder
        builder = ConsensusBuilder()
        result = builder.build(all_votes)

        duration = time.monotonic() - start
        log.info(
            f"Simulation complete: {result.action} @ {result.confidence:.2f} "
            f"in {duration:.2f}s ({len(all_votes)} votes)"
        )

        return SimulationResult(
            consensus=result.action,
            confidence=result.confidence,
            votes=all_votes,
            duration_seconds=round(duration, 3),
        )
