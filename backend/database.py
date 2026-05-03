"""
backend/database.py
-------------------
SQLAlchemy async engine and session factory for PostgreSQL.

Usage in FastAPI endpoints (dependency injection):

    from backend.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @app.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(FMEASession))
        ...
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.models import Base

# ---------------------------------------------------------------------------
# Engine — created once at module import time
# ---------------------------------------------------------------------------

def _build_database_url() -> str:
    """
    Returns the asyncpg-compatible DATABASE_URL.
    Accepts both plain postgresql:// and postgresql+asyncpg:// forms.
    """
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Copy .env.example to .env and fill in the PostgreSQL credentials."
        )
    # Ensure the asyncpg driver is used
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# ---------------------------------------------------------------------------
# Lazy engine — created on first use, not at import time
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Returns the shared AsyncEngine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _build_database_url(),
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns the shared session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession per request and closes it afterwards.

    Use as a FastAPI dependency:
        db: AsyncSession = Depends(get_db)
    """
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# ---------------------------------------------------------------------------
# Startup helper — called from main.py lifespan
# ---------------------------------------------------------------------------

async def create_tables() -> None:
    """
    Creates all tables that do not yet exist.
    In production use Alembic migrations instead; this is a fallback for
    development environments where Alembic has not been run yet.
    """
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
