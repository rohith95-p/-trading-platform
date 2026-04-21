"""
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from src.api import auth, execution, intelligence, backtesting, test, api_keys, roles
from src.database import get_db
from src.rbac.rbac_service import RBACService
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup - Create database tables
    logger.info("Creating database tables...")
    try:
        from src.database import Base, engine
        from sqlalchemy import text as sql_text
        Base.metadata.create_all(bind=engine)
        # Create RBAC tables (raw SQL since they use text queries)
        with engine.connect() as conn:
            conn.execute(sql_text("""
                CREATE TABLE IF NOT EXISTS roles (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR UNIQUE NOT NULL,
                    description VARCHAR,
                    permissions JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(sql_text("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    role_id VARCHAR NOT NULL REFERENCES roles(id),
                    assigned_at TIMESTAMP DEFAULT NOW(),
                    assigned_by VARCHAR,
                    UNIQUE(user_id, role_id)
                )
            """))
            conn.commit()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")

    logger.info("Initializing default RBAC roles...")
    try:
        db = next(get_db())
        rbac_service = RBACService(db)
        await rbac_service.initialize_default_roles()
        logger.info("Default RBAC roles initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize default roles: {str(e)}")
    
    # Initialize WebSocket manager for real-time indicator updates
    logger.info("Initializing WebSocket manager...")
    try:
        from src.intelligence.indicator_websocket_service import initialize_ws_manager
        await initialize_ws_manager()
        logger.info("WebSocket manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {str(e)}")
    
    # Initialize indicator cache service
    logger.info("Initializing indicator cache service...")
    try:
        from src.intelligence.indicator_cache_service import initialize_cache
        await initialize_cache()
        logger.info("Indicator cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize cache service: {str(e)}")
    
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://trading-platform.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(roles.router)
app.include_router(execution.router)
app.include_router(intelligence.router)
app.include_router(backtesting.router)
app.include_router(test.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

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
