"""
Pydantic models for news articles and news ingestion.

This module defines the data models for news articles from various sources.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import hashlib


class NewsArticleBase(BaseModel):
    """Base model for news articles."""
    source: Literal["rss", "twitter", "telegram"] = Field(..., description="Source of the news article")
    title: str = Field(..., min_length=1, max_length=1000, description="Article title/headline")
    content: Optional[str] = Field(None, description="Full article content or summary")
    url: str = Field(..., description="URL to the original article")
    author: Optional[str] = Field(None, description="Author of the article")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source-specific metadata")
    published_at: datetime = Field(..., description="When the article was published")


class NewsArticleCreate(NewsArticleBase):
    """Model for creating a news article."""

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, v):
        """Normalize title for consistent hashing."""
        if v is None:
            return v
        # Remove extra whitespace and normalize
        return " ".join(v.split())

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, v):
        """Normalize content for consistent hashing."""
        if v is None:
            return None
        # Remove extra whitespace and normalize
        return " ".join(v.split())
    
    def generate_content_hash(self) -> str:
        """Generate SHA-256 hash of normalized content for deduplication."""
        # Combine title and content for hashing
        content_to_hash = f"{self.title.lower().strip()}"
        if self.content:
            content_to_hash += f"|{self.content.lower().strip()}"
        
        return hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()


class NewsArticle(NewsArticleBase):
    """Model for a news article with database fields."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier")
    content_hash: str = Field(..., description="SHA-256 hash for deduplication")
    created_at: datetime = Field(..., description="When the article was ingested")


class NewsArticleResponse(BaseModel):
    """Response model for news article API."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    title: str
    content: Optional[str]
    url: str
    author: Optional[str]
    published_at: datetime
    created_at: datetime


class NewsArticleList(BaseModel):
    """Response model for listing news articles."""
    articles: list[NewsArticleResponse]
    total: int
    page: int
    page_size: int


class NewsSourceConfig(BaseModel):
    """Configuration for a news source."""
    source_type: Literal["rss", "twitter", "telegram"]
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = Field(default=15, ge=1, le=1440)
    priority: int = Field(default=1, ge=1, le=10)


class NewsIngestionStats(BaseModel):
    """Statistics for news ingestion."""
    total_articles: int
    articles_by_source: Dict[str, int]
    articles_last_hour: int
    articles_last_24h: int
    duplicates_detected: int
    errors: int
    last_ingestion_at: Optional[datetime]
