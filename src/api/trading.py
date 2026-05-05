"""
Trading API endpoints - order placement, positions, balance, circuit breaker.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.interfaces.exchange_connector import Order
from src.exchanges.router import ExchangeRouter
from src.risk.manager import RiskManager
from src.risk.circuit_breaker import CircuitBreaker
from src.database import get_db
from src.data.models import Trade as TradeDB

log = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])

# ---------------------------------------------------------------------------
# Shared singletons (can be overridden in tests via dependency injection)
# ---------------------------------------------------------------------------

_exchange_router = ExchangeRouter()
_risk_manager = RiskManager()
_circuit_breaker = CircuitBreaker()


def get_exchange_router() -> ExchangeRouter:
    return _exchange_router


def get_risk_manager() -> RiskManager:
    return _risk_manager


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class PlaceOrderRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exchange": "alpaca",
                "symbol": "AAPL",
                "side": "buy",
                "type": "limit",
                "size": 10,
                "price": 150.0,
                "portfolio_value": 10000.0,
            }
        }
    )

    exchange: str = Field(..., description="Exchange connector name")
    symbol: str = Field(..., description="Trading symbol, e.g. BTC-USD")
    side: str = Field(..., description="buy or sell")
    type: str = Field("market", description="market, limit, stop")
    size: float = Field(..., gt=0, description="Order size in base units")
    price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)")
    leverage: Optional[float] = Field(None, description="Leverage multiplier")
    portfolio_value: float = Field(..., gt=0, description="Current portfolio value for risk checks")



class OrderResponse(BaseModel):
    trade_id: str
    exchange: str
    symbol: str
    side: str
    size: float
    price: float
    fee: float
    timestamp: datetime


class PositionsResponse(BaseModel):
    positions: Dict[str, List[Dict[str, Any]]]
    total_positions: int


class BalanceResponse(BaseModel):
    total_balance: float
    balances: Dict[str, Dict[str, float]]


class TradesResponse(BaseModel):
    trades: List[Dict[str, Any]]
    total: int


class CircuitBreakerStatus(BaseModel):
    triggered: bool
    daily_pnl: float
    trade_count: int
    position_loss_threshold: float
    daily_drawdown_threshold: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/orders", response_model=OrderResponse, summary="Place a new order")
async def place_order(
    request: PlaceOrderRequest,
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
    risk_manager: RiskManager = Depends(get_risk_manager),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
):
    """
    Place an order on the specified exchange after risk validation.

    - Validates order against position, exposure, and leverage limits
    - Rejects orders when the circuit breaker is triggered
    - Routes the order to the correct exchange connector
    """
    # Circuit breaker guard
    if circuit_breaker.is_triggered():
        raise HTTPException(
            status_code=403,
            detail="Circuit breaker is active. Trading is halted.",
        )

    # Build Order object
    order = Order(
        symbol=request.symbol,
        side=request.side,
        type=request.type,
        size=request.size,
        price=request.price,
        stop_price=request.stop_price,
        leverage=request.leverage,
    )

    # Fetch current positions for risk check
    try:
        all_positions = await exchange_router.get_all_positions()
        current_positions = [
            pos
            for positions in all_positions.values()
            for pos in positions
        ]
    except Exception as exc:
        log.warning(f"Could not fetch positions for risk check: {exc}")
        current_positions = []

    # Risk validation
    try:
        risk_manager.validate_order(
            order=order,
            portfolio_value=request.portfolio_value,
            current_positions=current_positions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Place order
    try:
        trade = await exchange_router.place_order(request.exchange, order)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.error(f"Order placement failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Order placement failed: {exc}")

    return OrderResponse(
        trade_id=trade.id,
        exchange=request.exchange,
        symbol=trade.symbol,
        side=trade.side,
        size=trade.size,
        price=trade.price,
        fee=trade.fee,
        timestamp=trade.timestamp,
    )


@router.get("/positions", response_model=PositionsResponse, summary="Get all open positions")
async def get_positions(
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """Return open positions across all registered exchanges."""
    try:
        all_positions = await exchange_router.get_all_positions()
    except Exception as exc:
        log.error(f"Failed to fetch positions: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {exc}")

    serialized: Dict[str, List[Dict[str, Any]]] = {}
    total = 0
    for exchange, positions in all_positions.items():
        serialized[exchange] = [
            {
                "id": p.id,
                "symbol": p.symbol,
                "side": p.side,
                "size": p.size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "pnl": p.pnl,
                "pnl_percent": p.pnl_percent,
            }
            for p in positions
        ]
        total += len(positions)

    return PositionsResponse(positions=serialized, total_positions=total)


@router.get("/trades", response_model=TradesResponse, summary="Get recent trade executions")
async def get_trades(
    limit: int = Query(100, ge=1, le=500),
    user_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return recent trade executions recorded in the database."""
    try:
        query = select(TradeDB)

        if user_id:
            query = query.where(TradeDB.user_id == user_id)
        if symbol:
            query = query.where(TradeDB.symbol == symbol)

        query = query.order_by(desc(TradeDB.timestamp)).limit(limit)
        rows = db.execute(query).scalars().all()

        trades = [
            {
                "id": trade.id,
                "user_id": trade.user_id,
                "strategy_id": trade.strategy_id,
                "exchange": trade.exchange,
                "symbol": trade.symbol,
                "side": trade.side,
                "type": trade.type,
                "price": float(trade.price),
                "size": float(trade.size),
                "fee": float(trade.fee or 0),
                "pnl": float(trade.pnl or 0),
                "timestamp": trade.timestamp.isoformat(),
            }
            for trade in rows
        ]

        return TradesResponse(trades=trades, total=len(trades))

    except Exception as exc:
        log.error(f"Failed to fetch trades: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {exc}")


@router.get("/balance", response_model=BalanceResponse, summary="Get total balance")
async def get_balance(
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """Return total balance and per-exchange breakdown."""
    try:
        balances = await exchange_router.get_balances()
        total = await exchange_router.get_total_balance()
    except Exception as exc:
        log.error(f"Failed to fetch balances: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch balances: {exc}")

    serialized = {
        name: {"total": b.total, "available": b.available, "used": b.used}
        for name, b in balances.items()
    }

    return BalanceResponse(total_balance=total, balances=serialized)


@router.delete("/orders/{order_id}", summary="Cancel an order")
async def cancel_order(
    order_id: str,
    exchange: str,
    exchange_router: ExchangeRouter = Depends(get_exchange_router),
):
    """
    Cancel an open order on the specified exchange.

    Query parameter `exchange` specifies which connector to use.
    """
    try:
        success = await exchange_router.cancel_order(exchange, order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.error(f"Cancel order failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cancel order failed: {exc}")

    if not success:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found or already filled")

    return {"status": "cancelled", "order_id": order_id, "exchange": exchange}


@router.get("/circuit-breaker", response_model=CircuitBreakerStatus, summary="Circuit breaker status")
async def get_circuit_breaker_status(
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
):
    """Return the current state of the circuit breaker."""
    return CircuitBreakerStatus(
        triggered=circuit_breaker.is_triggered(),
        daily_pnl=circuit_breaker.daily_pnl,
        trade_count=circuit_breaker.trade_count,
        position_loss_threshold=circuit_breaker.position_loss_threshold,
        daily_drawdown_threshold=circuit_breaker.daily_drawdown_threshold,
    )
