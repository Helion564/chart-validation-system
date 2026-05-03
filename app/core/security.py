"""
Security Middleware — API Key Authentication
=============================================
Provides a FastAPI dependency that enforces X-API-Key header authentication.

Design:
  - Uses `secrets.compare_digest` to prevent timing attacks.
  - Returns HTTP 401 (not 403) on missing key — standard for missing auth.
  - Returns HTTP 403 on wrong key — standard for bad credentials.
  - Bypasses auth entirely when API_KEY_ENABLED=False (test environments).
  - The valid key is read from settings.API_KEY (SecretStr — never logged).

Usage:
    @router.post("/validate-chart", dependencies=[Depends(require_api_key)])
    async def validate(...):
        ...
"""

import secrets
import logging
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger("app.security")

# FastAPI security scheme — adds the key field to Swagger UI's "Authorize"
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_API_KEY_HEADER)) -> str:
    """
    FastAPI dependency that validates the X-API-Key request header.

    Returns the validated key string on success so downstream handlers
    can use it for audit logging if needed.

    Raises
    ------
    HTTP 401  — header is missing entirely.
    HTTP 403  — header is present but the value is wrong.
    """
    if not settings.API_KEY_ENABLED:
        return "auth-disabled"

    if api_key is None:
        logger.warning("Request rejected: missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Set the X-API-Key request header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison prevents timing-based key enumeration
    valid = secrets.compare_digest(
        api_key.encode(),
        settings.API_KEY.get_secret_value().encode(),
    )

    if not valid:
        logger.warning("Request rejected: invalid X-API-Key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
