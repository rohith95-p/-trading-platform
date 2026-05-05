"""
Unit tests for authentication module.
"""

import pytest
from datetime import datetime, timedelta
import jwt

from src.auth.jwt_handler import JWTHandler
from src.auth.models import UserRegistration, UserLogin


class TestJWTHandler:
    """Test JWT token handling."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.jwt_handler = JWTHandler()
        self.user_id = "123e4567-e89b-12d3-a456-426614174000"
        self.email = "test@example.com"
    
    def test_create_access_token(self):
        """Test access token creation."""
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = self.jwt_handler.verify_token(token, token_type="access")
        assert payload["sub"] == self.user_id
        assert payload["email"] == self.email
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = self.jwt_handler.create_refresh_token(self.user_id, self.email)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = self.jwt_handler.verify_token(token, token_type="refresh")
        assert payload["sub"] == self.user_id
        assert payload["email"] == self.email
        assert payload["type"] == "refresh"
    
    def test_verify_valid_token(self):
        """Test verification of valid token."""
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        payload = self.jwt_handler.verify_token(token, token_type="access")
        
        assert payload["sub"] == self.user_id
        assert payload["email"] == self.email
    
    def test_verify_expired_token(self):
        """Test verification of expired token."""
        # Create token that expires immediately
        self.jwt_handler.access_token_expire_hours = -1
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        
        # Reset expiration
        self.jwt_handler.access_token_expire_hours = 24
        
        with pytest.raises(jwt.ExpiredSignatureError):
            self.jwt_handler.verify_token(token, token_type="access")
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(jwt.InvalidTokenError):
            self.jwt_handler.verify_token(invalid_token, token_type="access")
    
    def test_verify_wrong_token_type(self):
        """Test verification with wrong token type."""
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        
        with pytest.raises(jwt.InvalidTokenError):
            self.jwt_handler.verify_token(token, token_type="refresh")
    
    def test_refresh_access_token(self):
        """Test token refresh."""
        refresh_token = self.jwt_handler.create_refresh_token(self.user_id, self.email)
        
        new_access_token, new_refresh_token = self.jwt_handler.refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != refresh_token
        # Note: new_refresh_token may equal refresh_token if generated in same second
        # Verify by checking payload types instead
        access_payload = self.jwt_handler.verify_token(new_access_token, token_type="access")
        refresh_payload = self.jwt_handler.verify_token(new_refresh_token, token_type="refresh")
        
        assert access_payload["sub"] == self.user_id
        assert refresh_payload["sub"] == self.user_id
    
    def test_get_token_expiration(self):
        """Test getting token expiration."""
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        expiration = self.jwt_handler.get_token_expiration(token)
        
        assert expiration is not None
        assert isinstance(expiration, datetime)
        assert expiration > datetime.utcnow()
    
    def test_is_token_expired(self):
        """Test checking if token is expired."""
        # Create valid token
        token = self.jwt_handler.create_access_token(self.user_id, self.email)
        assert not self.jwt_handler.is_token_expired(token)
        
        # Create expired token
        self.jwt_handler.access_token_expire_hours = -1
        expired_token = self.jwt_handler.create_access_token(self.user_id, self.email)
        self.jwt_handler.access_token_expire_hours = 24
        
        assert self.jwt_handler.is_token_expired(expired_token)


class TestUserRegistration:
    """Test user registration model."""
    
    def test_valid_registration(self):
        """Test valid registration data."""
        registration = UserRegistration(
            email="test@example.com",
            password="SecurePass123!",
            full_name="John Doe",
            timezone="America/New_York"
        )
        
        assert registration.email == "test@example.com"
        assert registration.password == "SecurePass123!"
        assert registration.full_name == "John Doe"
        assert registration.timezone == "America/New_York"
    
    def test_weak_password(self):
        """Test password strength validation."""
        with pytest.raises(ValueError, match="uppercase"):
            UserRegistration(
                email="test@example.com",
                password="weakpass123!",
            )
        
        with pytest.raises(ValueError, match="lowercase"):
            UserRegistration(
                email="test@example.com",
                password="WEAKPASS123!",
            )
        
        with pytest.raises(ValueError, match="digit"):
            UserRegistration(
                email="test@example.com",
                password="WeakPass!",
            )
        
        with pytest.raises(ValueError, match="special character"):
            UserRegistration(
                email="test@example.com",
                password="WeakPass123",
            )
    
    def test_short_password(self):
        """Test minimum password length."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserRegistration(
                email="test@example.com",
                password="Short1!",
            )


class TestUserLogin:
    """Test user login model."""
    
    def test_valid_login(self):
        """Test valid login data."""
        login = UserLogin(
            email="test@example.com",
            password="SecurePass123!",
            remember_me=True
        )
        
        assert login.email == "test@example.com"
        assert login.password == "SecurePass123!"
        assert login.remember_me is True
    
    def test_default_remember_me(self):
        """Test default remember_me value."""
        login = UserLogin(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        assert login.remember_me is False


# Property-based tests would go here using Hypothesis
# Example:
# @given(st.emails(), st.text(min_size=8))
# def test_registration_with_random_data(email, password):
#     # Test with random valid data
#     pass
