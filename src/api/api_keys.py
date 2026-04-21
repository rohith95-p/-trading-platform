"""
API Key management endpoints

This module handles secure storage, encryption, and management of exchange API keys.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from src.data.database import get_db
from src.data.models import User
from src.api.auth import get_current_user
from src.api_keys.api_key_service import APIKeyService
from src.api_keys.models import (
    AddAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    MaskedAPIKeyResponse,
    ValidateAPIKeyResponse,
    RotateKeyRequest,
    APIKeyUsageStats,
)

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])

# Initialize service
api_key_service = APIKeyService()


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def add_api_key(
    request: AddAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new API key for an exchange.
    
    - **exchange**: Exchange name (alpaca, kalshi, polymarket, etc.)
    - **api_key**: API key from exchange
    - **api_secret**: API secret from exchange
    - **passphrase**: Optional passphrase (required for some exchanges)
    - **exchange_account_id**: Optional exchange account identifier
    - **permissions**: API key permissions (read, trade, withdraw)
    - **expires_at**: Optional expiration timestamp
    - **metadata**: Optional additional metadata
    """
    try:
        return api_key_service.add_api_key(current_user.id, request, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add API key"
        )


@router.get("/", response_model=list[MaskedAPIKeyResponse])
async def list_api_keys(
    include_expired: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's API keys with masked credentials.
    
    - **include_expired**: Whether to include expired keys (default: false)
    
    Returns API keys with only the last 4 characters visible.
    """
    try:
        return api_key_service.list_api_keys(current_user.id, db, include_expired)
    except Exception as e:
        logger.error(f"Failed to list API keys: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get API key details (without decrypted credentials).
    
    - **key_id**: API key ID
    """
    try:
        return api_key_service.get_api_key(current_user.id, key_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key"
        )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update API key metadata (not credentials).
    
    - **key_id**: API key ID
    - **permissions**: Optional updated permissions
    - **expires_at**: Optional updated expiration timestamp
    - **metadata**: Optional updated metadata
    """
    try:
        return api_key_service.update_api_key(current_user.id, key_id, request, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an API key.
    
    - **key_id**: API key ID
    """
    try:
        api_key_service.delete_api_key(current_user.id, key_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )


@router.post("/{key_id}/validate", response_model=ValidateAPIKeyResponse)
async def validate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate an API key by making a test API call to the exchange.
    
    - **key_id**: API key ID
    
    Returns validation status and any error messages.
    """
    try:
        return api_key_service.validate_api_key(current_user.id, key_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to validate API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key"
        )


@router.post("/{key_id}/rotate", response_model=APIKeyResponse)
async def rotate_api_key(
    key_id: str,
    request: RotateKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rotate API key credentials (replace with new credentials).
    
    - **key_id**: API key ID
    - **new_api_key**: New API key from exchange
    - **new_api_secret**: New API secret from exchange
    - **new_passphrase**: Optional new passphrase
    
    This replaces the stored credentials with new ones while maintaining
    the same API key record and metadata.
    """
    try:
        return api_key_service.rotate_api_key(current_user.id, key_id, request, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to rotate API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key"
        )


@router.get("/{key_id}/usage", response_model=APIKeyUsageStats)
async def get_api_key_usage(
    key_id: str,
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get API key usage statistics.
    
    - **key_id**: API key ID
    - **days**: Number of days to include in stats (default: 7)
    """
    try:
        return api_key_service.get_usage_stats(current_user.id, key_id, db, days)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get API key usage: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key usage"
        )


# Internal helper function for other services
def get_decrypted_api_key(
    user_id: str,
    exchange: str,
    db: Session,
    exchange_account_id: str = None
) -> tuple[str, str, str]:
    """
    Get decrypted API key and secret for internal use.
    
    Args:
        user_id: User ID
        exchange: Exchange name
        db: Database session
        exchange_account_id: Optional exchange account ID
        
    Returns:
        Tuple of (api_key, api_secret, passphrase)
        
    Raises:
        HTTPException: If API key not found or invalid
    """
    try:
        return api_key_service.get_decrypted_credentials(
            user_id, exchange, db, exchange_account_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )
