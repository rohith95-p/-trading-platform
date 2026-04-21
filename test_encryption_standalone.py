"""
Standalone test for API key encryption
"""

import sys
import os
import base64

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.api_keys.encryption import APIKeyEncryption

def test_encryption():
    """Test basic encryption functionality"""
    print("Testing API Key Encryption...")
    
    # Generate a test key
    test_key = base64.b64encode(b"0" * 32).decode('utf-8')
    print(f"✓ Generated test key: {test_key[:20]}...")
    
    # Initialize encryption
    encryption = APIKeyEncryption(test_key)
    print("✓ Initialized encryption")
    
    # Test encryption
    plaintext = "my_secret_api_key_12345"
    nonce, ciphertext, version = encryption.encrypt(plaintext)
    print(f"✓ Encrypted plaintext (nonce length: {len(nonce)}, ciphertext length: {len(ciphertext)})")
    
    # Test decryption
    decrypted = encryption.decrypt(nonce, ciphertext, version)
    assert decrypted == plaintext, "Decryption failed!"
    print(f"✓ Decrypted successfully: {decrypted}")
    
    # Test key generation
    new_key = APIKeyEncryption.generate_master_key()
    print(f"✓ Generated new master key: {new_key[:20]}...")
    
    # Test key derivation
    password = "my_password"
    derived_key, salt = APIKeyEncryption.derive_key_from_password(password)
    print(f"✓ Derived key from password (key length: {len(derived_key)}, salt length: {len(salt)})")
    
    print("\n✅ All encryption tests passed!")

if __name__ == "__main__":
    try:
        test_encryption()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
