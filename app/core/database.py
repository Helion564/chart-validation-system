"""
Database Layer — SQLAlchemy Async Setup
========================================
Uses SQLAlchemy 2.0 async API with aiosqlite (SQLite) or any PostgreSQL
URL in production. All calls are async — no thread-pool blocking.

Key objects exported:
  - engine          : AsyncEngine (create once at startup)
  - AsyncSessionLocal : async session factory
  - Base            : declarative base for ORM models
  - get_db()        : FastAPI dependency that yields a session per request
  - init_db()       : called at startup to create all tables
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# connect_args only applies to SQLite — required to allow multi-thread use.
_connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # log SQL only in debug mode
    connect_args=_connect_args,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""

    pass


# ── FastAPI Dependency ────────────────────────────────────────────────────────
async def get_db():
    """
    Yields an async database session per request.
    Automatically rolls back on exception and closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Table Creation ────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Create all tables that do not yet exist. Safe to call repeatedly."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
