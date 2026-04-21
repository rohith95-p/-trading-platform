"""
Pydantic models for session management.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    
    user_id: str = Field(..., description="User ID")
    token: str = Field(..., description="JWT access token")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional session metadata")


class SessionResponse(BaseModel):
    """Response model for session information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    is_active: bool = Field(..., description="Whether session is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    
    sessions: list[SessionResponse] = Field(..., description="List of user sessions")
    total: int = Field(..., description="Total number of sessions")
    active: int = Field(..., description="Number of active sessions")


class SessionRefreshRequest(BaseModel):
    """Request model for refreshing a session."""
    
    session_id: UUID = Field(..., description="Session ID to refresh")


class SessionValidationResult(BaseModel):
    """Result of session validation."""
    
    is_valid: bool = Field(..., description="Whether session is valid")
    session_id: Optional[UUID] = Field(None, description="Session ID if valid")
    user_id: Optional[str] = Field(None, description="User ID if valid")
    reason: Optional[str] = Field(None, description="Reason for invalid session")
