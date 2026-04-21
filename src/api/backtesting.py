"""Backtesting routes"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.backtesting.pandas_backtester import PandasBacktester

router = APIRouter(prefix="/api/v1", tags=["backtesting"])

@router.post("/backtest")
async def run_backtest(config: dict, db: Session = Depends(get_db)):
    """Run backtest"""
    backtester = PandasBacktester()
    
    # Placeholder data
    historical_data = [
        {"datetime": "2024-01-01", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}
        for _ in range(100)
    ]
    
    result = backtester.backtest("test_strategy", historical_data, config)
    
    return {
        "strategy": result.strategy_name,
        "metrics": {
            "total_return": result.metrics.total_return,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "trades": result.metrics.trades_count
        }
    }
