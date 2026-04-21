#!/usr/bin/env python3
"""
Generate secure secrets for deployment
Run this script to generate JWT_SECRET and ENCRYPTION_KEY
"""

import secrets
import sys


def generate_jwt_secret(length=32):
    """Generate a secure random string for JWT_SECRET"""
    return secrets.token_urlsafe(length)


def generate_encryption_key():
    """Generate a 32-byte hex key for ENCRYPTION_KEY"""
    return secrets.token_hex(32)


def main():
    print("=" * 60)
    print("Secure Secrets Generator for Task 1.3")
    print("=" * 60)
    print()
    
    print("Copy these values to your Railway environment variables:")
    print()
    
    jwt_secret = generate_jwt_secret()
    print(f"JWT_SECRET={jwt_secret}")
    print()
    
    encryption_key = generate_encryption_key()
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    
    print("=" * 60)
    print("⚠️  IMPORTANT: Keep these secrets secure!")
    print("   - Never commit them to Git")
    print("   - Only add them to Railway environment variables")
    print("   - Save them in a secure password manager")
    print("=" * 60)


if __name__ == "__main__":
    main()
