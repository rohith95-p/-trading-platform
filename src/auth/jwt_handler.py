"""
JWT token handler for authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import logging
from src.config import settings
from src.core.time import utc_from_timestamp, utc_now

logger = logging.getLogger(__name__)


class JWTHandler:
    """Handle JWT token creation and validation."""
    
    def __init__(self):
        """Initialize JWT handler with configuration."""
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_hours = settings.JWT_EXPIRATION_HOURS
        self.refresh_token_expire_days = settings.JWT_REFRESH_EXPIRATION_DAYS
        self.issuer = settings.JWT_ISSUER
        self.audience = settings.JWT_AUDIENCE
        self.leeway_seconds = settings.JWT_LEEWAY_SECONDS
        
        if self.secret_key in {
            "your-secret-key-change-in-production",
            "change-this-in-production-use-railway-env-var",
        }:
            logger.warning("Using default JWT secret key. Change this in production!")
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new access token.
        
        Args:
            user_id: User ID
            email: User email
            additional_claims: Additional claims to include in token
            
        Returns:
            JWT access token string
        """
        now = utc_now()
        expires_at = now + timedelta(hours=self.access_token_expire_hours)

        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "iat": now,
            "nbf": now,
            "exp": expires_at,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": str(uuid4()),
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        email: str
    ) -> str:
        """
        Create a new refresh token.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            JWT refresh token string
        """
        now = utc_now()
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "nbf": now,
            "exp": expires_at,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": str(uuid4()),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token has expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.leeway_seconds,
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise InvalidTokenError(f"Invalid token type. Expected {token_type}")
            
            return payload
            
        except ExpiredSignatureError:
            logger.warning(f"Token expired: {token[:20]}...")
            raise
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Create new access and refresh tokens from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            InvalidTokenError: If refresh token is invalid
            ExpiredSignatureError: If refresh token has expired
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token, token_type="refresh")
        
        user_id = payload["sub"]
        email = payload["email"]
        
        # Create new tokens
        new_access_token = self.create_access_token(user_id, email)
        new_refresh_token = self.create_refresh_token(user_id, email)
        
        return new_access_token, new_refresh_token
    
    def decode_token_without_verification(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging only).
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
        """
        return jwt.decode(token, options={"verify_signature": False})
    
    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time.
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration datetime or None if invalid
        """
        try:
            payload = self.decode_token_without_verification(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return utc_from_timestamp(exp_timestamp)
            return None
        except Exception as e:
            logger.error(f"Error getting token expiration: {str(e)}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired.
        
        Args:
            token: JWT token string
            
        Returns:
            True if expired, False otherwise
        """
        expiration = self.get_token_expiration(token)
        if expiration:
            return utc_now() > expiration
        return True
