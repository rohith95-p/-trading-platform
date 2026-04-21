"""
Security utilities for authentication and encryption
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib
import hmac

from src.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)

# JWT tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

# Encryption
def get_cipher():
    """Get Fernet cipher"""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest())
    return Fernet(key)

def encrypt_data(data: str) -> str:
    """Encrypt data"""
    cipher = get_cipher()
    encrypted = cipher.encrypt(data.encode())
    return encrypted.decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data"""
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_data.encode())
    return decrypted.decode()

# HMAC signatures
def create_signature(data: str, secret: str) -> str:
    """Create HMAC-SHA256 signature"""
    return hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature"""
    expected_signature = create_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)
