# News Classification Documentation

## Overview

The News Classification module provides real-time news article classification using Anthropic's Claude API. It extracts sentiment, confidence scores, and generates trading signals for relevant markets.

## Features

### 1. Claude API Integration
- Uses Claude 3.5 Sonnet for high-quality classification
- Extracts sentiment (bullish/bearish/neutral)
- Provides confidence scores [0, 1]
- Identifies relevant assets and key topics
- Generates detailed rationale

### 2. Redis Caching
- Caches classification results for 24 hours
- Avoids re-classifying identical articles
- Significantly reduces API costs and latency
- Automatic cache invalidation

### 3. Error Handling & Retries
- Exponential backoff retry logic
- Handles rate limits gracefully
- Timeout protection
- Comprehensive error logging
- Fallback to neutral classification on errors

### 4. Batch Processing
- Classify multiple articles concurrently
- More efficient than sequential classification
- Handles individual failures gracefully
- Returns results for all articles

### 5. Trading Signal Generation
- Automatically generates trading signals
- Only for high-confidence classifications (≥0.6)
- Includes asset, direction, confidence, and rationale
- Stored in database for tracking

### 6. WebSocket Real-Time Feed
- Real-time classification updates
- Broadcast to all connected clients
- Ping/pong heartbeat support
- Automatic reconnection handling

### 7. Monitoring & Metrics
- Classification count and rate
- Average and P95 latency
- Error rate tracking
- Cache hit rate
- Sentiment distribution
- Health status endpoint

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    News Classification Flow                  │
└─────────────────────────────────────────────────────────────┘

1. Article Ingestion (Task 2.1)
   ↓
2. Check Redis Cache
   ↓
3. Cache Hit? → Return Cached Result
   ↓ (Cache Miss)
4. Call Claude API
   ↓
5. Parse & Validate Response
   ↓
6. Generate Trading Signals
   ↓
7. Store in Redis Cache
   ↓
8. Store Signals in Database
   ↓
9. Broadcast via WebSocket
   ↓
10. Record Metrics
```

## API Endpoints

### Classify Single Article

```http
POST /api/v1/intelligence/classify-news
Content-Type: application/json

{
  "title": "Bitcoin Reaches New All-Time High",
  "content": "Bitcoin has surged to a new record high...",
  "source": "rss",
  "url": "https://example.com/article"
}
```

**Response:**
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
      "rationale": "Strong positive momentum",
      "source": "news_classification"
    }
  ],
  "classified_at": "2024-01-15T12:00:00Z",
  "latency_ms": 1234
}
```

### Classify Batch

```http
POST /api/v1/intelligence/classify-news/batch
Content-Type: application/json

[
  {
    "title": "Article 1",
    "content": "Content 1",
    "source": "rss",
    "url": "https://example.com/1"
  },
  {
    "title": "Article 2",
    "content": "Content 2",
    "source": "rss",
    "url": "https://example.com/2"
  }
]
```

**Response:**
```json
{
  "results": [
    { /* classification result 1 */ },
    { /* classification result 2 */ }
  ],
  "total": 2,
  "signals_generated": 3
}
```

### WebSocket News Feed

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/intelligence/ws/news-feed');

ws.onopen = () => {
  console.log('Connected to news feed');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'connected') {
    console.log('Welcome message:', data.message);
  } else if (data.type === 'classification') {
    console.log('New classification:', data.data);
  }
};

// Send ping to keep connection alive
setInterval(() => {
  ws.send('ping');
}, 30000);
```

### Get Metrics

```http
GET /api/v1/intelligence/classification/metrics
```

**Response:**
```json
{
  "total_classifications": 1000,
  "total_errors": 5,
  "total_signals_generated": 450,
  "uptime_seconds": 3600,
  "classifications_per_minute": 16.67,
  "recent_classifications_per_minute": 20.0,
  "error_rate": 0.005,
  "cache_hit_rate": 0.65,
  "avg_latency_ms": 1234.56,
  "p95_latency_ms": 2500.0,
  "sentiment_distribution": {
    "bullish": 0.35,
    "bearish": 0.25,
    "neutral": 0.40
  },
  "cache_stats": {
    "hits": 650,
    "misses": 350,
    "total": 1000
  }
}
```

### Get Health Status

```http
GET /api/v1/intelligence/classification/health
```

**Response:**
```json
{
  "status": "healthy",
  "warnings": [],
  "metrics": { /* full metrics */ },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Claude API
ANTHROPIC_API_KEY=your-anthropic-api-key

# Redis
REDIS_URL=redis://localhost:6379

# Classification Settings (optional)
CLASSIFICATION_CACHE_TTL=86400  # 24 hours
CLASSIFICATION_MAX_RETRIES=3
CLASSIFICATION_TIMEOUT=5.0  # seconds
```

## Usage Examples

### Python Client

```python
import httpx
import asyncio

async def classify_article():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/intelligence/classify-news",
            json={
                "title": "Bitcoin Surges",
                "content": "Bitcoin has reached new highs...",
                "source": "rss",
                "url": "https://example.com/article"
            }
        )
        result = response.json()
        
        print(f"Sentiment: {result['sentiment']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Signals: {len(result['signals'])}")

