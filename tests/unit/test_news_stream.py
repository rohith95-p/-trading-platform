"""
Unit tests for news stream integration.

Tests cover:
- RSS feed parsing
- Twitter API integration
- Telegram API integration
- Deduplication logic
- News ingestion service
- API endpoints
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from src.data.models import Base, NewsArticle as NewsArticleDB
from src.intelligence.news.models import NewsArticleCreate
from src.intelligence.news.deduplication import NewsDeduplicator
from src.intelligence.news.news_stream import NewsStreamService
from src.intelligence.news.sources.rss import RSSFeedHandler
from src.intelligence.news.sources.twitter import TwitterHandler
from src.intelligence.news.sources.telegram import TelegramHandler


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_article():
    """Create a sample news article."""
    return NewsArticleCreate(
        source="rss",
        title="Bitcoin Reaches New All-Time High",
        content="Bitcoin has reached a new all-time high of $100,000...",
        url="https://example.com/bitcoin-ath",
        author="John Doe",
        metadata={"feed_url": "https://example.com/feed"},
        published_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def deduplicator(db_session):
    """Create a NewsDeduplicator instance."""
    return NewsDeduplicator(db_session)


@pytest.fixture
def news_service(db_session):
    """Create a NewsStreamService instance."""
    return NewsStreamService(db_session)


# ============================================================================
# DEDUPLICATION TESTS
# ============================================================================

def test_deduplication_new_article(deduplicator, sample_article):
    """Test that a new article is not marked as duplicate."""
    is_duplicate, reason = deduplicator.is_duplicate(sample_article)
    assert not is_duplicate
    assert reason is None


def test_deduplication_duplicate_url(deduplicator, sample_article, db_session):
    """Test that duplicate URLs are detected."""
    # Insert article into database
    content_hash = sample_article.generate_content_hash()
    db_article = NewsArticleDB(
        source=sample_article.source,
        title=sample_article.title,
        content=sample_article.content,
        url=sample_article.url,
        author=sample_article.author,
        metadata=sample_article.metadata,
        content_hash=content_hash,
        published_at=sample_article.published_at,
    )
    db_session.add(db_article)
    db_session.commit()
    
    # Check for duplicate
    is_duplicate, reason = deduplicator.is_duplicate(sample_article)
    assert is_duplicate
    assert "url" in reason.lower()


def test_deduplication_duplicate_content(deduplicator, sample_article, db_session):
    """Test that duplicate content is detected."""
    # Insert article with different URL but same content
    content_hash = sample_article.generate_content_hash()
    db_article = NewsArticleDB(
        source=sample_article.source,
        title=sample_article.title,
        content=sample_article.content,
        url="https://different-url.com/article",
        author=sample_article.author,
        metadata=sample_article.metadata,
        content_hash=content_hash,
        published_at=sample_article.published_at,
    )
    db_session.add(db_article)
    db_session.commit()
    
    # Check for duplicate with different URL
    duplicate_article = NewsArticleCreate(
        source=sample_article.source,
        title=sample_article.title,
        content=sample_article.content,
        url="https://another-url.com/article",
        author=sample_article.author,
        metadata=sample_article.metadata,
        published_at=sample_article.published_at,
    )
    
    is_duplicate, reason = deduplicator.is_duplicate(duplicate_article)
    assert is_duplicate
    assert "content" in reason.lower()


def test_deduplication_cache(deduplicator, sample_article):
    """Test that deduplication cache works correctly."""
    # Mark as seen
    content_hash = sample_article.generate_content_hash()
    deduplicator.mark_as_seen(sample_article.url, content_hash)
    
    # Check for duplicate
    is_duplicate, reason = deduplicator.is_duplicate(sample_article)
    assert is_duplicate


def test_content_hash_generation(sample_article):
    """Test that content hash is generated consistently."""
    hash1 = sample_article.generate_content_hash()
    hash2 = sample_article.generate_content_hash()
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex characters


def test_content_hash_normalization():
    """Test that content normalization works for hashing."""
    article1 = NewsArticleCreate(
        source="rss",
        title="  Bitcoin  Reaches  ATH  ",  # Extra spaces
        content="  Bitcoin   has   reached   $100k  ",
        url="https://example.com/1",
        published_at=datetime.now(timezone.utc),
    )
    
    article2 = NewsArticleCreate(
        source="rss",
        title="Bitcoin Reaches ATH",  # No extra spaces
        content="Bitcoin has reached $100k",
        url="https://example.com/2",
        published_at=datetime.now(timezone.utc),
    )
    
    # After Pydantic validation, both title and content should be normalized
    assert article1.title == "Bitcoin Reaches ATH"  # Validator normalizes
    assert article2.title == "Bitcoin Reaches ATH"
    assert article1.content == "Bitcoin has reached $100k"  # Validator normalizes
    assert article2.content == "Bitcoin has reached $100k"
    
    # Hashes should be the same because both are normalized
    hash1 = article1.generate_content_hash()
    hash2 = article2.generate_content_hash()
    assert hash1 == hash2


# ============================================================================
# NEWS SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ingest_article_success(news_service, sample_article, db_session):
    """Test successful article ingestion."""
    article_id = await news_service.ingest_article(sample_article)
    
    assert article_id is not None
    assert news_service.stats["total_ingested"] == 1
    assert news_service.stats["by_source"]["rss"] == 1
    
    # Verify in database
    db_article = db_session.execute(
        select(NewsArticleDB).where(NewsArticleDB.id == article_id)
    ).scalar_one()
    
    assert db_article.title == sample_article.title
    assert db_article.url == sample_article.url


@pytest.mark.asyncio
async def test_ingest_duplicate_article(news_service, sample_article):
    """Test that duplicate articles are not ingested."""
    # Ingest first time
    article_id1 = await news_service.ingest_article(sample_article)
    assert article_id1 is not None
    
    # Try to ingest again
    article_id2 = await news_service.ingest_article(sample_article)
    assert article_id2 is None
    assert news_service.stats["duplicates_detected"] == 1


@pytest.mark.asyncio
async def test_ingest_multiple_articles(news_service):
    """Test ingesting multiple articles."""
    articles = [
        NewsArticleCreate(
            source="rss",
            title=f"Article {i}",
            content=f"Content {i}",
            url=f"https://example.com/article-{i}",
            published_at=datetime.now(timezone.utc),
        )
        for i in range(5)
    ]
    
    for article in articles:
        article_id = await news_service.ingest_article(article)
        assert article_id is not None
    
    assert news_service.stats["total_ingested"] == 5


# ============================================================================
# RSS HANDLER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rss_handler_initialization():
    """Test RSS handler initialization."""
    handler = RSSFeedHandler()
    assert len(handler.feeds) > 0  # Should have default feeds


@pytest.mark.asyncio
async def test_rss_parse_entry():
    """Test parsing an RSS entry."""
    handler = RSSFeedHandler()
    
    # Mock RSS entry
    entry = {
        "title": "Test Article",
        "link": "https://example.com/test",
        "summary": "This is a test article",
        "author": "Test Author",
        "published_parsed": (2024, 1, 15, 12, 0, 0, 0, 0, 0),
    }
    
    article = handler._parse_entry(entry, "https://example.com/feed")
    
    assert article is not None
    assert article.title == "Test Article"
    assert article.url == "https://example.com/test"
    assert article.source == "rss"


@pytest.mark.asyncio
async def test_rss_parse_entry_missing_title():
    """Test that entries without titles are skipped."""
    handler = RSSFeedHandler()
    
    entry = {
        "link": "https://example.com/test",
        "summary": "This is a test article",
    }
    
    article = handler._parse_entry(entry, "https://example.com/feed")
    assert article is None


@pytest.mark.asyncio
async def test_rss_parse_entry_missing_url():
    """Test that entries without URLs are skipped."""
    handler = RSSFeedHandler()
    
    entry = {
        "title": "Test Article",
        "summary": "This is a test article",
    }
    
    article = handler._parse_entry(entry, "https://example.com/feed")
    assert article is None


# ============================================================================
# TWITTER HANDLER TESTS
# ============================================================================

def test_twitter_handler_disabled_without_credentials():
    """Test that Twitter handler is disabled without credentials."""
    with patch.dict("os.environ", {}, clear=True):
        handler = TwitterHandler()
        assert not handler.is_enabled()


def test_twitter_handler_enabled_with_credentials():
    """Test that Twitter handler is enabled with credentials."""
    with patch.dict("os.environ", {
        "TWITTER_BEARER_TOKEN": "test_token",
        "TWITTER_KEYWORDS": "bitcoin,ethereum",
    }):
        handler = TwitterHandler()
        assert handler.is_enabled()
        assert len(handler.keywords) == 2


@pytest.mark.asyncio
async def test_twitter_parse_tweet():
    """Test parsing a tweet."""
    with patch.dict("os.environ", {
        "TWITTER_BEARER_TOKEN": "test_token",
        "TWITTER_KEYWORDS": "bitcoin",
    }):
        handler = TwitterHandler()
        
        tweet = {
            "id": "123456789",
            "text": "Bitcoin reaches new all-time high!",
            "created_at": "2024-01-15T12:00:00.000Z",
            "author_id": "user123",
        }
        
        users = {
            "user123": {
                "username": "cryptonews",
                "name": "Crypto News",
            }
        }
        
        article = handler._parse_tweet(tweet, users)
        
        assert article is not None
        assert article.source == "twitter"
        assert "Bitcoin" in article.title
        assert "123456789" in article.url


# ============================================================================
# TELEGRAM HANDLER TESTS
# ============================================================================

def test_telegram_handler_disabled_without_credentials():
    """Test that Telegram handler is disabled without credentials."""
    with patch.dict("os.environ", {}, clear=True):
        handler = TelegramHandler()
        assert not handler.is_enabled()


def test_telegram_handler_enabled_with_credentials():
    """Test that Telegram handler is enabled with credentials."""
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_IDS": "123,456",
    }):
        handler = TelegramHandler()
        assert handler.is_enabled()
        assert len(handler.channel_ids) == 2


@pytest.mark.asyncio
async def test_telegram_parse_update():
    """Test parsing a Telegram update."""
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_IDS": "123",
    }):
        handler = TelegramHandler()
        
        update = {
            "update_id": 1,
            "channel_post": {
                "message_id": 100,
                "text": "Breaking: Bitcoin reaches $100k",
                "date": 1705320000,
                "chat": {
                    "id": 123,
                    "title": "Crypto News",
                    "username": "cryptonews",
                },
            }
        }
        
        article = handler._parse_update(update)
        
        assert article is not None
        assert article.source == "telegram"
        assert "Bitcoin" in article.title


# ============================================================================
# STATISTICS TESTS
# ============================================================================

def test_deduplication_stats(deduplicator, db_session):
    """Test deduplication statistics."""
    # Add some articles
    for i in range(5):
        article = NewsArticleDB(
            source="rss",
            title=f"Article {i}",
            content=f"Content {i}",
            url=f"https://example.com/{i}",
            content_hash=f"hash{i}",
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(article)
    db_session.commit()
    
    stats = deduplicator.get_stats()
    
    assert stats["total_articles"] == 5
    assert "articles_last_24h" in stats


@pytest.mark.asyncio
async def test_news_service_stats(news_service, db_session):
    """Test news service statistics."""
    # Add some articles
    for i in range(3):
        article = NewsArticleDB(
            source="rss",
            title=f"Article {i}",
            content=f"Content {i}",
            url=f"https://example.com/{i}",
            content_hash=f"hash{i}",
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(article)
    db_session.commit()
    
    stats = news_service.get_stats()
    
    assert stats.total_articles == 3
    assert stats.articles_by_source["rss"] == 3


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ingest_article_database_error(news_service, sample_article):
    """Test error handling during article ingestion."""
    # Mock the database add to raise an exception
    from unittest.mock import patch
    
    with patch.object(news_service.db, 'add', side_effect=Exception("Database error")):
        article_id = await news_service.ingest_article(sample_article)
        
        assert article_id is None
        assert news_service.stats["errors"] > 0


@pytest.mark.asyncio
async def test_rss_handler_network_error():
    """Test RSS handler handles network errors gracefully."""
    handler = RSSFeedHandler()
    
    with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
        articles = await handler.fetch_articles()
        assert articles == []


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_ingestion_cycle(news_service):
    """Test a complete ingestion cycle."""
    with patch.object(news_service.rss_handler, "fetch_articles", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = [
            NewsArticleCreate(
                source="rss",
                title="Test Article",
                content="Test content",
                url="https://example.com/test",
                published_at=datetime.now(timezone.utc),
            )
        ]
        
        results = await news_service.run_ingestion_cycle()
        
        assert results["total"] >= 1
        assert results["rss"] >= 1
