"""
Simulation API - POST /intelligence/simulate
Auto-triggers for trades > $1K.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.simulation.engine import SimulationEngine, AgentVote

log = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["simulation"])

# Singleton engine (reused across requests)
_engine: Optional[SimulationEngine] = None


def _get_engine() -> SimulationEngine:
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
    return _engine


AUTO_TRIGGER_THRESHOLD = 1000.0  # USD


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC-USD",
                "context": {"price": 45000, "rsi": 62.5},
                "trade_value": 1500.0,
            }
        }
    )

    symbol: str = Field(..., description="Trading symbol, e.g. BTC-USD")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional market context (price, indicators, etc.)"
    )
    trade_value: Optional[float] = Field(
        default=None, description="Trade value in USD; auto-triggers simulation when > $1K"
    )


class AgentVoteResponse(BaseModel):
    agent_id: int
    action: str
    confidence: float
    round: int
    reasoning: str


class SimulateResponse(BaseModel):
    consensus: str
    confidence: float
    votes: List[AgentVoteResponse]
    duration_seconds: float
    auto_triggered: bool


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/simulate", response_model=SimulateResponse)
async def run_simulation(request: SimulateRequest):
    """
    Run a multi-agent simulation for a trading decision.

    - **symbol**: Trading symbol to evaluate
    - **context**: Optional market context passed to each agent
    - **trade_value**: When > $1,000 the simulation is considered auto-triggered

    Returns consensus action (BUY/SELL/HOLD), confidence, all agent votes,
    wall-clock duration, and whether it was auto-triggered.
    """
    auto_triggered = bool(
        request.trade_value is not None and request.trade_value > AUTO_TRIGGER_THRESHOLD
    )

    # Build context dict for the engine
    sim_context: Dict[str, Any] = {"symbol": request.symbol}
    if request.context:
        sim_context.update(request.context)
    if request.trade_value is not None:
        sim_context["trade_value"] = request.trade_value

    try:
        engine = _get_engine()
        result = await engine.run(sim_context)
    except Exception as exc:
        log.error(f"Simulation failed for {request.symbol}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")

    vote_responses = [
        AgentVoteResponse(
            agent_id=v.agent_id,
            action=v.action,
            confidence=v.confidence,
            round=v.round,
            reasoning=v.reasoning,
        )
        for v in result.votes
    ]

    return SimulateResponse(
        consensus=result.consensus,
        confidence=result.confidence,
        votes=vote_responses,
        duration_seconds=result.duration_seconds,
        auto_triggered=auto_triggered,
    )
