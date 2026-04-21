"""
Unit tests for API key management

Tests encryption, service layer, and API endpoints for API key management.
"""

import pytest
import os
import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api_keys.encryption import APIKeyEncryption
from src.api_keys.api_key_service import APIKeyService
from src.api_keys.models import (
    AddAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyPermissions,
    ExchangeType,
    RotateKeyRequest,
)
from src.data.models import Base, User, APIKey, AuditLog


# Test fixtures
@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        id="test-user-123",
        email="test@example.com",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def encryption():
    """Create encryption instance with test key"""
    test_key = base64.b64encode(b"0" * 32).decode('utf-8')
    return APIKeyEncryption(test_key)


@pytest.fixture
def api_key_service(encryption):
    """Create API key service with test encryption"""
    return APIKeyService(encryption)


# Encryption tests
class TestAPIKeyEncryption:
    """Test AES-256-GCM encryption"""
    
    def test_generate_master_key(self):
        """Test master key generation"""
        key = APIKeyEncryption.generate_master_key()
        assert isinstance(key, str)
        
        # Decode and verify length
        decoded = base64.b64decode(key)
        assert len(decoded) == 32
    
    def test_encryption_initialization(self):
        """Test encryption initialization with valid key"""
        test_key = base64.b64encode(b"0" * 32).decode('utf-8')
        encryption = APIKeyEncryption(test_key)
        assert encryption.master_key == b"0" * 32
        assert encryption.CURRENT_KEY_VERSION == 1
    
    def test_encryption_initialization_invalid_key(self):
        """Test encryption initialization with invalid key"""
        with pytest.raises(ValueError, match="Master key must be 32 bytes"):
            APIKeyEncryption("short_key")
    
    def test_encryption_initialization_missing_key(self):
        """Test encryption initialization without key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ENCRYPTION_KEY environment variable is required"):
                APIKeyEncryption()
    
    def test_encrypt_decrypt(self, encryption):
        """Test basic encryption and decryption"""
        plaintext = "my_secret_api_key_12345"
        
        nonce, ciphertext, version = encryption.encrypt(plaintext)
        
        assert len(nonce) == 12  # 96-bit nonce
        assert len(ciphertext) > 0
        assert version == 1
        assert ciphertext != plaintext.encode()
        
        # Decrypt
        decrypted = encryption.decrypt(nonce, ciphertext, version)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self, encryption):
        """Test encryption of empty string fails"""
        with pytest.raises(ValueError, match="Plaintext cannot be empty"):
            encryption.encrypt("")
    
    def test_decrypt_invalid_nonce(self, encryption):
        """Test decryption with invalid nonce fails"""
        _, ciphertext, version = encryption.encrypt("test")
        
        with pytest.raises(ValueError, match="Nonce must be 12 bytes"):
            encryption.decrypt(b"short", ciphertext, version)
    
    def test_decrypt_corrupted_data(self, encryption):
        """Test decryption of corrupted data fails"""
        nonce, ciphertext, version = encryption.encrypt("test")
        
        # Corrupt the ciphertext
        corrupted = ciphertext[:-1] + b"X"
        
        with pytest.raises(ValueError, match="Decryption failed or data corrupted"):
            encryption.decrypt(nonce, corrupted, version)
    
    def test_key_rotation(self, encryption):
        """Test key rotation"""
        plaintext = "my_secret_key"
        
        # Encrypt with version 1
        old_nonce, old_ciphertext, old_version = encryption.encrypt(plaintext, 1)
        
        # Add new key version
        new_key = os.urandom(32)
        encryption.add_key_version(2, new_key)
        
        # Rotate to new version
        new_nonce, new_ciphertext, new_version = encryption.rotate_key(
            old_nonce, old_ciphertext, old_version
        )
        
        assert new_version == 1  # Still uses current version
        assert new_nonce != old_nonce
        assert new_ciphertext != old_ciphertext
        
        # Verify decryption works
        decrypted = encryption.decrypt(new_nonce, new_ciphertext, new_version)
        assert decrypted == plaintext
    
    def test_add_duplicate_key_version(self, encryption):
        """Test adding duplicate key version fails"""
        new_key = os.urandom(32)
        
        with pytest.raises(ValueError, match="Key version 1 already exists"):
            encryption.add_key_version(1, new_key)
    
    def test_derive_key_from_password(self):
        """Test key derivation from password"""
        password = "my_secure_password"
        
        key1, salt1 = APIKeyEncryption.derive_key_from_password(password)
        assert len(key1) == 32
        assert len(salt1) == 16
        
        # Same password with same salt produces same key
        key2, _ = APIKeyEncryption.derive_key_from_password(password, salt1)
        assert key1 == key2
        
        # Different salt produces different key
        key3, salt3 = APIKeyEncryption.derive_key_from_password(password)
        assert key3 != key1
        assert salt3 != salt1


# Service tests
class TestAPIKeyService:
    """Test API key service"""
    
    def test_add_api_key(self, api_key_service, test_user, db_session):
        """Test adding a new API key"""
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="PKTEST123456",
            api_secret="SECRET123456",
            exchange_account_id="account_1",
            permissions=APIKeyPermissions(read=True, trade=True, withdraw=False)
        )
        
        response = api_key_service.add_api_key(test_user.id, request, db_session)
        
        assert response.exchange == "alpaca"
        assert response.exchange_account_id == "account_1"
        assert response.is_valid is True
        assert response.permissions["read"] is True
        assert response.permissions["trade"] is True
        assert response.permissions["withdraw"] is False
        assert response.usage_count == 0
        
        # Verify in database
        api_key = db_session.query(APIKey).filter_by(id=response.id).first()
        assert api_key is not None
        assert api_key.exchange == "alpaca"
    
    def test_add_duplicate_api_key(self, api_key_service, test_user, db_session):
        """Test adding duplicate API key fails"""
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="PKTEST123456",
            api_secret="SECRET123456"
        )
        
        # Add first key
        api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Try to add duplicate
        with pytest.raises(ValueError, match="API key already exists"):
            api_key_service.add_api_key(test_user.id, request, db_session)
    
    def test_add_api_key_with_passphrase(self, api_key_service, test_user, db_session):
        """Test adding API key with passphrase"""
        request = AddAPIKeyRequest(
            exchange=ExchangeType.KRAKEN,
            api_key="KRAKEN_KEY",
            api_secret="KRAKEN_SECRET",
            passphrase="my_passphrase"
        )
        
        response = api_key_service.add_api_key(test_user.id, request, db_session)
        
        assert response.exchange == "kraken"
        
        # Verify passphrase is encrypted
        api_key = db_session.query(APIKey).filter_by(id=response.id).first()
        assert api_key.passphrase_encrypted is not None
        assert api_key.passphrase_nonce is not None
    
    def test_list_api_keys(self, api_key_service, test_user, db_session):
        """Test listing API keys"""
        # Add multiple keys
        for exchange in [ExchangeType.ALPACA, ExchangeType.KALSHI]:
            request = AddAPIKeyRequest(
                exchange=exchange,
                api_key=f"{exchange.value.upper()}_KEY",
                api_secret=f"{exchange.value.upper()}_SECRET"
            )
            api_key_service.add_api_key(test_user.id, request, db_session)
        
        # List keys
        keys = api_key_service.list_api_keys(test_user.id, db_session)
        
        assert len(keys) == 2
        assert all(key.key_preview.startswith("****") for key in keys)
        assert {key.exchange for key in keys} == {"alpaca", "kalshi"}
    
    def test_list_api_keys_exclude_expired(self, api_key_service, test_user, db_session):
        """Test listing API keys excludes expired keys by default"""
        # Add expired key
        request1 = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="EXPIRED_KEY",
            api_secret="EXPIRED_SECRET",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        api_key_service.add_api_key(test_user.id, request1, db_session)
        
        # Add valid key
        request2 = AddAPIKeyRequest(
            exchange=ExchangeType.KALSHI,
            api_key="VALID_KEY",
            api_secret="VALID_SECRET"
        )
        api_key_service.add_api_key(test_user.id, request2, db_session)
        
        # List without expired
        keys = api_key_service.list_api_keys(test_user.id, db_session, include_expired=False)
        assert len(keys) == 1
        assert keys[0].exchange == "kalshi"
        
        # List with expired
        keys_all = api_key_service.list_api_keys(test_user.id, db_session, include_expired=True)
        assert len(keys_all) == 2
    
    def test_get_api_key(self, api_key_service, test_user, db_session):
        """Test getting API key details"""
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="TEST_KEY",
            api_secret="TEST_SECRET"
        )
        
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Get key
        retrieved = api_key_service.get_api_key(test_user.id, added.id, db_session)
        
        assert retrieved.id == added.id
        assert retrieved.exchange == "alpaca"
    
    def test_get_api_key_not_found(self, api_key_service, test_user, db_session):
        """Test getting non-existent API key fails"""
        with pytest.raises(ValueError, match="API key not found"):
            api_key_service.get_api_key(test_user.id, "invalid_id", db_session)
    
    def test_update_api_key(self, api_key_service, test_user, db_session):
        """Test updating API key metadata"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="TEST_KEY",
            api_secret="TEST_SECRET"
        )
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Update
        update_request = UpdateAPIKeyRequest(
            permissions=APIKeyPermissions(read=True, trade=True, withdraw=True),
            expires_at=datetime.utcnow() + timedelta(days=30),
            metadata={"note": "Updated"}
        )
        
        updated = api_key_service.update_api_key(test_user.id, added.id, update_request, db_session)
        
        assert updated.permissions["withdraw"] is True
        assert updated.expires_at is not None
        assert updated.metadata["note"] == "Updated"
    
    def test_delete_api_key(self, api_key_service, test_user, db_session):
        """Test deleting API key"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="TEST_KEY",
            api_secret="TEST_SECRET"
        )
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Delete
        api_key_service.delete_api_key(test_user.id, added.id, db_session)
        
        # Verify deleted
        api_key = db_session.query(APIKey).filter_by(id=added.id).first()
        assert api_key is None
        
        # Verify audit log
        audit = db_session.query(AuditLog).filter_by(
            user_id=test_user.id,
            action="api_key_deleted"
        ).first()
        assert audit is not None
    
    def test_validate_api_key(self, api_key_service, test_user, db_session):
        """Test API key validation"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="TEST_KEY",
            api_secret="TEST_SECRET"
        )
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Validate
        result = api_key_service.validate_api_key(test_user.id, added.id, db_session)
        
        assert result.valid is True
        assert result.exchange == "alpaca"
        assert result.last_validated_at is not None
    
    def test_rotate_api_key(self, api_key_service, test_user, db_session):
        """Test API key rotation"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="OLD_KEY",
            api_secret="OLD_SECRET"
        )
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Rotate
        rotate_request = RotateKeyRequest(
            new_api_key="NEW_KEY",
            new_api_secret="NEW_SECRET"
        )
        
        rotated = api_key_service.rotate_api_key(test_user.id, added.id, rotate_request, db_session)
        
        assert rotated.id == added.id  # Same record
        assert rotated.is_valid is True
        assert rotated.last_validated_at is None  # Reset validation
        
        # Verify new credentials are encrypted
        api_key = db_session.query(APIKey).filter_by(id=added.id).first()
        decrypted_key = api_key_service.encryption.decrypt(
            api_key.key_nonce,
            api_key.key_encrypted,
            api_key.key_version
        )
        assert decrypted_key == "NEW_KEY"
    
    def test_get_decrypted_credentials(self, api_key_service, test_user, db_session):
        """Test getting decrypted credentials"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="MY_KEY",
            api_secret="MY_SECRET",
            passphrase="MY_PASS"
        )
        api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Get decrypted
        key, secret, passphrase = api_key_service.get_decrypted_credentials(
            test_user.id, "alpaca", db_session
        )
        
        assert key == "MY_KEY"
        assert secret == "MY_SECRET"
        assert passphrase == "MY_PASS"
        
        # Verify usage tracking
        api_key = db_session.query(APIKey).filter_by(
            user_id=test_user.id,
            exchange="alpaca"
        ).first()
        assert api_key.usage_count == 1
        assert api_key.last_used_at is not None
    
    def test_get_decrypted_credentials_not_found(self, api_key_service, test_user, db_session):
        """Test getting decrypted credentials for non-existent key fails"""
        with pytest.raises(ValueError, match="Valid API key not found"):
            api_key_service.get_decrypted_credentials(
                test_user.id, "nonexistent", db_session
            )
    
    def test_get_decrypted_credentials_expired(self, api_key_service, test_user, db_session):
        """Test getting decrypted credentials for expired key fails"""
        # Add expired key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="EXPIRED_KEY",
            api_secret="EXPIRED_SECRET",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        api_key_service.add_api_key(test_user.id, request, db_session)
        
        with pytest.raises(ValueError, match="Valid API key not found"):
            api_key_service.get_decrypted_credentials(
                test_user.id, "alpaca", db_session
            )
    
    def test_check_expiration(self, api_key_service, test_user, db_session):
        """Test checking and marking expired keys"""
        # Add expired key
        request1 = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="EXPIRED_KEY",
            api_secret="EXPIRED_SECRET",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        api_key_service.add_api_key(test_user.id, request1, db_session)
        
        # Add valid key
        request2 = AddAPIKeyRequest(
            exchange=ExchangeType.KALSHI,
            api_key="VALID_KEY",
            api_secret="VALID_SECRET"
        )
        api_key_service.add_api_key(test_user.id, request2, db_session)
        
        # Check expiration
        count = api_key_service.check_expiration(db_session)
        
        assert count == 1
        
        # Verify expired key is marked invalid
        expired_key = db_session.query(APIKey).filter_by(
            user_id=test_user.id,
            exchange="alpaca"
        ).first()
        assert expired_key.is_valid is False
        assert expired_key.validation_error == "API key expired"
    
    def test_get_usage_stats(self, api_key_service, test_user, db_session):
        """Test getting usage statistics"""
        # Add key
        request = AddAPIKeyRequest(
            exchange=ExchangeType.ALPACA,
            api_key="TEST_KEY",
            api_secret="TEST_SECRET"
        )
        added = api_key_service.add_api_key(test_user.id, request, db_session)
        
        # Use key multiple times
        for _ in range(5):
            api_key_service.get_decrypted_credentials(test_user.id, "alpaca", db_session)
        
        # Get stats
        stats = api_key_service.get_usage_stats(test_user.id, added.id, db_session)
        
        assert stats.total_usage == 5
        assert stats.last_used_at is not None


# Integration tests would go here for testing the FastAPI endpoints
# These would use TestClient from fastapi.testclient

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