asyncio.run(classify_article())
```

### Batch Classification

```python
async def classify_batch():
    articles = [
        {
            "title": f"Article {i}",
            "content": f"Content {i}",
            "source": "rss",
            "url": f"https://example.com/{i}"
        }
        for i in range(10)
    ]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/intelligence/classify-news/batch",
            json=articles
        )
        result = response.json()
        
        print(f"Classified {result['total']} articles")
        print(f"Generated {result['signals_generated']} signals")

asyncio.run(classify_batch())
```

## Performance

### Latency Requirements
- Target: <5 seconds per classification
- Typical: 1-2 seconds with Claude API
- Cached: <100ms

### Throughput
- Single classification: ~1-2 seconds
- Batch (10 articles): ~3-5 seconds
- Concurrent requests: Handled via asyncio

### Caching
- Cache hit rate: 60-70% typical
- Reduces API costs by 60-70%
- Reduces latency by 90%+

## Accuracy

### Target: 80%+ Accuracy

The classifier is designed to achieve 80%+ accuracy on validation data. Accuracy is measured by:

1. **Sentiment Accuracy**: Correct sentiment classification (bullish/bearish/neutral)
2. **Confidence Calibration**: Confidence scores match actual accuracy
3. **Signal Quality**: Generated signals lead to profitable trades

### Validation

To validate accuracy:

1. Create labeled validation dataset
2. Run classification on all articles
3. Compare predictions to ground truth
4. Calculate accuracy metrics

```python
# Example validation
validation_data = [
    ("Bitcoin Surges to New High", "bullish"),
    ("Market Crash Imminent", "bearish"),
    ("Sideways Trading Continues", "neutral"),
]

correct = 0
total = len(validation_data)

for title, expected_sentiment in validation_data:
    result = await classifier.classify({
        "title": title,
        "content": "...",
        "source": "test",
        "url": "https://test.com"
    })
    
    if result["sentiment"] == expected_sentiment:
        correct += 1

accuracy = correct / total
print(f"Accuracy: {accuracy:.2%}")
```

## Monitoring

### Key Metrics to Monitor

1. **Classification Rate**: Classifications per minute
2. **Latency**: Average and P95 latency
3. **Error Rate**: Percentage of failed classifications
4. **Cache Hit Rate**: Percentage of cached results
5. **Sentiment Distribution**: Balance of bullish/bearish/neutral
6. **Signal Generation Rate**: Signals per classification

### Health Checks

The health endpoint provides automatic health assessment:

- **Healthy**: Error rate <10%, latency <5s
- **Degraded**: Error rate 10-20%, latency 5-10s
- **Unhealthy**: Error rate >20%, latency >10s

### Alerts

Set up alerts for:
- Error rate >10%
- P95 latency >5 seconds
- Cache hit rate <30%
- Classification rate drops significantly

## Error Handling

### Retry Logic

The classifier implements exponential backoff retry:

1. First attempt fails
2. Wait 2 seconds, retry
3. Wait 4 seconds, retry
4. Wait 8 seconds, retry
5. Return error after max retries

### Error Types

- **RateLimitError**: Retry with backoff
- **APITimeoutError**: Retry with backoff
- **APIError**: Retry with backoff
- **ValidationError**: Return neutral classification
- **NetworkError**: Retry with backoff

### Fallback Behavior

On error after max retries:
- Return neutral sentiment
- Confidence = 0.0
- No signals generated
- Error logged and tracked

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/test_news_classifier.py -v

# Run with coverage
pytest tests/unit/test_news_classifier.py --cov=src/intelligence/news_classifier --cov-report=html
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/test_news_classification_api.py -v
```

### Property-Based Tests

The test suite includes property-based tests using Hypothesis to verify:
- Classification always returns valid structure
- Sentiment is always one of valid values
- Confidence is always in [0, 1] range

## Cost Optimization

### Caching Strategy

- Cache TTL: 24 hours
- Cache key: SHA-256 hash of title + content
- Reduces API calls by 60-70%
- Saves ~$0.01-0.02 per cached classification

### Batch Processing

- Process multiple articles concurrently
- Reduces total time by 50-70%
- More efficient use of API quota

### Content Truncation

- Limit content to 2000 characters
- Reduces token usage
- Maintains classification quality

## Security

### API Key Protection

- Store API key in environment variables
- Never log API keys
- Rotate keys regularly

### Input Validation

- Validate article structure
- Sanitize content
- Limit content length
- Prevent injection attacks

### Rate Limiting

- Respect Claude API rate limits
- Implement client-side rate limiting
- Queue requests during high load

## Troubleshooting

### High Latency

1. Check Claude API status
2. Verify network connectivity
3. Check Redis connection
4. Review error logs

### Low Cache Hit Rate

1. Verify Redis is running
2. Check cache TTL settings
3. Review cache key generation
4. Monitor cache eviction

### High Error Rate

1. Check API key validity
2. Verify API quota
3. Review error logs
4. Check network connectivity

### Poor Accuracy

1. Review classification prompt
2. Adjust confidence thresholds
3. Validate on labeled data
4. Consider fine-tuning

## Future Enhancements

- [ ] Support for multiple LLM providers
- [ ] Custom classification prompts per user
- [ ] Fine-tuning on historical data
- [ ] Multi-language support
- [ ] Sentiment trend analysis
- [ ] Automated accuracy monitoring
- [ ] A/B testing of prompts
- [ ] Cost tracking and optimization

## References

- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [Redis Caching Best Practices](https://redis.io/docs/manual/patterns/)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
