"""
Helpers for OAuth state generation and cookie naming.
"""

from __future__ import annotations

import secrets


def build_oauth_state() -> str:
    """Return a cryptographically strong OAuth state token."""
    return secrets.token_urlsafe(32)


def oauth_state_cookie_name(provider: str) -> str:
    """Return the cookie name used for a provider OAuth state token."""
    return f"oauth_state_{provider}"

