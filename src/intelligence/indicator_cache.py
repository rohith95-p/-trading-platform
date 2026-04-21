"""
Enhanced indicator caching with TTL management and monitoring.

Provides Redis-based caching for all indicators with configurable TTLs,
cache invalidation, and hit rate monitoring.
"""
import logging
import json
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class IndicatorCacheManager:
    """Manages indicator caching with TTL and monitoring."""
    
    # Default TTLs for different indicator types
    DEFAULT_TTLS = {
        "fast": 60,        # 1 minute for fast-moving indicators
        "medium": 300,     # 5 minutes for medium-term indicators
        "slow": 3600,      # 1 hour for slow-moving indicators
        "daily": 86400,    # 1 day for daily indicators
    }
    
    # Indicator classification for TTL selection
    INDICATOR_TTLS = {
        # Phase 1 indicators
        "EMA_20": "fast",
        "EMA_50": "medium",
        "EMA_200": "slow",
        "RSI_14": "fast",
        "MACD": "fast",
        "ATR_14": "medium",
        "BBANDS_20": "medium",
        "ADX_14": "slow",
        "OBV": "fast",
        "VWAP": "fast",
        
        # Phase 1.5 indicators
        "STOCHASTIC": "fast",
        "CCI_20": "fast",
        "WILLR_14": "fast",
        "ICHIMOKU": "slow",
        "AROON": "medium",
        "KELTNER": "medium",
        "MFI_14": "fast",
        "ROC_12": "fast",
        "AD": "fast",
        "CMF_20": "medium",
    }
    
    def __init__(self, redis_client=None):
        """Initialize cache manager.
        
        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis = redis_client
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
    
    def _make_key(self, symbol: str, timeframe: str, indicator: str) -> str:
        """Generate cache key."""
        key_str = f"{symbol}:{timeframe}:{indicator}"
        return f"ind_cache:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def _get_ttl(self, indicator: str) -> int:
        """Get TTL for an indicator."""
        ttl_type = self.INDICATOR_TTLS.get(indicator, "medium")
        return self.DEFAULT_TTLS.get(ttl_type, 300)
    
    def get(self, symbol: str, timeframe: str, indicator: str) -> Optional[Dict[str, Any]]:
        """Get cached indicator value.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe (e.g., "1h")
            indicator: Indicator name
        
        Returns:
            Cached value or None
        """
        if not self.redis:
            return None
        
        try:
            key = self._make_key(symbol, timeframe, indicator)
            cached = self.redis.get(key)
            
            if cached:
                self.stats["hits"] += 1
                return json.loads(cached)
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            log.debug(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None
    
    def set(self, symbol: str, timeframe: str, indicator: str, value: Dict[str, Any]) -> bool:
        """Set cached indicator value.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            indicator: Indicator name
            value: Value to cache
        
        Returns:
            True if successful
        """
        if not self.redis:
            return False
        
        try:
            key = self._make_key(symbol, timeframe, indicator)
            ttl = self._get_ttl(indicator)
            self.redis.setex(key, ttl, json.dumps(value))
            self.stats["sets"] += 1
            return True
        except Exception as e:
            log.debug(f"Cache set error: {e}")
            self.stats["errors"] += 1
            return False
    
    def delete(self, symbol: str, timeframe: str, indicator: str) -> bool:
        """Delete cached indicator value.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            indicator: Indicator name
        
        Returns:
            True if successful
        """
        if not self.redis:
            return False
        
        try:
            key = self._make_key(symbol, timeframe, indicator)
            self.redis.delete(key)
            self.stats["deletes"] += 1
            return True
        except Exception as e:
            log.debug(f"Cache delete error: {e}")
            self.stats["errors"] += 1
            return False
    
    def invalidate_symbol(self, symbol: str) -> int:
        """Invalidate all cache for a symbol.
        
        Args:
            symbol: Asset symbol
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            pattern = f"ind_cache:*{symbol}*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                log.debug(f"Invalidated {deleted} cache entries for {symbol}")
                return deleted
            return 0
        except Exception as e:
            log.debug(f"Cache invalidation error: {e}")
            self.stats["errors"] += 1
            return 0
    
    def invalidate_timeframe(self, symbol: str, timeframe: str) -> int:
        """Invalidate cache for a symbol and timeframe.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            pattern = f"ind_cache:*{symbol}*{timeframe}*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                log.debug(f"Invalidated {deleted} cache entries for {symbol} {timeframe}")
                return deleted
            return 0
        except Exception as e:
            log.debug(f"Cache invalidation error: {e}")
            self.stats["errors"] += 1
            return 0
    
    def invalidate_indicator(self, indicator: str) -> int:
        """Invalidate cache for a specific indicator across all symbols/timeframes.
        
        Args:
            indicator: Indicator name
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            pattern = f"ind_cache:*{indicator}*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                log.debug(f"Invalidated {deleted} cache entries for {indicator}")
                return deleted
            return 0
        except Exception as e:
            log.debug(f"Cache invalidation error: {e}")
            self.stats["errors"] += 1
            return 0
    
    def clear_all(self) -> int:
        """Clear all indicator cache.
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            pattern = "ind_cache:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                log.info(f"Cleared {deleted} cache entries")
                return deleted
            return 0
        except Exception as e:
            log.debug(f"Cache clear error: {e}")
            self.stats["errors"] += 1
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_requests": total,
            "hit_rate_percent": hit_rate,
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "errors": self.stats["errors"],
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
    
    def set_custom_ttl(self, indicator: str, ttl_seconds: int) -> None:
        """Set custom TTL for an indicator.
        
        Args:
            indicator: Indicator name
            ttl_seconds: TTL in seconds
        """
        # Store in a custom TTL dict (would need to be persisted in production)
        if not hasattr(self, "custom_ttls"):
            self.custom_ttls = {}
        
        self.custom_ttls[indicator] = ttl_seconds
        log.info(f"Set custom TTL for {indicator}: {ttl_seconds}s")
    
    def get_cache_size(self) -> int:
        """Get approximate cache size in bytes.
        
        Returns:
            Approximate size in bytes
        """
        if not self.redis:
            return 0
        
        try:
            info = self.redis.info("memory")
            return info.get("used_memory", 0)
        except Exception as e:
            log.debug(f"Error getting cache size: {e}")
            return 0
