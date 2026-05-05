"""
Configuration management
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "Unified Trading Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_BASE_URL: str = "https://ultracore-api.up.railway.app"
    FRONTEND_BASE_URL: str = "http://localhost:3001"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/trading_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "change-this-in-production-use-railway-env-var"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 30
    JWT_ISSUER: str = "ultracore-api"
    JWT_AUDIENCE: str = "ultracore-client"
    JWT_LEEWAY_SECONDS: int = 30

    # Encryption
    ENCRYPTION_KEY: str = "change-this-in-production-use-railway-env-var"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Claude API (for news classification)
    ANTHROPIC_API_KEY: str = ""

    # OpenAI API (for simulation engine, optional - falls back to mock)
    OPENAI_API_KEY: str = ""

    # Exchange APIs (all default to paper trading)
    KALSHI_API_KEY: Optional[str] = None
    KALSHI_API_SECRET: Optional[str] = None

    POLYMARKET_API_KEY: Optional[str] = None

    ALPACA_API_KEY: Optional[str] = None
    ALPACA_API_SECRET: Optional[str] = None

    HYPERLIQUID_API_KEY: Optional[str] = None
    HYPERLIQUID_API_SECRET: Optional[str] = None

    DYDX_API_KEY: Optional[str] = None
    DYDX_API_SECRET: Optional[str] = None

    KRAKEN_API_KEY: Optional[str] = None
    KRAKEN_API_SECRET: Optional[str] = None

    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None

    # Feature flags
    ENABLE_PAPER_TRADING: bool = True
    ENABLE_REAL_TRADING: bool = False
    ENABLE_DRL_AGENT: bool = True
    ENABLE_SIMULATION: bool = True
    ENABLE_NEWS_CLASSIFICATION: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://trading-platform.vercel.app",
        ]
    )

    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: str = "price_free_tier"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "https://trading-platform.vercel.app",
            ]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    def validate_for_startup(self) -> None:
        """Fail fast when production is configured with development placeholders."""
        if not self.is_production():
            return

        default_values = {
            "JWT_SECRET": {
                "change-this-in-production-use-railway-env-var",
                "your-secret-key-change-in-production",
                "dev-secret-key-DO-NOT-USE-IN-PRODUCTION",
            },
            "ENCRYPTION_KEY": {
                "change-this-in-production-use-railway-env-var",
                "dev-encryption-key-DO-NOT-USE-IN-PRODUCTION",
            },
            "DATABASE_URL": {
                "postgresql://user:password@localhost/trading_db",
                "postgresql://user:password@localhost:5432/trading_platform",
                "postgresql://user:password@host:port/database",
            },
        }
        invalid = [
            key
            for key, placeholders in default_values.items()
            if getattr(self, key) in placeholders
        ]
        if invalid:
            raise RuntimeError(
                "Production configuration is using placeholder values for: "
                + ", ".join(invalid)
            )

# Create settings instance
settings = Settings()
settings.validate_for_startup()
