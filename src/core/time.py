"""
UTC time helpers used across the application.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """Return a UTC datetime without tzinfo for legacy DB columns."""
    return utc_now().replace(tzinfo=None)


def utc_from_timestamp(timestamp: float | int) -> datetime:
    """Return a timezone-aware UTC datetime from a UNIX timestamp."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

