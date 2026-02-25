"""
Database Session & Engine Setup

The app is fully async:
  - `engine`            — AsyncEngine  (used for `await engine.dispose()`)
  - `AsyncSessionLocal` — async_sessionmaker, used as context manager
  - `get_db()`          — async FastAPI dependency yielding AsyncSession

Health-check helpers use a lightweight *sync* engine to avoid
the need for a running event loop at import time.
"""
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.exc import SQLAlchemyError
from config.settings import settings
from utils.logger import logger


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------ Async (primary)
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async FastAPI dependency — yields an AsyncSession per request.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ------------------------------------------------------------------ Sync (health checks only)
_sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=0,
)


def check_database_connection() -> bool:
    """
    Check database connection health.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with _sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check: OK")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database check: {str(e)}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information.

    Returns:
        Dictionary with database info including pool statistics
    """
    try:
        with _sync_engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
        return {
            "connected": True,
            "url": settings.DATABASE_URL_SAFE,
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "version": version,
        }
    except Exception as exc:
        logger.error(f"Failed to get database info: {str(exc)}")
        return {"connected": False, "error": str(exc)}
