"""
Conftest for integration tests.

Sets required environment variables before any imports so that modules
that validate env vars at import time don't raise errors.
"""

import os

# Set required env vars before any app imports
os.environ.setdefault("ENCRYPTION_KEY", "OhmeXCdnlRP9mtBGxUCGganlwKBnvBm2tHt9TngcVw4=")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_key_for_testing_only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
