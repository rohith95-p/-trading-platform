# News Integration Documentation

## Overview

The News Integration module provides real-time news ingestion from multiple sources including RSS feeds, Twitter, and Telegram. It includes deduplication logic, database storage, and API endpoints for accessing news articles.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    News Stream Service                       │
│  - Coordinates ingestion from all sources                   │
│  - Handles deduplication                                     │
│  - Stores articles in database                               │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
┌───▼───┐ ┌──▼──┐ ┌──▼────┐
│  RSS  │ │Twitter│ │Telegram│
│Handler│ │Handler│ │Handler │
└───────┘ └──────┘ └────────┘
```

## Features

### 1. Multi-Source Ingestion

- **RSS Feeds**: Fetch articles from configured RSS feeds
- **Twitter**: Monitor tweets matching specific keywords (optional)
- **Telegram**: Monitor messages from specific channels (optional)

### 2. Deduplication

- **URL-based**: Prevents duplicate articles with the same URL
- **Content-based**: Detects duplicate content using SHA-256 hashing
- **In-memory cache**: Fast duplicate detection with database fallback

### 3. Database Storage

Articles are stored in the `news_articles` table with the following fields:

- `id`: Unique identifier (UUID)
- `source`: Source type (rss, twitter, telegram)
- `title`: Article title/headline
- `content`: Full article content or summary
- `url`: URL to the original article
- `author`: Author name (optional)
- `metadata`: Additional source-specific metadata (JSONB)
- `content_hash`: SHA-256 hash for deduplication
- `published_at`: When the article was published
- `created_at`: When the article was ingested

## Configuration

### Environment Variables

#### RSS Feeds

```bash
# Comma-separated list of RSS feed URLs
RSS_FEEDS="https://feeds.bloomberg.com/markets/news.rss,https://www.cnbc.com/id/100003114/device/rss/rss.html"
```

If not configured, the system uses default financial news feeds.

#### Twitter (Optional)

```bash
# Twitter API credentials
TWITTER_API_KEY="your_api_key"
TWITTER_API_SECRET="your_api_secret"
TWITTER_BEARER_TOKEN="your_bearer_token"

# Comma-separated list of keywords to monitor
TWITTER_KEYWORDS="bitcoin,ethereum,crypto,trading"
```

#### Telegram (Optional)

```bash
# Telegram bot token
TELEGRAM_BOT_TOKEN="your_bot_token"

# Comma-separated list of channel IDs to monitor
TELEGRAM_CHANNEL_IDS="123456789,987654321"
```

#### News Polling Interval

```bash
# Polling interval in minutes (default: 15)
NEWS_POLLING_INTERVAL=15
```

## API Endpoints

### List News Articles

```http
GET /api/v1/intelligence/news?page=1&page_size=20&source=rss
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `source` (optional): Filter by source (rss, twitter, telegram)

**Response:**
```json
{
  "articles": [
    {
      "id": "uuid",
      "source": "rss",
      "title": "Bitcoin Reaches New All-Time High",
      "content": "Bitcoin has reached...",
      "url": "https://example.com/article",
      "author": "John Doe",
      "published_at": "2024-01-15T12:00:00Z",
      "created_at": "2024-01-15T12:05:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### Get Single Article

```http
GET /api/v1/intelligence/news/{article_id}
```

**Response:**
```json
{
  "id": "uuid",
  "source": "rss",
  "title": "Bitcoin Reaches New All-Time High",
  "content": "Bitcoin has reached...",
  "url": "https://example.com/article",
  "author": "John Doe",
  "published_at": "2024-01-15T12:00:00Z",
  "created_at": "2024-01-15T12:05:00Z"
}
```

### Trigger Manual Ingestion

```http
POST /api/v1/intelligence/news/ingest
```

**Response:**
```json
{
  "status": "success",
  "message": "Ingested 15 articles",
  "details": {
    "total": 15,
    "rss": 10,
    "twitter": 3,
    "telegram": 2
  }
}
```

### Get Ingestion Statistics

```http
GET /api/v1/intelligence/news/stats
```

**Response:**
```json
{
  "total_articles": 1000,
  "articles_by_source": {
    "rss": 800,
    "twitter": 150,
    "telegram": 50
  },
  "articles_last_hour": 5,
  "articles_last_24h": 120,
  "duplicates_detected": 50,
  "errors": 2,
  "last_ingestion_at": "2024-01-15T12:00:00Z"
}
```

### List Configured Sources

```http
GET /api/v1/intelligence/news/sources
```

**Response:**
```json
{
  "rss": {
    "enabled": true,
    "feed_count": 3,
    "feeds": [
      "https://feeds.bloomberg.com/markets/news.rss",
      "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    ]
  },
  "twitter": {
    "enabled": true,
    "keyword_count": 4,
    "keywords": ["bitcoin", "ethereum", "crypto", "trading"]
  },
  "telegram": {
    "enabled": false,
    "channel_count": 0,
    "channels": []
  }
}
```

## Usage Examples

### Python Client

```python
import httpx
import asyncio

async def fetch_news():
    async with httpx.AsyncClient() as client:
        # Get recent news articles
        response = await client.get(
            "http://localhost:8000/api/v1/intelligence/news",
            params={"page": 1, "page_size": 10}
        )
        articles = response.json()
        
        for article in articles["articles"]:
            print(f"{article['title']} - {article['source']}")

asyncio.run(fetch_news())
```

### Trigger Ingestion

```python
async def trigger_ingestion():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/intelligence/news/ingest"
        )
        result = response.json()
        print(f"Ingested {result['details']['total']} articles")

