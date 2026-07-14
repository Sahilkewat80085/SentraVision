"""
SentraVision — Async SQLAlchemy Engine + Session Factory
"""
from collections.abc import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger("sentravision.database")
settings = get_settings()

logger.info("Initializing async database engine...")
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy declarative models.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async database session.
    Automatically handles transaction rollback on exception and resource cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database session opened.")
            yield session
        except Exception as exc:
            logger.error("Exception encountered in database session; performing rollback.", exc_info=exc)
            await session.rollback()
            raise
        finally:
            logger.debug("Database session closed.")
            await session.close()


async def init_db() -> None:
    """
    Create all database tables on startup.
    Note: For production environments, database migrations should be managed via Alembic.
    """
    logger.info("Initializing database schemas and registering models...")
    try:
        async with engine.begin() as conn:
            from app.models import video, roi  # noqa: F401 — register models
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialization completed successfully.")
    except Exception as exc:
        logger.critical("Database initialization failed!", exc_info=exc)
        raise

