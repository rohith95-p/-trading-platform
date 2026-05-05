"""
Authentication API endpoints.
"""

import secrets
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from src.auth.auth_service import AuthService
from src.auth.middleware import get_current_user, get_current_user_optional
from src.auth.oauth_state import build_oauth_state, oauth_state_cookie_name
from src.auth.models import (
    UserRegistration,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    PasswordReset,
    PasswordResetConfirm,
    EmailVerification,
    ResendVerification,
    TwoFactorSetup,
    TwoFactorVerify,
    TwoFactorEnable,
    TwoFactorDisable,
    UserProfile,
    ChangePassword,
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize auth service
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request,
    registration: UserRegistration
) -> TokenResponse:
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **full_name**: User's full name (optional)
    - **timezone**: User's timezone (default: UTC)
    
    Returns access and refresh tokens upon successful registration.
    """
    try:
        return await auth_service.register_user(registration)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: UserLogin
) -> TokenResponse:
    """
    Login with email and password.
    
    - **email**: User email address
    - **password**: User password
    - **remember_me**: Keep user logged in (default: false)
    
    Returns access and refresh tokens upon successful authentication.
    """
    try:
        return await auth_service.login_user(
            login_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Logout current user and invalidate tokens.
    
    Requires authentication.
    """
    try:
        user_id = current_user["user_id"]
        await auth_service.logout_user(access_token="", user_id=user_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logged out successfully"}
        )
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/hour")
async def refresh_token(
    request: Request,
    token_data: TokenRefresh
) -> TokenResponse:
    """
    Refresh access and refresh tokens.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access and refresh tokens.
    """
    try:
        return await auth_service.refresh_tokens(token_data.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/verify-email")
@limiter.limit("10/hour")
async def verify_email(
    request: Request,
    verification: EmailVerification
) -> JSONResponse:
    """
    Verify user email with token.
    
    - **token**: Email verification token from email
    
    Returns success message upon verification.
    """
    try:
        await auth_service.verify_email(verification.token)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Email verified successfully"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/resend-verification")
@limiter.limit("3/hour")
async def resend_verification(
    request: Request,
    resend: ResendVerification
) -> JSONResponse:
    """
    Resend verification email.
    
    - **email**: User email address
    
    Returns success message.
    """
    try:
        await auth_service.resend_verification_email(resend.email)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Verification email sent"}
        )
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/password-reset")
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_request: PasswordReset
) -> JSONResponse:
    """
    Request password reset email.
    
    - **email**: User email address
    
    Returns success message. Email will be sent if account exists.
    """
    try:
        await auth_service.request_password_reset(reset_request.email)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password reset email sent if account exists"}
        )
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Always return success to prevent email enumeration
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password reset email sent if account exists"}
        )


@router.post("/password-reset/confirm")
@limiter.limit("5/hour")
async def confirm_password_reset(
    request: Request,
    reset_confirm: PasswordResetConfirm
) -> JSONResponse:
    """
    Confirm password reset with token.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 chars, uppercase, lowercase, digit, special char)
    
    Returns success message upon password reset.
    """
    try:
        await auth_service.reset_password(reset_confirm.token, reset_confirm.new_password)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password reset successfully"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password reset confirm error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/change-password")
async def change_password(
    password_change: ChangePassword,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Change user password.
    
    - **current_password**: Current password
    - **new_password**: New password (min 8 chars, uppercase, lowercase, digit, special char)
    
    Requires authentication.
    """
    try:
        success = await auth_service.change_password(
            user_id=current_user["user_id"],
            current_password=password_change.current_password,
            new_password=password_change.new_password,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password changed successfully"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
) -> UserProfile:
    """
    Get current user profile.
    
    Requires authentication.
    """
    try:
        profile = await auth_service.get_user_profile(current_user["user_id"])
        return profile
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile"
        )


@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_two_factor_auth(
    current_user: dict = Depends(get_current_user)
) -> TwoFactorSetup:
    """
    Setup two-factor authentication.
    
    Returns QR code and backup codes for 2FA setup.
    Requires authentication.
    """
    try:
        return await auth_service.setup_two_factor(
            current_user["user_id"],
            current_user["email"]
        )
    except Exception as e:
        logger.error(f"2FA setup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA setup failed"
        )


@router.post("/2fa/enable")
async def enable_two_factor_auth(
    enable_data: TwoFactorEnable,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Enable two-factor authentication.
    
    - **code**: 6-digit code from authenticator app
    
    Requires authentication.
    """
    try:
        is_valid = await auth_service.verify_two_factor(
            current_user["user_id"],
            enable_data.code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA code"
            )
        enabled = await auth_service.enable_two_factor(current_user["user_id"])
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA setup is missing. Run /auth/2fa/setup first."
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "2FA enabled successfully"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA enable error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA enable failed"
        )


