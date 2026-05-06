"""
FastAPI application entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text as sql_text

from src.api import auth, execution, intelligence, intelligence_legacy, backtesting, test, api_keys, roles, trading, drl as drl_api, webhooks as webhooks_api
from src.api import billing
from src.api import simulation as simulation_api
from src.api import sessions as sessions_api
from src.database import get_db
from src.rbac.rbac_service import RBACService
from src.config import settings

try:
    import redis
except Exception:  # pragma: no cover - optional dependency check
    redis = None

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    app.state.startup_complete = False
    app.state.startup_errors = []
    app.state.db = auth.auth_service.supabase

    # Startup - Create database tables
    logger.info("Creating database tables...")
    try:
        from src.database import Base, engine
        Base.metadata.create_all(bind=engine)
        # Create RBAC tables (raw SQL since they use text queries)
        with engine.connect() as conn:
            is_sqlite = engine.dialect.name == "sqlite"
            permissions_type = "TEXT" if is_sqlite else "JSONB"
            timestamp_default = "CURRENT_TIMESTAMP" if is_sqlite else "NOW()"

            conn.execute(sql_text(f"""
                CREATE TABLE IF NOT EXISTS roles (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR UNIQUE NOT NULL,
                    description VARCHAR,
                    permissions {permissions_type},
                    created_at TIMESTAMP DEFAULT {timestamp_default}
                )
            """))
            conn.execute(sql_text(f"""
                CREATE TABLE IF NOT EXISTS user_roles (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    role_id VARCHAR NOT NULL REFERENCES roles(id),
                    assigned_at TIMESTAMP DEFAULT {timestamp_default},
                    assigned_by VARCHAR,
                    UNIQUE(user_id, role_id)
                )
            """))
            conn.commit()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        app.state.startup_errors.append(f"database_tables:{e}")

    logger.info("Initializing default RBAC roles...")
    try:
        db = next(get_db())
        rbac_service = RBACService(db)
        await rbac_service.initialize_default_roles()
        logger.info("Default RBAC roles initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize default roles: {str(e)}")
        app.state.startup_errors.append(f"rbac:{e}")
    
    # Initialize WebSocket manager for real-time indicator updates
    logger.info("Initializing WebSocket manager...")
    try:
        from src.intelligence.indicator_websocket_service import initialize_ws_manager
        await initialize_ws_manager()
        logger.info("WebSocket manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {str(e)}")
        app.state.startup_errors.append(f"indicator_ws:{e}")
    
    # Initialize indicator cache service
    logger.info("Initializing indicator cache service...")
    try:
        from src.intelligence.indicator_cache_service import initialize_cache
        await initialize_cache()
        logger.info("Indicator cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize cache service: {str(e)}")
        app.state.startup_errors.append(f"indicator_cache:{e}")

    # ----------------------------------------------------------------
    # Wire exchange connectors from environment / settings
    # ----------------------------------------------------------------
    logger.info("Initializing exchange connectors...")
    try:
        from src.api.trading import _exchange_router
        from src.config import settings

        connectors_registered = 0

        # Alpaca (stocks / paper trading)
        if settings.ALPACA_API_KEY and settings.ALPACA_API_SECRET:
            try:
                from src.exchanges.alpaca import AlpacaConnector
                connector = AlpacaConnector(
                    api_key=settings.ALPACA_API_KEY,
                    secret=settings.ALPACA_API_SECRET,
                    paper=settings.ENABLE_PAPER_TRADING,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Alpaca connector registered")
            except Exception as e:
                logger.warning(f"✗ Alpaca connector failed: {e}")

        # Binance (spot/futures)
        if settings.BINANCE_API_KEY and settings.BINANCE_API_SECRET:
            try:
                from src.exchanges.binance import BinanceConnector
                connector = BinanceConnector(
                    api_key=settings.BINANCE_API_KEY,
                    secret=settings.BINANCE_API_SECRET,
                    trading_mode="futures" if not settings.ENABLE_PAPER_TRADING else "spot",
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Binance connector registered")
            except Exception as e:
                logger.warning(f"✗ Binance connector failed: {e}")

        # Kraken
        if settings.KRAKEN_API_KEY and settings.KRAKEN_API_SECRET:
            try:
                from src.exchanges.kraken import KrakenConnector
                connector = KrakenConnector(
                    api_key=settings.KRAKEN_API_KEY,
                    secret=settings.KRAKEN_API_SECRET,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Kraken connector registered")
            except Exception as e:
                logger.warning(f"✗ Kraken connector failed: {e}")

        # Hyperliquid
        if settings.HYPERLIQUID_API_KEY and settings.HYPERLIQUID_API_SECRET:
            try:
                from src.exchanges.hyperliquid import HyperliquidConnector
                connector = HyperliquidConnector(
                    api_key=settings.HYPERLIQUID_API_KEY,
                    secret=settings.HYPERLIQUID_API_SECRET,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Hyperliquid connector registered")
            except Exception as e:
                logger.warning(f"✗ Hyperliquid connector failed: {e}")

        # dYdX
        if settings.DYDX_API_KEY and settings.DYDX_API_SECRET:
            try:
                from src.exchanges.dydx import DydxConnector
                connector = DydxConnector(
                    api_key=settings.DYDX_API_KEY,
                    secret=settings.DYDX_API_SECRET,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ dYdX connector registered")
            except Exception as e:
                logger.warning(f"✗ dYdX connector failed: {e}")

        # Kalshi
        if settings.KALSHI_API_KEY and settings.KALSHI_API_SECRET:
            try:
                from src.exchanges.kalshi import KalshiConnector
                connector = KalshiConnector(
                    api_key=settings.KALSHI_API_KEY,
                    secret=settings.KALSHI_API_SECRET,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Kalshi connector registered")
            except Exception as e:
                logger.warning(f"✗ Kalshi connector failed: {e}")

        # Polymarket
        if settings.POLYMARKET_API_KEY:
            try:
                from src.exchanges.polymarket import PolymarketConnector
                connector = PolymarketConnector(
                    api_key=settings.POLYMARKET_API_KEY,
                )
                await connector.connect()
                _exchange_router.add_connector(connector)
                connectors_registered += 1
                logger.info("✓ Polymarket connector registered")
            except Exception as e:
                logger.warning(f"✗ Polymarket connector failed: {e}")

        if connectors_registered == 0:
            logger.warning(
                "No exchange connectors registered. "
                "Set ALPACA_API_KEY, BINANCE_API_KEY, etc. in environment to enable trading."
            )
        else:
            logger.info(f"Exchange connectors initialized: {connectors_registered} registered")

    except Exception as e:
        logger.error(f"Exchange connector initialization failed: {e}")
        app.state.startup_errors.append(f"exchange_connectors:{e}")

    app.state.startup_complete = True

    yield

    
    # Shutdown
    logger.info("Application shutting down...")
    
    # Close WebSocket manager
    try:
        from src.intelligence.indicator_websocket_service import close_ws_manager
        await close_ws_manager()
        logger.info("WebSocket manager closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket manager: {str(e)}")
    
    # Close cache service
    try:
        from src.intelligence.indicator_cache_service import close_cache
        await close_cache()
        logger.info("Cache service closed")
    except Exception as e:
        logger.error(f"Error closing cache service: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="Unified Trading Intelligence Platform",
    description="Complete trading platform with news classification, technical analysis, and DRL agents",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Build the effective CORS origin list.
# This merges CORS_ORIGINS with FRONTEND_BASE_URL and any Railway-injected
# domain variables (RAILWAY_PUBLIC_DOMAIN, RAILWAY_PRIVATE_DOMAIN) so that
# the frontend service and Railway internal routing are always permitted,
# even when CORS_ORIGINS was not explicitly updated after a redeploy.
_effective_cors_origins = settings.effective_cors_origins()
logger.info("CORS allowed origins: %s", _effective_cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(api_keys.router)
app.include_router(roles.router)
app.include_router(sessions_api.router)
app.include_router(execution.router)
app.include_router(intelligence.router)
app.include_router(intelligence_legacy.router)
app.include_router(backtesting.router)
app.include_router(test.router)
app.include_router(trading.router)
app.include_router(simulation_api.router)
app.include_router(drl_api.router)
app.include_router(webhooks_api.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


def _database_health() -> tuple[bool, str]:
    try:
        from src.database import engine

        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _redis_health() -> tuple[bool | None, str]:
    if not redis or not settings.REDIS_URL:
        return None, "not-configured"

    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


@app.get("/health/live")
async def liveness_probe():
    """Liveness probe for container platforms."""
    return {"status": "alive", "version": settings.APP_VERSION}


@app.get("/health/ready")
async def readiness_probe():
    """Readiness probe for deployment checks."""
    db_ok, db_detail = _database_health()
    redis_ok, redis_detail = _redis_health()
    ready = bool(app.state.startup_complete and db_ok and (redis_ok in {True, None}))

    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if ready else "degraded",
            "startup_complete": bool(app.state.startup_complete),
            "checks": {
                "database": {"ok": db_ok, "detail": db_detail},
                "redis": {"ok": redis_ok, "detail": redis_detail},
            },
            "startup_errors": getattr(app.state, "startup_errors", []),
        },
    )


@app.get("/health/details")
async def detailed_health():
    """Detailed runtime health for operators."""
    db_ok, db_detail = _database_health()
    redis_ok, redis_detail = _redis_health()
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "checks": {
            "database": {"ok": db_ok, "detail": db_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
        },
        "startup_complete": bool(app.state.startup_complete),
        "startup_errors": getattr(app.state, "startup_errors", []),
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Unified Trading Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
