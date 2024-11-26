"""
News Storage Configuration Module

Provides async configuration and initialization for the news storage system
"""
import os
import logging
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Database URL
DATABASE_URL = os.getenv('NEWS_STORAGE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/news_storage')

# Create engine
storage_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    poolclass=NullPool
)

# Create session factory
AsyncStorageSessionLocal = sessionmaker(
    storage_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Import after engine creation to avoid circular imports
from news_storage.database import StorageBase

async def init_storage():
    """Initialize news storage by creating all tables"""
    from news_storage.models import Article, Content, Comment, CommentStats
    async with storage_engine.begin() as conn:
        await conn.run_sync(StorageBase.metadata.create_all)
    logger.info("News storage tables initialized successfully.")


async def get_storage_session():
    """Get an async database session for news storage"""
    async with AsyncStorageSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def reset_storage():
    """Reset (drop and recreate) all storage tables"""
    from news_storage.models import Article, Content, Comment, CommentStats
    async with storage_engine.begin() as conn:
        await conn.run_sync(StorageBase.metadata.drop_all)
        await conn.run_sync(StorageBase.metadata.create_all)
    logger.info("News storage tables reset successfully.")
