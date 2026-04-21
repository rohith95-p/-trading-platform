"""
Telegram Bot API Handler for news ingestion (optional).

This module handles fetching messages from Telegram channels.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from ..models import NewsArticleCreate

log = logging.getLogger(__name__)


class TelegramHandler:
    """Handler for Telegram Bot API ingestion."""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Channel IDs to monitor
        channels_str = os.getenv("TELEGRAM_CHANNEL_IDS", "")
        self.channel_ids = [c.strip() for c in channels_str.split(",") if c.strip()]
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.last_update_id = 0
        
        if self.is_enabled():
            log.info(f"Telegram handler initialized with {len(self.channel_ids)} channels")
        else:
            log.info("Telegram handler disabled (no bot token or channels)")
    
    def is_enabled(self) -> bool:
        """Check if Telegram handler is enabled."""
        return bool(self.bot_token and self.channel_ids)
    
    async def fetch_articles(self, timeout: int = 30) -> List[NewsArticleCreate]:
        """
        Fetch recent messages from configured Telegram channels.
        
        Args:
            timeout: Timeout for long polling in seconds
        
        Returns:
            List of NewsArticleCreate objects
        """
        if not self.is_enabled():
            return []
        
        articles = []
        
        try:
            # Get updates using long polling
            async with httpx.AsyncClient(timeout=timeout + 5.0) as client:
                response = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": timeout,
                        "allowed_updates": ["channel_post", "message"],
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            if not data.get("ok"):
                log.error(f"Telegram API error: {data.get('description')}")
                return []
            
            # Parse updates
            updates = data.get("result", [])
            
            for update in updates:
                self.last_update_id = update.get("update_id", self.last_update_id)
                
                try:
                    article = self._parse_update(update)
                    if article:
                        articles.append(article)
                except Exception as e:
                    log.debug(f"Error parsing Telegram update: {e}")
            
            log.info(f"Fetched {len(articles)} messages from Telegram")
        
        except Exception as e:
            log.error(f"Error fetching Telegram updates: {e}")
        
        return articles
    
    def _parse_update(self, update: dict) -> Optional[NewsArticleCreate]:
        """
        Parse a Telegram update into a NewsArticleCreate object.
        
        Args:
            update: Update data from Telegram API
        
        Returns:
            NewsArticleCreate object or None
        """
        # Get message (could be channel_post or message)
        message = update.get("channel_post") or update.get("message")
        if not message:
            return None
        
        # Extract text
        text = message.get("text", "").strip()
        if not text:
            return None
        
        # Extract chat info
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        
        # Check if this is from a monitored channel
        if self.channel_ids and chat_id not in self.channel_ids:
            return None
        
        # Extract message ID
        message_id = message.get("message_id", "")
        
        # Build URL (if channel has username)
        chat_username = chat.get("username", "")
        url = f"https://t.me/{chat_username}/{message_id}" if chat_username else f"telegram://channel/{chat_id}/{message_id}"
        
        # Extract author
        author = None
        if "from" in message:
            from_user = message["from"]
            username = from_user.get("username", "")
            first_name = from_user.get("first_name", "")
            last_name = from_user.get("last_name", "")
            author = f"@{username}" if username else f"{first_name} {last_name}".strip()
        elif "sender_chat" in message:
            sender_chat = message["sender_chat"]
            author = sender_chat.get("title", "")
        
        # Extract published date
        date_timestamp = message.get("date", 0)
        published_at = datetime.fromtimestamp(date_timestamp, tz=timezone.utc) if date_timestamp else datetime.now(timezone.utc)
        
        # Create metadata
        metadata = {
            "message_id": message_id,
            "chat_id": chat_id,
            "chat_title": chat.get("title", ""),
            "chat_username": chat_username,
        }
        
        return NewsArticleCreate(
            source="telegram",
            title=text[:500],  # Use first 500 chars as title
            content=text,
            url=url,
            author=author,
            metadata=metadata,
            published_at=published_at,
        )
