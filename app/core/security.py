"""
Provides FastAPI dependencies for OAuth2 with Password (and hashing),
Bearer with JWT tokens.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.db_models import User
from app.models.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ─── Password Hashing (stdlib only — no passlib dependency) ──────────────────


def get_password_hash(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
    return salt.hex() + ":" + dk.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its PBKDF2-HMAC-SHA256 hash."""
    try:
        salt_hex, dk_hex = hashed_password.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = bytes.fromhex(dk_hex)
        new_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, 260000)
        return hmac.compare_digest(dk, new_dk)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not settings.API_KEY_ENABLED:
        return User(username="test_user", role="admin", is_active=True)

    if api_key:
        if api_key == settings.API_KEY.get_secret_value():
            return User(username="api_key_user", role="admin", is_active=True)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except InvalidTokenError:
        raise credentials_exception

    user = (
        await db.execute(select(User).where(User.username == token_data.username))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def require_role(required_role: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        # Admin overrides all
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return current_user

    return role_checker


"""
Security Middleware — API Key Authentication
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
