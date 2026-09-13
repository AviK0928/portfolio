"""Admin authentication. Fails closed when no token is configured."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def require_configured_token(settings: Settings = Depends(get_settings)) -> str:
    """Reject everything when ADMIN_API_TOKEN is unset.

    Without this, an unset token would be the empty string and any request
    sending an empty Authorization header would authenticate successfully.
    """
    token = settings.admin_api_token
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is not configured.",
        )
    return token


def require_admin(
    authorization: str = Header(default=""),
    configured: str = Depends(require_configured_token),
) -> None:
    scheme, _, presented = authorization.partition(" ")
    if scheme.lower() != "bearer" or not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # compare_digest, not ==: equality short-circuits on the first differing
    # byte, which leaks token content through response timing.
    if not secrets.compare_digest(presented, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
