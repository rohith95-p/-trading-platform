"""
Unit tests for indicator cache service with Redis connection pooling.

Tests cover:
- Redis connection pooling
- Cache key generation
- TTL policies per indicator
- Cache invalidation
- Cache monitoring
- Cache warming
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.intelligence.indicator_cache_service import (
    IndicatorCacheService,
    get_cache_service,
    initialize_cache,
    close_cache,
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.scan = AsyncMock(return_value=(0, []))
    redis_mock.flushdb = AsyncMock()
    redis_mock.dbsize = AsyncMock(return_value=0)
    redis_mock.info = AsyncMock(return_value={
        "used_memory": 1024 * 1024,
        "used_memory_peak": 2 * 1024 * 1024,
    })
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_pool():
    """Create mock connection pool."""
    pool_mock = AsyncMock()
    pool_mock.disconnect = AsyncMock()
    return pool_mock


class TestCacheInitialization:
    """Test cache initialization and connection pooling."""
    
    @pytest.mark.asyncio
    async def test_initialize_with_redis(self, mock_redis, mock_pool):
        """Test successful Redis initialization."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                assert cache.redis_client is not None
                assert cache.pool is not None
                mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_without_redis(self):
        """Test fallback to memory cache when Redis unavailable."""
        with patch('redis.asyncio.ConnectionPool.from_url', side_effect=Exception("Connection failed")):
            cache = IndicatorCacheService()
            await cache.initialize()
            
            assert cache.redis_client is None
            assert cache.pool is None
    
    @pytest.mark.asyncio
    async def test_close_connections(self, mock_redis, mock_pool):
        """Test closing Redis connections."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                await cache.close()
                
                mock_redis.close.assert_called_once()
                mock_pool.disconnect.assert_called_once()


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_generate_cache_key_consistency(self):
        """Test that same inputs generate same key."""
        cache = IndicatorCacheService()
        
        key1 = cache._generate_cache_key(
            "BTC-USD", "1h", ["EMA_20", "RSI_14"], "abc123"
        )
        key2 = cache._generate_cache_key(
            "BTC-USD", "1h", ["EMA_20", "RSI_14"], "abc123"
        )
        
        assert key1 == key2
    
    def test_generate_cache_key_order_independence(self):
        """Test that indicator order doesn't affect key."""
        cache = IndicatorCacheService()
        
        key1 = cache._generate_cache_key(
            "BTC-USD", "1h", ["EMA_20", "RSI_14"], "abc123"
        )
        key2 = cache._generate_cache_key(
            "BTC-USD", "1h", ["RSI_14", "EMA_20"], "abc123"
        )
        
        assert key1 == key2
    
    def test_generate_cache_key_uniqueness(self):
        """Test that different inputs generate different keys."""
        cache = IndicatorCacheService()
        
        key1 = cache._generate_cache_key(
            "BTC-USD", "1h", ["EMA_20"], "abc123"
        )
        key2 = cache._generate_cache_key(
            "ETH-USD", "1h", ["EMA_20"], "abc123"
        )
        key3 = cache._generate_cache_key(
            "BTC-USD", "4h", ["EMA_20"], "abc123"
        )
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
    
    def test_hash_market_data(self):
        """Test market data hashing."""
        cache = IndicatorCacheService()
        
        highs = [100.0, 101.0, 102.0]
        lows = [99.0, 100.0, 101.0]
        closes = [100.5, 101.5, 101.8]
        volumes = [1000, 1100, 1050]
        
        hash1 = cache._hash_market_data(highs, lows, closes, volumes)
        hash2 = cache._hash_market_data(highs, lows, closes, volumes)
        
        assert hash1 == hash2
        assert len(hash1) == 16


