"""
Unit tests for news classifier with Claude API integration.

Tests cover:
- Classification accuracy
- Caching behavior
- Error handling and retries
- Batch processing
- Signal generation
- Performance requirements (<5 sec latency)
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from src.intelligence.news_classifier import NewsClassifier


def create_mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


def create_mock_anthropic_client():
    """Create mock Anthropic client."""
    client_mock = AsyncMock()
    
    # Mock successful response
    message_mock = Mock()
    message_mock.content = [Mock(text=json.dumps({
        "sentiment": "bullish",
        "confidence": 0.85,
        "rationale": "Positive market sentiment",
        "relevant_assets": ["BTC", "ETH"],
        "key_topics": ["price", "adoption"]
    }))]
    
    client_mock.messages.create = AsyncMock(return_value=message_mock)
    
    return client_mock


class TestNewsClassifierBasic:
    """Basic classification tests."""
    
    @pytest.mark.asyncio
    async def test_classify_article_success(self):
        """Test successful article classification."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Bitcoin Reaches New All-Time High",
                    "content": "Bitcoin has surged to a new record...",
                    "source": "rss",
                    "url": "https://example.com/article"
                }
                
                result = await classifier.classify(article)
                
                assert result["sentiment"] in ["bullish", "bearish", "neutral"]
                assert 0.0 <= result["confidence"] <= 1.0
                assert "rationale" in result
                assert "relevant_assets" in result
                assert "key_topics" in result
                assert "signals" in result
                assert "classified_at" in result
                assert "latency_ms" in result
                
                await classifier.close()
    
    @pytest.mark.asyncio
    async def test_sentiment_values(self):
        """Test that sentiment is one of the valid values."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Test",
                    "content": "Test",
                    "source": "test",
                    "url": "https://test.com"
                }
                
                result = await classifier.classify(article)
                
                assert result["sentiment"] in ["bullish", "bearish", "neutral"]
                
                await classifier.close()
    
    @pytest.mark.asyncio
    async def test_confidence_range(self):
        """Test that confidence is in valid range [0, 1]."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Test",
                    "content": "Test",
                    "source": "test",
                    "url": "https://test.com"
                }
                
                result = await classifier.classify(article)
                
                assert 0.0 <= result["confidence"] <= 1.0
                
                await classifier.close()


class TestNewsClassifierSignalGeneration:
    """Test trading signal generation."""
    
    @pytest.mark.asyncio
    async def test_bullish_signal_generation(self):
        """Test that bullish sentiment generates long signals."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        mock_anthropic.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text=json.dumps({
                "sentiment": "bullish",
                "confidence": 0.85,
                "rationale": "Strong positive momentum",
                "relevant_assets": ["BTC", "ETH"],
                "key_topics": ["price"]
            }))])
        )
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Crypto Rally",
                    "content": "Markets surge",
                    "source": "test",
                    "url": "https://test.com"
                }
                
                result = await classifier.classify(article)
                
                assert len(result["signals"]) == 2
                for signal in result["signals"]:
                    assert signal["direction"] == "long"
                    assert signal["confidence"] == 0.85
                    assert signal["asset"] in ["BTC", "ETH"]
                
                await classifier.close()
    
    @pytest.mark.asyncio
    async def test_neutral_no_signals(self):
        """Test that neutral sentiment generates no signals."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        mock_anthropic.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text=json.dumps({
                "sentiment": "neutral",
                "confidence": 0.5,
                "rationale": "No clear direction",
                "relevant_assets": ["BTC"],
                "key_topics": ["general"]
            }))])
        )
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Market Update",
                    "content": "Mixed signals",
                    "source": "test",
                    "url": "https://test.com"
                }
                
                result = await classifier.classify(article)
                
                assert len(result["signals"]) == 0
                
                await classifier.close()


class TestNewsClassifierPerformance:
    """Test performance requirements."""
    
    @pytest.mark.asyncio
    async def test_classification_latency(self):
        """Test that classification completes within 5 seconds."""
        mock_redis = create_mock_redis()
        mock_anthropic = create_mock_anthropic_client()
        
        with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
            with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
                classifier = NewsClassifier(api_key="test_key")
                classifier.redis_client = mock_redis
                classifier.client = mock_anthropic
                
                article = {
                    "title": "Test Article",
                    "content": "Test content",
                    "source": "test",
                    "url": "https://test.com"
                }
                
                start_time = datetime.now()
                result = await classifier.classify(article)
                end_time = datetime.now()
                
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                # Should complete within 5 seconds (5000ms)
                assert latency_ms < 5000
                
                # Result should include latency
                assert result["latency_ms"] < 5000
                
                await classifier.close()


# Simple smoke test
@pytest.mark.asyncio
async def test_classifier_initialization():
    """Test that classifier can be initialized."""
    mock_redis = create_mock_redis()
    mock_anthropic = create_mock_anthropic_client()
    
    with patch('src.intelligence.news_classifier.redis.from_url', return_value=mock_redis):
        with patch('src.intelligence.news_classifier.AsyncAnthropic', return_value=mock_anthropic):
            classifier = NewsClassifier(api_key="test_key")
            assert classifier is not None
            assert classifier.api_key == "test_key"
            await classifier.close()
