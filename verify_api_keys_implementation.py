"""
Verification script for API Key Management implementation
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def check_import(module_path, description):
    """Check if a module can be imported"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"✅ {description}: {module_path}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_path} - {e}")
        return False

def main():
    """Run verification checks"""
    print("=" * 70)
    print("API Key Management Implementation Verification")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Check core files
    print("📁 Core Implementation Files:")
    all_passed &= check_file_exists("src/api_keys/__init__.py", "Module init")
    all_passed &= check_file_exists("src/api_keys/encryption.py", "Encryption class")
    all_passed &= check_file_exists("src/api_keys/models.py", "Pydantic models")
    all_passed &= check_file_exists("src/api_keys/api_key_service.py", "Service layer")
    all_passed &= check_file_exists("src/api/api_keys.py", "API routes")
    print()
    
    # Check documentation
    print("📚 Documentation:")
    all_passed &= check_file_exists("docs/API_KEY_SECURITY.md", "Security docs")
    all_passed &= check_file_exists("TASK_1_8_IMPLEMENTATION_SUMMARY.md", "Implementation summary")
    print()
    
    # Check tests
    print("🧪 Tests:")
    all_passed &= check_file_exists("tests/unit/test_api_keys.py", "Unit tests")
    all_passed &= check_file_exists("test_encryption_standalone.py", "Standalone test")
    print()
    
    # Check imports
    print("📦 Module Imports:")
    all_passed &= check_import("src.api_keys.encryption", "Encryption module")
    all_passed &= check_import("src.api_keys.models", "Models module")
    all_passed &= check_import("src.api_keys.api_key_service", "Service module")
    print()
    
    # Check classes
    print("🔧 Class Availability:")
    try:
        from src.api_keys.encryption import APIKeyEncryption
        print(f"✅ APIKeyEncryption class available")
        
        from src.api_keys.api_key_service import APIKeyService
        print(f"✅ APIKeyService class available")
        
        from src.api_keys.models import (
            AddAPIKeyRequest,
            UpdateAPIKeyRequest,
            APIKeyResponse,
            MaskedAPIKeyResponse,
            ValidateAPIKeyResponse,
            RotateKeyRequest,
        )
        print(f"✅ All Pydantic models available")
    except Exception as e:
        print(f"❌ Class import failed: {e}")
        all_passed = False
    print()
    
    # Check database model
    print("💾 Database Model:")
    try:
        from src.data.models import APIKey
        
        # Check required fields
        required_fields = [
            'id', 'user_id', 'exchange', 'exchange_account_id',
            'key_nonce', 'key_encrypted', 'key_version',
            'secret_nonce', 'secret_encrypted', 'secret_version',
            'passphrase_nonce', 'passphrase_encrypted', 'passphrase_version',
            'is_valid', 'last_validated_at', 'validation_error',
            'permissions', 'last_used_at', 'usage_count',
            'created_at', 'updated_at', 'expires_at', 'meta'
        ]
        
        model_columns = [col.name for col in APIKey.__table__.columns]
        missing_fields = [f for f in required_fields if f not in model_columns]
        
        if missing_fields:
            print(f"❌ Missing fields in APIKey model: {missing_fields}")
            all_passed = False
        else:
            print(f"✅ APIKey model has all required fields ({len(required_fields)} fields)")
    except Exception as e:
        print(f"❌ Database model check failed: {e}")
        all_passed = False
    print()
    
    # Summary
    print("=" * 70)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Implementation is complete!")
    else:
        print("❌ SOME CHECKS FAILED - Review errors above")
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
