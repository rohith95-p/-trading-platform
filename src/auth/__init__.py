"""
Authentication module for the Unified Trading Intelligence Platform.

This module provides comprehensive authentication functionality including:
- User registration with email/password
- Email verification
- Login with JWT tokens
- Password reset
- OAuth integration (Google, GitHub)
- Token refresh
- Two-factor authentication (2FA)
- Rate limiting
"""

from src.auth.auth_service import AuthService
from src.auth.jwt_handler import JWTHandler
from src.auth.middleware import auth_required, optional_auth
from src.auth.models import (
    UserRegistration,
    UserLogin,
    TokenResponse,
    PasswordReset,
    EmailVerification,
    TwoFactorSetup,
    TwoFactorVerify,
)

__all__ = [
    "AuthService",
    "JWTHandler",
    "auth_required",
    "optional_auth",
    "UserRegistration",
    "UserLogin",
    "TokenResponse",
    "PasswordReset",
    "EmailVerification",
    "TwoFactorSetup",
    "TwoFactorVerify",
]
