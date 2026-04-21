"""
News classification using Claude API with caching and error handling.

This module provides news article classification using Anthropic's Claude API.
It includes Redis caching, retry logic, and comprehensive error handling.
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
import hashlib
import json
import os
from datetime import datetime, timedelta
import anthropic
from anthropic import AsyncAnthropic
import redis.asyncio as redis

log = logging.getLogger(__name__)


class NewsClassifier:
    """
    Classify news articles using Claude API with caching and error handling.
    
    Features:
    - Claude API integration for sentiment analysis
    - Redis caching to avoid re-classifying articles
    - Exponential backoff retry logic
    - Comprehensive error handling
    - Batch classification support
    - Trading signal generation
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        redis_url: Optional[str] = None,
        cache_ttl: int = 86400,  # 24 hours
        max_retries: int = 3,
        timeout: float = 5.0,
    ):
        """
        Initialize the news classifier.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            cache_ttl: Cache TTL in seconds (default: 24 hours)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Initialize Redis cache
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Classification prompt template
        self.classification_prompt = """Analyze the following news article and provide a trading sentiment classification.

Title: {title}
Content: {content}
Source: {source}

Provide your analysis in the following JSON format:
{{
  "sentiment": "bullish" | "bearish" | "neutral",
  "confidence": <float between 0 and 1>,
  "rationale": "<brief explanation>",
  "relevant_assets": ["<asset1>", "<asset2>", ...],
  "key_topics": ["<topic1>", "<topic2>", ...]
}}

Guidelines:
- sentiment: "bullish" for positive market impact, "bearish" for negative, "neutral" for no clear direction
- confidence: 0.0 to 1.0, where 1.0 is highest confidence
- rationale: Brief explanation (1-2 sentences) of why you chose this sentiment
- relevant_assets: List of assets/markets this news affects (e.g., ["BTC", "ETH", "SPY"])
- key_topics: Main topics covered (e.g., ["regulation", "adoption", "earnings"])

