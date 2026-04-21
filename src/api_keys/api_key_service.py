"""
API Key Service

This service handles all API key management operations including encryption,
validation, usage tracking, and expiration policies.
"""

import logging
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.api_keys.encryption import APIKeyEncryption
from src.api_keys.models import (
    AddAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    MaskedAPIKeyResponse,
    ValidateAPIKeyResponse,
    RotateKeyRequest,
    APIKeyUsageStats,
)
from src.data.models import APIKey, User, AuditLog

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys with encryption and validation"""
    
    def __init__(self, encryption: Optional[APIKeyEncryption] = None):
        """
        Initialize API key service.
        
        Args:
            encryption: APIKeyEncryption instance (creates new if None)
        """
        self.encryption = encryption or APIKeyEncryption()
    
    def add_api_key(
        self,
        user_id: str,
        request: AddAPIKeyRequest,
        db: Session
    ) -> APIKeyResponse:
        """
        Add a new API key for a user.
        
        Args:
            user_id: User ID
            request: API key details
            db: Database session
            
        Returns:
            APIKeyResponse with created API key details
            
        Raises:
            ValueError: If API key already exists or validation fails
        """
        # Check if key already exists for this exchange/account
        existing_key = db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.exchange == request.exchange.value,
            APIKey.exchange_account_id == request.exchange_account_id
        ).first()
        
        if existing_key:
            raise ValueError(
                f"API key already exists for {request.exchange.value}"
                + (f" account {request.exchange_account_id}" if request.exchange_account_id else "")
            )
        
        try:
            # Encrypt API key
            key_nonce, key_encrypted, key_version = self.encryption.encrypt(request.api_key)
            
            # Encrypt API secret
            secret_nonce, secret_encrypted, secret_version = self.encryption.encrypt(request.api_secret)
            
            # Encrypt passphrase if provided
            passphrase_nonce = None
            passphrase_encrypted = None
            passphrase_version = None
            if request.passphrase:
                passphrase_nonce, passphrase_encrypted, passphrase_version = self.encryption.encrypt(
                    request.passphrase
                )
            
            # Create API key record
            api_key = APIKey(
                user_id=user_id,
                exchange=request.exchange.value,
                exchange_account_id=request.exchange_account_id,
                key_nonce=key_nonce,
                key_encrypted=key_encrypted,
                key_version=key_version,
                secret_nonce=secret_nonce,
                secret_encrypted=secret_encrypted,
                secret_version=secret_version,
                passphrase_nonce=passphrase_nonce,
                passphrase_encrypted=passphrase_encrypted,
                passphrase_version=passphrase_version,
                is_valid=True,
                permissions=request.permissions.dict() if request.permissions else {"read": True, "trade": False, "withdraw": False},
                expires_at=request.expires_at,
                meta=request.metadata or {},
                usage_count=0
            )
            
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            
            # Log audit event (NEVER log unencrypted keys)
            audit_log = AuditLog(
                user_id=user_id,
                action="api_key_added",
                details={
                    "exchange": request.exchange.value,
                    "exchange_account_id": request.exchange_account_id,
                    "permissions": api_key.permissions
                }
            )
            db.add(audit_log)
            db.commit()
            
            logger.info(f"API key added for user {user_id} on {request.exchange.value}")
            
            return self._to_response(api_key)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add API key: {type(e).__name__}")
            raise ValueError(f"Failed to add API key: {str(e)}")
    
    def list_api_keys(
        self,
        user_id: str,
        db: Session,
        include_expired: bool = False
    ) -> List[MaskedAPIKeyResponse]:
        """
        List user's API keys with masked credentials.
        
        Args:
            user_id: User ID
            db: Database session
            include_expired: Whether to include expired keys
            
        Returns:
            List of MaskedAPIKeyResponse
        """
        query = db.query(APIKey).filter(APIKey.user_id == user_id)
        
        if not include_expired:
            # Filter out expired keys
            query = query.filter(
                (APIKey.expires_at.is_(None)) | (APIKey.expires_at > datetime.utcnow())
            )
        
        api_keys = query.all()
        
        result = []
        for key in api_keys:
            try:
                # Decrypt to get preview (last 4 characters)
                decrypted_key = self.encryption.decrypt(
                    key.key_nonce,
                    key.key_encrypted,
                    key.key_version
                )
                key_preview = f"****{decrypted_key[-4:]}" if len(decrypted_key) >= 4 else "****"
            except Exception as e:
                logger.error(f"Failed to decrypt API key preview: {type(e).__name__}")
                key_preview = "****"
            
            result.append(MaskedAPIKeyResponse(
                id=str(key.id),
                exchange=key.exchange,
                exchange_account_id=key.exchange_account_id,
                key_preview=key_preview,
                is_valid=key.is_valid,
                last_validated_at=key.last_validated_at,
                permissions=key.permissions,
                last_used_at=key.last_used_at,
                usage_count=key.usage_count,
                created_at=key.created_at,
                expires_at=key.expires_at
            ))
        
        return result
    
    def get_api_key(
        self,
        user_id: str,
        key_id: str,
        db: Session
    ) -> APIKeyResponse:
        """
        Get API key details (without decrypted credentials).
        
        Args:
            user_id: User ID
            key_id: API key ID
            db: Database session
            
        Returns:
            APIKeyResponse
            
        Raises:
            ValueError: If API key not found
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        return self._to_response(api_key)
    
    def update_api_key(
        self,
        user_id: str,
        key_id: str,
        request: UpdateAPIKeyRequest,
        db: Session
    ) -> APIKeyResponse:
        """
        Update API key metadata (not credentials).
        
        Args:
            user_id: User ID
            key_id: API key ID
            request: Update request
            db: Database session
            
        Returns:
            Updated APIKeyResponse
            
        Raises:
            ValueError: If API key not found
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        # Update fields
        if request.permissions is not None:
            api_key.permissions = request.permissions.dict()
        
        if request.expires_at is not None:
            api_key.expires_at = request.expires_at
        
        if request.metadata is not None:
            api_key.meta = request.metadata
        
        api_key.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(api_key)
        
        # Log audit event
        audit_log = AuditLog(
            user_id=user_id,
            action="api_key_updated",
            details={
                "key_id": key_id,
                "exchange": api_key.exchange,
                "updated_fields": {
                    "permissions": request.permissions.dict() if request.permissions else None,
                    "expires_at": request.expires_at.isoformat() if request.expires_at else None
                }
            }
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"API key {key_id} updated for user {user_id}")
        
        return self._to_response(api_key)
    
    def delete_api_key(
        self,
        user_id: str,
        key_id: str,
        db: Session
    ) -> None:
        """
        Delete an API key.
        
        Args:
            user_id: User ID
            key_id: API key ID
            db: Database session
            
        Raises:
            ValueError: If API key not found
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        exchange = api_key.exchange
        db.delete(api_key)
        db.commit()
        
        # Log audit event
        audit_log = AuditLog(
            user_id=user_id,
            action="api_key_deleted",
            details={
                "key_id": key_id,
                "exchange": exchange
            }
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"API key {key_id} deleted for user {user_id} on {exchange}")
    
    def validate_api_key(
        self,
        user_id: str,
        key_id: str,
        db: Session
    ) -> ValidateAPIKeyResponse:
        """
        Validate an API key by making a test API call to the exchange.
        
        Args:
            user_id: User ID
            key_id: API key ID
            db: Database session
            
        Returns:
            ValidateAPIKeyResponse
            
        Raises:
            ValueError: If API key not found
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        try:
            # Decrypt credentials (NEVER log these)
            decrypted_key = self.encryption.decrypt(
                api_key.key_nonce,
                api_key.key_encrypted,
                api_key.key_version
            )
            decrypted_secret = self.encryption.decrypt(
                api_key.secret_nonce,
                api_key.secret_encrypted,
                api_key.secret_version
            )
            
            decrypted_passphrase = None
            if api_key.passphrase_encrypted:
                decrypted_passphrase = self.encryption.decrypt(
                    api_key.passphrase_nonce,
                    api_key.passphrase_encrypted,
                    api_key.passphrase_version
                )
            
            # TODO: Make actual test API call to exchange
            # For now, just mark as valid if decryption succeeded
            is_valid = True
            validation_error = None
            message = f"API key is valid for {api_key.exchange}"
            
            # Update validation status
            api_key.is_valid = is_valid
            api_key.last_validated_at = datetime.utcnow()
            api_key.validation_error = validation_error
            db.commit()
            
            logger.info(f"API key {key_id} validated for user {user_id} on {api_key.exchange}")
            
            return ValidateAPIKeyResponse(
                valid=is_valid,
                exchange=api_key.exchange,
                message=message,
                validation_error=validation_error,
                last_validated_at=api_key.last_validated_at
            )
            
        except Exception as e:
            logger.error(f"API key validation failed: {type(e).__name__}")
            
            # Update validation status
            api_key.is_valid = False
            api_key.validation_error = str(e)
            api_key.last_validated_at = datetime.utcnow()
            db.commit()
            
            return ValidateAPIKeyResponse(
                valid=False,
                exchange=api_key.exchange,
                message="API key validation failed",
                validation_error=str(e),
                last_validated_at=api_key.last_validated_at
            )
    
    def rotate_api_key(
        self,
        user_id: str,
        key_id: str,
        request: RotateKeyRequest,
        db: Session
    ) -> APIKeyResponse:
        """
        Rotate API key credentials (replace with new credentials).
        
        Args:
            user_id: User ID
            key_id: API key ID
            request: New credentials
            db: Database session
            
        Returns:
            Updated APIKeyResponse
            
        Raises:
            ValueError: If API key not found or rotation fails
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        try:
            # Encrypt new credentials
            key_nonce, key_encrypted, key_version = self.encryption.encrypt(request.new_api_key)
            secret_nonce, secret_encrypted, secret_version = self.encryption.encrypt(request.new_api_secret)
            
            passphrase_nonce = None
            passphrase_encrypted = None
            passphrase_version = None
            if request.new_passphrase:
                passphrase_nonce, passphrase_encrypted, passphrase_version = self.encryption.encrypt(
                    request.new_passphrase
                )
            
            # Update API key
            api_key.key_nonce = key_nonce
            api_key.key_encrypted = key_encrypted
            api_key.key_version = key_version
            api_key.secret_nonce = secret_nonce
            api_key.secret_encrypted = secret_encrypted
            api_key.secret_version = secret_version
            api_key.passphrase_nonce = passphrase_nonce
            api_key.passphrase_encrypted = passphrase_encrypted
            api_key.passphrase_version = passphrase_version
            api_key.updated_at = datetime.utcnow()
            
            # Reset validation status
            api_key.is_valid = True
            api_key.last_validated_at = None
            api_key.validation_error = None
            
            db.commit()
            db.refresh(api_key)
            
            # Log audit event (NEVER log credentials)
            audit_log = AuditLog(
                user_id=user_id,
                action="api_key_rotated",
                details={
                    "key_id": key_id,
                    "exchange": api_key.exchange
                }
            )
            db.add(audit_log)
            db.commit()
            
            logger.info(f"API key {key_id} rotated for user {user_id}")
            
            return self._to_response(api_key)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to rotate API key: {type(e).__name__}")
            raise ValueError(f"Failed to rotate API key: {str(e)}")
    
    def get_decrypted_credentials(
        self,
        user_id: str,
        exchange: str,
        db: Session,
        exchange_account_id: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Get decrypted API credentials for internal use.
        
        Args:
            user_id: User ID
            exchange: Exchange name
            db: Database session
            exchange_account_id: Optional exchange account ID
            
        Returns:
            Tuple of (api_key, api_secret, passphrase)
            
        Raises:
            ValueError: If API key not found or invalid
        """
        query = db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.exchange == exchange,
            APIKey.is_valid == True
        )
        
        if exchange_account_id:
            query = query.filter(APIKey.exchange_account_id == exchange_account_id)
        
        # Check expiration
        query = query.filter(
            (APIKey.expires_at.is_(None)) | (APIKey.expires_at > datetime.utcnow())
        )
        
        api_key = query.first()
        
        if not api_key:
            raise ValueError(f"Valid API key not found for {exchange}")
        
        try:
            # Decrypt credentials (NEVER log these)
            decrypted_key = self.encryption.decrypt(
                api_key.key_nonce,
                api_key.key_encrypted,
                api_key.key_version
            )
            decrypted_secret = self.encryption.decrypt(
                api_key.secret_nonce,
                api_key.secret_encrypted,
                api_key.secret_version
            )
            
            decrypted_passphrase = None
            if api_key.passphrase_encrypted:
                decrypted_passphrase = self.encryption.decrypt(
                    api_key.passphrase_nonce,
                    api_key.passphrase_encrypted,
                    api_key.passphrase_version
                )
            
            # Track usage
            api_key.usage_count += 1
            api_key.last_used_at = datetime.utcnow()
            db.commit()
            
            return decrypted_key, decrypted_secret, decrypted_passphrase
            
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {type(e).__name__}")
            raise ValueError("Failed to decrypt API key")
    
    def get_usage_stats(
        self,
        user_id: str,
        key_id: str,
        db: Session,
        days: int = 7
    ) -> APIKeyUsageStats:
        """
        Get API key usage statistics.
        
        Args:
            user_id: User ID
            key_id: API key ID
            db: Database session
            days: Number of days to include in stats
            
        Returns:
            APIKeyUsageStats
            
        Raises:
            ValueError: If API key not found
        """
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        # TODO: Implement detailed usage tracking by day
        # For now, return basic stats
        usage_by_day = {}
        
        return APIKeyUsageStats(
            total_usage=api_key.usage_count,
            last_used_at=api_key.last_used_at,
            usage_by_day=usage_by_day
        )
    
    def check_expiration(
        self,
        db: Session
    ) -> int:
        """
        Check and mark expired API keys as invalid.
        
        Args:
            db: Database session
            
        Returns:
            Number of keys marked as expired
        """
        now = datetime.utcnow()
        
        expired_keys = db.query(APIKey).filter(
            APIKey.expires_at.isnot(None),
            APIKey.expires_at <= now,
            APIKey.is_valid == True
        ).all()
        
        count = 0
        for key in expired_keys:
            key.is_valid = False
            key.validation_error = "API key expired"
            count += 1
        
        if count > 0:
            db.commit()
            logger.info(f"Marked {count} API keys as expired")
        
        return count
    
    def _to_response(self, api_key: APIKey) -> APIKeyResponse:
        """Convert APIKey model to APIKeyResponse"""
        return APIKeyResponse(
            id=str(api_key.id),
            exchange=api_key.exchange,
            exchange_account_id=api_key.exchange_account_id,
            is_valid=api_key.is_valid,
            last_validated_at=api_key.last_validated_at,
            validation_error=api_key.validation_error,
            permissions=api_key.permissions,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            expires_at=api_key.expires_at,
            metadata=api_key.meta
        )
