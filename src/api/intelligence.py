"""Intelligence layer routes"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from src.database import get_db
from src.models import (
    IndicatorRequest,
    IndicatorResponse,
    IndicatorComputeRequest,
    IndicatorComputeResponse,
    BatchIndicatorRequest,
    BatchIndicatorResponse,
)
from src.intelligence.indicators import TechnicalIndicators
from src.intelligence.indicator_registry import IndicatorRegistry
from src.intelligence.indicator_cache_service import get_cache_service
from src.intelligence.indicator_websocket_service import (
    get_ws_manager,
    IndicatorSubscription,
)
from src.intelligence.news.models import (
    NewsArticleResponse,
    NewsArticleList,
    NewsIngestionStats,
)
from src.intelligence.news.news_stream import NewsStreamService
from src.intelligence.news_classifier import NewsClassifier
from src.data.models import NewsArticle as NewsArticleDB, Signal as SignalDB
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import numpy as np
import time
import uuid

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections for real-time news feed."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        log.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

# Global connection manager
ws_manager = ConnectionManager()

@router.post("/indicators", response_model=IndicatorResponse)
async def compute_indicators(request: IndicatorRequest, db: Session = Depends(get_db)):
    """Compute technical indicators"""
    # Placeholder - in production would fetch real data
    prices = [100.0 + i for i in range(100)]
    
    indicators = {}
    if "EMA_20" in request.indicators:
        indicators["EMA_20"] = TechnicalIndicators.ema(prices, 20)[-1]
    if "RSI_14" in request.indicators:
        indicators["RSI_14"] = TechnicalIndicators.rsi(prices, 14)
    if "MACD" in request.indicators:
        indicators["MACD"] = TechnicalIndicators.macd(prices)
    
    return IndicatorResponse(
        symbol=request.symbol,
        timeframe=request.timeframe,
        indicators=indicators,
        computed_at=datetime.utcnow()
    )


# ============================================================================
# TECHNICAL ANALYSIS API (Task 2.6)
# ============================================================================

@router.post("/indicators/compute", response_model=IndicatorComputeResponse)
@limiter.limit("100/hour")
async def compute_indicators_enhanced(
    request_obj: Request,
    request: IndicatorComputeRequest,
    db: Session = Depends(get_db)
):
    """
    Compute technical indicators with caching and validation.
    
    **Features:**
    - Supports 20+ technical indicators
    - Multi-timeframe support (1m, 5m, 15m, 1h, 4h, 1d)
    - Response caching with timeframe-appropriate TTLs
    - Rate limiting: 100 calls/hour per user
    - Target latency: <100ms
    
    **Supported Indicators:**
    - Phase 1: EMA_20, EMA_50, EMA_200, RSI_14, MACD, ATR_14, BBANDS_20, ADX_14, OBV, VWAP
    - Phase 1.5: STOCHASTIC, CCI_20, WILLR_14, ICHIMOKU, AROON, KELTNER, MFI_14, ROC_12, AD, CMF_20
    
    **Timeframes:**
    - 1m, 5m, 15m, 1h, 4h, 1d
    
    **Example Request:**
    ```json
    {
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": ["EMA_20", "RSI_14", "MACD"],
        "market_data": {
            "highs": [100.5, 101.2, 102.0],
            "lows": [99.5, 100.0, 101.0],
            "closes": [100.0, 101.0, 101.5],
            "volumes": [1000, 1200, 1100]
        }
    }
    ```
    
    **Example Response:**
    ```json
    {
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": {
            "EMA_20": 101.2,
            "RSI_14": 65.3,
            "MACD": {
                "macd": 0.5,
                "signal": 0.3,
                "histogram": 0.2
            }
        },
        "computed_at": "2024-01-15T12:00:00Z",
        "latency_ms": 45.2,
        "cached": false
    }
    ```
    """
    start_time = time.time()
    
    try:
        # Validate timeframe
        valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        if request.timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        # Validate market data lengths
        data_lengths = [
            len(request.market_data.highs),
            len(request.market_data.lows),
            len(request.market_data.closes),
        ]
        
        if request.market_data.volumes:
            data_lengths.append(len(request.market_data.volumes))
        
        if len(set(data_lengths)) > 1:
            raise HTTPException(
                status_code=400,
                detail="All market data arrays must have the same length"
            )
        
        if data_lengths[0] < 2:
            raise HTTPException(
                status_code=400,
                detail="Market data must contain at least 2 data points"
            )
        
        # Convert to numpy arrays
        highs = np.array(request.market_data.highs, dtype=float)
        lows = np.array(request.market_data.lows, dtype=float)
        closes = np.array(request.market_data.closes, dtype=float)
        volumes = np.array(request.market_data.volumes, dtype=float) if request.market_data.volumes else None
        
        # Check cache
        cache_service = get_cache_service()
        cached_result = await cache_service.get(
            symbol=request.symbol,
            timeframe=request.timeframe,
            indicators=request.indicators,
            highs=request.market_data.highs,
            lows=request.market_data.lows,
            closes=request.market_data.closes,
            volumes=request.market_data.volumes,
        )
        
        if cached_result:
            latency_ms = (time.time() - start_time) * 1000
            log.info(f"Cache hit for {request.symbol} {request.timeframe} - {latency_ms:.2f}ms")
            return IndicatorComputeResponse(
                symbol=request.symbol,
                timeframe=request.timeframe,
                indicators=cached_result,
                computed_at=datetime.utcnow(),
                latency_ms=latency_ms,
                cached=True,
            )
        
        # Initialize indicator registry
        registry = IndicatorRegistry()
        
        # Validate indicators
        available_indicators = registry.get_available_indicators()
        invalid_indicators = [ind for ind in request.indicators if ind not in available_indicators]
        
        if invalid_indicators:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid indicators: {', '.join(invalid_indicators)}. "
                       f"Available: {', '.join(available_indicators)}"
            )
        
        # Compute indicators
        results = {}
        for indicator_name in request.indicators:
            try:
                result = registry.compute(
                    indicator_name=indicator_name,
                    highs=highs,
                    lows=lows,
                    closes=closes,
                    volumes=volumes,
                )
                
                # Convert numpy arrays to lists for JSON serialization
                if isinstance(result, np.ndarray):
                    # Get latest non-NaN value
                    valid_values = result[~np.isnan(result)]
                    results[indicator_name] = float(valid_values[-1]) if len(valid_values) > 0 else None
                elif isinstance(result, dict):
                    # Handle dict results (e.g., MACD, Bollinger Bands)
                    results[indicator_name] = {}
                    for key, value in result.items():
                        if isinstance(value, np.ndarray):
                            valid_values = value[~np.isnan(value)]
                            results[indicator_name][key] = float(valid_values[-1]) if len(valid_values) > 0 else None
                        else:
                            results[indicator_name][key] = float(value) if value is not None else None
                else:
                    results[indicator_name] = float(result) if result is not None else None
            
            except Exception as e:
                log.error(f"Error computing {indicator_name}: {e}")
                results[indicator_name] = {"error": str(e)}
        
        # Cache results
        await cache_service.set(
            symbol=request.symbol,
            timeframe=request.timeframe,
            indicators=request.indicators,
            highs=request.market_data.highs,
            lows=request.market_data.lows,
            closes=request.market_data.closes,
            volumes=request.market_data.volumes,
            data=results,
        )
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        log.info(f"Computed {len(request.indicators)} indicators for {request.symbol} {request.timeframe} in {latency_ms:.2f}ms")
        
        return IndicatorComputeResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            indicators=results,
            computed_at=datetime.utcnow(),
            latency_ms=latency_ms,
            cached=False,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error computing indicators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Indicator computation failed: {str(e)}")


@router.post("/indicators/compute/batch", response_model=BatchIndicatorResponse)
@limiter.limit("50/hour")
async def compute_indicators_batch(
    request_obj: Request,
    request: BatchIndicatorRequest,
    db: Session = Depends(get_db)
):
    """
    Compute indicators for multiple symbols/timeframes in batch.
    
    **Features:**
    - Batch processing for efficiency
    - Parallel computation
    - Rate limiting: 50 calls/hour per user
    - Shared caching across requests
    
    **Example Request:**
    ```json
    {
        "requests": [
            {
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"],
                "market_data": {
                    "highs": [100.5, 101.2],
                    "lows": [99.5, 100.0],
                    "closes": [100.0, 101.0],
                    "volumes": [1000, 1200]
                }
            },
            {
                "symbol": "ETH-USD",
                "timeframe": "1h",
                "indicators": ["MACD", "BBANDS_20"],
                "market_data": {
                    "highs": [2000.5, 2010.2],
                    "lows": [1995.5, 2000.0],
                    "closes": [2000.0, 2005.0],
                    "volumes": [5000, 5200]
                }
            }
        ]
    }
    ```
    """
    start_time = time.time()
    
    try:
        if len(request.requests) > 10:
            raise HTTPException(
                status_code=400,
                detail="Batch size limited to 10 requests"
            )
        
        results = []
        
        # Process each request
        for req in request.requests:
            try:
                # Create a mock Request object for rate limiting
                mock_request = type('Request', (), {'client': request_obj.client})()
                
                # Compute indicators (reuse single endpoint logic)
                result = await compute_indicators_enhanced(mock_request, req, db)
                results.append(result)
            
            except Exception as e:
                log.error(f"Error in batch request for {req.symbol}: {e}")
                # Add error result
                results.append(
                    IndicatorComputeResponse(
                        symbol=req.symbol,
                        timeframe=req.timeframe,
                        indicators={"error": str(e)},
                        computed_at=datetime.utcnow(),
                        latency_ms=0,
                        cached=False,
                    )
                )
        
        total_latency_ms = (time.time() - start_time) * 1000
        
        return BatchIndicatorResponse(
            results=results,
            total=len(results),
            total_latency_ms=total_latency_ms,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error in batch computation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch computation failed: {str(e)}")


@router.get("/indicators/available")
async def list_available_indicators():
    """
    List all available technical indicators.
    
    Returns a list of indicator names and their descriptions.
    """
    registry = IndicatorRegistry()
    available = registry.get_available_indicators()
    
    # Add descriptions
    descriptions = {
        "EMA_20": "Exponential Moving Average (20 period)",
        "EMA_50": "Exponential Moving Average (50 period)",
        "EMA_200": "Exponential Moving Average (200 period)",
        "RSI_14": "Relative Strength Index (14 period)",
        "MACD": "Moving Average Convergence Divergence",
        "ATR_14": "Average True Range (14 period)",
        "BBANDS_20": "Bollinger Bands (20 period, 2 std dev)",
        "ADX_14": "Average Directional Index (14 period)",
        "OBV": "On Balance Volume",
        "VWAP": "Volume Weighted Average Price",
        "STOCHASTIC": "Stochastic Oscillator (14, 3, 3)",
        "CCI_20": "Commodity Channel Index (20 period)",
        "WILLR_14": "Williams %R (14 period)",
        "ICHIMOKU": "Ichimoku Cloud (9, 26, 52)",
        "AROON": "Aroon Indicator (25 period)",
        "KELTNER": "Keltner Channels (20 period, 2x ATR)",
        "MFI_14": "Money Flow Index (14 period)",
        "ROC_12": "Rate of Change (12 period)",
        "AD": "Accumulation/Distribution Line",
        "CMF_20": "Chaikin Money Flow (20 period)",
    }
    
    return {
        "indicators": [
            {
                "name": name,
                "description": descriptions.get(name, "No description available")
            }
            for name in available
        ],
        "total": len(available),
    }


@router.get("/indicators/cache/stats")
async def get_cache_stats():
    """
    Get indicator cache statistics.
    
    Returns cache hit rate, size, and other metrics.
    """
    cache_service = get_cache_service()
    return await cache_service.get_stats()


@router.post("/indicators/cache/clear")
async def clear_cache():
    """
    Clear indicator cache.
    
    Useful for testing or when data needs to be refreshed.
    """
    cache_service = get_cache_service()
    await cache_service.clear()
    return {"status": "success", "message": "Cache cleared"}


@router.post("/indicators/cache/cleanup")
async def cleanup_cache():
    """
    Remove expired entries from cache.
    
    Returns number of entries removed.
    """
    cache_service = get_cache_service()
    removed = await cache_service.cleanup_expired()
    return {
        "status": "success",
        "removed": removed,
        "message": f"Removed {removed} expired entries"
    }


@router.post("/indicators/cache/invalidate")
async def invalidate_cache(pattern: str):
    """
    Invalidate cache entries matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "indicator:BTC-USD:*")
    
    Returns number of keys invalidated.
    """
    cache_service = get_cache_service()
    removed = await cache_service.invalidate(pattern)
    return {
        "status": "success",
        "removed": removed,
        "message": f"Invalidated {removed} cache entries matching {pattern}"
    }


@router.post("/indicators/cache/warm")
async def warm_cache():
    """
    Warm cache with frequently accessed indicators.
    
    Pre-computes and caches common indicator combinations.
    """
    cache_service = get_cache_service()
    result = await cache_service.warm_cache()
    return {
        "status": "success",
        "warmed": result["warmed"],
        "errors": result["errors"],
        "message": f"Warmed {result['warmed']} cache entries"
    }


# ============================================================================
# NEWS CLASSIFICATION ENDPOINTS
# ============================================================================

@router.post("/classify-news")
async def classify_news(
    article: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Classify a news article using Claude API.
    
    - **article**: Dictionary with title, content, source, url
    
    Returns classification with sentiment, confidence, rationale, and trading signals.
    
    Example request:
    ```json
    {
        "title": "Bitcoin Reaches New All-Time High",
        "content": "Bitcoin has surged to a new all-time high...",
        "source": "rss",
        "url": "https://example.com/article"
    }
    ```
    
    Example response:
    ```json
    {
        "sentiment": "bullish",
        "confidence": 0.85,
        "rationale": "Strong positive momentum in crypto markets",
        "relevant_assets": ["BTC", "ETH"],
        "key_topics": ["price", "adoption"],
        "signals": [
            {
                "asset": "BTC",
                "direction": "long",
                "confidence": 0.85,
                "rationale": "Strong positive momentum"
            }
        ],
        "classified_at": "2024-01-15T12:00:00Z",
        "latency_ms": 1234
    }
    ```
    """
    try:
        # Initialize classifier
        classifier = NewsClassifier()
        
        # Classify article
        result = await classifier.classify(article)
        
        # Store signals in database if user_id is provided
        if "user_id" in article and result.get("signals"):
            for signal_data in result["signals"]:
                signal = SignalDB(
                    user_id=article["user_id"],
                    source="news_classification",
                    asset=signal_data["asset"],
                    direction=signal_data["direction"],
                    confidence=signal_data["confidence"],
                    rationale=signal_data["rationale"],
                    indicators={"article_url": article.get("url", "")},
                    timestamp=datetime.utcnow(),
                )
                db.add(signal)
            
            db.commit()
            log.info(f"Stored {len(result['signals'])} signals in database")
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast({
            "type": "classification",
            "data": {
                "article": {
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                },
                "classification": result,
            }
        })
        
        # Close classifier connections
        await classifier.close()
        
        return result
    
    except Exception as e:
        log.error(f"Error classifying news: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/classify-news/batch")
