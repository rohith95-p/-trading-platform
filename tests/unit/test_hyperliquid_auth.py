"""
Unit tests for Hyperliquid authentication implementation.

Tests cover:
- API key and secret validation
- HMAC-SHA256 request signing
- Credential encryption/decryption
- Authentication error handling
- Secure credential storage

Validates: Requirements 1.2 (Authentication with API key and secret)
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from cryptography.fernet import Fernet

from src.exchanges.hyperliquid import (
    HyperliquidConnector,
    AuthenticationError,
    CredentialEncryption,
    RequestSigner,
)


class TestCredentialEncryption:
    """Test credential encryption and decryption"""
    
    def test_encryption_key_generation(self):
        """Test that encryption key can be generated"""
        key = Fernet.generate_key().decode()
        encryption = CredentialEncryption(key)
        assert encryption.cipher is not None
    
    def test_encrypt_credential(self):
        """Test credential encryption"""
        key = Fernet.generate_key().decode()
        encryption = CredentialEncryption(key)
        
        credential = "test_api_key_12345"
        encrypted = encryption.encrypt_credential(credential)
        
        assert encrypted != credential
        assert isinstance(encrypted, str)
    
    def test_decrypt_credential(self):
        """Test credential decryption"""
        key = Fernet.generate_key().decode()
        encryption = CredentialEncryption(key)
        
        credential = "test_api_key_12345"
        encrypted = encryption.encrypt_credential(credential)
        decrypted = encryption.decrypt_credential(encrypted)
        
        assert decrypted == credential
    
    def test_no_encryption_when_key_is_none(self):
        """Test that credentials are not encrypted when key is None"""
        encryption = CredentialEncryption(None)
        
        credential = "test_api_key_12345"
        encrypted = encryption.encrypt_credential(credential)
        
        assert encrypted == credential
    
    def test_decrypt_with_wrong_key_raises_error(self):
        """Test that decryption with wrong key raises AuthenticationError"""
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()
        
        encryption1 = CredentialEncryption(key1)
        encryption2 = CredentialEncryption(key2)
        
        credential = "test_api_key_12345"
        encrypted = encryption1.encrypt_credential(credential)
        
        with pytest.raises(AuthenticationError):
            encryption2.decrypt_credential(encrypted)


class TestRequestSigner:
    """Test HMAC-SHA256 request signing"""
    
    def test_sign_request_without_body(self):
        """Test signing a request without body"""
        api_secret = "test_secret_12345"
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        
        signature = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
        )
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex is 64 chars
    
    def test_sign_request_with_body(self):
        """Test signing a request with body"""
        api_secret = "test_secret_12345"
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        request_body = '{"symbol": "BTC-USD", "size": 1.0}'
        
        signature = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
            request_body,
        )
        
        assert isinstance(signature, str)
        assert len(signature) == 64
    
    def test_signature_is_deterministic(self):
        """Test that same inputs produce same signature"""
        api_secret = "test_secret_12345"
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        request_body = '{"symbol": "BTC-USD"}'
        
        sig1 = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
            request_body,
        )
        sig2 = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
            request_body,
        )
        
        assert sig1 == sig2
    
    def test_different_secrets_produce_different_signatures(self):
        """Test that different secrets produce different signatures"""
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        request_body = '{"symbol": "BTC-USD"}'
        
        sig1 = RequestSigner.sign_request(
            "secret1",
            timestamp,
            api_key,
            request_body,
        )
        sig2 = RequestSigner.sign_request(
            "secret2",
            timestamp,
            api_key,
            request_body,
        )
        
        assert sig1 != sig2
    
    def test_verify_signature_valid(self):
        """Test signature verification with valid signature"""
        api_secret = "test_secret_12345"
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        request_body = '{"symbol": "BTC-USD"}'
        
        signature = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
            request_body,
        )
        
        is_valid = RequestSigner.verify_signature(
            api_secret,
            timestamp,
            api_key,
            signature,
            request_body,
        )
        
        assert is_valid is True
    
    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature"""
        api_secret = "test_secret_12345"
        timestamp = "1234567890000"
        api_key = "test_key_12345"
        
        is_valid = RequestSigner.verify_signature(
            api_secret,
            timestamp,
            api_key,
            "invalid_signature_0000000000000000000000000000000000000000000000000000000000000000",
        )
        
        assert is_valid is False


