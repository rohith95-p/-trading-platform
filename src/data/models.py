"""
SQLAlchemy models for all database tables

This module defines the data models for users, API keys, strategies, trades, positions, signals, and audit logs.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, LargeBinary,
    ForeignKey, Index, UniqueConstraint, DECIMAL, Enum, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

# Use JSON for SQLite compatibility, JSONB for PostgreSQL
try:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType
except ImportError:
    JSONType = JSON

class User(Base):
    """Users table with quota limits"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Quota limits
    max_strategies = Column(Integer, default=10, nullable=False)
    max_trades_per_day = Column(Integer, default=100, nullable=False)
    max_api_calls_per_hour = Column(Integer, default=1000, nullable=False)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class APIKey(Base):
    """API keys table with encryption fields"""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    exchange_account_id = Column(String(255), nullable=True)
    
    # Encrypted fields (stored as binary)
    key_nonce = Column(LargeBinary, nullable=False)
    key_encrypted = Column(LargeBinary, nullable=False)
    key_version = Column(Integer, default=1, nullable=False)
    
    secret_nonce = Column(LargeBinary, nullable=False)
    secret_encrypted = Column(LargeBinary, nullable=False)
    secret_version = Column(Integer, default=1, nullable=False)
    
    passphrase_nonce = Column(LargeBinary, nullable=True)
    passphrase_encrypted = Column(LargeBinary, nullable=True)
    passphrase_version = Column(Integer, nullable=True)
    
    # Validation
    is_valid = Column(Boolean, default=True, nullable=False)
    last_validated_at = Column(DateTime, nullable=True)
    validation_error = Column(Text, nullable=True)
    
    # Permissions
    permissions = Column(JSON, default={"read": True, "trade": False, "withdraw": False}, nullable=False)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    meta = Column(JSON, default={}, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Unique constraint: one key per user/exchange/account
    __table_args__ = (
        UniqueConstraint("user_id", "exchange", "exchange_account_id", name="uq_user_exchange_account"),
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_exchange", "exchange"),
    )
    
    def __repr__(self):
        return f"<APIKey {self.exchange}>"


class Strategy(Base):
    """Strategies table with JSONB config"""
    __tablename__ = "strategies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'directional', 'grid', 'market-making', 'arbitrage'
    config = Column(JSON, nullable=False)  # Strategy configuration as JSON
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")
    
    # Indexes
    __table_args__ = (
        Index("idx_strategies_user_id", "user_id"),
        Index("idx_strategies_type", "type"),
    )
    
    def __repr__(self):
        return f"<Strategy {self.name}>"


class Trade(Base):
    """Trades table with indexes"""
    __tablename__ = "trades"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(String(36), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # 'buy', 'sell'
    type = Column(String(20), nullable=False)  # 'market', 'limit'
    price = Column(DECIMAL(20, 8), nullable=False)
    size = Column(DECIMAL(20, 8), nullable=False)
    fee = Column(DECIMAL(20, 8), default=0, nullable=False)
    pnl = Column(DECIMAL(20, 8), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    
    # Indexes
    __table_args__ = (
        Index("idx_trades_user_id", "user_id"),
        Index("idx_trades_strategy_id", "strategy_id"),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_timestamp", "timestamp"),
        Index("idx_trades_user_timestamp", "user_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.side}>"


class Position(Base):
    """Positions table with unique constraints"""
    __tablename__ = "positions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    size = Column(DECIMAL(20, 8), nullable=False)
    avg_price = Column(DECIMAL(20, 8), nullable=False)
    current_price = Column(DECIMAL(20, 8), nullable=True)
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True)
    realized_pnl = Column(DECIMAL(20, 8), default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    
    # Unique constraint: one position per user/exchange/symbol
    __table_args__ = (
        UniqueConstraint("user_id", "exchange", "symbol", name="uq_user_exchange_symbol"),
        Index("idx_positions_user_id", "user_id"),
        Index("idx_positions_symbol", "symbol"),
    )
    
    def __repr__(self):
        return f"<Position {self.symbol}>"


class Signal(Base):
    """Signals table from Intelligence Layer"""
    __tablename__ = "signals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # 'news', 'technical', 'drl', 'simulation'
    asset = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False)  # 'long', 'short', 'neutral'
    confidence = Column(DECIMAL(3, 2), nullable=False)  # 0.00 to 1.00
    rationale = Column(Text, nullable=True)
    indicators = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="signals")
    
    # Indexes
    __table_args__ = (
        Index("idx_signals_user_id", "user_id"),
        Index("idx_signals_timestamp", "timestamp"),
        Index("idx_signals_source", "source"),
    )
    
    def __repr__(self):
        return f"<Signal {self.asset} {self.direction}>"


class AuditLog(Base):
    """Audit log table for compliance"""
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_action", "action"),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.action}>"


class NewsArticle(Base):
    """News articles table for news ingestion"""
    __tablename__ = "news_articles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(50), nullable=False, index=True)  # 'rss', 'twitter', 'telegram'
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    url = Column(Text, unique=True, nullable=False, index=True)
    author = Column(Text, nullable=True)
    meta = Column("metadata", JSON, default={}, nullable=False)  # Use JSON for SQLite compatibility
    content_hash = Column(Text, nullable=False, index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_news_articles_source", "source"),
        Index("idx_news_articles_published_at", "published_at"),
        Index("idx_news_articles_content_hash", "content_hash"),
        Index("idx_news_articles_created_at", "created_at"),
        Index("idx_news_articles_url", "url"),
    )
    
    def __repr__(self):
        return f"<NewsArticle {self.title[:50]}>"
