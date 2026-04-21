"""
Multi-Timeframe Analysis for technical indicators.

Computes indicators across multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d) simultaneously
with Redis caching and cache invalidation on new candle formation.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np

log = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Analyzes indicators across multiple timeframes with caching."""
    
    # Standard timeframes
    STANDARD_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    # Timeframe to seconds mapping
    TIMEFRAME_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    
    # Cache TTLs for each timeframe
    CACHE_TTLS = {
        "1m": 60,      # 1 minute
        "5m": 300,     # 5 minutes
        "15m": 900,    # 15 minutes
        "1h": 3600,    # 1 hour
        "4h": 14400,   # 4 hours
        "1d": 86400,   # 1 day
    }
    
    def __init__(self, indicator_registry, redis_client=None, custom_timeframes: Optional[List[str]] = None):
        """Initialize multi-timeframe analyzer.
        
        Args:
            indicator_registry: IndicatorRegistry instance
            redis_client: Redis client for caching (optional)
            custom_timeframes: Custom timeframe combinations (optional)
        """
        self.registry = indicator_registry
        self.redis = redis_client
        self.timeframes = custom_timeframes or self.STANDARD_TIMEFRAMES
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _make_cache_key(self, symbol: str, timeframe: str, indicators_hash: str) -> str:
        """Generate cache key for multi-timeframe analysis."""
        return f"mta:{symbol}:{timeframe}:{indicators_hash}"
    
    def _get_indicators_hash(self, indicators: List[str]) -> str:
        """Generate hash of indicator list."""
        import hashlib
        indicators_str = ",".join(sorted(indicators))
        return hashlib.md5(indicators_str.encode()).hexdigest()
    
    async def analyze(
        self,
        symbol: str,
        indicators: List[str],
        ohlcv_data: Dict[str, List[Dict[str, float]]],
    ) -> Dict[str, Dict[str, Any]]:
        """Compute indicators across multiple timeframes.
        
        Args:
            symbol: Asset symbol (e.g., "BTC/USD")
            indicators: List of indicator names to compute
            ohlcv_data: Dict mapping timeframe -> list of OHLCV candles
                       Each candle: {"open": float, "high": float, "low": float, "close": float, "volume": float}
        
        Returns:
            Dict mapping timeframe -> Dict of computed indicators
        """
        results = {}
        indicators_hash = self._get_indicators_hash(indicators)
        
        # Compute indicators for each timeframe in parallel
        tasks = []
        for timeframe in self.timeframes:
            if timeframe not in ohlcv_data:
                log.warning(f"No OHLCV data for {symbol} {timeframe}")
                continue
            
            task = self._analyze_timeframe(
                symbol, timeframe, indicators, ohlcv_data[timeframe], indicators_hash
            )
            tasks.append((timeframe, task))
        
        # Run all tasks concurrently
        for timeframe, task in tasks:
            try:
                results[timeframe] = await task
            except Exception as e:
                log.error(f"Error analyzing {symbol} {timeframe}: {e}")
                results[timeframe] = {"error": str(e)}
        
        return results
    
    async def _analyze_timeframe(
        self,
        symbol: str,
        timeframe: str,
        indicators: List[str],
        candles: List[Dict[str, float]],
        indicators_hash: str,
    ) -> Dict[str, Any]:
        """Analyze a single timeframe."""
        cache_key = self._make_cache_key(symbol, timeframe, indicators_hash)
        
        # Check cache
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    self.cache_hits += 1
                    return json.loads(cached)
            except Exception as e:
                log.debug(f"Cache get failed: {e}")
        
        self.cache_misses += 1
        
        # Convert candles to numpy arrays
        if not candles or len(candles) == 0:
            return {}
        
        highs = np.array([c.get("high", 0) for c in candles])
        lows = np.array([c.get("low", 0) for c in candles])
        closes = np.array([c.get("close", 0) for c in candles])
        volumes = np.array([c.get("volume", 0) for c in candles])
        
        # Compute indicators
        result = self.registry.compute_multiple(
            indicators, highs, lows, closes, volumes
        )
        
        # Extract latest values
        latest_values = {}
        for indicator_name, indicator_data in result.items():
            if isinstance(indicator_data, dict) and "error" not in indicator_data:
                # Multi-value indicator (e.g., MACD, Ichimoku)
                latest_values[indicator_name] = {}
                for key, values in indicator_data.items():
                    if isinstance(values, np.ndarray):
                        valid = values[~np.isnan(values)]
                        if len(valid) > 0:
                            latest_values[indicator_name][key] = float(valid[-1])
            elif isinstance(indicator_data, np.ndarray):
                # Single-value indicator
                valid = indicator_data[~np.isnan(indicator_data)]
                if len(valid) > 0:
                    latest_values[indicator_name] = float(valid[-1])
            else:
                latest_values[indicator_name] = indicator_data
        
        # Cache result
        if self.redis:
            try:
                ttl = self.CACHE_TTLS.get(timeframe, 60)
                self.redis.setex(cache_key, ttl, json.dumps(latest_values))
            except Exception as e:
                log.debug(f"Cache set failed: {e}")
        
        return latest_values
    
    def invalidate_cache(self, symbol: str, timeframe: str) -> None:
        """Invalidate cache for a specific symbol and timeframe.
        
        Called when a new candle forms to ensure fresh data.
        """
        if not self.redis:
            return
        
        try:
            # Delete all cache entries for this symbol/timeframe
            pattern = f"mta:{symbol}:{timeframe}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                log.debug(f"Invalidated {len(keys)} cache entries for {symbol} {timeframe}")
        except Exception as e:
            log.debug(f"Cache invalidation failed: {e}")
    
    def invalidate_symbol_cache(self, symbol: str) -> None:
        """Invalidate all cache for a symbol across all timeframes."""
        if not self.redis:
            return
        
        try:
            pattern = f"mta:{symbol}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                log.debug(f"Invalidated {len(keys)} cache entries for {symbol}")
        except Exception as e:
            log.debug(f"Cache invalidation failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": total,
            "hit_rate_percent": hit_rate,
        }
    
    def reset_cache_stats(self) -> None:
        """Reset cache statistics."""
        self.cache_hits = 0
        self.cache_misses = 0
    
    def set_custom_timeframes(self, timeframes: List[str]) -> None:
        """Set custom timeframe combinations.
        
        Args:
            timeframes: List of timeframe strings (e.g., ["1m", "5m", "1h"])
        """
        self.timeframes = timeframes
        log.info(f"Custom timeframes set: {timeframes}")
    
    def get_timeframe_alignment(self, timeframe: str, timestamp: int) -> int:
        """Get seconds until next timeframe alignment.
        
        Args:
            timeframe: Timeframe string (e.g., "1h")
            timestamp: Unix timestamp
        
        Returns:
            Seconds until next candle closes
        """
        timeframe_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 60)
        seconds_in_timeframe = timestamp % timeframe_seconds
        return timeframe_seconds - seconds_in_timeframe
    
    async def analyze_with_filtering(
        self,
        symbol: str,
        indicators: List[str],
        ohlcv_data: Dict[str, List[Dict[str, float]]],
        filter_timeframes: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze indicators with optional timeframe filtering.
        
        Args:
            symbol: Asset symbol
            indicators: List of indicator names
            ohlcv_data: OHLCV data by timeframe
            filter_timeframes: Optional list of timeframes to include
        
        Returns:
            Filtered results
        """
        results = await self.analyze(symbol, indicators, ohlcv_data)
        
        if filter_timeframes:
            results = {tf: results[tf] for tf in filter_timeframes if tf in results}
        
        return results
