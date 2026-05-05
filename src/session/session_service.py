"""
Session service for managing user sessions and token validation.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from src.session.models import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    SessionValidationResult,
)
from src.core.time import utc_now

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user sessions."""
    
    # Session configuration
    ABSOLUTE_EXPIRATION_HOURS = 24  # 24 hours from creation
    IDLE_TIMEOUT_HOURS = 2  # 2 hours of inactivity
    MAX_SESSIONS_PER_USER = 5  # Maximum concurrent sessions
    
    def __init__(self, db_connection):
        """
        Initialize session service.
        
        Args:
            db_connection: Database connection (Supabase client or similar)
        """
        self.db = db_connection
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash JWT token for storage.
        
        Args:
            token: JWT token string
            
        Returns:
            SHA-256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_session(
        self,
        user_id: str,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> SessionResponse:
        """
        Create a new session for user.
        
        Args:
            user_id: User ID
            token: JWT access token
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional session metadata
            
        Returns:
            SessionResponse with session details
            
        Raises:
            ValueError: If session creation fails
        """
        try:
            # Hash token for storage
            token_hash = self.hash_token(token)
            
            # Calculate expiration time
            now = utc_now()
            expires_at = now + timedelta(hours=self.ABSOLUTE_EXPIRATION_HOURS)
            
            # Prepare session data
            session_data = {
                "user_id": user_id,
                "token_hash": token_hash,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_active": True,
                "metadata": metadata or {}
            }
            
            # Insert session into database
            result = self.db.table("sessions").insert(session_data).execute()
            
            if not result.data:
                raise ValueError("Failed to create session")
            
            session = result.data[0]
            logger.info(f"Created session {session['id']} for user {user_id}")
            
            return SessionResponse(**session)
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise ValueError(f"Failed to create session: {str(e)}")
    
    async def validate_session(
        self,
        token: str,
        update_activity: bool = True
    ) -> SessionValidationResult:
        """
        Validate session and optionally update activity timestamp.
        
        Args:
            token: JWT access token
            update_activity: Whether to update last_activity_at
            
        Returns:
            SessionValidationResult with validation status
        """
        try:
            # Hash token for lookup
            token_hash = self.hash_token(token)
            
            # Find session by token hash
            result = self.db.table("sessions").select("*").eq(
                "token_hash", token_hash
            ).eq("is_active", True).execute()
            
            if not result.data:
                return SessionValidationResult(
                    is_valid=False,
                    reason="Session not found or inactive"
                )
            
            session = result.data[0]
            now = utc_now()
            
            # Check absolute expiration
            expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
            if now > expires_at:
                # Mark session as inactive
                await self._deactivate_session(session["id"])
                return SessionValidationResult(
                    is_valid=False,
                    reason="Session expired (absolute timeout)"
                )
            
            # Check idle timeout
            last_activity = datetime.fromisoformat(session["last_activity_at"].replace("Z", "+00:00"))
            idle_duration = now - last_activity
            if idle_duration > timedelta(hours=self.IDLE_TIMEOUT_HOURS):
                # Mark session as inactive
                await self._deactivate_session(session["id"])
                return SessionValidationResult(
                    is_valid=False,
                    reason="Session expired (idle timeout)"
                )
            
            # Update activity timestamp if requested
            if update_activity:
                self.db.table("sessions").update({
                    "last_activity_at": now.isoformat()
                }).eq("id", session["id"]).execute()
            
            return SessionValidationResult(
                is_valid=True,
                session_id=session["id"],
                user_id=session["user_id"]
            )
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return SessionValidationResult(
                is_valid=False,
                reason=f"Validation error: {str(e)}"
            )
    
    async def _deactivate_session(self, session_id: str) -> None:
        """
        Mark session as inactive.
        
        Args:
            session_id: Session ID to deactivate
        """
        try:
            self.db.table("sessions").update({
                "is_active": False
            }).eq("id", session_id).execute()
            logger.info(f"Deactivated session {session_id}")
        except Exception as e:
            logger.error(f"Error deactivating session {session_id}: {str(e)}")
    
    async def logout_session(self, session_id: UUID, user_id: str) -> bool:
        """
        Logout specific session.
        
        Args:
            session_id: Session ID to logout
            user_id: User ID (for authorization)
            
        Returns:
            True if logout successful
            
        Raises:
            ValueError: If session not found or unauthorized
        """
        try:
            # Verify session belongs to user
            result = self.db.table("sessions").select("user_id").eq(
                "id", str(session_id)
            ).execute()
            
            if not result.data:
                raise ValueError("Session not found")
            
            if result.data[0]["user_id"] != user_id:
                raise ValueError("Unauthorized to logout this session")
            
            # Deactivate session
            await self._deactivate_session(str(session_id))
            logger.info(f"User {user_id} logged out session {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging out session: {str(e)}")
            raise ValueError(f"Failed to logout session: {str(e)}")
    
    async def logout_all_sessions(self, user_id: str) -> int:
        """
        Logout all sessions for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions logged out
        """
        try:
            # Deactivate all active sessions for user
            result = self.db.table("sessions").update({
                "is_active": False
            }).eq("user_id", user_id).eq("is_active", True).execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Logged out {count} sessions for user {user_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error logging out all sessions: {str(e)}")
            raise ValueError(f"Failed to logout all sessions: {str(e)}")
    
    async def list_user_sessions(
        self,
        user_id: str,
        include_inactive: bool = False
    ) -> SessionListResponse:
        """
        List all sessions for user.
        
        Args:
            user_id: User ID
            include_inactive: Whether to include inactive sessions
            
        Returns:
            SessionListResponse with list of sessions
        """
        try:
            # Query sessions
            query = self.db.table("sessions").select("*").eq("user_id", user_id)
            
            if not include_inactive:
                query = query.eq("is_active", True)
            
            result = query.order("last_activity_at", desc=True).execute()
            
            sessions = [SessionResponse(**s) for s in result.data] if result.data else []
            active_count = sum(1 for s in sessions if s.is_active)
            
            return SessionListResponse(
                sessions=sessions,
                total=len(sessions),
                active=active_count
            )
            
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            raise ValueError(f"Failed to list sessions: {str(e)}")
    
    async def get_session(
        self,
        session_id: UUID,
        user_id: str
    ) -> SessionResponse:
        """
        Get session details.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            
        Returns:
            SessionResponse with session details
            
        Raises:
            ValueError: If session not found or unauthorized
        """
        try:
            result = self.db.table("sessions").select("*").eq(
                "id", str(session_id)
            ).execute()
            
            if not result.data:
                raise ValueError("Session not found")
            
            session = result.data[0]
            
            if session["user_id"] != user_id:
                raise ValueError("Unauthorized to view this session")
            
            return SessionResponse(**session)
            
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            raise ValueError(f"Failed to get session: {str(e)}")
    
    async def refresh_session(
        self,
        session_id: UUID,
        user_id: str
    ) -> SessionResponse:
        """
        Refresh session expiration (extend by ABSOLUTE_EXPIRATION_HOURS).
        
        Args:
            session_id: Session ID to refresh
            user_id: User ID (for authorization)
            
        Returns:
            SessionResponse with updated session
            
        Raises:
            ValueError: If session not found or unauthorized
        """
        try:
            # Verify session belongs to user and is active
            result = self.db.table("sessions").select("*").eq(
                "id", str(session_id)
            ).eq("user_id", user_id).eq("is_active", True).execute()
            
            if not result.data:
                raise ValueError("Session not found or inactive")
            
            # Calculate new expiration
            now = utc_now()
            new_expires_at = now + timedelta(hours=self.ABSOLUTE_EXPIRATION_HOURS)
            
            # Update session
            update_result = self.db.table("sessions").update({
                "expires_at": new_expires_at.isoformat(),
                "last_activity_at": now.isoformat()
            }).eq("id", str(session_id)).execute()
            
            if not update_result.data:
                raise ValueError("Failed to refresh session")
            
            logger.info(f"Refreshed session {session_id} for user {user_id}")
            
            return SessionResponse(**update_result.data[0])
            
        except Exception as e:
            logger.error(f"Error refreshing session: {str(e)}")
            raise ValueError(f"Failed to refresh session: {str(e)}")
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (background task).
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            # Call database function to cleanup expired sessions
            result = self.db.rpc("cleanup_expired_sessions").execute()
            
            count = result.data if result.data else 0
            logger.info(f"Cleaned up {count} expired sessions")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
