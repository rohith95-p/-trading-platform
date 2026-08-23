"""
Unit tests for session management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.session.session_service import SessionService
from src.session.models import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    SessionValidationResult,
)


class TestSessionService:
    """Test session service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        db = Mock()
        db.table = Mock(return_value=db)
        db.select = Mock(return_value=db)
        db.insert = Mock(return_value=db)
        db.update = Mock(return_value=db)
        db.eq = Mock(return_value=db)
        db.order = Mock(return_value=db)
        db.rpc = Mock(return_value=db)
        return db
    
    @pytest.fixture
    def session_service(self, mock_db):
        """Create session service instance."""
        return SessionService(mock_db)
    
    def test_hash_token(self, session_service):
        """Test token hashing."""
        token = "test_token_12345"
        hash1 = session_service.hash_token(token)
        hash2 = session_service.hash_token(token)
        
        # Same token should produce same hash
        assert hash1 == hash2
        
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64
        
        # Different token should produce different hash
        different_token = "different_token"
        hash3 = session_service.hash_token(different_token)
        assert hash1 != hash3
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_db):
        """Test successful session creation."""
        user_id = str(uuid4())
        token = "test_access_token"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        # Mock database response
        session_id = str(uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=24)
        
        mock_db.execute = Mock(return_value=Mock(data=[{
            "id": session_id,
            "user_id": user_id,
            "token_hash": session_service.hash_token(token),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": now.isoformat(),
            "last_activity_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "metadata": {}
        }]))
        
        # Create session
        session = await session_service.create_session(
            user_id=user_id,
            token=token,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Verify session created
        assert str(session.user_id) == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_create_session_failure(self, session_service, mock_db):
        """Test session creation failure."""
        user_id = str(uuid4())
        token = "test_access_token"
        
        # Mock database failure
        mock_db.execute = Mock(return_value=Mock(data=None))
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Failed to create session"):
            await session_service.create_session(
                user_id=user_id,
                token=token
            )
    
    @pytest.mark.asyncio
    async def test_validate_session_success(self, session_service, mock_db):
        """Test successful session validation."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        token = "test_access_token"
        token_hash = session_service.hash_token(token)
        
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=24)
        last_activity = now - timedelta(minutes=30)
        
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=[{
            "id": session_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "created_at": now.isoformat(),
            "last_activity_at": last_activity.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "metadata": {}
        }]))
        
        # Validate session
        result = await session_service.validate_session(token)
        
        # Verify validation successful
        assert result.is_valid is True
        assert result.user_id == user_id
        assert str(result.session_id) == session_id
    
    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, session_service, mock_db):
        """Test session validation when session not found."""
        token = "nonexistent_token"
        
        # Mock database response (no session found)
        mock_db.execute = Mock(return_value=Mock(data=[]))
        
        # Validate session
        result = await session_service.validate_session(token)
        
        # Verify validation failed
        assert result.is_valid is False
        assert "not found" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_validate_session_expired_absolute(self, session_service, mock_db):
        """Test session validation with absolute expiration."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        token = "test_access_token"
        token_hash = session_service.hash_token(token)
        
        now = datetime.utcnow()
        expires_at = now - timedelta(hours=1)  # Expired 1 hour ago
        
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=[{
            "id": session_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "created_at": (now - timedelta(hours=25)).isoformat(),
            "last_activity_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "metadata": {}
        }]))
        
        # Validate session
        result = await session_service.validate_session(token)
        
        # Verify validation failed due to expiration
        assert result.is_valid is False
        assert "expired" in result.reason.lower()
        assert "absolute" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_validate_session_expired_idle(self, session_service, mock_db):
        """Test session validation with idle timeout."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        token = "test_access_token"
        token_hash = session_service.hash_token(token)
        
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=12)  # Not expired yet
        last_activity = now - timedelta(hours=3)  # Idle for 3 hours
        
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=[{
            "id": session_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "last_activity_at": last_activity.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "metadata": {}
        }]))
        
        # Validate session
        result = await session_service.validate_session(token)
        
        # Verify validation failed due to idle timeout
        assert result.is_valid is False
        assert "expired" in result.reason.lower()
        assert "idle" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_logout_session_success(self, session_service, mock_db):
        """Test successful session logout."""
        user_id = str(uuid4())
        session_id = uuid4()
        
        # Mock database responses
        mock_db.execute = Mock(return_value=Mock(data=[{
            "user_id": user_id
        }]))
        
        # Logout session
        result = await session_service.logout_session(session_id, user_id)
        
        # Verify logout successful
        assert result is True
    
    @pytest.mark.asyncio
    async def test_logout_session_not_found(self, session_service, mock_db):
        """Test logout when session not found."""
        user_id = str(uuid4())
        session_id = uuid4()
        
        # Mock database response (no session found)
        mock_db.execute = Mock(return_value=Mock(data=[]))
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Session not found"):
            await session_service.logout_session(session_id, user_id)
    
    @pytest.mark.asyncio
    async def test_logout_session_unauthorized(self, session_service, mock_db):
        """Test logout when user doesn't own session."""
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        session_id = uuid4()
        
        # Mock database response (session belongs to different user)
        mock_db.execute = Mock(return_value=Mock(data=[{
            "user_id": other_user_id
        }]))
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Unauthorized"):
            await session_service.logout_session(session_id, user_id)
    
    @pytest.mark.asyncio
    async def test_logout_all_sessions(self, session_service, mock_db):
        """Test logout all sessions for user."""
        user_id = str(uuid4())
        
        # Mock database response (3 sessions logged out)
        mock_db.execute = Mock(return_value=Mock(data=[
            {"id": str(uuid4())},
            {"id": str(uuid4())},
            {"id": str(uuid4())}
        ]))
        
        # Logout all sessions
        count = await session_service.logout_all_sessions(user_id)
        
        # Verify count
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_list_user_sessions(self, session_service, mock_db):
        """Test listing user sessions."""
        user_id = str(uuid4())
        now = datetime.utcnow()
        
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=[
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "created_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "is_active": True,
                "metadata": {}
            },
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "ip_address": "192.168.1.2",
                "user_agent": "Chrome/90.0",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "last_activity_at": (now - timedelta(hours=1)).isoformat(),
                "expires_at": (now + timedelta(hours=23)).isoformat(),
                "is_active": True,
                "metadata": {}
            }
        ]))
        
        # List sessions
        result = await session_service.list_user_sessions(user_id)
        
        # Verify results
        assert result.total == 2
        assert result.active == 2
        assert len(result.sessions) == 2
    
    @pytest.mark.asyncio
    async def test_get_session_success(self, session_service, mock_db):
        """Test getting session details."""
        user_id = str(uuid4())
        session_id = uuid4()
        now = datetime.utcnow()
        
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=[{
            "id": str(session_id),
            "user_id": user_id,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "created_at": now.isoformat(),
            "last_activity_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "is_active": True,
            "metadata": {}
        }]))
        
        # Get session
        session = await session_service.get_session(session_id, user_id)
        
        # Verify session details
        assert str(session.id) == str(session_id)
        assert str(session.user_id) == user_id
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service, mock_db):
        """Test getting session when not found."""
        user_id = str(uuid4())
        session_id = uuid4()
        
        # Mock database response (no session found)
        mock_db.execute = Mock(return_value=Mock(data=[]))
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Session not found"):
            await session_service.get_session(session_id, user_id)
    
    @pytest.mark.asyncio
    async def test_refresh_session_success(self, session_service, mock_db):
        """Test refreshing session expiration."""
        user_id = str(uuid4())
        session_id = uuid4()
        now = datetime.utcnow()
        
        # Mock database responses
        mock_db.execute = Mock(side_effect=[
            # First call: select session
            Mock(data=[{
                "id": str(session_id),
                "user_id": user_id,
                "created_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=12)).isoformat(),
                "is_active": True,
                "metadata": {}
            }]),
            # Second call: update session
            Mock(data=[{
                "id": str(session_id),
                "user_id": user_id,
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "created_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "is_active": True,
                "metadata": {}
            }])
        ])
        
        # Refresh session
        session = await session_service.refresh_session(session_id, user_id)
        
        # Verify session refreshed
        assert str(session.id) == str(session_id)
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_refresh_session_not_found(self, session_service, mock_db):
        """Test refreshing session when not found."""
        user_id = str(uuid4())
        session_id = uuid4()
        
        # Mock database response (no session found)
        mock_db.execute = Mock(return_value=Mock(data=[]))
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Session not found"):
            await session_service.refresh_session(session_id, user_id)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service, mock_db):
        """Test cleanup of expired sessions."""
        # Mock database response
        mock_db.execute = Mock(return_value=Mock(data=5))
        
        # Cleanup expired sessions
        count = await session_service.cleanup_expired_sessions()
        
        # Verify count
        assert count == 5


