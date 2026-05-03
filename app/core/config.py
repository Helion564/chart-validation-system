"""
Configuration Management Module
================================
v3.0.0 — Production-hardened:
  - SecretStr for API_KEY and SECRET_KEY (values never appear in logs/repr)
  - validate_production_secrets() startup guard: crashes with a clear error
    if the default placeholder secrets are used when DEBUG=False
  - API_KEY_ENABLED flag for toggling auth in test environments
  - Rate limit configuration
  - Pinned DATABASE_URL (real, not a placeholder comment)
"""

import secrets
import sys
import logging
from typing import List

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")

_DEFAULT_SECRET = "change-me-in-production"
_DEFAULT_API_KEY = "dev-key-change-me"


class Settings(BaseSettings):
    """Application-wide settings. Override any field via environment variable."""

    # ── General ──────────────────────────────────────────────────────────
    APP_NAME: str = "Chart Validation & Objective Compliance System"
    APP_VERSION: str = "3.0.0"
    APP_DESCRIPTION: str = (
        "DevSecOps-integrated API for validating chart data against "
        "objective compliance rules, visualization best practices, "
        "and data quality standards."
    )
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"  # nosec B104 — Required for Docker/container binding
    PORT: int = 8000

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Validation Rules ─────────────────────────────────────────────────
    ALLOWED_CHART_TYPES: List[str] = [
        "bar",
        "line",
        "pie",
        "scatter",
        "histogram",
    ]
    MIN_DATA_POINTS: int = 1
    VALID_SCORE_THRESHOLD: int = 70

    # ── Security ─────────────────────────────────────────────────────────
    # SecretStr: value is masked in logs, repr, and JSON serialisation.
    # Set these via environment variables or a .env file — NEVER hardcode.
    SECRET_KEY: SecretStr = SecretStr(_DEFAULT_SECRET)  # nosec B105
    API_KEY: SecretStr = SecretStr(_DEFAULT_API_KEY)  # nosec B105
    API_KEY_ENABLED: bool = True  # Set False only in test environments

    CORS_ORIGINS: List[str] = ["*"]

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATE_LIMIT: str = "30/minute"  # Applied to /validate-chart endpoints
    RATE_LIMIT_BATCH: str = "10/minute"

    # ── Persistence ───────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./chart_validation.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


def validate_production_secrets(s: Settings) -> None:
    """
    Startup guard — refuses to boot in production with default secrets.

    Called once at application startup. In DEBUG=True mode, emits warnings
    but does NOT crash (to keep local dev frictionless). In DEBUG=False
    (production) mode, any default placeholder secret causes a hard exit.
    """
    problems = []

    if s.SECRET_KEY.get_secret_value() == _DEFAULT_SECRET:
        problems.append(
            "SECRET_KEY is still the default placeholder. "
            f"Set SECRET_KEY=<random string> in your environment. "
            f"Hint: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    if s.API_KEY_ENABLED and s.API_KEY.get_secret_value() == _DEFAULT_API_KEY:
        problems.append(
            "API_KEY is still the default placeholder. "
            "Set API_KEY=<strong random key> in your environment."
        )

    if not problems:
        return

    if s.DEBUG:
        for msg in problems:
            logger.warning("SECURITY WARNING: %s", msg)
    else:
        logger.critical(
            "REFUSING TO START: Production mode requires secure secrets. "
            "Fix the following issues:\n  - %s",
            "\n  - ".join(problems),
        )
        sys.exit(1)


# Singleton instance
settings = Settings()
