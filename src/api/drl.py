"""
DRL API - POST /intelligence/drl/predict endpoint.

Implements Requirement 7 (PPO Reinforcement Learning Agent) - REST API.
"""

import logging
from typing import Dict, Any, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field

from src.drl.ppo_agent import PPOAgent
from src.drl.guardrails import ConstitutionalGuardrails, HOLD, BUY, SELL
from src.risk.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["drl"])

_ppo_agent = PPOAgent()
_circuit_breaker = CircuitBreaker()

ACTION_NAMES = {HOLD: "hold", BUY: "buy", SELL: "sell"}


def get_ppo_agent() -> PPOAgent:
    return _ppo_agent


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker


class DRLPredictRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": [1.0, 1.0, 1.01, 0.99, 0.55, 0.002, 0.0018, 0.01, 1.02, 0.98],
                "context": {"circuit_breaker_triggered": False, "current_leverage": 1.0},
            }
        }
    )

    state: List[float] = Field(
        ...,
        description="Market state feature vector (10 floats: price, volume, indicators)",
        min_length=1,
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional runtime context (circuit_breaker_triggered, current_leverage, …)",
    )


class DRLPredictResponse(BaseModel):
    action: int = Field(..., description="Predicted action: 0=hold, 1=buy, 2=sell")
    action_name: str = Field(..., description="Human-readable action name")
    confidence: float = Field(..., description="Confidence score [0, 1]")
    guardrail_applied: bool = Field(
        ..., description="True if a constitutional guardrail overrode the raw prediction"
    )


@router.post(
    "/drl/predict",
    response_model=DRLPredictResponse,
    summary="Get DRL agent trading prediction",
)
async def drl_predict(
    request: DRLPredictRequest,
    agent: PPOAgent = Depends(get_ppo_agent),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> DRLPredictResponse:
    """
    Get a trading action prediction from the PPO agent.

    The agent applies constitutional guardrails before returning the action:
    - HOLD is forced when the circuit breaker is triggered.
    - BUY is blocked when leverage exceeds the configured limit.
    """
    try:
        state = np.array(request.state, dtype=np.float32)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid state vector: {exc}")

    ctx: Dict[str, Any] = dict(request.context or {})
    ctx.setdefault("circuit_breaker_triggered", circuit_breaker.is_triggered())

    overrides_before = agent.guardrails.override_count

    try:
        action = agent.predict_with_context(state, context=ctx)
    except Exception as exc:
        log.error("DRL prediction failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    guardrail_applied = agent.guardrails.override_count > overrides_before
    confidence = 0.75 if agent.is_trained() else 0.5

    return DRLPredictResponse(
        action=action,
        action_name=ACTION_NAMES.get(action, "unknown"),
        confidence=confidence,
        guardrail_applied=guardrail_applied,
    )
