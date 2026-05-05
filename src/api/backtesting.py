"""Backtesting routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from src.database import get_db
from src.backtesting.pandas_backtester import PandasBacktester
import logging

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["backtesting"])


class OHLCVBar(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class BacktestRequest(BaseModel):
    strategy_name: str = Field(..., description="Name of the strategy to backtest")
    historical_data: List[OHLCVBar] = Field(..., description="List of OHLCV bars")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional backtest configuration"
    )


class TradeLog(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float


class BacktestMetricsResponse(BaseModel):
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float


class BacktestResponse(BaseModel):
    strategy_name: str
    start_date: str
    end_date: str
    metrics: BacktestMetricsResponse
    trades: List[TradeLog]
    equity_curve: List[float]


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(get_db),
):
    """
    Run a vectorized backtest.

    - `strategy_name`: identifier for the strategy
    - `historical_data`: list of OHLCV dicts (datetime, open, high, low, close, volume)
    - `config` (optional): fee_rate, slippage_rate, timeframe overrides
    """
    try:
        cfg = request.config or {}
        backtester = PandasBacktester(
            fee_rate=cfg.get("fee_rate", 0.001),
            slippage_rate=cfg.get("slippage_rate", 0.0005),
            timeframe=cfg.get("timeframe", "1d"),
        )

        raw_data = [bar.model_dump() for bar in request.historical_data]
        result = backtester.backtest(request.strategy_name, raw_data, cfg)

        trades_log = [
            TradeLog(
                entry_time=t.entry_time.isoformat(),
                exit_time=t.exit_time.isoformat(),
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                pnl=t.pnl,
                pnl_percent=t.pnl_percent,
            )
            for t in result.trades
        ]

        return BacktestResponse(
            strategy_name=result.strategy_name,
            start_date=result.start_date.isoformat(),
            end_date=result.end_date.isoformat(),
            metrics=BacktestMetricsResponse(
                total_return=result.metrics.total_return,
                annual_return=result.metrics.annual_return,
                sharpe_ratio=result.metrics.sharpe_ratio,
                max_drawdown=result.metrics.max_drawdown,
                win_rate=result.metrics.win_rate,
                profit_factor=result.metrics.profit_factor,
                trades_count=result.metrics.trades_count,
                winning_trades=result.metrics.winning_trades,
                losing_trades=result.metrics.losing_trades,
                avg_win=result.metrics.avg_win,
                avg_loss=result.metrics.avg_loss,
            ),
            trades=trades_log,
            equity_curve=result.equity_curve,
        )

    except Exception as exc:
        log.error("Backtest failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}")
