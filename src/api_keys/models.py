"""
Pydantic models for API key management

This module defines request and response models for API key operations.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ExchangeType(str, Enum):
    """Supported exchanges"""
    ALPACA = "alpaca"
    KALSHI = "kalshi"
    POLYMARKET = "polymarket"
    HYPERLIQUID = "hyperliquid"
    DYDX = "dydx"
    KRAKEN = "kraken"
    BINANCE = "binance"


class APIKeyPermissions(BaseModel):
    """API key permissions"""
    read: bool = True
    trade: bool = False
    withdraw: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "read": True,
                "trade": True,
                "withdraw": False
            }
        }


class AddAPIKeyRequest(BaseModel):
    """Request model for adding a new API key"""
    exchange: ExchangeType = Field(..., description="Exchange name")
    api_key: str = Field(..., min_length=1, description="API key from exchange")
    api_secret: str = Field(..., min_length=1, description="API secret from exchange")
    passphrase: Optional[str] = Field(None, description="API passphrase (required for some exchanges)")
    exchange_account_id: Optional[str] = Field(None, description="Exchange account identifier")
    permissions: Optional[APIKeyPermissions] = Field(
        default_factory=lambda: APIKeyPermissions(read=True, trade=False, withdraw=False),
        description="API key permissions"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('api_key', 'api_secret')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("API key and secret cannot be empty")
        return v.strip()
    
    @validator('passphrase')
    def validate_passphrase(cls, v, values):
        # Some exchanges require passphrase
        exchange = values.get('exchange')
        if exchange in [ExchangeType.KRAKEN] and not v:
            raise ValueError(f"{exchange} requires a passphrase")
        return v.strip() if v else None
    
    class Config:
        json_schema_extra = {
            "example": {
                "exchange": "alpaca",
                "api_key": "PKXXXXXXXXXXXXXXXX",
                "api_secret": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "passphrase": None,
                "exchange_account_id": "account_123",
                "permissions": {
                    "read": True,
                    "trade": True,
                    "withdraw": False
                },
                "expires_at": None,
                "metadata": {"environment": "paper"}
            }
        }


class UpdateAPIKeyRequest(BaseModel):
    """Request model for updating an API key"""
    permissions: Optional[APIKeyPermissions] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "permissions": {
                    "read": True,
                    "trade": True,
                    "withdraw": False
                },
                "expires_at": "2024-12-31T23:59:59Z",
                "metadata": {"note": "Updated permissions"}
            }
        }


class APIKeyResponse(BaseModel):
    """Response model for API key (full details)"""
    id: str
    exchange: str
    exchange_account_id: Optional[str]
    is_valid: bool
    last_validated_at: Optional[datetime]
    validation_error: Optional[str]
    permissions: Dict[str, bool]
    last_used_at: Optional[datetime]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "exchange": "alpaca",
                "exchange_account_id": "account_123",
                "is_valid": True,
                "last_validated_at": "2024-01-15T10:30:00Z",
                "validation_error": None,
                "permissions": {
                    "read": True,
                    "trade": True,
                    "withdraw": False
                },
                "last_used_at": "2024-01-15T12:00:00Z",
                "usage_count": 42,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "expires_at": None,
                "metadata": {"environment": "paper"}
            }
        }


class MaskedAPIKeyResponse(BaseModel):
    """Response model for API key list (masked for security)"""
    id: str
    exchange: str
    exchange_account_id: Optional[str]
    key_preview: str  # Last 4 characters only
    is_valid: bool
    last_validated_at: Optional[datetime]
    permissions: Dict[str, bool]
    last_used_at: Optional[datetime]
    usage_count: int
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "exchange": "alpaca",
                "exchange_account_id": "account_123",
                "key_preview": "****XXXX",
                "is_valid": True,
                "last_validated_at": "2024-01-15T10:30:00Z",
                "permissions": {
                    "read": True,
                    "trade": True,
                    "withdraw": False
                },
                "last_used_at": "2024-01-15T12:00:00Z",
                "usage_count": 42,
                "created_at": "2024-01-01T00:00:00Z",
                "expires_at": None
            }
        }


class ValidateAPIKeyResponse(BaseModel):
    """Response model for API key validation"""
    valid: bool
    exchange: str
    message: str
    validation_error: Optional[str] = None
    last_validated_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "exchange": "alpaca",
                "message": "API key is valid and has read/trade permissions",
                "validation_error": None,
                "last_validated_at": "2024-01-15T10:30:00Z"
            }
        }


class RotateKeyRequest(BaseModel):
    """Request model for key rotation"""
    new_api_key: str = Field(..., min_length=1, description="New API key from exchange")
    new_api_secret: str = Field(..., min_length=1, description="New API secret from exchange")
    new_passphrase: Optional[str] = Field(None, description="New API passphrase (if required)")
    
    @validator('new_api_key', 'new_api_secret')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("New API key and secret cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_api_key": "PKNEWXXXXXXXXXXXXXXXX",
                "new_api_secret": "NEWXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "new_passphrase": None
            }
        }


class APIKeyUsageStats(BaseModel):
    """API key usage statistics"""
    total_usage: int
    last_used_at: Optional[datetime]
    usage_by_day: Dict[str, int]  # Date -> count
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_usage": 150,
                "last_used_at": "2024-01-15T12:00:00Z",
                "usage_by_day": {
                    "2024-01-15": 42,
                    "2024-01-14": 38,
                    "2024-01-13": 70
                }
            }
        }
