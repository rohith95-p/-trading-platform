"""
Execution layer routes (v1 prefix).

These endpoints delegate to the ExchangeRouter which holds the real connectors.
For order placement with full risk validation use POST /trading/orders instead.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.exchanges.router import ExchangeRouter
from src.api.trading import get_exchange_router
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["execution"])


@router.get("/exchanges")
async def list_exchanges(
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """
    List exchange connectors that are currently registered and connected.

    Returns an empty list if no API keys have been configured yet.
    """
    return {
        "exchanges": exchange_router.connector_names,
        "total": len(exchange_router.connector_names),
    }


@router.get("/positions")
async def get_positions(
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """
    Get open positions across all registered exchanges.

    Delegates to GET /trading/positions for full detail.
    """
    try:
        all_positions = await exchange_router.get_all_positions()
        serialized = {}
        total = 0
        for exchange, positions in all_positions.items():
            serialized[exchange] = [
                {
                    "symbol": p.symbol,
                    "size": p.size,
                    "entry_price": getattr(p, "entry_price", getattr(p, "avgPrice", 0)),
                    "current_price": getattr(p, "current_price", getattr(p, "currentPrice", 0)),
                    "pnl": getattr(p, "pnl", getattr(p, "unrealizedPnl", 0)),
                }
                for p in positions
            ]
            total += len(positions)
        return {"positions": serialized, "total_positions": total}
    except Exception as exc:
        log.error(f"Failed to fetch positions: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {exc}")


@router.get("/balance")
async def get_balance(
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """
    Get total balance across all registered exchanges.
    """
    try:
        balances = await exchange_router.get_balances()
        total = await exchange_router.get_total_balance()
        serialized = {
            name: {"total": b.total, "available": b.available, "used": b.used}
            for name, b in balances.items()
        }
        return {"total": total, "available": total, "balances": serialized}
    except Exception as exc:
        log.error(f"Failed to fetch balances: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch balances: {exc}")


@router.post("/orders")
async def place_order_redirect():
    """
    Order placement is handled by POST /trading/orders (includes risk validation).
    This stub exists for backwards compatibility.
    """
    raise HTTPException(
        status_code=308,
        detail="Use POST /trading/orders for order placement with risk validation.",
        headers={"Location": "/trading/orders"},
    )