Respond ONLY with the JSON object, no additional text."""
    
    def _generate_cache_key(self, article: Dict[str, str]) -> str:
        """Generate cache key from article content."""
        content = f"{article.get('title', '')}|{article.get('content', '')}|{article.get('url', '')}"
        return f"news_classification:{hashlib.sha256(content.encode()).hexdigest()}"
    
    async def _get_cached_classification(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve classification from cache."""
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                log.debug(f"Cache hit for {cache_key}")
                return json.loads(cached)
        except Exception as e:
            log.warning(f"Cache retrieval error: {e}")
        return None
    
    async def _cache_classification(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Store classification in cache."""
        try:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result)
            )
            log.debug(f"Cached classification for {cache_key}")
        except Exception as e:
            log.warning(f"Cache storage error: {e}")
    
    async def _call_claude_api(self, prompt: str, attempt: int = 1) -> Dict[str, Any]:
        """
        Call Claude API with retry logic.
        
        Args:
            prompt: The classification prompt
            attempt: Current attempt number
            
        Returns:
            Classification result
            
        Raises:
            Exception: If all retries fail
        """
        try:
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.0,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=self.timeout,
            )
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            
            # Try to parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                    result = json.loads(response_text)
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                    result = json.loads(response_text)
                else:
                    raise
            
            # Validate result structure
            required_fields = ["sentiment", "confidence", "rationale"]
            if not all(field in result for field in required_fields):
                raise ValueError(f"Missing required fields in response: {result}")
            
            # Validate sentiment value
            if result["sentiment"] not in ["bullish", "bearish", "neutral"]:
                raise ValueError(f"Invalid sentiment value: {result['sentiment']}")
            
            # Validate confidence range
            if not (0.0 <= result["confidence"] <= 1.0):
                raise ValueError(f"Confidence out of range: {result['confidence']}")
            
            return result
        
        except anthropic.RateLimitError as e:
            log.warning(f"Rate limit error (attempt {attempt}/{self.max_retries}): {e}")
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(wait_time)
                return await self._call_claude_api(prompt, attempt + 1)
            raise
        
        except anthropic.APITimeoutError as e:
            log.warning(f"Timeout error (attempt {attempt}/{self.max_retries}): {e}")
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                return await self._call_claude_api(prompt, attempt + 1)
            raise
        
        except anthropic.APIError as e:
            log.error(f"Claude API error (attempt {attempt}/{self.max_retries}): {e}")
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                return await self._call_claude_api(prompt, attempt + 1)
            raise
        
        except Exception as e:
            log.error(f"Unexpected error in Claude API call: {e}", exc_info=True)
            raise
    
    async def classify(self, article: Dict[str, str]) -> Dict[str, Any]:
        """
        Classify a single news article.
        
        Args:
            article: Dictionary with title, content, source, url
            
        Returns:
            Classification result with sentiment, confidence, rationale, and signals
            
        Example:
            {
                "sentiment": "bullish",
                "confidence": 0.85,
                "rationale": "Positive earnings report exceeds expectations",
                "relevant_assets": ["AAPL", "TECH"],
                "key_topics": ["earnings", "revenue"],
                "signals": [
                    {
                        "asset": "AAPL",
                        "direction": "long",
                        "confidence": 0.85,
                        "rationale": "Strong earnings beat"
                    }
                ],
                "classified_at": "2024-01-15T12:00:00Z"
            }
        """
        start_time = datetime.utcnow()
        cache_hit = False
        
        # Check cache first
        cache_key = self._generate_cache_key(article)
        cached_result = await self._get_cached_classification(cache_key)
        if cached_result:
            cache_hit = True
            
            # Record metrics
            from src.intelligence.classification_monitor import record_classification
            record_classification(
                sentiment=cached_result.get("sentiment", "neutral"),
                confidence=cached_result.get("confidence", 0.0),
                latency_ms=cached_result.get("latency_ms", 0),
                signals_count=len(cached_result.get("signals", [])),
                cache_hit=True,
                error=False,
            )
            
            return cached_result
        
        try:
            # Prepare prompt
            prompt = self.classification_prompt.format(
                title=article.get("title", ""),
                content=article.get("content", "")[:2000],  # Limit content length
                source=article.get("source", "unknown"),
            )
            
            # Call Claude API
            result = await self._call_claude_api(prompt)
            
            # Generate trading signals
            signals = self._generate_signals(result)
            result["signals"] = signals
            
            # Add metadata
            result["classified_at"] = datetime.utcnow().isoformat()
            result["latency_ms"] = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Cache result
            await self._cache_classification(cache_key, result)
            
            # Record metrics
            from src.intelligence.classification_monitor import record_classification
            record_classification(
                sentiment=result["sentiment"],
                confidence=result["confidence"],
                latency_ms=result["latency_ms"],
                signals_count=len(signals),
                cache_hit=False,
                error=False,
            )
            
            log.info(
                f"Classified article: {article.get('title', '')[:50]}... "
                f"sentiment={result['sentiment']}, confidence={result['confidence']:.2f}, "
                f"latency={result['latency_ms']}ms"
            )
            
            return result
        
        except Exception as e:
            log.error(f"Classification failed for article: {e}", exc_info=True)
            
            # Record error metrics
            from src.intelligence.classification_monitor import record_classification
            record_classification(
                sentiment="neutral",
                confidence=0.0,
                latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                signals_count=0,
                cache_hit=False,
                error=True,
            )
            
            # Return neutral classification on error
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "rationale": f"Classification failed: {str(e)}",
                "relevant_assets": [],
                "key_topics": [],
                "signals": [],
                "classified_at": datetime.utcnow().isoformat(),
                "error": str(e),
            }
    
    def _generate_signals(self, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals from classification result.
        
        Args:
            classification: Classification result from Claude
            
        Returns:
            List of trading signals
        """
        signals = []
        
        sentiment = classification.get("sentiment")
        confidence = classification.get("confidence", 0.0)
        relevant_assets = classification.get("relevant_assets", [])
        rationale = classification.get("rationale", "")
        
        # Only generate signals for non-neutral sentiment with sufficient confidence
        if sentiment != "neutral" and confidence >= 0.6:
            direction = "long" if sentiment == "bullish" else "short"
            
            for asset in relevant_assets:
                signals.append({
                    "asset": asset,
                    "direction": direction,
                    "confidence": confidence,
                    "rationale": rationale,
                    "source": "news_classification",
                })
        
        return signals
    
    async def classify_batch(self, articles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Classify multiple articles in batch.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            List of classification results
        """
        tasks = [self.classify(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Batch classification error for article {i}: {result}")
                processed_results.append({
                    "sentiment": "neutral",
                    "confidence": 0.0,
                    "rationale": f"Classification failed: {str(result)}",
                    "relevant_assets": [],
                    "key_topics": [],
                    "signals": [],
                    "classified_at": datetime.utcnow().isoformat(),
                    "error": str(result),
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def close(self):
        """Close connections."""
        await self.redis_client.close()
