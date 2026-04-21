"""
Configuration management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Unified Trading Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/trading_db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # API Keys
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-encryption-key-change-in-production")
    
    # Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Exchange APIs
    KALSHI_API_KEY: Optional[str] = os.getenv("KALSHI_API_KEY")
    KALSHI_API_SECRET: Optional[str] = os.getenv("KALSHI_API_SECRET")
    
    POLYMARKET_API_KEY: Optional[str] = os.getenv("POLYMARKET_API_KEY")
    POLYMARKET_API_SECRET: Optional[str] = os.getenv("POLYMARKET_API_SECRET")
    
    ALPACA_API_KEY: Optional[str] = os.getenv("ALPACA_API_KEY")
    ALPACA_API_SECRET: Optional[str] = os.getenv("ALPACA_API_SECRET")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "https://trading-platform.vercel.app"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
