"""
RSS Feed Handler for news ingestion.

This module handles fetching and parsing RSS feeds from configured sources.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List
import feedparser
import httpx

from ..models import NewsArticleCreate

log = logging.getLogger(__name__)


class RSSFeedHandler:
    """Handler for RSS feed ingestion."""
    
    def __init__(self):
        # Get RSS feeds from environment variable
        feeds_str = os.getenv("RSS_FEEDS", "")
        self.feeds = [f.strip() for f in feeds_str.split(",") if f.strip()]
        
        # Default feeds if none configured
        if not self.feeds:
            self.feeds = [
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
                "https://feeds.reuters.com/reuters/businessNews",
            ]
        
        log.info(f"RSS handler initialized with {len(self.feeds)} feeds")
    
    async def fetch_articles(self, max_per_feed: int = 10) -> List[NewsArticleCreate]:
        """
        Fetch articles from all configured RSS feeds.
        
        Args:
            max_per_feed: Maximum number of articles to fetch per feed
        
        Returns:
            List of NewsArticleCreate objects
        """
        articles = []
        
        for feed_url in self.feeds:
            try:
                feed_articles = await self._fetch_feed(feed_url, max_per_feed)
                articles.extend(feed_articles)
                log.debug(f"Fetched {len(feed_articles)} articles from {feed_url}")
            except Exception as e:
                log.error(f"Error fetching RSS feed {feed_url}: {e}")
        
        log.info(f"Fetched {len(articles)} total articles from {len(self.feeds)} RSS feeds")
        return articles
    
    async def _fetch_feed(self, feed_url: str, max_articles: int) -> List[NewsArticleCreate]:
        """
        Fetch and parse a single RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            max_articles: Maximum number of articles to return
        
        Returns:
            List of NewsArticleCreate objects
        """
        articles = []
        
        try:
            # Fetch feed with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                feed_content = response.text
            
            # Parse feed
            feed = feedparser.parse(feed_content)
            
            # Process entries
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._parse_entry(entry, feed_url)
                    if article:
                        articles.append(article)
                except Exception as e:
                    log.debug(f"Error parsing RSS entry: {e}")
        
        except Exception as e:
            log.error(f"Error fetching RSS feed {feed_url}: {e}")
        
        return articles
    
    def _parse_entry(self, entry, feed_url: str) -> NewsArticleCreate:
        """
        Parse a single RSS entry into a NewsArticleCreate object.
        
        Args:
            entry: feedparser entry object
            feed_url: URL of the source feed
        
        Returns:
            NewsArticleCreate object
        """
        # Extract title
        title = entry.get("title", "").strip()
        if not title:
            return None
        
        # Extract URL
        url = entry.get("link", "").strip()
        if not url:
            return None
        
        # Extract content/summary
        content = entry.get("summary", "") or entry.get("description", "")
        if content:
            # Remove HTML tags
            import re
            content = re.sub(r'<[^>]+>', '', content).strip()
        
        # Extract author
        author = entry.get("author", "") or entry.get("dc:creator", "")
        
        # Extract published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except:
                pass
        
        if not published_at:
            published_at = datetime.now(timezone.utc)
        
        # Create metadata
        metadata = {
            "feed_url": feed_url,
            "feed_title": entry.get("source", {}).get("title", ""),
        }
        
        return NewsArticleCreate(
            source="rss",
            title=title,
            content=content,
            url=url,
            author=author,
            metadata=metadata,
            published_at=published_at,
        )