async def classify_news_batch(
    articles: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """
    Classify multiple news articles in batch.
    
    - **articles**: List of article dictionaries
    
    Returns list of classification results.
    
    This endpoint is more efficient than calling /classify-news multiple times
    as it processes articles concurrently.
    """
    try:
        # Initialize classifier
        classifier = NewsClassifier()
        
        # Classify articles in batch
        results = await classifier.classify_batch(articles)
        
        # Store signals in database
        total_signals = 0
        for i, result in enumerate(results):
            article = articles[i]
            if "user_id" in article and result.get("signals"):
                for signal_data in result["signals"]:
                    signal = SignalDB(
                        user_id=article["user_id"],
                        source="news_classification",
                        asset=signal_data["asset"],
                        direction=signal_data["direction"],
                        confidence=signal_data["confidence"],
                        rationale=signal_data["rationale"],
                        indicators={"article_url": article.get("url", "")},
                        timestamp=datetime.utcnow(),
                    )
                    db.add(signal)
                    total_signals += 1
        
        if total_signals > 0:
            db.commit()
            log.info(f"Stored {total_signals} signals from batch classification")
        
        # Close classifier connections
        await classifier.close()
        
        return {
            "results": results,
            "total": len(results),
            "signals_generated": total_signals,
        }
    
    except Exception as e:
        log.error(f"Error in batch classification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch classification failed: {str(e)}")


@router.websocket("/ws/news-feed")
async def news_feed_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time news feed.
    
    Clients can connect to this endpoint to receive real-time updates when:
    - New articles are ingested
    - Articles are classified
    - Trading signals are generated
    
    Message format:
    ```json
    {
        "type": "classification" | "ingestion" | "signal",
        "data": { ... }
    }
    ```
    """
    await ws_manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to news feed",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (e.g., ping/pong)
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                log.error(f"WebSocket error: {e}")
                break
    
    finally:
        ws_manager.disconnect(websocket)


@router.post("/simulate")
async def simulate(data: dict, db: Session = Depends(get_db)):
    """Run multi-agent simulation"""
    return {
        "confidence": 0.65,
        "consensus": "bullish",
        "dissent": "bearish",
        "reasoning": "Placeholder simulation"
    }


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================

@router.get("/classification/metrics")
async def get_classification_metrics():
    """
    Get classification metrics.
    
    Returns metrics including:
    - Total classifications
    - Classifications per minute
    - Average latency
    - Error rate
    - Cache hit rate
    - Sentiment distribution
    """
    from src.intelligence.classification_monitor import get_metrics
    return get_metrics()


@router.get("/classification/health")
async def get_classification_health():
    """
    Get classification health status.
    
    Returns health status with warnings and metrics.
    """
    from src.intelligence.classification_monitor import get_health_status
    return get_health_status()


# ============================================================================
# NEWS ENDPOINTS
# ============================================================================

@router.get("/news", response_model=NewsArticleList)
async def list_news_articles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(None, description="Filter by source (rss, twitter, telegram)"),
    db: Session = Depends(get_db)
):
    """
    List recent news articles with pagination.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of articles per page (max 100)
    - **source**: Optional filter by source type
    """
    try:
        # Build query
        query = select(NewsArticleDB)
        
        if source:
            query = query.where(NewsArticleDB.source == source)
        
        # Get total count
        total_query = select(func.count(NewsArticleDB.id))
        if source:
            total_query = total_query.where(NewsArticleDB.source == source)
        total = db.execute(total_query).scalar() or 0
        
        # Get paginated results
        query = query.order_by(desc(NewsArticleDB.published_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        articles = db.execute(query).scalars().all()
        
        # Convert to response models
        article_responses = [
            NewsArticleResponse(
                id=str(article.id),
                source=article.source,
                title=article.title,
                content=article.content,
                url=article.url,
                author=article.author,
                published_at=article.published_at,
                created_at=article.created_at,
            )
            for article in articles
        ]
        
        return NewsArticleList(
            articles=article_responses,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news articles: {str(e)}")


@router.get("/news/{article_id}", response_model=NewsArticleResponse)
async def get_news_article(article_id: str, db: Session = Depends(get_db)):
    """
    Get a specific news article by ID.
    
    - **article_id**: UUID of the news article
    """
    try:
        article = db.execute(
            select(NewsArticleDB).where(NewsArticleDB.id == article_id)
        ).scalar_one_or_none()
        
        if not article:
            raise HTTPException(status_code=404, detail="News article not found")
        
        return NewsArticleResponse(
            id=str(article.id),
            source=article.source,
            title=article.title,
            content=article.content,
            url=article.url,
            author=article.author,
            published_at=article.published_at,
            created_at=article.created_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news article: {str(e)}")


@router.post("/news/ingest")
async def trigger_news_ingestion(db: Session = Depends(get_db)):
    """
    Manually trigger news ingestion from all sources.
    
    This endpoint is typically used for testing or manual ingestion.
    In production, ingestion runs on a schedule.
    """
    try:
        service = NewsStreamService(db)
        results = await service.run_ingestion_cycle()
        
        return {
            "status": "success",
            "message": f"Ingested {results['total']} articles",
            "details": results,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during ingestion: {str(e)}")


@router.get("/news/stats", response_model=NewsIngestionStats)
async def get_news_stats(db: Session = Depends(get_db)):
    """
    Get news ingestion statistics.
    
    Returns statistics about total articles, articles by source, and recent activity.
    """
    try:
        service = NewsStreamService(db)
        stats = service.get_stats()
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/news/sources")
async def list_news_sources():
    """
    List configured news sources and their status.
    
    Returns information about RSS feeds, Twitter, and Telegram configuration.
    """
    import os
    
    rss_feeds = os.getenv("RSS_FEEDS", "").split(",")
    rss_feeds = [f.strip() for f in rss_feeds if f.strip()]
    
    twitter_enabled = bool(os.getenv("TWITTER_BEARER_TOKEN"))
    twitter_keywords = os.getenv("TWITTER_KEYWORDS", "").split(",")
    twitter_keywords = [k.strip() for k in twitter_keywords if k.strip()]
    
    telegram_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    telegram_channels = os.getenv("TELEGRAM_CHANNEL_IDS", "").split(",")
    telegram_channels = [c.strip() for c in telegram_channels if c.strip()]
    
    return {
        "rss": {
            "enabled": len(rss_feeds) > 0,
            "feed_count": len(rss_feeds),
            "feeds": rss_feeds if rss_feeds else ["Using default feeds"],
        },
        "twitter": {
            "enabled": twitter_enabled,
            "keyword_count": len(twitter_keywords),
            "keywords": twitter_keywords if twitter_keywords else [],
        },
        "telegram": {
            "enabled": telegram_enabled,
            "channel_count": len(telegram_channels),
            "channels": telegram_channels if telegram_channels else [],
        },
    }


# ============================================================================
# REAL-TIME INDICATOR WEBSOCKET ENDPOINTS (Task 2.8)
# ============================================================================

@router.websocket("/ws/indicators")
async def indicator_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time indicator updates.
    
    **Connection Flow:**
    1. Client connects to /api/v1/intelligence/ws/indicators
    2. Server sends welcome message with client_id
    3. Client subscribes to indicators via JSON message
    4. Server streams real-time indicator updates
    5. Client sends periodic pings to maintain connection
    
    **Message Types:**
    
    **From Client:**
    - `ping`: Heartbeat to keep connection alive
    - `subscribe`: Subscribe to indicator updates
    - `unsubscribe`: Unsubscribe from indicator updates
    
    **From Server:**
    - `connected`: Welcome message with client_id
    - `pong`: Response to ping
    - `subscribed`: Confirmation of subscription
    - `unsubscribed`: Confirmation of unsubscription
    - `indicator_update`: Real-time indicator values
    - `error`: Error message
    
    **Subscribe Message Format:**
    ```json
    {
        "action": "subscribe",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": ["EMA_20", "RSI_14", "MACD"]
    }
    ```
    
    **Unsubscribe Message Format:**
    ```json
    {
        "action": "unsubscribe",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": ["EMA_20", "RSI_14", "MACD"]
    }
    ```
    
    **Indicator Update Message Format:**
    ```json
    {
        "type": "indicator_update",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": {
            "EMA_20": 45123.45,
            "RSI_14": 65.3,
            "MACD": {
                "macd": 123.45,
                "signal": 98.76,
                "histogram": 24.69
            }
        },
        "timestamp": "2024-01-15T12:00:00Z"
    }
    ```
    
    **Example Usage (JavaScript):**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/intelligence/ws/indicators');
    
    ws.onopen = () => {
        console.log('Connected');
        
        // Subscribe to indicators
        ws.send(JSON.stringify({
            action: 'subscribe',
            symbol: 'BTC-USD',
            timeframe: '1h',
            indicators: ['EMA_20', 'RSI_14', 'MACD']
        }));
        
        // Send periodic pings
        setInterval(() => {
            ws.send('ping');
        }, 30000);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'indicator_update') {
            console.log('Indicator update:', data);
            // Update UI with new indicator values
        }
    };
    ```
    """
    manager = get_ws_manager()
    client_id = str(uuid.uuid4())
    
    try:
        # Connect client
        await manager.connect(websocket, client_id)
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await manager.handle_ping(client_id)
                    continue
                
                # Parse JSON message
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await manager.send_to_client(client_id, {
                        "type": "error",
                        "message": "Invalid JSON format",
                    })
                    continue
                
                action = message.get("action")
                
                # Handle subscribe
                if action == "subscribe":
                    symbol = message.get("symbol")
                    timeframe = message.get("timeframe")
                    indicators = message.get("indicators", [])
                    
                    if not symbol or not timeframe or not indicators:
                        await manager.send_to_client(client_id, {
                            "type": "error",
                            "message": "Missing required fields: symbol, timeframe, indicators",
                        })
                        continue
                    
                    subscription = IndicatorSubscription(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicators=indicators,
                    )
                    
                    result = await manager.subscribe(client_id, subscription)
                    
                    await manager.send_to_client(client_id, {
                        "type": "subscribed" if result["status"] == "success" else "error",
                        **result,
                    })
                
                # Handle unsubscribe
                elif action == "unsubscribe":
                    symbol = message.get("symbol")
                    timeframe = message.get("timeframe")
                    indicators = message.get("indicators", [])
                    
                    if not symbol or not timeframe or not indicators:
                        await manager.send_to_client(client_id, {
                            "type": "error",
                            "message": "Missing required fields: symbol, timeframe, indicators",
                        })
                        continue
                    
                    subscription = IndicatorSubscription(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicators=indicators,
                    )
                    
                    result = await manager.unsubscribe(client_id, subscription)
                    
                    await manager.send_to_client(client_id, {
                        "type": "unsubscribed" if result["status"] == "success" else "error",
                        **result,
                    })
                
                else:
                    await manager.send_to_client(client_id, {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                log.error(f"WebSocket error for client {client_id}: {e}")
                await manager.send_to_client(client_id, {
                    "type": "error",
                    "message": str(e),
                })
    
    finally:
        await manager.disconnect(client_id)


@router.post("/indicators/broadcast")
async def broadcast_indicator_update(
    symbol: str,
    timeframe: str,
    indicators: List[str],
    market_data: Dict[str, List[float]],
):
    """
    Broadcast indicator updates to subscribed WebSocket clients.
    
    This endpoint is typically called by market data ingestion services
    when new data arrives. It computes indicators and broadcasts updates
    to all subscribed clients.
    
    **Parameters:**
    - symbol: Trading symbol (e.g., "BTC-USD")
    - timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
    - indicators: List of indicator names to compute
    - market_data: Dict with highs, lows, closes, volumes arrays
    
    **Example Request:**
    ```json
    {
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "indicators": ["EMA_20", "RSI_14", "MACD"],
        "market_data": {
            "highs": [100.5, 101.2, 102.0],
            "lows": [99.5, 100.0, 101.0],
            "closes": [100.0, 101.0, 101.5],
            "volumes": [1000, 1200, 1100]
        }
    }
    ```
    
    **Returns:**
    ```json
    {
        "status": "success",
        "clients_notified": 5,
        "message": "Broadcast sent to 5 clients"
    }
    ```
    """
    try:
        manager = get_ws_manager()
        
        # Broadcast to subscribed clients
        await manager.broadcast_indicator_update(
            symbol=symbol,
            timeframe=timeframe,
            indicators=indicators,
            market_data=market_data,
        )
        
        # Count subscribed clients
        subscription = IndicatorSubscription(
            symbol=symbol,
            timeframe=timeframe,
            indicators=indicators,
        )
        sub_key = subscription.to_key()
        clients_notified = len(manager.subscriptions.get(sub_key, set()))
        
        return {
            "status": "success",
            "clients_notified": clients_notified,
            "message": f"Broadcast sent to {clients_notified} clients",
        }
    
    except Exception as e:
        log.error(f"Error broadcasting indicator update: {e}")
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")


@router.get("/indicators/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns statistics about active connections, subscriptions,
    messages sent, and errors.
    
    **Returns:**
    ```json
    {
        "total_connections": 100,
        "active_connections": 25,
        "total_subscriptions": 50,
        "messages_sent": 10000,
        "errors": 5,
        "subscriptions_by_key": {
            "BTC-USD:1h:EMA_20,RSI_14": 10,
            "ETH-USD:4h:MACD": 5
        }
    }
    ```
    """
    manager = get_ws_manager()
    return manager.get_stats()
