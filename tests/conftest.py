"""
Test Configuration — conftest.py
===================================
Sets up an in-memory SQLite database for tests using FastAPI's
dependency_overrides. This isolates tests from the real DB, ensures
a clean state per session, and avoids async/sync event loop conflicts
with the synchronous TestClient.
"""

import os

# Must be set before any app imports
os.environ["API_KEY_ENABLED"] = "false"
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import asyncio  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# ── In-memory async engine for tests ─────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def _create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Create tables once before the test session
asyncio.run(_create_tables())


# ── Override get_db dependency ─────────────────────────────────────────────────


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


# ── Test client fixture ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def client(test_client):
    return test_client
