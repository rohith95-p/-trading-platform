"""
Tests for API key management endpoints

This module tests secure storage, encryption, and management of exchange API keys.
"""

import pytest
from src.data.models import APIKey

@pytest.fixture
def auth_token(client):
    """Create a test user and return auth token"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123"
        }
    )
    return response.json()["token"]

class TestAddAPIKey:
    """Test adding API keys"""
    
    def test_add_api_key_success(self, client, auth_token):
        """Test successful API key addition"""
        response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exchange"] == "kalshi"
        assert data["is_valid"] == True
        assert "id" in data
    
    def test_add_api_key_duplicate_exchange(self, client, auth_token):
        """Test adding duplicate API key for same exchange"""
        # Add first key
        client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Try to add second key for same exchange
        response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_99999",
                "api_secret": "test_secret_99999"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_add_api_key_invalid_exchange(self, client, auth_token):
        """Test adding API key with invalid exchange"""
        response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "invalid_exchange",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_add_api_key_no_auth(self, client):
        """Test adding API key without authentication"""
        response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            }
        )
        assert response.status_code == 401

class TestListAPIKeys:
    """Test listing API keys"""
    
    def test_list_api_keys_empty(self, client, auth_token):
        """Test listing API keys when none exist"""
        response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_api_keys_masked(self, client, auth_token):
        """Test that API keys are masked in list"""
        # Add API key
        client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # List keys
        response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["exchange"] == "kalshi"
        assert "key_preview" in data[0]
        assert data[0]["key_preview"] == "2345"  # Last 4 chars
        # Ensure full key is not exposed
        assert "test_key_12345" not in str(data)
    
    def test_list_api_keys_multiple(self, client, auth_token):
        """Test listing multiple API keys"""
        # Add multiple keys
        for exchange in ["kalshi", "polymarket", "alpaca"]:
            client.post(
                "/api/v1/api-keys/",
                json={
                    "exchange": exchange,
                    "api_key": f"key_{exchange}",
                    "api_secret": f"secret_{exchange}"
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        # List keys
        response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        exchanges = [key["exchange"] for key in data]
        assert "kalshi" in exchanges
        assert "polymarket" in exchanges
        assert "alpaca" in exchanges

class TestDeleteAPIKey:
    """Test deleting API keys"""
    
    def test_delete_api_key_success(self, client, auth_token):
        """Test successful API key deletion"""
        # Add API key
        add_response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        key_id = add_response.json()["id"]
        
        # Delete key
        response = client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify key is deleted
        list_response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert len(list_response.json()) == 0
    
    def test_delete_api_key_not_found(self, client, auth_token):
        """Test deleting non-existent API key"""
        response = client.delete(
            "/api/v1/api-keys/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_delete_api_key_no_auth(self, client):
        """Test deleting API key without authentication"""
        response = client.delete(
            "/api/v1/api-keys/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

class TestValidateAPIKey:
    """Test validating API keys"""
    
    def test_validate_api_key_success(self, client, auth_token):
        """Test successful API key validation"""
        # Add API key
        add_response = client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        key_id = add_response.json()["id"]
        
        # Validate key
        response = client.post(
            f"/api/v1/api-keys/{key_id}/validate",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["exchange"] == "kalshi"
    
    def test_validate_api_key_not_found(self, client, auth_token):
        """Test validating non-existent API key"""
        response = client.post(
            "/api/v1/api-keys/00000000-0000-0000-0000-000000000000/validate",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

class TestEncryption:
    """Test API key encryption"""
    
    def test_api_key_encrypted_at_rest(self, client, auth_token, test_db):
        """Test that API keys are encrypted in database"""
        # Add API key
        client.post(
            "/api/v1/api-keys/",
            json={
                "exchange": "kalshi",
                "api_key": "test_key_12345",
                "api_secret": "test_secret_67890"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Check database directly
        api_key = test_db.query(APIKey).first()
        
        # Verify encryption
        assert api_key.key_encrypted != b"test_key_12345"
        assert api_key.secret_encrypted != b"test_secret_67890"
        assert api_key.key_nonce is not None
        assert api_key.secret_nonce is not None
