"""Legacy intelligence endpoints kept for backward compatibility tests.

These routes expose the older `/intelligence/*` contract while delegating
computation to the newer indicator/classifier services.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import src.api.intelligence as intelligence_api
from src.core.time import utc_now
from src.intelligence.indicator_registry import IndicatorRegistry
from src.intelligence.indicator_cache_service import get_cache_service

router = APIRouter(prefix="/intelligence", tags=["intelligence-legacy"])


class LegacyNewsArticle(BaseModel):
    title: str = Field(..., min_length=1)
    content: str
    source: str
    url: Optional[str] = None


class LegacyClassifyNewsRequest(BaseModel):
    article: LegacyNewsArticle
    market_question: str = Field(..., min_length=1)
    yes_price: Optional[float] = None


class LegacyIndicatorRequest(BaseModel):
    symbol: str
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|1h|4h|1d)$")
    indicators: List[str] = Field(..., min_length=1)
    highs: List[float] = Field(..., min_length=1)
    lows: List[float] = Field(..., min_length=1)
    closes: List[float] = Field(..., min_length=1)
    volumes: Optional[List[float]] = None


class LegacyBatchIndicatorRequest(BaseModel):
    requests: List[LegacyIndicatorRequest] = Field(..., min_length=1)


def _to_legacy_indicator_name(name: str) -> str:
    return name.strip().upper()


def _extract_latest(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        valid_values = value[~np.isnan(value)]
        return float(valid_values[-1]) if len(valid_values) else None
    if isinstance(value, dict):
        reduced: Dict[str, Any] = {}
        for key, item in value.items():
            reduced[key] = _extract_latest(item)
        return reduced
    if isinstance(value, (float, int, np.floating, np.integer)):
        return float(value)
    return value


def _compute_legacy_indicators(payload: LegacyIndicatorRequest) -> Dict[str, Any]:
    if not (
        len(payload.highs) == len(payload.lows) == len(payload.closes)
        and (payload.volumes is None or len(payload.volumes) == len(payload.closes))
    ):
        raise HTTPException(status_code=422, detail="OHLCV arrays must have matching lengths")

    if any(high < low for high, low in zip(payload.highs, payload.lows)):
        raise HTTPException(status_code=400, detail="Invalid OHLCV data: high must be >= low")

    highs = np.array(payload.highs, dtype=float)
    lows = np.array(payload.lows, dtype=float)
    closes = np.array(payload.closes, dtype=float)
    volumes = np.array(payload.volumes, dtype=float) if payload.volumes else None

    registry = IndicatorRegistry()
    available = set(registry.get_available_indicators())

    indicator_rows: List[Dict[str, Any]] = []
    for indicator in payload.indicators:
        normalized = _to_legacy_indicator_name(indicator)
        if normalized not in available:
            continue
        computed = registry.compute(normalized, highs, lows, closes, volumes)
        latest = _extract_latest(computed)
        if latest is None and normalized.startswith("EMA_") and len(closes) > 0:
            # Legacy callers expect a value even for short windows.
            latest = float(closes[-1])
        indicator_rows.append(
            {
                "name": indicator.lower(),
                "latest": latest,
            }
        )

    return {
        "symbol": payload.symbol,
        "timeframe": payload.timeframe,
        "indicators": indicator_rows,
    }


@router.post("/classify-news")
async def classify_news_legacy(
    payload: LegacyClassifyNewsRequest,
    user_id: Optional[str] = Query(None),
):
    classifier = intelligence_api.get_classifier()
    article = payload.article.model_dump()
    if user_id:
        article["user_id"] = user_id

    if hasattr(classifier, "classify_async"):
        result = await classifier.classify_async(
            article=article,
            market_question=payload.market_question,
            yes_price=payload.yes_price,
        )
    elif hasattr(classifier, "classify"):
        result = await classifier.classify(article)
    else:
        raise HTTPException(status_code=500, detail="Classifier does not support async classification")

    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    if isinstance(result, dict):
        return result
    return {"result": result}


@router.post("/indicators")
async def indicators_legacy(
    payload: LegacyIndicatorRequest,
    user_id: Optional[str] = Query(None),
):
    _ = user_id
    started = time.perf_counter()
    result = _compute_legacy_indicators(payload)
            result["computed_at"] = utc_now().isoformat()
    result["latency_ms"] = max(0.0, (time.perf_counter() - started) * 1000)
    return result


@router.post("/indicators/batch")
async def indicators_batch_legacy(
    payload: LegacyBatchIndicatorRequest,
    user_id: Optional[str] = Query(None),
):
    _ = user_id
    started = time.perf_counter()
    results: List[Dict[str, Any]] = []
    for request in payload.requests:
        computed = _compute_legacy_indicators(request)
            computed["computed_at"] = utc_now().isoformat()
        computed["latency_ms"] = 0.0
        results.append(computed)
    return {
        "results": results,
        "total_latency_ms": max(0.0, (time.perf_counter() - started) * 1000),
    }


@router.get("/health")
async def health_legacy():
    return {"status": "healthy", "service": "intelligence-layer"}


@router.get("/stats")
async def stats_legacy():
    cache = get_cache_service()
    cache_stats = await cache.get_stats()
    return {
        "classifier": {"status": "ready"},
        "rate_limiter": {"status": "active"},
        "cache": cache_stats,
    }