class TestTTLPolicies:
    """Test TTL policies per timeframe."""
    
    def test_ttl_mapping(self):
        """Test TTL values for different timeframes."""
        cache = IndicatorCacheService()
        
        assert cache.TTL_MAP["1m"] == 60
        assert cache.TTL_MAP["5m"] == 300
        assert cache.TTL_MAP["15m"] == 900
        assert cache.TTL_MAP["1h"] == 3600
        assert cache.TTL_MAP["4h"] == 14400
        assert cache.TTL_MAP["1d"] == 86400
    
    @pytest.mark.asyncio
    async def test_set_with_correct_ttl(self, mock_redis, mock_pool):
        """Test that cache sets correct TTL based on timeframe."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                await cache.set(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000],
                    data={"EMA_20": 100.3}
                )
                
                # Verify setex was called with correct TTL (3600 for 1h)
                mock_redis.setex.assert_called_once()
                call_args = mock_redis.setex.call_args
                assert call_args[0][1] == 3600  # TTL argument


class TestCacheOperations:
    """Test cache get/set operations."""
    
    @pytest.mark.asyncio
    async def test_get_from_redis(self, mock_redis, mock_pool):
        """Test getting cached data from Redis."""
        cached_data = {"EMA_20": 100.5}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                result = await cache.get(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000]
                )
                
                assert result == cached_data
                assert cache.stats["hits"] == 1
                assert cache.stats["misses"] == 0
    
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, mock_redis, mock_pool):
        """Test cache miss."""
        mock_redis.get = AsyncMock(return_value=None)
        
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                result = await cache.get(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000]
                )
                
                assert result is None
                assert cache.stats["hits"] == 0
                assert cache.stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_set_to_redis(self, mock_redis, mock_pool):
        """Test setting data to Redis."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                await cache.set(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000],
                    data={"EMA_20": 100.3}
                )
                
                assert cache.stats["sets"] == 1
                mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_memory_cache_fallback(self):
        """Test fallback to memory cache when Redis unavailable."""
        cache = IndicatorCacheService()
        # Don't initialize Redis
        
        # Set data
        await cache.set(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20"],
            highs=[100.0],
            lows=[99.0],
            closes=[100.5],
            volumes=[1000],
            data={"EMA_20": 100.3}
        )
        
        # Get data
        result = await cache.get(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20"],
            highs=[100.0],
            lows=[99.0],
            closes=[100.5],
            volumes=[1000]
        )
        
        assert result == {"EMA_20": 100.3}
        assert cache.stats["hits"] == 1
        assert cache.stats["sets"] == 1


class TestCacheInvalidation:
    """Test cache invalidation."""
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, mock_redis, mock_pool):
        """Test invalidating cache entries by pattern."""
        mock_redis.scan = AsyncMock(return_value=(0, ["key1", "key2", "key3"]))
        
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                removed = await cache.invalidate("indicator:BTC-USD:*")
                
                assert removed == 3
                mock_redis.delete.assert_called_once_with("key1", "key2", "key3")
    
    @pytest.mark.asyncio
    async def test_clear_all(self, mock_redis, mock_pool):
        """Test clearing all cache entries."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                await cache.clear()
                
                mock_redis.flushdb.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_cache(self):
        """Test cleanup of expired memory cache entries."""
        import time
        
        cache = IndicatorCacheService()
        
        # Add entry with short TTL
        cache.memory_cache["test_key"] = {
            "data": {"test": "data"},
            "expires_at": time.time() - 1,  # Already expired
            "created_at": time.time() - 10,
        }
        
        removed = await cache.cleanup_expired()
        
        assert removed == 1
        assert "test_key" not in cache.memory_cache


class TestCacheMonitoring:
    """Test cache monitoring and statistics."""
    
    @pytest.mark.asyncio
    async def test_get_stats_basic(self):
        """Test getting basic cache statistics."""
        cache = IndicatorCacheService()
        
        cache.stats["hits"] = 80
        cache.stats["misses"] = 20
        cache.stats["sets"] = 100
        
        stats = await cache.get_stats()
        
        assert stats["hits"] == 80
        assert stats["misses"] == 20
        assert stats["sets"] == 100
        assert stats["hit_rate"] == 0.8
    
    @pytest.mark.asyncio
    async def test_get_stats_with_redis(self, mock_redis, mock_pool):
        """Test getting stats including Redis info."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                stats = await cache.get_stats()
                
                assert "redis_memory_used_mb" in stats
                assert "redis_memory_peak_mb" in stats
                assert "redis_keys" in stats
                assert stats["redis_connected"] is True
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        cache = IndicatorCacheService()
        
        # Simulate cache operations
        cache.stats["hits"] = 85
        cache.stats["misses"] = 15
        
        stats = await cache.get_stats()
        
        assert stats["hit_rate"] == 0.85
    
    @pytest.mark.asyncio
    async def test_hit_rate_zero_requests(self):
        """Test hit rate when no requests made."""
        cache = IndicatorCacheService()
        
        stats = await cache.get_stats()
        
        assert stats["hit_rate"] == 0