class TestSessionModels:
    """Test session Pydantic models."""
    
    def test_session_create_model(self):
        """Test SessionCreate model."""
        session_create = SessionCreate(
            user_id=str(uuid4()),
            token="test_token",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert session_create.user_id is not None
        assert session_create.token == "test_token"
        assert session_create.ip_address == "192.168.1.1"
    
    def test_session_response_model(self):
        """Test SessionResponse model."""
        session_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()
        
        session_response = SessionResponse(
            id=session_id,
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=24),
            is_active=True,
            metadata={}
        )
        
        assert session_response.id == session_id
        assert session_response.user_id == user_id
        assert session_response.is_active is True
    
    def test_session_validation_result_valid(self):
        """Test SessionValidationResult for valid session."""
        result = SessionValidationResult(
            is_valid=True,
            session_id=uuid4(),
            user_id=str(uuid4())
        )
        
        assert result.is_valid is True
        assert result.session_id is not None
        assert result.user_id is not None
    
    def test_session_validation_result_invalid(self):
        """Test SessionValidationResult for invalid session."""
        result = SessionValidationResult(
            is_valid=False,
            reason="Session expired"
        )
        
        assert result.is_valid is False
        assert result.reason == "Session expired"
        assert result.session_id is None
        assert result.user_id is None
