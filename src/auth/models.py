"""
Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


class UserRegistration(BaseModel):
    """User registration request model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "timezone": "America/New_York",
            }
        }
    )

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    timezone: str = Field("UTC", description="User's timezone")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    """User login request model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "remember_me": False,
            }
        }
    )

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Remember user session")


class TokenResponse(BaseModel):
    """Authentication token response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
            }
        }
    )

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")


class TokenRefresh(BaseModel):
    """Token refresh request model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )

    refresh_token: str = Field(..., description="Refresh token")


class PasswordReset(BaseModel):
    """Password reset request model."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset-token-here",
                "new_password": "NewSecurePass123!",
            }
        }
    )

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class EmailVerification(BaseModel):
    """Email verification request model."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"token": "verification-token-here"}}
    )

    token: str = Field(..., description="Email verification token")


class ResendVerification(BaseModel):
    """Resend verification email request model."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )

    email: EmailStr = Field(..., description="User email address")


class TwoFactorSetup(BaseModel):
    """Two-factor authentication setup response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "backup_codes": ["12345678", "87654321", "11223344"],
            }
        }
    )

    secret: str = Field(..., description="2FA secret key")
    qr_code: str = Field(..., description="QR code data URL")
    backup_codes: list[str] = Field(..., description="Backup recovery codes")


class TwoFactorVerify(BaseModel):
    """Two-factor authentication verification model."""

    model_config = ConfigDict(json_schema_extra={"example": {"code": "123456"}})

    code: str = Field(..., min_length=6, max_length=6, description="6-digit 2FA code")

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Validate code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Code must contain only digits")
        if len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        return v


class TwoFactorEnable(BaseModel):
    """Enable two-factor authentication model."""

    model_config = ConfigDict(json_schema_extra={"example": {"code": "123456"}})

    code: str = Field(..., min_length=6, max_length=6, description="6-digit 2FA code")

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Validate code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Code must contain only digits")
        if len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        return v


class TwoFactorDisable(BaseModel):
    """Disable two-factor authentication model."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"password": "SecurePass123!"}}
    )

    password: str = Field(..., description="User password for confirmation")


class OAuthCallback(BaseModel):
    """OAuth callback model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "oauth-code-here",
                "state": "random-state-string",
            }
        }
    )

    code: str = Field(..., description="OAuth authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")


class UserProfile(BaseModel):
    """User profile response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "timezone": "America/New_York",
                "is_active": True,
                "is_premium": False,
                "subscription_tier": "free",
                "email_verified": True,
                "two_factor_enabled": False,
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-15T12:00:00Z",
            }
        }
    )

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    timezone: str = Field(..., description="User's timezone")
    is_active: bool = Field(..., description="Account active status")
    is_premium: bool = Field(..., description="Premium account flag")
    subscription_tier: str = Field(..., description="Subscription level")
    email_verified: bool = Field(..., description="Email verification status")
    two_factor_enabled: bool = Field(..., description="2FA enabled status")
    created_at: datetime = Field(..., description="Account creation time")
    last_login_at: Optional[datetime] = Field(None, description="Last login time")


class ChangePassword(BaseModel):
    """Change password request model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!",
            }
        }
    )

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v
