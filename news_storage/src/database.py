"""
Database configuration for news_storage module using SQLAlchemy with async support.
Based on the Full Stack FastAPI Template pattern.
"""

from typing import AsyncGenerator, Generator
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:password@localhost:5432/news_db')
print(f"Using database URL: {DATABASE_URL}")

# Create engine with better connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv('DB_ECHO', 'False').lower() == 'true',
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
    max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
    pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
    pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '1800')),  # Recycle connections after 30 minutes
)

# Create session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Don't autoflush by default for better control
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting a database session.
    
    Usage:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.
    Should be called during application startup.
    
    In production, use Alembic migrations instead.
    """
    if os.getenv('ENVIRONMENT', 'development') == 'development':
        async with engine.begin() as conn:
            # Import all models to ensure they're registered with SQLModel metadata
            from news_storage.src.models import Article, Content, Comment, CommentStats
            
            # Create tables
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables initialized successfully.")


class DatabaseOperations:
    """
    Base class for database operations.
    Provides common methods for CRUD operations.
    """
    
    @staticmethod
    async def execute_transaction(transaction_func, *args, **kwargs):
        """
        Execute a database transaction with automatic session management.
        
        Args:
            transaction_func: Async function to execute within a transaction
            *args: Positional arguments for the transaction function
            **kwargs: Keyword arguments for the transaction function
            
        Returns:
            Result of the transaction function
        """
        async with async_session_factory() as session:
            async with session.begin():
                return await transaction_func(session, *args, **kwargs)
