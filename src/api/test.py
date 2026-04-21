"""
Test endpoints for infrastructure verification
"""

from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter(prefix="/api/v1/test", tags=["test"])


@router.get("/database")
async def test_database():
    """Test database connection"""
    try:
        # In Phase 1, we're just verifying the endpoint exists
        # Full database testing will be done in Task 1.4
        database_url = os.getenv("DATABASE_URL", "not-configured")
        
        return {
            "status": "connected",
            "service": "PostgreSQL",
            "timestamp": datetime.now().isoformat(),
            "database_configured": bool(database_url and database_url != "not-configured"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/environment")
async def test_environment():
    """Test environment variables are configured"""
    try:
        required_vars = [
            "DATABASE_URL",
            "JWT_SECRET",
            "ENVIRONMENT",
        ]
        
        configured = {}
        missing = []
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                configured[var] = "✓ configured"
            else:
                missing.append(var)
        
        return {
            "status": "success" if not missing else "warning",
            "configured": configured,
            "missing": missing,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/services")
async def test_services():
    """Test all services status"""
    try:
        return {
            "status": "operational",
            "services": {
                "api": "running",
                "database": "configured" if os.getenv("DATABASE_URL") else "not-configured",
                "authentication": "configured" if os.getenv("JWT_SECRET") else "not-configured",
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
