"""
API endpoints for session management.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request

from src.session.models import (
    SessionResponse,
    SessionListResponse,
    SessionRefreshRequest,
)
from src.session.session_service import SessionService
from src.session.middleware import get_current_user_from_session, get_current_session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def get_session_service(request: Request) -> SessionService:
    """
    Dependency to get session service instance.
    
    Args:
        request: FastAPI request
        
    Returns:
        SessionService instance
    """
    # Get database connection from app state
    db = request.app.state.db
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session storage is not configured",
        )
    return SessionService(db)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    include_inactive: bool = False,
    request: Request = None,
    user_id: str = Depends(get_current_user_from_session),
    session_service: SessionService = Depends(get_session_service)
):
    """
    List all sessions for the current user.
    
    Args:
        include_inactive: Whether to include inactive sessions
        user_id: Current user ID (from session)
        session_service: Session service instance
        
    Returns:
        SessionListResponse with list of sessions
    """
    try:
        sessions = await session_service.list_user_sessions(
            user_id=user_id,
            include_inactive=include_inactive
        )
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    request: Request = None,
    user_id: str = Depends(get_current_user_from_session),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Get details for a specific session.
    
    Args:
        session_id: Session ID
        user_id: Current user ID (from session)
        session_service: Session service instance
        
    Returns:
        SessionResponse with session details
    """
    try:
        session = await session_service.get_session(
            session_id=session_id,
            user_id=user_id
        )
        return session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete("/{session_id}")
async def logout_session(
    session_id: UUID,
    request: Request = None,
    user_id: str = Depends(get_current_user_from_session),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Logout a specific session.
    
    Args:
        session_id: Session ID to logout
        user_id: Current user ID (from session)
        session_service: Session service instance
        
    Returns:
        Success message
    """
    try:
        await session_service.logout_session(
            session_id=session_id,
            user_id=user_id
        )
        return {"message": "Session logged out successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error logging out session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout session: {str(e)}"
        )


@router.delete("")
async def logout_all_sessions(
    request: Request = None,
    user_id: str = Depends(get_current_user_from_session),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Logout all sessions for the current user.
    
    Args:
        user_id: Current user ID (from session)
        session_service: Session service instance
        
    Returns:
        Success message with count of logged out sessions
    """
    try:
        count = await session_service.logout_all_sessions(user_id=user_id)
        return {
            "message": f"Logged out {count} sessions successfully",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error logging out all sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout all sessions: {str(e)}"
        )


@router.post("/refresh", response_model=SessionResponse)
async def refresh_session(
    refresh_request: SessionRefreshRequest,
    request: Request = None,
    user_id: str = Depends(get_current_user_from_session),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Refresh a session to extend its expiration.
    
    Args:
        refresh_request: Session refresh request
        user_id: Current user ID (from session)
        session_service: Session service instance
        
    Returns:
        SessionResponse with updated session
    """
    try:
        session = await session_service.refresh_session(
            session_id=refresh_request.session_id,
            user_id=user_id
        )
        return session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh session: {str(e)}"
        )


@router.get("/current/info")
async def get_current_session_info(
    request: Request = None,
    session_info: dict = Depends(get_current_session)
):
    """
    Get information about the current session.
    
    Args:
        session_info: Current session information
        
    Returns:
        Current session details
    """
    return {
        "user_id": session_info["user_id"],
        "session_id": session_info["session_id"],
        "token_payload": session_info["token_payload"]
    }
