"""
Claude classification engine — replaces probability estimation with direction classification.
Asks "does this news confirm or deny the market question?" instead of "what's the probability?"

Adapted from Polymarket Pipeline for unified trading platform.
"""
from __future__ import annotations

import json
import time
import logging
import os
from dataclasses import dataclass
from typing import Optional
import asyncio

import anthropic

log = logging.getLogger(__name__)

# Load API key from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "claude-3-5-sonnet-20241022")

CLASSIFICATION_PROMPT = """You are a news classifier for prediction markets and trading.

## Market Question
{question}

## Current Market Price
YES: {yes_price:.2f} (implied probability: {yes_price:.0%})

## Breaking News
{headline}
Source: {source}

## Task
Does this news make the market question MORE likely to resolve YES, MORE likely to resolve NO, or is it NOT RELEVANT?

Also rate the MATERIALITY — how much should this move the price? 0.0 means no impact, 1.0 means this is definitive evidence.

Respond with ONLY valid JSON:
{{
  "direction": "bullish" | "bearish" | "neutral",
  "materiality": <float 0.0 to 1.0>,
  "reasoning": "<1 sentence>"
}}"""


@dataclass
class Classification:
    """Result of news classification."""
    direction: str  # "bullish", "bearish", "neutral"
    materiality: float  # 0.0-1.0
    reasoning: str
    latency_ms: int
    model: str
    confidence: float = 0.0  # 0.0-1.0 based on materiality


class NewsClassifier:
    """Claude-powered news classifier with caching support."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, cache=None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or CLASSIFICATION_MODEL
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        self.cache = cache  # Optional Redis cache
        self.stats = {"total": 0, "cached": 0, "errors": 0}

    def _cache_key(self, headline: str, question: str) -> str:
        """Generate cache key for classification."""
        import hashlib
        key_str = f"{headline}:{question}"
        return f"news_class:{hashlib.md5(key_str.encode()).hexdigest()}"

    def classify(
        self,
        headline: str,
        question: str,
        yes_price: float = 0.5,
        source: str = "unknown",
    ) -> Classification:
        """Classify a news headline against a market question. Synchronous."""
        if not self.client:
            log.error("No Anthropic API key configured")
            return Classification(
                direction="neutral",
                materiality=0.0,
                reasoning="API not configured",
                latency_ms=0,
                model=self.model,
                confidence=0.0,
            )

        self.stats["total"] += 1
        start = time.time()

        # Check cache
        cache_key = self._cache_key(headline, question)
        if self.cache:
            try:
                cached = self.cache.get(cache_key)
                if cached:
                    self.stats["cached"] += 1
                    latency = int((time.time() - start) * 1000)
                    result = json.loads(cached)
                    result["latency_ms"] = latency
                    result["cached"] = True
                    return Classification(**result)
            except Exception as e:
                log.debug(f"Cache lookup failed: {e}")

        prompt = CLASSIFICATION_PROMPT.format(
            question=question,
            yes_price=yes_price,
            headline=headline,
            source=source,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            latency = int((time.time() - start) * 1000)

            direction = result.get("direction", "neutral")
            if direction not in ("bullish", "bearish", "neutral"):
                direction = "neutral"

            materiality = max(0.0, min(1.0, float(result.get("materiality", 0))))
            confidence = materiality  # Use materiality as confidence

            classification = Classification(
                direction=direction,
                materiality=materiality,
                reasoning=result.get("reasoning", ""),
                latency_ms=latency,
                model=self.model,
                confidence=confidence,
            )

            # Cache result (60 second TTL)
            if self.cache:
                try:
                    cache_data = {
                        "direction": classification.direction,
                        "materiality": classification.materiality,
                        "reasoning": classification.reasoning,
                        "model": classification.model,
                        "confidence": classification.confidence,
                    }
                    self.cache.setex(cache_key, 60, json.dumps(cache_data))
                except Exception as e:
                    log.debug(f"Cache write failed: {e}")

            return classification

        except Exception as e:
            self.stats["errors"] += 1
            latency = int((time.time() - start) * 1000)
            log.warning(f"[classifier] Error: {e}")
            return Classification(
                direction="neutral",
                materiality=0.0,
                reasoning=f"Classification error: {type(e).__name__}",
                latency_ms=latency,
                model=self.model,
                confidence=0.0,
            )

    async def classify_async(
        self,
        headline: str,
        question: str,
        yes_price: float = 0.5,
        source: str = "unknown",
    ) -> Classification:
        """Async wrapper around classify()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.classify, headline, question, yes_price, source
        )

    def get_stats(self) -> dict:
        """Get classifier statistics."""
        return self.stats.copy()


# Global classifier instance
_classifier: Optional[NewsClassifier] = None


def get_classifier(cache=None) -> NewsClassifier:
    """Get or create global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = NewsClassifier(cache=cache)
    return _classifier


def classify(
    headline: str,
    question: str,
    yes_price: float = 0.5,
    source: str = "unknown",
) -> Classification:
    """Classify a news headline (convenience function)."""
    classifier = get_classifier()
    return classifier.classify(headline, question, yes_price, source)


async def classify_async(
    headline: str,
    question: str,
    yes_price: float = 0.5,
    source: str = "unknown",
) -> Classification:
    """Classify a news headline asynchronously (convenience function)."""
    classifier = get_classifier()
    return await classifier.classify_async(headline, question, yes_price, source)
