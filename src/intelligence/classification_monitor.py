"""
Monitoring and metrics for news classification.

This module tracks:
- Classification count and rate
- Average latency
- Error rate
- Cache hit rate
- Sentiment distribution
- Signal generation rate
"""

import logging
from datetime import timedelta
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import asyncio
from src.core.time import utc_now

log = logging.getLogger(__name__)


class ClassificationMonitor:
    """
    Monitor and track news classification metrics.
    
    Metrics tracked:
    - Total classifications
    - Classifications per minute
    - Average latency
    - Error rate
    - Cache hit rate
    - Sentiment distribution
    - Signals generated
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize the monitor.
        
        Args:
            window_size: Number of recent classifications to track for rolling metrics
        """
        self.window_size = window_size
        
        # Counters
        self.total_classifications = 0
        self.total_errors = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        self.total_signals_generated = 0
        
        # Sentiment distribution
        self.sentiment_counts = defaultdict(int)
        
        # Rolling window for recent classifications
        self.recent_latencies = deque(maxlen=window_size)
        self.recent_timestamps = deque(maxlen=window_size)
        self.recent_sentiments = deque(maxlen=window_size)
        
        # Start time
        self.start_time = utc_now()
    
    def record_classification(
        self,
        sentiment: str,
        confidence: float,
        latency_ms: int,
        signals_count: int,
        cache_hit: bool = False,
        error: bool = False,
    ):
        """
        Record a classification event.
        
        Args:
            sentiment: Classification sentiment (bullish/bearish/neutral)
            confidence: Confidence score [0, 1]
            latency_ms: Classification latency in milliseconds
            signals_count: Number of signals generated
            cache_hit: Whether result was from cache
            error: Whether classification failed
        """
        self.total_classifications += 1
        
        if error:
            self.total_errors += 1
        else:
            # Update sentiment distribution
            self.sentiment_counts[sentiment] += 1
            
            # Update rolling windows
            self.recent_latencies.append(latency_ms)
        self.recent_timestamps.append(utc_now())
            self.recent_sentiments.append(sentiment)
            
            # Update signals
            self.total_signals_generated += signals_count
        
        # Update cache metrics
        if cache_hit:
            self.total_cache_hits += 1
        else:
            self.total_cache_misses += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.
        
        Returns:
            Dictionary of metrics
        """
        uptime = (utc_now() - self.start_time).total_seconds()
        
        # Calculate rates
        classifications_per_minute = (self.total_classifications / uptime) * 60 if uptime > 0 else 0
        error_rate = self.total_errors / self.total_classifications if self.total_classifications > 0 else 0
        
        # Calculate cache hit rate
        total_cache_requests = self.total_cache_hits + self.total_cache_misses
        cache_hit_rate = self.total_cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        # Calculate average latency
        avg_latency = sum(self.recent_latencies) / len(self.recent_latencies) if self.recent_latencies else 0
        
        # Calculate p95 latency
        p95_latency = 0
        if self.recent_latencies:
            sorted_latencies = sorted(self.recent_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
        
        # Calculate recent classifications per minute (last 5 minutes)
        recent_rate = 0
        if self.recent_timestamps:
        five_minutes_ago = utc_now() - timedelta(minutes=5)
            recent_count = sum(1 for ts in self.recent_timestamps if ts >= five_minutes_ago)
            recent_rate = (recent_count / 5) if recent_count > 0 else 0
        
        # Sentiment distribution
        total_sentiments = sum(self.sentiment_counts.values())
        sentiment_distribution = {
            sentiment: count / total_sentiments if total_sentiments > 0 else 0
            for sentiment, count in self.sentiment_counts.items()
        }
        
        return {
            "total_classifications": self.total_classifications,
            "total_errors": self.total_errors,
            "total_signals_generated": self.total_signals_generated,
            "uptime_seconds": int(uptime),
            "classifications_per_minute": round(classifications_per_minute, 2),
            "recent_classifications_per_minute": round(recent_rate, 2),
            "error_rate": round(error_rate, 4),
            "cache_hit_rate": round(cache_hit_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "sentiment_distribution": sentiment_distribution,
            "cache_stats": {
                "hits": self.total_cache_hits,
                "misses": self.total_cache_misses,
                "total": total_cache_requests,
            },
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status based on metrics.
        
        Returns:
            Health status with warnings
        """
        metrics = self.get_metrics()
        
        warnings = []
        status = "healthy"
        
        # Check error rate
        if metrics["error_rate"] > 0.1:  # >10% error rate
            warnings.append("High error rate")
            status = "degraded"
        
        # Check latency
        if metrics["p95_latency_ms"] > 5000:  # >5 seconds
            warnings.append("High latency")
            status = "degraded"
        
        # Check cache hit rate
        if metrics["cache_hit_rate"] < 0.3:  # <30% cache hit rate
            warnings.append("Low cache hit rate")
        
        if len(warnings) > 2:
            status = "unhealthy"
        
        return {
            "status": status,
            "warnings": warnings,
            "metrics": metrics,
            "timestamp": utc_now().isoformat(),
        }
    
    def reset(self):
        """Reset all metrics."""
        self.total_classifications = 0
        self.total_errors = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        self.total_signals_generated = 0
        self.sentiment_counts.clear()
        self.recent_latencies.clear()
        self.recent_timestamps.clear()
        self.recent_sentiments.clear()
        self.start_time = utc_now()
        log.info("Classification monitor metrics reset")


# Global monitor instance
_monitor = ClassificationMonitor()


def get_monitor() -> ClassificationMonitor:
    """Get the global monitor instance."""
    return _monitor


def record_classification(
    sentiment: str,
    confidence: float,
    latency_ms: int,
    signals_count: int,
    cache_hit: bool = False,
    error: bool = False,
):
    """
    Record a classification event (convenience function).
    
    Args:
        sentiment: Classification sentiment
        confidence: Confidence score
        latency_ms: Latency in milliseconds
        signals_count: Number of signals generated
        cache_hit: Whether result was from cache
        error: Whether classification failed
    """
    _monitor.record_classification(
        sentiment=sentiment,
        confidence=confidence,
        latency_ms=latency_ms,
        signals_count=signals_count,
        cache_hit=cache_hit,
        error=error,
    )


def get_metrics() -> Dict[str, Any]:
    """Get current metrics (convenience function)."""
    return _monitor.get_metrics()


def get_health_status() -> Dict[str, Any]:
    """Get health status (convenience function)."""
    return _monitor.get_health_status()
