"""
Application Entry Point — v3.0.0
==================================
Gaps closed vs v2:
  - validate_production_secrets() called at startup — hard exit on bad secrets
  - init_db() called at startup — tables created before first request
  - slowapi rate limiter wired to FastAPI exception handlers
  - request instrumentation middleware unchanged
  - lifespan context manager for clean startup/shutdown
"""

import logging
import logging.config
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, List, Optional
import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings, validate_production_secrets
from app.core.database import init_db
from app.api.routes import limiter, router

# ─── Logging ────────────────────────────────────────────────────────────────

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": settings.LOG_LEVEL, "handlers": ["console"]},
    "loggers": {
        "uvicorn.access": {"propagate": False},
        "app": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app.main")


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: validate secrets, create DB tables. Shutdown: log."""
    # GAP 1 CLOSED: Hard-exit in production if default secrets detected
    validate_production_secrets(settings)

    # GAP 2 CLOSED: Create DB tables before accepting requests
    await init_db()
    logger.info(
        "Database initialised | url=%s",
        settings.DATABASE_URL.split("///")[-1],
    )
    logger.info(
        "Starting %s v%s | debug=%s | auth=%s | rate_limit=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.DEBUG,
        settings.API_KEY_ENABLED,
        settings.RATE_LIMIT,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# ─── App Factory ─────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "Chart Validation DevSecOps Team",
            "url": "https://github.com/nageshbhagelli/chart-validation-system",
        },
        license_info={"name": "MIT"},
    )

    # GAP 3 CLOSED: Rate limiter wired to app state + exception handler
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request instrumentation middleware
    @application.middleware("http")
    async def request_instrumentation(request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        logger.info(
            "REQUEST | %s %s | status=%d | duration=%sms | corr_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id,
        )
        return response

    # Routes
    application.include_router(router)

    # Static frontend (Production)
    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.isdir(frontend_dist):
        application.mount(
            "/dashboard",
            StaticFiles(directory=frontend_dist, html=True),
            name="frontend",
        )
        logger.info("Production frontend mounted at /dashboard")
    else:
        logger.warning("Production frontend (dist) not found. Run 'npm run build' in frontend directory.")

    return application


app = create_app()