class TestHyperliquidConnectorAuthentication:
    """Test HyperliquidConnector authentication"""
    
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        assert connector.api_key == "test_key_12345"
        assert connector.secret == "test_secret_12345"
        assert connector.name == "hyperliquid"
    
    def test_init_with_empty_api_key_raises_error(self):
        """Test that empty API key raises AuthenticationError"""
        with pytest.raises(AuthenticationError):
            HyperliquidConnector(
                api_key="",
                secret="test_secret_12345",
            )
    
    def test_init_with_empty_secret_raises_error(self):
        """Test that empty secret raises AuthenticationError"""
        with pytest.raises(AuthenticationError):
            HyperliquidConnector(
                api_key="test_key_12345",
                secret="",
            )
    
    def test_init_with_short_api_key_raises_error(self):
        """Test that short API key raises AuthenticationError"""
        with pytest.raises(AuthenticationError):
            HyperliquidConnector(
                api_key="short",
                secret="test_secret_12345",
            )
    
    def test_init_with_short_secret_raises_error(self):
        """Test that short secret raises AuthenticationError"""
        with pytest.raises(AuthenticationError):
            HyperliquidConnector(
                api_key="test_key_12345",
                secret="short",
            )
    
    def test_init_with_encryption_key(self):
        """Test initialization with encryption key"""
        encryption_key = Fernet.generate_key().decode()
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
            encryption_key=encryption_key,
        )
        
        assert connector.credential_encryption.cipher is not None
    
    def test_init_stores_encrypted_credentials(self):
        """Test that credentials are encrypted during initialization"""
        encryption_key = Fernet.generate_key().decode()
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
            encryption_key=encryption_key,
        )
        
        # Encrypted credentials should be different from original
        assert connector._api_key != "test_key_12345"
        assert connector._secret != "test_secret_12345"
    
    @pytest.mark.asyncio
    async def test_connect_with_invalid_credentials(self):
        """Test connection with invalid credentials"""
        connector = HyperliquidConnector(
            api_key="invalid_key_12345",
            secret="invalid_secret_12345",
            testnet=True,
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Unauthorized")
            
            mock_session_instance = AsyncMock()
            mock_session_instance.request = AsyncMock(
                return_value=mock_response.__aenter__.return_value
            )
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None
            
            mock_session.return_value = mock_session_instance
            
            with pytest.raises(AuthenticationError):
                await connector.connect()
    
    def test_get_headers_includes_authentication(self):
        """Test that headers include authentication fields"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        headers = connector._get_headers()
        
        assert "X-API-Key" in headers
        assert "X-Signature" in headers
        assert "X-Timestamp" in headers
        assert headers["X-API-Key"] == "test_key_12345"
        assert headers["Content-Type"] == "application/json"
    
    def test_get_headers_with_payload(self):
        """Test that headers include payload in signature"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        payload = {"symbol": "BTC-USD", "size": 1.0}
        headers1 = connector._get_headers(payload)
        headers2 = connector._get_headers(None)
        
        # Signatures should be different
        assert headers1["X-Signature"] != headers2["X-Signature"]
    
    def test_sign_request_uses_hmac_sha256(self):
        """Test that request signing uses HMAC-SHA256"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        timestamp = "1234567890000"
        signature = connector._sign_request(timestamp)
        
        # Verify signature is valid hex string of correct length
        assert isinstance(signature, str)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)
    
    def test_max_leverage_validation(self):
        """Test that max leverage is stored correctly"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
            max_leverage=10.0,
        )
        
        assert connector.max_leverage == 10.0
    
    def test_testnet_flag(self):
        """Test that testnet flag sets correct base URL"""
        connector_mainnet = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
            testnet=False,
        )
        
        connector_testnet = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
            testnet=True,
        )
        
        assert connector_mainnet.base_url == "https://api.hyperliquid.xyz"
        assert connector_testnet.base_url == "https://testnet.hyperliquid.xyz"


class TestAuthenticationErrorHandling:
    """Test authentication error handling"""
    
    @pytest.mark.asyncio
    async def test_request_with_401_raises_authentication_error(self):
        """Test that 401 response raises AuthenticationError"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        
        with patch.object(connector, 'session') as mock_session:
            mock_session.request = MagicMock(return_value=mock_context)
            
            with pytest.raises(AuthenticationError):
                await connector._request("GET", "/account")
    
    @pytest.mark.asyncio
    async def test_request_with_403_raises_authentication_error(self):
        """Test that 403 response raises AuthenticationError"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Forbidden")
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        
        with patch.object(connector, 'session') as mock_session:
            mock_session.request = MagicMock(return_value=mock_context)
            
            with pytest.raises(AuthenticationError):
                await connector._request("GET", "/account")
    
    @pytest.mark.asyncio
    async def test_request_without_session_raises_authentication_error(self):
        """Test that request without session raises AuthenticationError"""
        connector = HyperliquidConnector(
            api_key="test_key_12345",
            secret="test_secret_12345",
        )
        
        connector.session = None
        
        with pytest.raises(AuthenticationError):
            await connector._request("GET", "/account")
