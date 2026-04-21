"""
Pydantic models for request/response validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

# User Models
class UserBase(BaseModel):
    email: EmailStr
    
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
class UserResponse(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# API Key Models
class APIKeyCreate(BaseModel):
    exchange: str
    api_key: str
    api_secret: str
    
class APIKeyResponse(BaseModel):
    id: str
    exchange: str
    masked_key: str  # Only show last 4 characters
    created_at: datetime
    
    class Config:
        from_attributes = True

# Strategy Models
class StrategyConfig(BaseModel):
    timeframe: str
    indicators: List[str]
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    
class StrategyCreate(BaseModel):
    name: str
    type: str
    config: StrategyConfig
    
class StrategyResponse(StrategyCreate):
    id: str
    user_id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Trade Models
class TradeCreate(BaseModel):
    strategy_id: str
    exchange: str
    symbol: str
    side: str  # buy or sell
    price: float
    size: float
    
class TradeResponse(TradeCreate):
    id: str
    user_id: str
    fee: Optional[float]
    pnl: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Signal Models
class SignalCreate(BaseModel):
    source: str
    asset: str
    direction: str  # buy, sell, hold
    confidence: float = Field(..., ge=0, le=1)
    rationale: str
    
class SignalResponse(SignalCreate):
    id: str
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Indicator Models
class IndicatorRequest(BaseModel):
    symbol: str
    timeframe: str
    indicators: List[str]
    
class IndicatorResponse(BaseModel):
    symbol: str
    timeframe: str
    indicators: Dict[str, Any]
    computed_at: datetime

# Enhanced Indicator Models for Technical Analysis API
class MarketData(BaseModel):
    """Market data for indicator computation"""
    highs: List[float] = Field(..., description="High prices")
    lows: List[float] = Field(..., description="Low prices")
    closes: List[float] = Field(..., description="Close prices")
    volumes: Optional[List[float]] = Field(None, description="Volume data (optional)")

class IndicatorComputeRequest(BaseModel):
    """Request for computing technical indicators"""
    symbol: str = Field(..., description="Trading symbol (e.g., BTC-USD)")
    timeframe: str = Field(..., description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d")
    indicators: List[str] = Field(..., description="List of indicator names to compute")
    market_data: MarketData = Field(..., description="Market data (OHLCV)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14", "MACD"],
                "market_data": {
                    "highs": [100.5, 101.2, 102.0],
                    "lows": [99.5, 100.0, 101.0],
                    "closes": [100.0, 101.0, 101.5],
                    "volumes": [1000, 1200, 1100]
                }
            }
        }

class BatchIndicatorRequest(BaseModel):
    """Request for batch indicator computation"""
    requests: List[IndicatorComputeRequest] = Field(..., description="List of indicator requests")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "symbol": "BTC-USD",
                        "timeframe": "1h",
                        "indicators": ["EMA_20", "RSI_14"],
                        "market_data": {
                            "highs": [100.5, 101.2],
                            "lows": [99.5, 100.0],
                            "closes": [100.0, 101.0],
                            "volumes": [1000, 1200]
                        }
                    }
                ]
            }
        }

class IndicatorComputeResponse(BaseModel):
    """Response for indicator computation"""
    symbol: str
    timeframe: str
    indicators: Dict[str, Any] = Field(..., description="Computed indicator values")
    computed_at: datetime
    latency_ms: float = Field(..., description="Computation time in milliseconds")
    cached: bool = Field(False, description="Whether result was served from cache")
    
class BatchIndicatorResponse(BaseModel):
    """Response for batch indicator computation"""
    results: List[IndicatorComputeResponse]
    total: int
    total_latency_ms: float

# Error Models
class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
