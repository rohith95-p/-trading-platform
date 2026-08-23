"""
Tests for authentication endpoints

This module tests user registration, login, password reset, and JWT token management.
"""

import pytest
from src.data.models import User

class TestRegistration:
    """Test user registration"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert "token" in data
        assert data["expires_in"] > 0
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        
        # Try to register with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword456"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_register_no_uppercase(self, client):
        """Test registration with password missing uppercase"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 422
    
    def test_register_no_digit(self, client):
        """Test registration with password missing digit"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword"
            }
        )
        assert response.status_code == 422

class TestLogin:
    """Test user login"""
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert "token" in data
    
    def test_login_invalid_email(self, client):
        """Test login with invalid email"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client):
        """Test login with invalid password"""
        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        
        # Try to login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123"
            }
        )
        assert response.status_code == 401

class TestGetCurrentUser:
    """Test getting current user profile"""
    
    def test_get_current_user_success(self, client):
        """Test getting current user profile"""
        # Register and login
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        token = register_response.json()["token"]
        
        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "quotas" in data
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

class TestRefreshToken:
    """Test token refresh"""
    
    def test_refresh_token_success(self, client):
        """Test successful token refresh"""
        # Register and login
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        token = register_response.json()["token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"] != token  # Should be a new token
