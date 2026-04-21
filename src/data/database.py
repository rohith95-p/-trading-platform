"""
Database connection and configuration for Supabase PostgreSQL

This module handles database connections, migrations, and session management.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/trading_platform"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable pooling for Supabase free tier
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={
        "connect_timeout": 10,
        "application_name": "trading-platform-api"
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Session:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from src.data.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

def health_check() -> bool:
    """Check database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
