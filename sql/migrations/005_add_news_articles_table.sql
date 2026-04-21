-- Migration 005: Add news_articles table for news ingestion
-- This table stores news articles from multiple sources (RSS, Twitter, Telegram)

CREATE TABLE IF NOT EXISTS news_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Source information
  source TEXT NOT NULL CHECK (source IN ('rss', 'twitter', 'telegram')),
  
  -- Article content
  title TEXT NOT NULL,
  content TEXT,
  url TEXT UNIQUE NOT NULL,
  
  -- Author and metadata
  author TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Deduplication
  content_hash TEXT NOT NULL,
  
  -- Timestamps
  published_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- Indexes for efficient querying
  CONSTRAINT news_articles_title_length CHECK (char_length(title) >= 1 AND char_length(title) <= 1000)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_articles_published_at ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_content_hash ON news_articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_news_articles_created_at ON news_articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_url ON news_articles(url);

-- Comments
COMMENT ON TABLE news_articles IS 'News articles ingested from multiple sources (RSS, Twitter, Telegram)';
COMMENT ON COLUMN news_articles.source IS 'Source of the news article: rss, twitter, or telegram';
COMMENT ON COLUMN news_articles.content_hash IS 'SHA-256 hash of normalized content for deduplication';
COMMENT ON COLUMN news_articles.metadata IS 'Additional metadata specific to the source (e.g., tweet ID, channel ID)';
