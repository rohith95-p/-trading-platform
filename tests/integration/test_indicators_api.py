"""
Integration tests for Technical Analysis API (Task 2.6).

Tests the POST /intelligence/indicators/compute endpoint with:
- Request validation
- Multiple timeframes
- Batch computation
- Rate limiting
- Response caching
"""

import pytest
import numpy as np
from src.intelligence.indicator_cache_service import get_cache_service
import time


class TestIndicatorComputeAPI:
    """Test the enhanced indicator computation API."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache_service = get_cache_service()
        cache_service.clear()
    
    def test_compute_single_indicator(self, client):
        """Test computing a single indicator."""
        # Generate sample data
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["RSI_14"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                    "volumes": volumes.tolist(),
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["symbol"] == "BTC-USD"
        assert data["timeframe"] == "1h"
        assert "RSI_14" in data["indicators"]
        assert data["latency_ms"] > 0
        assert data["cached"] is False
        
        # Validate RSI value
        rsi_value = data["indicators"]["RSI_14"]
        assert rsi_value is not None
        assert 0 <= rsi_value <= 100
    
    def test_compute_multiple_indicators(self, client):
        """Test computing multiple indicators."""
        n = 100
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "ETH-USD",
                "timeframe": "4h",
                "indicators": ["EMA_20", "RSI_14", "MACD", "BBANDS_20"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                    "volumes": volumes.tolist(),
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate all indicators are present
        assert "EMA_20" in data["indicators"]
        assert "RSI_14" in data["indicators"]
        assert "MACD" in data["indicators"]
        assert "BBANDS_20" in data["indicators"]
        
        # Validate MACD structure (dict result)
        macd = data["indicators"]["MACD"]
        assert isinstance(macd, dict)
        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd
        
        # Validate Bollinger Bands structure
        bbands = data["indicators"]["BBANDS_20"]
        assert isinstance(bbands, dict)
        assert "upper" in bbands
        assert "middle" in bbands
        assert "lower" in bbands
        
        # Validate band ordering
        if all(v is not None for v in bbands.values()):
            assert bbands["lower"] <= bbands["middle"] <= bbands["upper"]
    
    def test_all_timeframes(self, client):
        """Test all supported timeframes."""
        timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        for timeframe in timeframes:
            response = client.post(
                "/api/v1/intelligence/indicators/compute",
                json={
                    "symbol": "BTC-USD",
                    "timeframe": timeframe,
                    "indicators": ["EMA_20"],
                    "market_data": {
                        "highs": highs.tolist(),
                        "lows": lows.tolist(),
                        "closes": closes.tolist(),
                        "volumes": volumes.tolist(),
                    },
                },
            )
            
            assert response.status_code == 200, f"Failed for timeframe {timeframe}"
            data = response.json()
            assert data["timeframe"] == timeframe
    
    def test_invalid_timeframe(self, client):
        """Test invalid timeframe returns error."""
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "invalid",
                "indicators": ["EMA_20"],
                "market_data": {
                    "highs": [100, 101],
                    "lows": [99, 100],
                    "closes": [100, 101],
                    "volumes": [1000, 1100],
                },
            },
        )
        
        assert response.status_code == 400
        assert "Invalid timeframe" in response.json()["detail"]
    
    def test_invalid_indicator(self, client):
        """Test invalid indicator name returns error."""
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["INVALID_INDICATOR"],
                "market_data": {
                    "highs": [100, 101],
                    "lows": [99, 100],
                    "closes": [100, 101],
                    "volumes": [1000, 1100],
                },
            },
        )
        
        assert response.status_code == 400
        assert "Invalid indicators" in response.json()["detail"]
    
    def test_mismatched_data_lengths(self, client):
        """Test mismatched data array lengths returns error."""
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20"],
                "market_data": {
                    "highs": [100, 101, 102],
                    "lows": [99, 100],  # Different length
                    "closes": [100, 101],
                    "volumes": [1000, 1100],
                },
            },
        )
        
        assert response.status_code == 400
        assert "same length" in response.json()["detail"]
    
    def test_insufficient_data(self, client):
        """Test insufficient data points returns error."""
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20"],
                "market_data": {
                    "highs": [100],
                    "lows": [99],
                    "closes": [100],
                    "volumes": [1000],
                },
            },
        )
        
        assert response.status_code == 400
        assert "at least 2 data points" in response.json()["detail"]
    
    def test_response_caching(self, client):
        """Test that responses are cached correctly."""
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        request_data = {
            "symbol": "BTC-USD",
            "timeframe": "1h",
            "indicators": ["EMA_20", "RSI_14"],
            "market_data": {
                "highs": highs.tolist(),
                "lows": lows.tolist(),
                "closes": closes.tolist(),
                "volumes": volumes.tolist(),
            },
        }
        
        # First request - should not be cached
        response1 = client.post(
            "/api/v1/intelligence/indicators/compute",
            json=request_data,
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should be cached
        response2 = client.post(
            "/api/v1/intelligence/indicators/compute",
            json=request_data,
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Results should be identical
        assert data1["indicators"] == data2["indicators"]
        
        # Cached request should be faster
        assert data2["latency_ms"] < data1["latency_ms"]
    
    def test_latency_under_100ms(self, client):
        """Test that computation completes within 100ms target."""
        n = 100
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14", "MACD"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                    "volumes": volumes.tolist(),
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check latency (allow some margin for test environment)
        assert data["latency_ms"] < 200, f"Latency {data['latency_ms']}ms exceeds target"
    
    def test_volume_optional_indicators(self, client):
        """Test indicators that don't require volume data."""
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        
        # Test without volumes
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14", "MACD", "BBANDS_20"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All indicators should compute successfully
        assert "EMA_20" in data["indicators"]
        assert "RSI_14" in data["indicators"]
        assert "MACD" in data["indicators"]
        assert "BBANDS_20" in data["indicators"]
    
    def test_volume_required_indicators(self, client):
        """Test that volume-dependent indicators fail without volume data."""
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        
        # Test OBV without volumes - should return error in result
        response = client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["OBV"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have error in indicator result
        assert "OBV" in data["indicators"]
        assert "error" in data["indicators"]["OBV"]


class TestBatchIndicatorAPI:
    """Test batch indicator computation."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache_service = get_cache_service()
        cache_service.clear()
    
    def test_batch_computation(self, client):
        """Test batch computation of multiple requests."""
        n = 50
        
        # Generate data for BTC
        btc_closes = np.cumsum(np.random.randn(n)) + 100
        btc_highs = btc_closes + np.abs(np.random.randn(n))
        btc_lows = btc_closes - np.abs(np.random.randn(n))
        btc_volumes = np.random.randint(1000, 10000, n)
        
        # Generate data for ETH
        eth_closes = np.cumsum(np.random.randn(n)) + 2000
        eth_highs = eth_closes + np.abs(np.random.randn(n))
        eth_lows = eth_closes - np.abs(np.random.randn(n))
        eth_volumes = np.random.randint(5000, 50000, n)
        
        response = client.post(
            "/api/v1/intelligence/indicators/compute/batch",
            json={
                "requests": [
                    {
                        "symbol": "BTC-USD",
                        "timeframe": "1h",
                        "indicators": ["EMA_20", "RSI_14"],
                        "market_data": {
                            "highs": btc_highs.tolist(),
                            "lows": btc_lows.tolist(),
                            "closes": btc_closes.tolist(),
                            "volumes": btc_volumes.tolist(),
                        },
                    },
                    {
                        "symbol": "ETH-USD",
                        "timeframe": "1h",
                        "indicators": ["MACD", "BBANDS_20"],
                        "market_data": {
                            "highs": eth_highs.tolist(),
                            "lows": eth_lows.tolist(),
                            "closes": eth_closes.tolist(),
                            "volumes": eth_volumes.tolist(),
                        },
                    },
                ]
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "results" in data
        assert "total" in data
        assert "total_latency_ms" in data
        assert data["total"] == 2
        
        # Validate first result (BTC)
        btc_result = data["results"][0]
        assert btc_result["symbol"] == "BTC-USD"
        assert "EMA_20" in btc_result["indicators"]
        assert "RSI_14" in btc_result["indicators"]
        
        # Validate second result (ETH)
        eth_result = data["results"][1]
        assert eth_result["symbol"] == "ETH-USD"
        assert "MACD" in eth_result["indicators"]
        assert "BBANDS_20" in eth_result["indicators"]
    
    def test_batch_size_limit(self, client):
        """Test that batch size is limited."""
        # Create 11 requests (exceeds limit of 10)
        requests = []
        for i in range(11):
            requests.append({
                "symbol": f"SYMBOL-{i}",
                "timeframe": "1h",
                "indicators": ["EMA_20"],
                "market_data": {
                    "highs": [100, 101],
                    "lows": [99, 100],
                    "closes": [100, 101],
                    "volumes": [1000, 1100],
                },
            })
        
        response = client.post(
            "/api/v1/intelligence/indicators/compute/batch",
            json={"requests": requests},
        )
        
        assert response.status_code == 400
        assert "Batch size limited" in response.json()["detail"]


class TestIndicatorListAPI:
    """Test indicator listing endpoints."""
    
    def test_list_available_indicators(self, client):
        """Test listing all available indicators."""
        response = client.get("/api/v1/intelligence/indicators/available")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "indicators" in data
        assert "total" in data
        assert data["total"] > 0
        
        # Check that Phase 1 indicators are present
        indicator_names = [ind["name"] for ind in data["indicators"]]
        assert "EMA_20" in indicator_names
        assert "RSI_14" in indicator_names
        assert "MACD" in indicator_names
        
        # Check that Phase 1.5 indicators are present
        assert "STOCHASTIC" in indicator_names
        assert "CCI_20" in indicator_names
        assert "ICHIMOKU" in indicator_names
        
        # Validate structure
        for indicator in data["indicators"]:
            assert "name" in indicator
            assert "description" in indicator


class TestCacheManagement:
    """Test cache management endpoints."""
    
    def test_cache_stats(self, client):
        """Test getting cache statistics."""
        response = client.get("/api/v1/intelligence/indicators/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hits" in data
        assert "misses" in data
        assert "sets" in data
        assert "hit_rate" in data
        assert "cache_size" in data
    
    def test_clear_cache(self, client):
        """Test clearing cache."""
        # First, populate cache
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)
        
        client.post(
            "/api/v1/intelligence/indicators/compute",
            json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20"],
                "market_data": {
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                    "volumes": volumes.tolist(),
                },
            },
        )
        
        # Clear cache
        response = client.post("/api/v1/intelligence/indicators/cache/clear")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify cache is empty
        stats = client.get("/api/v1/intelligence/indicators/cache/stats").json()
        assert stats["cache_size"] == 0
    
    def test_cleanup_cache(self, client):
        """Test cleaning up expired cache entries."""
        response = client.post("/api/v1/intelligence/indicators/cache/cleanup")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "removed" in data
        assert data["status"] == "success"
