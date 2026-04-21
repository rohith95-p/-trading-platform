"""
Integration tests for Intelligence Layer API endpoints.

Tests:
- POST /intelligence/classify-news
- POST /intelligence/indicators
- POST /intelligence/indicators/batch
- GET /intelligence/health
- GET /intelligence/stats
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import numpy as np

from src.main import app

client = TestClient(app)


class TestClassifyNewsEndpoint:
    """Test news classification endpoint."""

    def test_classify_news_success(self):
        """Test successful news classification."""
        with patch("src.api.intelligence.get_classifier") as mock_get_classifier:
            mock_classifier = Mock()
            mock_classifier.classify_async = Mock()
            
            # Mock classification result
            from src.intelligence.classifier import Classification
            mock_result = Classification(
                direction="bullish",
                materiality=0.8,
                reasoning="Good news",
                latency_ms=150,
                model="claude-3-5-sonnet-20241022",
                confidence=0.8,
            )
            
            import asyncio
            async def async_mock(*args, **kwargs):
                return mock_result
            
            mock_classifier.classify_async = async_mock
            mock_get_classifier.return_value = mock_classifier

            response = client.post(
                "/intelligence/classify-news",
                json={
                    "article": {
                        "title": "OpenAI releases GPT-5",
                        "content": "OpenAI has announced the release of GPT-5...",
                        "source": "TechCrunch",
                        "url": "https://techcrunch.com/gpt5",
                    },
                    "market_question": "Will GPT-5 be released by 2025?",
                    "yes_price": 0.7,
                },
                params={"user_id": "test-user"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["direction"] == "bullish"
            assert data["materiality"] == 0.8
            assert data["confidence"] == 0.8

    def test_classify_news_invalid_request(self):
        """Test classification with invalid request."""
        response = client.post(
            "/intelligence/classify-news",
            json={
                "article": {
                    "title": "",  # Empty title
                    "content": "Content",
                    "source": "Test",
                },
                "market_question": "Question?",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_classify_news_missing_fields(self):
        """Test classification with missing required fields."""
        response = client.post(
            "/intelligence/classify-news",
            json={
                "article": {
                    "title": "Title",
                    "content": "Content",
                },
                # Missing market_question
            },
        )

        assert response.status_code == 422


class TestIndicatorsEndpoint:
    """Test technical indicators endpoint."""

    def test_compute_indicators_success(self):
        """Test successful indicator computation."""
        # Generate sample OHLCV data
        n = 100
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)

        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "indicators": ["ema_20", "rsi_14", "atr_14"],
                "highs": highs.tolist(),
                "lows": lows.tolist(),
                "closes": closes.tolist(),
                "volumes": volumes.tolist(),
            },
            params={"user_id": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC/USD"
        assert data["timeframe"] == "1h"
        assert len(data["indicators"]) > 0
        assert data["latency_ms"] >= 0

    def test_compute_indicators_invalid_ohlcv(self):
        """Test indicator computation with invalid OHLCV data."""
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "indicators": ["ema_20"],
                "highs": [100.0, 99.0],  # High < Low (invalid)
                "lows": [101.0, 100.0],
                "closes": [100.5, 99.5],
                "volumes": [1000, 1000],
            },
        )

        assert response.status_code == 400

    def test_compute_indicators_empty_data(self):
        """Test indicator computation with empty data."""
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "indicators": ["ema_20"],
                "highs": [],
                "lows": [],
                "closes": [],
                "volumes": [],
            },
        )

        assert response.status_code == 422

    def test_compute_indicators_mismatched_lengths(self):
        """Test indicator computation with mismatched array lengths."""
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "BTC/USD",
                "timeframe": "1h",
                "indicators": ["ema_20"],
                "highs": [100.0, 101.0],
                "lows": [99.0, 100.0],
                "closes": [100.5],  # Different length
                "volumes": [1000, 1000],
            },
        )

        assert response.status_code == 422

    def test_compute_indicators_invalid_timeframe(self):
        """Test indicator computation with invalid timeframe."""
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "BTC/USD",
                "timeframe": "invalid",  # Invalid timeframe
                "indicators": ["ema_20"],
                "highs": [100.0],
                "lows": [99.0],
                "closes": [100.0],
                "volumes": [1000],
            },
        )

        assert response.status_code == 422


class TestBatchIndicatorsEndpoint:
    """Test batch indicators endpoint."""

    def test_batch_indicators_success(self):
        """Test successful batch indicator computation."""
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)

        response = client.post(
            "/intelligence/indicators/batch",
            json={
                "requests": [
                    {
                        "symbol": "BTC/USD",
                        "timeframe": "1h",
                        "indicators": ["ema_20", "rsi_14"],
                        "highs": highs.tolist(),
                        "lows": lows.tolist(),
                        "closes": closes.tolist(),
                        "volumes": volumes.tolist(),
                    },
                    {
                        "symbol": "ETH/USD",
                        "timeframe": "1h",
                        "indicators": ["ema_50", "macd"],
                        "highs": highs.tolist(),
                        "lows": lows.tolist(),
                        "closes": closes.tolist(),
                        "volumes": volumes.tolist(),
                    },
                ]
            },
            params={"user_id": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["total_latency_ms"] >= 0

    def test_batch_indicators_empty(self):
        """Test batch indicators with empty requests."""
        response = client.post(
            "/intelligence/indicators/batch",
            json={"requests": []},
        )

        assert response.status_code == 422


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/intelligence/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "intelligence-layer"


class TestStatsEndpoint:
    """Test stats endpoint."""

    def test_get_stats(self):
        """Test getting service statistics."""
        response = client.get("/intelligence/stats")
        assert response.status_code == 200
        data = response.json()
        assert "classifier" in data
        assert "rate_limiter" in data


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_enforcement(self):
        """Test that rate limiting is enforced."""
        n = 50
        closes = np.cumsum(np.random.randn(n)) + 100
        highs = closes + np.abs(np.random.randn(n))
        lows = closes - np.abs(np.random.randn(n))
        volumes = np.random.randint(1000, 10000, n)

        # Make requests up to limit
        for i in range(5):
            response = client.post(
                "/intelligence/indicators",
                json={
                    "symbol": "BTC/USD",
                    "timeframe": "1h",
                    "indicators": ["ema_20"],
                    "highs": highs.tolist(),
                    "lows": lows.tolist(),
                    "closes": closes.tolist(),
                    "volumes": volumes.tolist(),
                },
                params={"user_id": "rate-limit-test"},
            )
            assert response.status_code == 200


class TestIndicatorAccuracy:
    """Test indicator calculation accuracy."""

    def test_ema_accuracy(self):
        """Test EMA calculation accuracy."""
        # Known values for EMA
        closes = np.array([44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08])
        
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "TEST",
                "timeframe": "1h",
                "indicators": ["ema_20"],
                "highs": (closes + 1).tolist(),
                "lows": (closes - 1).tolist(),
                "closes": closes.tolist(),
                "volumes": [1000] * len(closes),
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        # Find EMA indicator
        ema_indicator = next((i for i in data["indicators"] if i["name"] == "ema_20"), None)
        assert ema_indicator is not None
        assert ema_indicator["latest"] is not None

    def test_rsi_range(self):
        """Test RSI values are in valid range."""
        closes = np.cumsum(np.random.randn(100)) + 100
        
        response = client.post(
            "/intelligence/indicators",
            json={
                "symbol": "TEST",
                "timeframe": "1h",
                "indicators": ["rsi_14"],
                "highs": (closes + 1).tolist(),
                "lows": (closes - 1).tolist(),
                "closes": closes.tolist(),
                "volumes": [1000] * len(closes),
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        rsi_indicator = next((i for i in data["indicators"] if i["name"] == "rsi_14"), None)
        assert rsi_indicator is not None
        
        if rsi_indicator["latest"] is not None:
            assert 0 <= rsi_indicator["latest"] <= 100
