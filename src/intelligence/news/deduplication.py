"""
News deduplication logic.

This module handles deduplication of news articles based on content hash and URL.
"""

import logging
from typing import Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import NewsArticleCreate

log = logging.getLogger(__name__)


class NewsDeduplicator:
    """Handles deduplication of news articles."""
    
    def __init__(self, db: Session):
        self.db = db
        self._url_cache: Set[str] = set()
        self._hash_cache: Set[str] = set()
        self._cache_loaded = False
    
    def _load_cache(self):
        """Load recent URLs and hashes into memory cache."""
        if self._cache_loaded:
            return
        
        try:
            # Import here to avoid circular dependency
            from src.data.models import NewsArticle as NewsArticleDB
            
            # Load articles from last 7 days
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            recent_articles = self.db.execute(
                select(NewsArticleDB.url, NewsArticleDB.content_hash)
                .where(NewsArticleDB.created_at >= cutoff)
            ).all()
            
            for url, content_hash in recent_articles:
                self._url_cache.add(url)
                self._hash_cache.add(content_hash)
            
            self._cache_loaded = True
            log.info(f"Loaded {len(self._url_cache)} URLs and {len(self._hash_cache)} hashes into cache")
        
        except Exception as e:
            log.error(f"Failed to load deduplication cache: {e}")
            self._cache_loaded = True  # Prevent repeated failures
    
    def is_duplicate(self, article: NewsArticleCreate) -> tuple[bool, Optional[str]]:
        """
        Check if an article is a duplicate.
        
        Returns:
            tuple: (is_duplicate, reason)
        """
        self._load_cache()
        
        # Check URL
        if article.url in self._url_cache:
            log.debug(f"Duplicate URL detected: {article.url}")
            return True, "duplicate_url"
        
        # Check content hash
        content_hash = article.generate_content_hash()
        if content_hash in self._hash_cache:
            log.debug(f"Duplicate content hash detected: {content_hash[:16]}...")
            return True, "duplicate_content"
        
        # Check database for URL (in case cache is stale)
        try:
            from src.data.models import NewsArticle as NewsArticleDB
            
            existing = self.db.execute(
                select(NewsArticleDB.id)
                .where(NewsArticleDB.url == article.url)
                .limit(1)
            ).first()
            
            if existing:
                self._url_cache.add(article.url)
                log.debug(f"Duplicate URL found in database: {article.url}")
                return True, "duplicate_url_db"
            
            # Check database for content hash
            existing_hash = self.db.execute(
                select(NewsArticleDB.id)
                .where(NewsArticleDB.content_hash == content_hash)
                .limit(1)
            ).first()
            
            if existing_hash:
                self._hash_cache.add(content_hash)
                log.debug(f"Duplicate content hash found in database: {content_hash[:16]}...")
                return True, "duplicate_content_db"
        
        except Exception as e:
            log.error(f"Error checking database for duplicates: {e}")
            # Continue anyway - better to have a duplicate than miss an article
        
        return False, None
    
    def mark_as_seen(self, url: str, content_hash: str):
        """Mark an article as seen by adding to cache."""
        self._url_cache.add(url)
        self._hash_cache.add(content_hash)
        
        # Trim cache if it gets too large (keep last 10,000 entries)
        if len(self._url_cache) > 10000:
            self._url_cache = set(list(self._url_cache)[-5000:])
        if len(self._hash_cache) > 10000:
            self._hash_cache = set(list(self._hash_cache)[-5000:])
    
    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        try:
            from src.data.models import NewsArticle as NewsArticleDB
            
            total = self.db.execute(
                select(func.count(NewsArticleDB.id))
            ).scalar()
            
            last_24h = self.db.execute(
                select(func.count(NewsArticleDB.id))
                .where(NewsArticleDB.created_at >= datetime.utcnow() - timedelta(hours=24))
            ).scalar()
            
            return {
                "total_articles": total or 0,
                "articles_last_24h": last_24h or 0,
                "cache_urls": len(self._url_cache),
                "cache_hashes": len(self._hash_cache),
            }
        except Exception as e:
            log.error(f"Error getting deduplication stats: {e}")
            return {
                "total_articles": 0,
                "articles_last_24h": 0,
                "cache_urls": len(self._url_cache),
                "cache_hashes": len(self._hash_cache),
            }
