"""
core/database.py
────────────────
Async SQLAlchemy engine, session factory, and base model.

KEY FIX: Engine is created LAZILY inside get_engine() — NOT at module
import time. This means the .env file is fully loaded before any
database connection is attempted. Avoids the psycopg2/asyncpg conflict.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    pass

# ── Module-level singletons (None until first use) ───────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    """
    Return (or lazily create) the async SQLAlchemy engine.
    Called only after the app has fully loaded settings from .env.
    """
    global _engine
    if _engine is None:
        from app.core.config import settings

        # Ensure the URL uses the asyncpg driver.
        # Guard against accidentally using postgresql:// without +asyncpg
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            db_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=settings.is_development,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


# ── Convenience alias used in deps.py ────────────────────────────
class AsyncSessionLocal:
    """Proxy that delegates to the lazily-created session factory."""
    def __new__(cls):
        return get_session_factory()()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def init_db() -> None:
    """Create tables in dev. Use Alembic migrations in production."""
    from app.core.config import settings
    if settings.is_development:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
