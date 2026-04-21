"""
News ingestion and processing module.

This module handles news article ingestion from multiple sources (RSS, Twitter, Telegram),
deduplication, and storage.
"""

from .models import (
    NewsArticle,
    NewsArticleCreate,
    NewsArticleResponse,
    NewsArticleList,
    NewsSourceConfig,
    NewsIngestionStats,
)
from .news_stream import NewsStreamService
from .deduplication import NewsDeduplicator

__all__ = [
    "NewsArticle",
    "NewsArticleCreate",
    "NewsArticleResponse",
    "NewsArticleList",
    "NewsSourceConfig",
    "NewsIngestionStats",
    "NewsStreamService",
    "NewsDeduplicator",
]