class TestCacheWarming:
    """Test cache warming functionality."""
    
    @pytest.mark.asyncio
    async def test_warm_cache_disabled(self):
        """Test cache warming when disabled."""
        cache = IndicatorCacheService()
        cache.warm_cache_enabled = False
        
        result = await cache.warm_cache()
        
        assert result["warmed"] == 0
        assert result["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_no_provider(self):
        """Test cache warming without data provider."""
        cache = IndicatorCacheService()
        cache.warm_cache_enabled = True
        
        result = await cache.warm_cache()
        
        # Should complete without errors but not warm anything
        assert result["warmed"] == 0
        assert result["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_with_provider(self):
        """Test cache warming with data provider."""
        cache = IndicatorCacheService()
        cache.warm_cache_enabled = True
        
        # Mock data provider
        mock_provider = AsyncMock()
        mock_provider.get_data = AsyncMock(return_value={
            "highs": [100.0],
            "lows": [99.0],
            "closes": [100.5],
            "volumes": [1000]
        })
        
        result = await cache.warm_cache(mock_provider)
        
        # Should warm cache for configured symbols/timeframes
        expected_calls = len(cache.warm_cache_symbols) * len(cache.warm_cache_timeframes)
        assert result["warmed"] == expected_calls


class TestGlobalCacheInstance:
    """Test global cache instance management."""
    
    def test_get_cache_service_singleton(self):
        """Test that get_cache_service returns singleton."""
        cache1 = get_cache_service()
        cache2 = get_cache_service()
        
        assert cache1 is cache2
    
    @pytest.mark.asyncio
    async def test_initialize_cache(self, mock_redis, mock_pool):
        """Test initializing global cache."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                await initialize_cache()
                
                cache = get_cache_service()
                assert cache.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_close_cache(self, mock_redis, mock_pool):
        """Test closing global cache."""
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                await initialize_cache()
                await close_cache()
                
                # After close, get_cache_service should create new instance
                cache = get_cache_service()
                assert cache.redis_client is None


class TestErrorHandling:
    """Test error handling in cache operations."""
    
    @pytest.mark.asyncio
    async def test_get_with_redis_error(self, mock_redis, mock_pool):
        """Test graceful handling of Redis errors on get."""
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                result = await cache.get(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000]
                )
                
                assert result is None
                assert cache.stats["errors"] >= 1
    
    @pytest.mark.asyncio
    async def test_set_with_redis_error(self, mock_redis, mock_pool):
        """Test graceful handling of Redis errors on set."""
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                cache = IndicatorCacheService()
                await cache.initialize()
                
                # Should not raise exception
                await cache.set(
                    symbol="BTC-USD",
                    timeframe="1h",
                    indicators=["EMA_20"],
                    highs=[100.0],
                    lows=[99.0],
                    closes=[100.5],
                    volumes=[1000],
                    data={"EMA_20": 100.3}
                )
                
                # Should fall back to memory cache
                assert len(cache.memory_cache) == 1
                assert cache.stats["errors"] >= 1
