"""
Simple integration tests for Technical Analysis API (Task 2.6).

Tests the POST /intelligence/indicators/compute endpoint.
"""

import pytest
import numpy as np
from src.intelligence.indicator_cache_service import get_cache_service


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