@router.post("/2fa/verify")
async def verify_two_factor_code(
    verify_data: TwoFactorVerify,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Verify two-factor authentication code.
    
    - **code**: 6-digit code from authenticator app
    
    Requires authentication.
    """
    try:
        is_valid = await auth_service.verify_two_factor(
            current_user["user_id"],
            verify_data.code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA code"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "2FA code verified"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verify error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA verification failed"
        )


@router.post("/2fa/disable")
async def disable_two_factor_auth(
    disable_data: TwoFactorDisable,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Disable two-factor authentication.
    
    - **password**: User password for confirmation
    
    Requires authentication.
    """
    try:
        password_ok = await auth_service.verify_user_password(
            email=current_user["email"],
            password=disable_data.password,
        )
        if not password_ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password verification failed"
            )

        await auth_service.disable_two_factor(current_user["user_id"])
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "2FA disabled successfully"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA disable error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA disable failed"
        )


def _validate_oauth_state(request: Request, provider: str, state: str | None) -> None:
    expected_state = request.cookies.get(oauth_state_cookie_name(provider))
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )


def _build_social_registration(email: str, full_name: str | None = None) -> UserRegistration:
    fallback_password = f"{secrets.token_urlsafe(18)}Aa1!"
    return UserRegistration(
        email=email,
        password=fallback_password,
        full_name=full_name or "",
    )


def _frontend_auth_callback_url(token_response: TokenResponse) -> str:
    params = urllib.parse.urlencode(
        {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "expires_in": token_response.expires_in,
            "email": token_response.email,
            "user_id": token_response.user_id,
        }
    )
    return f"{settings.FRONTEND_BASE_URL}/auth/callback#{params}"


@router.get("/oauth/google")
async def oauth_google_login(request: Request) -> RedirectResponse:
    """
    Initiate Google OAuth login.
    
    Redirects to Google OAuth consent screen.
    """
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    redirect_uri = f"{settings.API_BASE_URL}/auth/oauth/callback/google"
    state = build_oauth_state()
    
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "state": state,
    })

    response = RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key=oauth_state_cookie_name("google"),
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.is_production(),
        samesite="lax",
    )
    return response


@router.get("/oauth/github")
async def oauth_github_login(request: Request) -> RedirectResponse:
    """
    Initiate GitHub OAuth login.
    
    Redirects to GitHub OAuth consent screen.
    """
    client_id = settings.GITHUB_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    redirect_uri = f"{settings.API_BASE_URL}/auth/oauth/callback/github"
    state = build_oauth_state()
    
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
        "state": state,
    })

    response = RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{params}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key=oauth_state_cookie_name("github"),
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.is_production(),
        samesite="lax",
    )
    return response


@router.get("/oauth/callback/google")
async def oauth_google_callback(request: Request, code: str, state: str = None) -> RedirectResponse:
    """
    Handle Google OAuth callback.
    
    - **code**: OAuth authorization code
    - **state**: OAuth state parameter
    
    Returns access and refresh tokens upon successful authentication.
    """
    try:
        import httpx

        _validate_oauth_state(request, "google", state)
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="Google OAuth is not configured")

        token_url = "https://oauth2.googleapis.com/token"
        user_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        async with httpx.AsyncClient() as client:
            token_res = await client.post(token_url, data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.API_BASE_URL}/auth/oauth/callback/google",
                "grant_type": "authorization_code",
            })
            
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")
            
            access_token = token_res.json().get("access_token")

            user_res = await client.get(user_url, headers={"Authorization": f"Bearer {access_token}"})
            user_data = user_res.json()

            token_response = await auth_service.social_login(
                _build_social_registration(
                    email=user_data.get("email", ""),
                    full_name=user_data.get("name", ""),
                ),
                "google",
            )
            response = RedirectResponse(
                url=_frontend_auth_callback_url(token_response),
                status_code=status.HTTP_302_FOUND,
            )
            response.delete_cookie(oauth_state_cookie_name("google"))
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")


@router.get("/oauth/callback/github")
async def oauth_github_callback(request: Request, code: str, state: str = None) -> RedirectResponse:
    """
    Handle GitHub OAuth callback.
    
    - **code**: OAuth authorization code
    - **state**: OAuth state parameter
    
    Returns access and refresh tokens upon successful authentication.
    """
    try:
        import httpx

        _validate_oauth_state(request, "github", state)
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

        token_url = "https://github.com/login/oauth/access_token"
        user_url = "https://api.github.com/user"

        async with httpx.AsyncClient() as client:
            token_res = await client.post(token_url, data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": f"{settings.API_BASE_URL}/auth/oauth/callback/github",
            }, headers={"Accept": "application/json"})
            
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")
            
            access_token = token_res.json().get("access_token")
            
            user_res = await client.get(user_url, headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            })
            user_data = user_res.json()

            email = user_data.get("email") or f"github_{user_data.get('id')}@placeholder.com"
            token_response = await auth_service.social_login(
                _build_social_registration(
                    email=email,
                    full_name=user_data.get("name", ""),
                ),
                "github",
            )
            response = RedirectResponse(
                url=_frontend_auth_callback_url(token_response),
                status_code=status.HTTP_302_FOUND,
            )
            response.delete_cookie(oauth_state_cookie_name("github"))
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")
