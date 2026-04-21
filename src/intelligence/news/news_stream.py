"""
News Stream Service - Main service for news ingestion.

This service coordinates news ingestion from multiple sources (RSS, Twitter, Telegram),
handles deduplication, and stores articles in the database.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from .models import NewsArticleCreate, NewsIngestionStats
from .deduplication import NewsDeduplicator
from .sources.rss import RSSFeedHandler
from .sources.twitter import TwitterHandler
from .sources.telegram import TelegramHandler

log = logging.getLogger(__name__)


class NewsStreamService:
    """Main service for news ingestion and processing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.deduplicator = NewsDeduplicator(db)
        
        # Initialize source handlers
        self.rss_handler = RSSFeedHandler()
        self.twitter_handler = TwitterHandler()
        self.telegram_handler = TelegramHandler()
        
        # Statistics
        self.stats = {
            "total_ingested": 0,
            "duplicates_detected": 0,
            "errors": 0,
            "by_source": {"rss": 0, "twitter": 0, "telegram": 0},
        }
    
    async def ingest_article(self, article: NewsArticleCreate) -> Optional[str]:
        """
        Ingest a single news article.
        
        Returns:
            Optional[str]: Article ID if ingested, None if duplicate or error
        """
        try:
            # Check for duplicates
            is_duplicate, reason = self.deduplicator.is_duplicate(article)
            if is_duplicate:
                self.stats["duplicates_detected"] += 1
                log.debug(f"Skipping duplicate article: {article.title[:50]}... (reason: {reason})")
                return None
            
            # Generate content hash
            content_hash = article.generate_content_hash()
            
            # Store in database
            from src.data.models import NewsArticle as NewsArticleDB
            
            db_article = NewsArticleDB(
                source=article.source,
                title=article.title,
                content=article.content,
                url=article.url,
                author=article.author,
                meta=article.metadata,  # Use 'meta' attribute which maps to 'metadata' column
                content_hash=content_hash,
                published_at=article.published_at,
                created_at=datetime.utcnow(),
            )
            
            self.db.add(db_article)
            self.db.commit()
            self.db.refresh(db_article)
            
            # Mark as seen in deduplicator
            self.deduplicator.mark_as_seen(article.url, content_hash)
            
            # Update stats
            self.stats["total_ingested"] += 1
            self.stats["by_source"][article.source] = self.stats["by_source"].get(article.source, 0) + 1
            
            log.info(f"Ingested article: {article.title[:50]}... from {article.source}")
            return str(db_article.id)
        
        except Exception as e:
            self.stats["errors"] += 1
            log.error(f"Error ingesting article: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    async def ingest_from_rss(self) -> int:
        """
        Ingest articles from RSS feeds.
        
        Returns:
            int: Number of articles ingested
        """
        try:
            articles = await self.rss_handler.fetch_articles()
            ingested = 0
            
            for article in articles:
                article_id = await self.ingest_article(article)
                if article_id:
                    ingested += 1
            
            log.info(f"RSS ingestion complete: {ingested} new articles")
            return ingested
        
        except Exception as e:
            log.error(f"Error in RSS ingestion: {e}", exc_info=True)
            return 0
    
    async def ingest_from_twitter(self) -> int:
        """
        Ingest articles from Twitter.
        
        Returns:
            int: Number of articles ingested
        """
        try:
            if not self.twitter_handler.is_enabled():
                log.debug("Twitter handler is disabled")
                return 0
            
            articles = await self.twitter_handler.fetch_articles()
            ingested = 0
            
            for article in articles:
                article_id = await self.ingest_article(article)
                if article_id:
                    ingested += 1
            
            log.info(f"Twitter ingestion complete: {ingested} new articles")
            return ingested
        
        except Exception as e:
            log.error(f"Error in Twitter ingestion: {e}", exc_info=True)
            return 0
    
    async def ingest_from_telegram(self) -> int:
        """
        Ingest articles from Telegram.
        
        Returns:
            int: Number of articles ingested
        """
        try:
            if not self.telegram_handler.is_enabled():
                log.debug("Telegram handler is disabled")
                return 0
            
            articles = await self.telegram_handler.fetch_articles()
            ingested = 0
            
            for article in articles:
                article_id = await self.ingest_article(article)
                if article_id:
                    ingested += 1
            
            log.info(f"Telegram ingestion complete: {ingested} new articles")
            return ingested
        
        except Exception as e:
            log.error(f"Error in Telegram ingestion: {e}", exc_info=True)
            return 0
    
    async def run_ingestion_cycle(self) -> dict:
        """
        Run a complete ingestion cycle from all sources.
        
        Returns:
            dict: Statistics for this cycle
        """
        log.info("Starting news ingestion cycle")
        
        # Run all sources concurrently
        results = await asyncio.gather(
            self.ingest_from_rss(),
            self.ingest_from_twitter(),
            self.ingest_from_telegram(),
            return_exceptions=True
        )
        
        rss_count = results[0] if not isinstance(results[0], Exception) else 0
        twitter_count = results[1] if not isinstance(results[1], Exception) else 0
        telegram_count = results[2] if not isinstance(results[2], Exception) else 0
        
        total = rss_count + twitter_count + telegram_count
        
        log.info(f"Ingestion cycle complete: {total} articles (RSS: {rss_count}, Twitter: {twitter_count}, Telegram: {telegram_count})")
        
        return {
            "total": total,
            "rss": rss_count,
            "twitter": twitter_count,
            "telegram": telegram_count,
        }
    
    def get_stats(self) -> NewsIngestionStats:
        """Get ingestion statistics."""
        try:
            from src.data.models import NewsArticle as NewsArticleDB
            from sqlalchemy import func, select
            from datetime import timedelta
            
            # Get total articles
            total = self.db.execute(
                select(func.count(NewsArticleDB.id))
            ).scalar() or 0
            
            # Get articles by source
            by_source = {}
            for source in ["rss", "twitter", "telegram"]:
                count = self.db.execute(
                    select(func.count(NewsArticleDB.id))
                    .where(NewsArticleDB.source == source)
                ).scalar() or 0
                by_source[source] = count
            
            # Get articles in last hour
            last_hour = self.db.execute(
                select(func.count(NewsArticleDB.id))
                .where(NewsArticleDB.created_at >= datetime.utcnow() - timedelta(hours=1))
            ).scalar() or 0
            
            # Get articles in last 24 hours
            last_24h = self.db.execute(
                select(func.count(NewsArticleDB.id))
                .where(NewsArticleDB.created_at >= datetime.utcnow() - timedelta(hours=24))
            ).scalar() or 0
            
            # Get last ingestion time
            last_article = self.db.execute(
                select(NewsArticleDB.created_at)
                .order_by(NewsArticleDB.created_at.desc())
                .limit(1)
            ).scalar()
            
            return NewsIngestionStats(
                total_articles=total,
                articles_by_source=by_source,
                articles_last_hour=last_hour,
                articles_last_24h=last_24h,
                duplicates_detected=self.stats["duplicates_detected"],
                errors=self.stats["errors"],
                last_ingestion_at=last_article,
            )
        
        except Exception as e:
            log.error(f"Error getting stats: {e}")
            return NewsIngestionStats(
                total_articles=0,
                articles_by_source={},
                articles_last_hour=0,
                articles_last_24h=0,
                duplicates_detected=self.stats["duplicates_detected"],
                errors=self.stats["errors"],
                last_ingestion_at=None,
            )