asyncio.run(trigger_ingestion())
```

## Background Task Scheduling

The news ingestion runs automatically on a schedule. To set up the background task:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.intelligence.news.news_stream import NewsStreamService
from src.database import get_db

scheduler = AsyncIOScheduler()

async def scheduled_ingestion():
    db = next(get_db())
    service = NewsStreamService(db)
    await service.run_ingestion_cycle()
    db.close()

# Run every 15 minutes
scheduler.add_job(
    scheduled_ingestion,
    'interval',
    minutes=15,
    id='news_ingestion'
)

scheduler.start()
```

## Error Handling

The news integration includes comprehensive error handling:

1. **Network Errors**: Retries with exponential backoff
2. **Parsing Errors**: Logs errors and continues with other articles
3. **Database Errors**: Rolls back transactions and logs errors
4. **Rate Limiting**: Respects API rate limits for Twitter and Telegram

## Monitoring

### Metrics to Monitor

- **Ingestion Rate**: Articles ingested per hour
- **Duplicate Rate**: Percentage of duplicates detected
- **Error Rate**: Errors per ingestion cycle
- **Source Health**: Success rate per source
- **Latency**: Time from publication to ingestion

### Logging

All operations are logged with appropriate levels:

- `INFO`: Successful ingestion, statistics
- `WARNING`: Retries, rate limiting
- `ERROR`: Failed ingestion, database errors
- `DEBUG`: Detailed parsing information

## Testing

Run the test suite:

```bash
# Run all news integration tests
pytest tests/unit/test_news_stream.py -v

# Run with coverage
pytest tests/unit/test_news_stream.py --cov=src/intelligence/news --cov-report=html
```

## Database Migration

Apply the news articles table migration:

```bash
# PostgreSQL
psql -U your_user -d your_database -f sql/migrations/005_add_news_articles_table.sql

# Or use the migration script
cd sql/migrations
./migrate.sh  # Linux/Mac
./migrate.ps1  # Windows
```

## Performance Considerations

### Caching

- Deduplication cache stores up to 10,000 URLs and hashes in memory
- Cache is automatically trimmed when it exceeds limits
- Database queries are used as fallback for cache misses

### Database Indexes

The following indexes are created for optimal performance:

- `idx_news_articles_source`: Filter by source
- `idx_news_articles_published_at`: Sort by publication date
- `idx_news_articles_content_hash`: Deduplication lookups
- `idx_news_articles_created_at`: Sort by ingestion date
- `idx_news_articles_url`: Unique URL constraint

### Batch Processing

- RSS feeds are fetched concurrently
- Articles are processed in batches
- Database commits are batched for efficiency

## Security Considerations

1. **API Keys**: Store Twitter and Telegram credentials in environment variables
2. **Input Validation**: All article data is validated using Pydantic models
3. **SQL Injection**: Parameterized queries prevent SQL injection
4. **Rate Limiting**: Respect API rate limits to avoid bans
5. **Content Sanitization**: HTML tags are stripped from RSS content

## Troubleshooting

### No Articles Being Ingested

1. Check environment variables are set correctly
2. Verify RSS feed URLs are accessible
3. Check logs for error messages
4. Verify database connection

### High Duplicate Rate

1. Check if polling interval is too short
2. Verify content hash generation is working
3. Check if feeds are returning old articles

### Twitter/Telegram Not Working

1. Verify API credentials are correct
2. Check if keywords/channels are configured
3. Verify network connectivity
4. Check API rate limits

## Future Enhancements

- [ ] Support for more news sources (Reddit, Discord)
- [ ] Natural language processing for article classification
- [ ] Sentiment analysis integration
- [ ] Real-time WebSocket streaming
- [ ] Article summarization using LLMs
- [ ] Custom source configuration via UI
- [ ] Advanced filtering and search
- [ ] Article categorization and tagging
