"""
Authentication service for user management and authentication.

This service integrates with Supabase Auth for authentication operations.
"""

import logging
from typing import Optional, Dict, Any
from datetime import timedelta
import pyotp
import qrcode
import io
import base64
from supabase import create_client, Client
from src.config import settings

from src.auth.jwt_handler import JWTHandler
from src.auth.models import (
    UserRegistration,
    UserLogin,
    TokenResponse,
    PasswordReset,
    TwoFactorSetup,
)
from src.core.time import utc_now

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management."""
    
    def __init__(self):
        """Initialize authentication service."""
        self.jwt_handler = JWTHandler()
        # Local in-memory stores used when DB-backed profile/2FA state is unavailable.
        self._two_factor_store: Dict[str, Dict[str, Any]] = {}
        self._last_login_store: Dict[str, datetime] = {}
        
        # Initialize Supabase client using centralised settings
        supabase_url = settings.SUPABASE_URL
        # Prefer service key for server-side operations; fall back to anon key
        supabase_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
        
        if supabase_url and supabase_key:
            try:
                self.supabase: Optional[Client] = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialised successfully")
            except Exception as exc:
                logger.warning(
                    "Supabase client could not be initialised. Falling back to local auth only: %s",
                    exc,
                )
                self.supabase = None
        else:
            logger.warning("Supabase credentials not configured. Using local auth only.")
            self.supabase = None
    
    async def register_user(self, registration: UserRegistration) -> TokenResponse:
        """
        Register a new user.
        
        Args:
            registration: User registration data
            
        Returns:
            TokenResponse with access and refresh tokens
            
        Raises:
            ValueError: If user already exists or validation fails
        """
        # Hash password
        # Create user in Supabase Auth
        if self.supabase:
            try:
                auth_response = self.supabase.auth.sign_up({
                    "email": registration.email,
                    "password": registration.password,
                    "options": {
                        "data": {
                            "full_name": registration.full_name,
                            "timezone": registration.timezone,
                        }
                    }
                })
                
                user_id = auth_response.user.id
                
            except Exception as e:
                logger.error(f"Supabase registration error: {str(e)}")
                raise ValueError(f"Registration failed: {str(e)}")
        else:
            # Local registration (for development)
            import uuid
            user_id = str(uuid.uuid4())
        
        # Create tokens
        access_token = self.jwt_handler.create_access_token(user_id, registration.email)
        refresh_token = self.jwt_handler.create_refresh_token(user_id, registration.email)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.jwt_handler.access_token_expire_hours * 3600,
            user_id=user_id,
            email=registration.email
        )
    
    async def login_user(
        self,
        login: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenResponse:
        """
        Authenticate user and return tokens.
        
        Args:
            login: User login credentials
            ip_address: Client IP address (for session tracking)
            user_agent: Client user agent (for session tracking)
            
        Returns:
            TokenResponse with access and refresh tokens
            
        Raises:
            ValueError: If credentials are invalid
        """
        if self.supabase:
            try:
                auth_response = self.supabase.auth.sign_in_with_password({
                    "email": login.email,
                    "password": login.password
                })
                
                user_id = auth_response.user.id
                
            except Exception as e:
                logger.error(f"Supabase login error: {str(e)}")
                raise ValueError("Invalid email or password")
        else:
            # Local login (for development)
            import uuid
            user_id = str(uuid.uuid4())
        
        # Create tokens
        access_token = self.jwt_handler.create_access_token(user_id, login.email)
        refresh_token = self.jwt_handler.create_refresh_token(user_id, login.email)
        
        # Create session
        try:
            from src.session.session_service import SessionService
            session_service = SessionService(self.supabase)
            session = await session_service.create_session(
                user_id=user_id,
                token=access_token,
                ip_address=ip_address,
                user_agent=user_agent
            )
            logger.info(f"Created session {session.id} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to create session: {str(e)}")
            # Don't fail login if session creation fails
        
        # Update last login time
        now = utc_now()
        self._last_login_store[user_id] = now
        if self.supabase:
            try:
                self.supabase.auth.admin.update_user_by_id(
                    user_id,
                    {"user_metadata": {"last_login_at": now.isoformat()}},
                )
            except Exception as exc:
                logger.warning(f"Could not persist last_login_at for {user_id}: {exc}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.jwt_handler.access_token_expire_hours * 3600,
            user_id=user_id,
            email=login.email
        )
    
    async def verify_email(self, token: str) -> bool:
        """
        Verify user email with token.
        
        Args:
            token: Email verification token
            
        Returns:
            True if verification successful
            
        Raises:
            ValueError: If token is invalid
        """
        if self.supabase:
            try:
                self.supabase.auth.verify_otp({
                    "token": token,
                    "type": "email"
                })
                return True
            except Exception as e:
                logger.error(f"Email verification error: {str(e)}")
                raise ValueError("Invalid verification token")
        else:
            # Local verification (for development)
            return True
    
    async def resend_verification_email(self, email: str) -> bool:
        """
        Resend verification email.
        
        Args:
            email: User email address
            
        Returns:
            True if email sent successfully
        """
        if self.supabase:
            try:
                self.supabase.auth.resend({
                    "type": "signup",
                    "email": email
                })
                return True
            except Exception as e:
                logger.error(f"Resend verification error: {str(e)}")
                return False
        else:
            # Local (for development)
            return True
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset email.
        
        Args:
            email: User email address
            
        Returns:
            True if email sent successfully
        """
        if self.supabase:
            try:
                self.supabase.auth.reset_password_email(email)
                return True
            except Exception as e:
                logger.error(f"Password reset request error: {str(e)}")
                return False
        else:
            # Local (for development)
            return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password with token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if password reset successful
            
        Raises:
            ValueError: If token is invalid
        """
        if self.supabase:
            try:
                self.supabase.auth.update_user({
                    "password": new_password
                })
                return True
            except Exception as e:
                logger.error(f"Password reset error: {str(e)}")
                raise ValueError("Invalid reset token")
        else:
            # Local (for development)
            return True
    
    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access and refresh tokens.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            TokenResponse with new tokens
            
        Raises:
            ValueError: If refresh token is invalid
        """
        try:
            # Verify and decode refresh token
            payload = self.jwt_handler.verify_token(refresh_token, token_type="refresh")
            user_id = payload["sub"]
            email = payload["email"]
            
            # Create new tokens
            new_access_token = self.jwt_handler.create_access_token(user_id, email)
            new_refresh_token = self.jwt_handler.create_refresh_token(user_id, email)
            
            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=self.jwt_handler.access_token_expire_hours * 3600,
                user_id=user_id,
                email=email
            )
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise ValueError("Invalid refresh token")
    
    async def setup_two_factor(self, user_id: str, email: str) -> TwoFactorSetup:
        """
        Setup two-factor authentication for user.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            TwoFactorSetup with secret and QR code
        """
        # Generate secret
        secret = pyotp.random_base32()
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=email,
            issuer_name="Trading Platform"
        )
        
        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"
        
        # Generate backup codes
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        
        self._two_factor_store[user_id] = {
            "secret": secret,
            "backup_codes": set(backup_codes),
            "enabled": False,
            "updated_at": utc_now(),
        }
        
        return TwoFactorSetup(
            secret=secret,
            qr_code=qr_code_data_url,
            backup_codes=backup_codes
        )
    
    async def verify_two_factor(self, user_id: str, code: str) -> bool:
        """
        Verify two-factor authentication code.
        
        Args:
            user_id: User ID
            code: 6-digit 2FA code
            
        Returns:
            True if code is valid
        """
        store = self._two_factor_store.get(user_id)
        if not store:
            return False

        backup_codes = store.get("backup_codes", set())
        if code in backup_codes:
            backup_codes.remove(code)
            store["updated_at"] = utc_now()
            return True
        
        secret = store.get("secret")
        if not secret:
            return False

        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    async def enable_two_factor(self, user_id: str) -> bool:
        """
        Mark 2FA as enabled for user after successful code verification.
        
        Args:
            user_id: User ID
            
        Returns:
            True if state was updated
        """
        store = self._two_factor_store.get(user_id)
        if not store:
            return False

        store["enabled"] = True
        store["updated_at"] = utc_now()

        if self.supabase:
            try:
                self.supabase.auth.admin.update_user_by_id(
                    user_id,
                    {"user_metadata": {"two_factor_enabled": True}},
                )
            except Exception as exc:
                logger.warning(f"Could not persist 2FA enabled state for {user_id}: {exc}")

        return True
    
    async def disable_two_factor(self, user_id: str) -> bool:
        """
        Disable two-factor authentication for user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if disabled successfully
        """
        if user_id in self._two_factor_store:
            del self._two_factor_store[user_id]

        if self.supabase:
            try:
                self.supabase.auth.admin.update_user_by_id(
                    user_id,
                    {"user_metadata": {"two_factor_enabled": False}},
                )
            except Exception as exc:
                logger.warning(f"Could not persist 2FA disable state for {user_id}: {exc}")

        return True

    async def verify_user_password(self, email: str, password: str) -> bool:
        """
        Verify current password for sensitive operations (e.g. disabling 2FA).
        
        Args:
            email: User email
            password: Candidate password
            
        Returns:
            True if password is valid
        """
        if self.supabase:
            try:
                self.supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })
                return True
            except Exception:
                return False

        # Local mode does not keep password hashes here; require non-empty confirmation.
        return bool(password and password.strip())

    async def get_user_profile(self, user_id: str):
        """
        Fetch user profile from Supabase Auth or fall back to minimal profile.

        Args:
            user_id: User ID from JWT

        Returns:
            UserProfile instance
        """
        from src.auth.models import UserProfile

        if self.supabase:
            try:
                # Use admin API to get user by ID
                response = self.supabase.auth.admin.get_user_by_id(user_id)
                user = response.user
                user_meta = user.user_metadata or {}
                return UserProfile(
                    id=user_id,
                    email=user.email or "",
                    full_name=user_meta.get("full_name"),
                    avatar_url=user_meta.get("avatar_url"),
                    timezone=user_meta.get("timezone", "UTC"),
                    is_active=True,
                    is_premium=False,
                    subscription_tier="free",
                    email_verified=user.email_confirmed_at is not None,
                    two_factor_enabled=False,
                    created_at=user.created_at,
                    last_login_at=user.last_sign_in_at,
                )
            except Exception as e:
                logger.error(f"Failed to fetch user profile from Supabase: {e}")

        # Fallback: return minimal profile from JWT claims only
        return UserProfile(
            id=user_id,
            email="",
            full_name=None,
            avatar_url=None,
            timezone="UTC",
            is_active=True,
            is_premium=False,
            subscription_tier="free",
            email_verified=False,
            two_factor_enabled=False,
            created_at=utc_now(),
            last_login_at=None,
        )

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        Change user password. Re-authenticates with current password first.

        Args:
            user_id: User ID
            current_password: The user's existing password
            new_password: The desired new password

        Returns:
            True if password changed successfully, False if current password wrong

        Raises:
            ValueError: If new password is invalid
        """
        if self.supabase:
            try:
                # We need the user's email to re-authenticate
                profile = await self.get_user_profile(user_id)
                email = profile.email

                # Verify current password by attempting sign-in
                self.supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": current_password,
                })

                # Update to new password
                self.supabase.auth.update_user({"password": new_password})
                logger.info(f"Password changed for user {user_id}")
                return True
            except Exception as e:
                error_msg = str(e).lower()
                if "invalid" in error_msg or "credentials" in error_msg:
                    return False
                logger.error(f"Password change error for {user_id}: {e}")
                return False
        else:
            # Local dev mode — always succeed
            logger.warning("Local auth mode: password change simulated")
            return True

    async def social_login(self, registration: UserRegistration, provider: str) -> TokenResponse:
        """
        Login or register user via social OAuth provider.
        
        Args:
            registration: User registration data from OAuth
            provider: OAuth provider name (google, github)
            
        Returns:
            TokenResponse with access and refresh tokens
        """
        import uuid
        user_id = str(uuid.uuid4())
        
        access_token = self.jwt_handler.create_access_token(user_id, registration.email)
        refresh_token = self.jwt_handler.create_refresh_token(user_id, registration.email)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.jwt_handler.access_token_expire_hours * 3600,
            user_id=user_id,
            email=registration.email
        )
    
    async def logout_user(self, access_token: str, user_id: Optional[str] = None) -> bool:
        """
        Logout user and invalidate token/session.
        
        Args:
            access_token: User's access token
            user_id: User ID (optional, for session cleanup)
            
        Returns:
            True if logout successful
        """
        # Invalidate session if user_id provided
        if user_id:
            try:
                from src.session.session_service import SessionService
                session_service = SessionService(self.supabase)
                await session_service.logout_all_sessions(user_id)
                logger.info(f"Logged out all sessions for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to logout sessions: {str(e)}")
        
        if self.supabase:
            try:
                self.supabase.auth.sign_out()
                return True
            except Exception as e:
                logger.error(f"Logout error: {str(e)}")
                return False
        else:
            # Local (for development)
            return True
