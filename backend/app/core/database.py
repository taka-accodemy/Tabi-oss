from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
import asyncio
import logging

from app.core.config import settings
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

# Internal global variables for lazy initialization
_engine = None
_async_session_maker = None

def get_engine():
    """Get or create the database engine lazily"""
    global _engine
    if _engine is None:
        url = config_service.get_async_db_url()
        if not url:
            # If we're here, we probably shouldn't be using the DB, but let's provide a dummy or raise error later
            logger.warning("Attempted to get database engine with empty URL")
            # Create a dummy engine that will fail on use instead of on import
            _engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        else:
            _engine = create_async_engine(
                url,
                echo=settings.DEBUG,
                pool_pre_ping=True,
                pool_recycle=300,
            )
    return _engine

def get_session_maker():
    """Get or create the session maker lazily"""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker

# Create declarative base
Base = declarative_base()

# Create metadata
metadata = MetaData()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables"""
    # Only try to init if we have a valid postgres config
    if config_service.get_db_type() != "postgres":
        logger.info("Skipping database initialization for non-postgres database")
        return

    try:
        # Add timeout to prevent hanging on startup
        async def _init():
            engine = get_engine()
            async with engine.begin() as conn:
                # Import models here to register them with Base
                # from app.models import user, query_history, etc.
                await conn.run_sync(Base.metadata.create_all)
        
        await asyncio.wait_for(_init(), timeout=5.0)
        logger.info("Database initialized successfully")
    except asyncio.TimeoutError:
        logger.warning("Database initialization timed out - continuing startup without DB")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Not fatal, allowing app to start so config can be fixed