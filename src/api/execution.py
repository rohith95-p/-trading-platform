"""Execution layer routes"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db

router = APIRouter(prefix="/api/v1", tags=["execution"])

@router.get("/exchanges")
async def list_exchanges(db: Session = Depends(get_db)):
    """List available exchanges"""
    return {
        "exchanges": ["kalshi", "polymarket", "alpaca"]
    }

@router.post("/orders")
async def place_order(order: dict, db: Session = Depends(get_db)):
    """Place order"""
    return {
        "order_id": "order_123",
        "status": "pending",
        "message": "Order placed successfully"
    }

@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    """Get open positions"""
    return {
        "positions": []
    }

@router.get("/balance")
async def get_balance(db: Session = Depends(get_db)):
    """Get account balance"""
    return {
        "total": 10000.0,
        "available": 10000.0,
        "used": 0.0
    }
