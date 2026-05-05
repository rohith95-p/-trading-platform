"""
AES-256-GCM Encryption for API Keys

This module provides secure encryption and decryption of API keys using AES-256-GCM.
Supports key rotation and secure key derivation.
"""

import os
import base64
import logging
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from src.config import settings

logger = logging.getLogger(__name__)


class APIKeyEncryption:
    """
    AES-256-GCM encryption for API keys with key rotation support.
    
    Features:
    - AES-256-GCM authenticated encryption
    - 96-bit nonce for each encryption operation
    - Key derivation from master key
    - Support for multiple key versions (rotation)
    """
    
    # Key version for rotation support
    CURRENT_KEY_VERSION = 1
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption with master key.
        
        Args:
            master_key: 32-byte master key encoded as hex (64 chars) or base64.
                        If None, reads from ENCRYPTION_KEY env var via settings.
            
        Raises:
            ValueError: If master key is invalid or missing
        """
        if master_key is None:
            master_key = settings.ENCRYPTION_KEY
        
        if not master_key or master_key.startswith("change-this"):
            raise ValueError("ENCRYPTION_KEY environment variable is required")
        
        try:
            # Accept hex (64-char) or base64 (44-char) encoding
            if len(master_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in master_key):
                self.master_key = bytes.fromhex(master_key)
            else:
                self.master_key = base64.b64decode(master_key)
            
            if len(self.master_key) != 32:
                raise ValueError("Master key must be 32 bytes for AES-256")
                
        except Exception as e:
            raise ValueError(f"Invalid master key format: {e}")
        
        # Initialize cipher
        self.cipher = AESGCM(self.master_key)
        
        # Key rotation support - store multiple key versions
        self.key_versions = {
            self.CURRENT_KEY_VERSION: self.master_key
        }
        
        logger.info(f"Encryption initialized with key version {self.CURRENT_KEY_VERSION}")

    
    def encrypt(self, plaintext: str, key_version: Optional[int] = None) -> Tuple[bytes, bytes, int]:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: String to encrypt
            key_version: Key version to use (defaults to current version)
            
        Returns:
            Tuple of (nonce, ciphertext, key_version)
            
        Raises:
            ValueError: If encryption fails
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")
        
        if key_version is None:
            key_version = self.CURRENT_KEY_VERSION
        
        if key_version not in self.key_versions:
            raise ValueError(f"Invalid key version: {key_version}")
        
        try:
            # Generate random 96-bit nonce
            nonce = os.urandom(12)
            
            # Get key for this version
            key = self.key_versions[key_version]
            cipher = AESGCM(key)
            
            # Encrypt with authenticated encryption
            ciphertext = cipher.encrypt(nonce, plaintext.encode('utf-8'), None)
            
            # NEVER log the plaintext
            logger.debug(f"Encrypted data with key version {key_version}")
            
            return nonce, ciphertext, key_version
            
        except Exception as e:
            logger.error(f"Encryption failed: {type(e).__name__}")
            raise ValueError("Encryption failed")
    
    def decrypt(self, nonce: bytes, ciphertext: bytes, key_version: int = None) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.
        
        Args:
            nonce: 96-bit nonce used during encryption
            ciphertext: Encrypted data
            key_version: Key version used for encryption (defaults to current version)
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails or authentication fails
        """
        if not nonce or not ciphertext:
            raise ValueError("Nonce and ciphertext are required")
        
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes (96 bits)")
        
        if key_version is None:
            key_version = self.CURRENT_KEY_VERSION
        
        if key_version not in self.key_versions:
            raise ValueError(f"Invalid key version: {key_version}")
        
        try:
            # Get key for this version
            key = self.key_versions[key_version]
            cipher = AESGCM(key)
            
            # Decrypt and verify authentication tag
            plaintext_bytes = cipher.decrypt(nonce, ciphertext, None)
            plaintext = plaintext_bytes.decode('utf-8')
            
            # NEVER log the decrypted plaintext
            logger.debug(f"Decrypted data with key version {key_version}")
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {type(e).__name__}")
            raise ValueError("Decryption failed or data corrupted")
    
    def add_key_version(self, version: int, key: bytes) -> None:
        """
        Add a new key version for key rotation.
        
        Args:
            version: Key version number
            key: 32-byte encryption key
            
        Raises:
            ValueError: If key is invalid
        """
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        
        if version in self.key_versions:
            raise ValueError(f"Key version {version} already exists")
        
        self.key_versions[version] = key
        logger.info(f"Added key version {version}")
    
    def rotate_key(self, old_nonce: bytes, old_ciphertext: bytes, old_version: int) -> Tuple[bytes, bytes, int]:
        """
        Re-encrypt data with the current key version.
        
        Args:
            old_nonce: Nonce from old encryption
            old_ciphertext: Ciphertext from old encryption
            old_version: Old key version
            
        Returns:
            Tuple of (new_nonce, new_ciphertext, new_version)
            
        Raises:
            ValueError: If rotation fails
        """
        try:
            # Decrypt with old key
            plaintext = self.decrypt(old_nonce, old_ciphertext, old_version)
            
            # Encrypt with current key
            new_nonce, new_ciphertext, new_version = self.encrypt(plaintext, self.CURRENT_KEY_VERSION)
            
            logger.info(f"Rotated key from version {old_version} to {new_version}")
            
            return new_nonce, new_ciphertext, new_version
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise ValueError("Key rotation failed")
    
    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new random 32-byte master key.
        
        Returns:
            Base64-encoded master key suitable for ENCRYPTION_KEY env var
        """
        key = os.urandom(32)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive a 32-byte key from a password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generates random if None)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
