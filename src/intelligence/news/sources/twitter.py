"""
Twitter API Handler for news ingestion (optional).

This module handles fetching tweets from Twitter API v2.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from ..models import NewsArticleCreate

log = logging.getLogger(__name__)


class TwitterHandler:
    """Handler for Twitter API v2 ingestion."""
    
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY", "")
        self.api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "")
        
        # Keywords to search for
        keywords_str = os.getenv("TWITTER_KEYWORDS", "")
        self.keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        
        self.base_url = "https://api.twitter.com/2"
        
        if self.is_enabled():
            log.info(f"Twitter handler initialized with {len(self.keywords)} keywords")
        else:
            log.info("Twitter handler disabled (no API credentials)")
    
    def is_enabled(self) -> bool:
        """Check if Twitter handler is enabled."""
        return bool(self.bearer_token and self.keywords)
    
    async def fetch_articles(self, max_results: int = 10) -> List[NewsArticleCreate]:
        """
        Fetch recent tweets matching configured keywords.
        
        Args:
            max_results: Maximum number of tweets to fetch (10-100)
        
        Returns:
            List of NewsArticleCreate objects
        """
        if not self.is_enabled():
            return []
        
        articles = []
        
        try:
            # Build search query
            query = " OR ".join(f'"{kw}"' for kw in self.keywords)
            
            # Fetch tweets
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/tweets/search/recent",
                    headers={"Authorization": f"Bearer {self.bearer_token}"},
                    params={
                        "query": query,
                        "max_results": min(max_results, 100),
                        "tweet.fields": "created_at,author_id,text,entities",
                        "expansions": "author_id",
                        "user.fields": "username,name",
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            # Parse tweets
            tweets = data.get("data", [])
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
            
            for tweet in tweets:
                try:
                    article = self._parse_tweet(tweet, users)
                    if article:
                        articles.append(article)
                except Exception as e:
                    log.debug(f"Error parsing tweet: {e}")
            
            log.info(f"Fetched {len(articles)} tweets from Twitter")
        
        except Exception as e:
            log.error(f"Error fetching tweets: {e}")
        
        return articles
    
    def _parse_tweet(self, tweet: dict, users: dict) -> Optional[NewsArticleCreate]:
        """
        Parse a tweet into a NewsArticleCreate object.
        
        Args:
            tweet: Tweet data from API
            users: User data lookup
        
        Returns:
            NewsArticleCreate object or None
        """
        # Extract text
        text = tweet.get("text", "").strip()
        if not text:
            return None
        
        # Extract tweet ID
        tweet_id = tweet.get("id", "")
        if not tweet_id:
            return None
        
        # Build URL
        url = f"https://twitter.com/i/status/{tweet_id}"
        
        # Extract author
        author_id = tweet.get("author_id", "")
        author = None
        if author_id and author_id in users:
            user = users[author_id]
            author = f"@{user.get('username', '')} ({user.get('name', '')})"
        
        # Extract published date
        created_at_str = tweet.get("created_at", "")
        published_at = datetime.now(timezone.utc)
        if created_at_str:
            try:
                published_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except:
                pass
        
        # Create metadata
        metadata = {
            "tweet_id": tweet_id,
            "author_id": author_id,
        }
        
        return NewsArticleCreate(
            source="twitter",
            title=text[:280],  # Twitter character limit
            content=text,
            url=url,
            author=author,
            metadata=metadata,
            published_at=published_at,
        )
