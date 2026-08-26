from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from src.intelligence.indicators import compute_all_indicators
from src.risk.position_sizer import PositionSizer

router = APIRouter(prefix="/analyze", tags=["Signals"])

class OHLCV(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class SignalRequest(BaseModel):
    symbol: str
    history: List[OHLCV]
    balance: Optional[float] = 10000.0

class SignalResponse(BaseModel):
    action: str  # BUY, SELL, HOLD
    size: float
    confidence: float
    reason: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@router.post("/", response_model=SignalResponse)
def analyze_signal(req: SignalRequest):
    if len(req.history) < 200:
        raise HTTPException(status_code=400, detail="Need at least 200 historical candles")

    df = pd.DataFrame([h.model_dump() for h in req.history])
    indicators = compute_all_indicators(df)
    
    latest_close = df['close'].iloc[-1]
    
    rsi_arr = indicators.get("rsi_14", [])
    ema_200_arr = indicators.get("ema_200", [])
    atr_arr = indicators.get("atr_14", [])
    
    rsi = rsi_arr[-1] if len(rsi_arr) > 0 and not np.isnan(rsi_arr[-1]) else 50.0
    ema_200 = ema_200_arr[-1] if len(ema_200_arr) > 0 and not np.isnan(ema_200_arr[-1]) else latest_close
    atr = atr_arr[-1] if len(atr_arr) > 0 and not np.isnan(atr_arr[-1]) else latest_close * 0.01

    action = "HOLD"
    reason = "No clear signal"
    confidence = 0.0
    stop_loss = None
    take_profit = None
    
    if rsi < 30 and latest_close > ema_200:
        action = "BUY"
        reason = "Oversold in an uptrend"
        confidence = 0.8
        stop_loss = latest_close - (2 * atr)
        take_profit = latest_close + (4 * atr)
    elif rsi > 70 and latest_close < ema_200:
        action = "SELL"
        reason = "Overbought in a downtrend"
        confidence = 0.8
        stop_loss = latest_close + (2 * atr)
        take_profit = latest_close - (4 * atr)

    size = 0.0
    if action != "HOLD":
        sizer = PositionSizer()
        kelly_fraction = sizer.kelly_criterion(win_rate=0.55, avg_win=2.0, avg_loss=1.0)
        size = sizer.get_position_size(kelly_fraction, req.balance)

    return SignalResponse(
        action=action,
        size=size,
        confidence=confidence,
        reason=reason,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
