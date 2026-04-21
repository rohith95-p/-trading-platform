"""
Real-time news monitor — event-driven architecture.
Sources: Twitter API v2 filtered stream, Telegram channels, RSS fallback.
Emits NewsEvent objects into an asyncio queue as breaking news arrives.

Adapted from Polymarket Pipeline for unified trading platform.
"""
from __future__ import annotations

import asyncio
import time
import logging
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

import httpx

log = logging.getLogger(__name__)


@dataclass
class NewsEvent:
    """Represents a news event from any source."""
    headline: str
    source: str  # "twitter", "telegram", "rss"
    url: str
    received_at: datetime
    published_at: datetime
    summary: str = ""
    raw_data: dict = field(default_factory=dict)
    latency_ms: int = 0  # time from publication to our receipt

    def age_seconds(self) -> float:
        """Get age of news event in seconds."""
        return (datetime.now(timezone.utc) - self.received_at).total_seconds()


class TwitterStream:
    """Twitter API v2 filtered stream for real-time keyword monitoring."""

    def __init__(self, bearer_token: Optional[str] = None, keywords: Optional[list[str]] = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN", "")
        self.keywords = keywords or os.getenv("TWITTER_KEYWORDS", "").split(",")
        self.base_url = "https://api.twitter.com/2"
        self.enabled = bool(self.bearer_token and self.keywords)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    async def setup_rules(self):
        """Set up filtered stream rules based on keywords."""
        if not self.enabled:
            return

        try:
            async with httpx.AsyncClient() as client:
                # Get existing rules
                resp = await client.get(
                    f"{self.base_url}/tweets/search/stream/rules",
                    headers=self._headers(),
                    timeout=10,
                )
                existing = resp.json().get("data", [])

                # Delete existing rules
                if existing:
                    ids = [r["id"] for r in existing]
                    await client.post(
                        f"{self.base_url}/tweets/search/stream/rules",
                        headers=self._headers(),
                        json={"delete": {"ids": ids}},
                        timeout=10,
                    )

                # Create new rules from keywords (max 25 chars per rule for Basic)
                rules = []
                # Batch keywords into OR groups
                batch_size = 5
                for i in range(0, len(self.keywords), batch_size):
                    batch = self.keywords[i:i + batch_size]
                    value = " OR ".join(f'"{kw}"' for kw in batch)
                    rules.append({"value": value, "tag": f"batch_{i // batch_size}"})

                if rules:
                    await client.post(
                        f"{self.base_url}/tweets/search/stream/rules",
                        headers=self._headers(),
                        json={"add": rules[:5]},  # Basic tier: 5 rules max
                        timeout=10,
                    )
        except Exception as e:
            log.warning(f"[twitter] Failed to setup rules: {e}")

    async def stream(self, queue: asyncio.Queue):
        """Connect to filtered stream and emit NewsEvents."""
        if not self.enabled:
            log.info("[twitter] No bearer token — stream disabled")
            return

        try:
            await self.setup_rules()
        except Exception as e:
            log.warning(f"[twitter] Failed to setup rules: {e}")
            return

        backoff = 1
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "GET",
                        f"{self.base_url}/tweets/search/stream",
                        headers=self._headers(),
                        params={"tweet.fields": "created_at,author_id,text"},
                        timeout=None,
                    ) as resp:
                        backoff = 1
                        async for line in resp.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                import json
                                data = json.loads(line)
                                tweet = data.get("data", {})
                                text = tweet.get("text", "")
                                created = tweet.get("created_at", "")

                                now = datetime.now(timezone.utc)
                                try:
                                    pub = datetime.fromisoformat(created.replace("Z", "+00:00"))
                                    latency = int((now - pub).total_seconds() * 1000)
                                except (ValueError, AttributeError):
                                    pub = now
                                    latency = 0

                                event = NewsEvent(
                                    headline=text[:280],
                                    source="twitter",
                                    url=f"https://twitter.com/i/status/{tweet.get('id', '')}",
                                    received_at=now,
                                    published_at=pub,
                                    latency_ms=latency,
                                    raw_data=data,
                                )
                                await queue.put(event)
                            except Exception as e:
                                log.debug(f"[twitter] Parse error: {e}")

            except (httpx.HTTPError, Exception) as e:
                log.warning(f"[twitter] Stream error: {e}, reconnecting in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)


class TelegramMonitor:
    """Monitor Telegram channels via Bot API long polling."""

    def __init__(self, bot_token: Optional[str] = None, channel_ids: Optional[list[str]] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.channel_ids = channel_ids or os.getenv("TELEGRAM_CHANNEL_IDS", "").split(",")
        self.enabled = bool(self.bot_token and self.channel_ids)
        self.last_update_id = 0

    async def stream(self, queue: asyncio.Queue):
        """Poll for new messages and emit NewsEvents."""
        if not self.enabled:
            log.info("[telegram] No bot token or channels — monitor disabled")
            return

        base_url = f"https://api.telegram.org/bot{self.bot_token}"

        while True:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{base_url}/getUpdates",
                        params={"offset": self.last_update_id + 1, "timeout": 30},
                        timeout=35,
                    )
                    data = resp.json()

                for update in data.get("result", []):
                    self.last_update_id = update["update_id"]
                    msg = update.get("channel_post") or update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = str(msg.get("chat", {}).get("id", ""))

                    if not text or (self.channel_ids and chat_id not in self.channel_ids):
                        continue

                    now = datetime.now(timezone.utc)
                    msg_date = msg.get("date", 0)
                    pub = datetime.fromtimestamp(msg_date, tz=timezone.utc) if msg_date else now
                    latency = int((now - pub).total_seconds() * 1000)

                    event = NewsEvent(
                        headline=text[:500],
                        source="telegram",
                        url="",
                        received_at=now,
                        published_at=pub,
                        latency_ms=latency,
                        raw_data=update,
                    )
                    await queue.put(event)

            except Exception as e:
                log.warning(f"[telegram] Error: {e}")
                await asyncio.sleep(5)


class RSSFallback:
    """Periodic RSS scraping as a fallback news source."""

    def __init__(self, interval_seconds: float = 120):
        self.interval = interval_seconds
        self._seen_headlines: set[str] = set()

    async def stream(self, queue: asyncio.Queue):
        """Poll RSS feeds periodically and emit new headlines."""
        while True:
            try:
                # Import feedparser for RSS parsing
                import feedparser
                
                # Default RSS feeds for trading/crypto news
                feeds = [
                    "https://feeds.bloomberg.com/markets/news.rss",
                    "https://feeds.cnbc.com/cnbc/financialnews",
                    "https://feeds.reuters.com/reuters/businessNews",
                ]
                
                now = datetime.now(timezone.utc)
                new_count = 0

                for feed_url in feeds:
                    try:
                        feed = feedparser.parse(feed_url)
                        for entry in feed.entries[:10]:  # Last 10 entries
                            headline = entry.get("title", "")
                            url = entry.get("link", "")
                            summary = entry.get("summary", "")
                            
                            key = headline.lower()[:80]
                            if key in self._seen_headlines:
                                continue
                            
                            self._seen_headlines.add(key)
                            new_count += 1

                            # Parse published date
                            try:
                                pub_date = entry.get("published_parsed")
                                if pub_date:
                                    pub = datetime(*pub_date[:6], tzinfo=timezone.utc)
                                else:
                                    pub = now
                            except:
                                pub = now

                            latency = int((now - pub).total_seconds() * 1000)

                            event = NewsEvent(
                                headline=headline,
                                source="rss",
                                url=url,
                                received_at=now,
                                published_at=pub,
                                summary=summary,
                                latency_ms=latency,
                            )
                            await queue.put(event)
                    except Exception as e:
                        log.debug(f"[rss] Feed error for {feed_url}: {e}")

                if new_count:
                    log.info(f"[rss] {new_count} new headlines")

                # Trim seen cache
                if len(self._seen_headlines) > 5000:
                    self._seen_headlines = set(list(self._seen_headlines)[-2000:])

            except Exception as e:
                log.warning(f"[rss] Error: {e}")

            await asyncio.sleep(self.interval)


class NewsAggregator:
    """Runs all news sources concurrently, deduplicates, emits to output queue."""

    def __init__(self, output_queue: asyncio.Queue):
        self.output_queue = output_queue
        self._internal_queue: asyncio.Queue = asyncio.Queue()
        self._seen: set[str] = set()

        self.twitter = TwitterStream()
        self.telegram = TelegramMonitor()
        self.rss = RSSFallback(interval_seconds=120)

        self.stats = {"twitter": 0, "telegram": 0, "rss": 0, "total": 0, "deduped": 0}

    async def run(self):
        """Start all sources and the dedup router."""
        await asyncio.gather(
            self.twitter.stream(self._internal_queue),
            self.telegram.stream(self._internal_queue),
            self.rss.stream(self._internal_queue),
            self._dedup_router(),
            return_exceptions=True,
        )

    async def _dedup_router(self):
        """Deduplicate and forward events to output queue."""
        while True:
            event = await self._internal_queue.get()
            key = event.headline.lower()[:80]
            if key in self._seen:
                self.stats["deduped"] += 1
                continue

            self._seen.add(key)
            self.stats[event.source] = self.stats.get(event.source, 0) + 1
            self.stats["total"] += 1

            await self.output_queue.put(event)

            if len(self._seen) > 10000:
                self._seen = set(list(self._seen)[-5000:])

    def get_stats(self) -> dict:
        """Get aggregator statistics."""
        return self.stats.copy()
