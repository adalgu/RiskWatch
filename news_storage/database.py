"""
Database configuration for news_storage module using SQLAlchemy with async support.
"""

from typing import Dict, Any, List
import logging
import pytz
from datetime import datetime
from sqlalchemy import update, delete
from sqlalchemy.future import select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession

# Create declarative base for storage models
StorageBase = declarative_base()

KST = pytz.timezone('Asia/Seoul')
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object"""
    try:
        if isinstance(dt_str, datetime):
            return dt_str
        if not dt_str:
            return None
        # Remove timezone info from string if present
        dt_str = dt_str.split('+')[0]
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=KST)
    except Exception as e:
        logger.error(f"Error parsing datetime {dt_str}: {e}")
        return None


class AsyncDatabaseOperations:
    """Async database operations for news storage"""

    @staticmethod
    def prepare_article_data(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare article data for database insertion"""
        data = article_data.copy()

        # Convert datetime strings to datetime objects
        if 'published_at' in data:
            data['published_at'] = parse_datetime(data['published_at'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        return data

    @staticmethod
    async def create_article(session: AsyncSession, article_data: Dict[str, Any]):
        """Create a new article record"""
        try:
            # Import here to avoid circular import
            from news_storage.models import Article

            # Prepare data with proper datetime objects
            prepared_data = AsyncDatabaseOperations.prepare_article_data(
                article_data)

            article = Article(**prepared_data)
            session.add(article)
            await session.commit()
            await session.refresh(article)
            return article
        except Exception as e:
            logger.error(f"Error creating article: {e}")
            await session.rollback()
            raise

    @staticmethod
    def prepare_content_data(content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content data for database insertion"""
        data = content_data.copy()

        # Convert datetime strings to datetime objects
        if 'published_at' in data:
            data['published_at'] = parse_datetime(data['published_at'])
        if 'modified_at' in data:
            data['modified_at'] = parse_datetime(data['modified_at'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        return data

    @staticmethod
    async def create_content(session: AsyncSession, content_data: Dict[str, Any], article_id: int):
        """Create a new content record"""
        try:
            # Import here to avoid circular import
            from news_storage.models import Content

            content_data['article_id'] = article_id
            prepared_data = AsyncDatabaseOperations.prepare_content_data(
                content_data)

            content = Content(**prepared_data)
            session.add(content)
            await session.commit()
            await session.refresh(content)
            return content
        except Exception as e:
            logger.error(f"Error creating content: {e}")
            await session.rollback()
            raise

    @staticmethod
    def prepare_comment_data(comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comment data for database insertion"""
        data = comment_data.copy()

        # Convert datetime strings to datetime objects
        if 'timestamp' in data:
            data['timestamp'] = parse_datetime(data['timestamp'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        return data

    @staticmethod
    async def create_comment(session: AsyncSession, comment_data: Dict[str, Any], article_id: int):
        """Create a new comment record"""
        try:
            # Import here to avoid circular import
            from news_storage.models import Comment

            comment_data['article_id'] = article_id
            prepared_data = AsyncDatabaseOperations.prepare_comment_data(
                comment_data)

            comment = Comment(**prepared_data)
            session.add(comment)
            await session.commit()
            await session.refresh(comment)
            return comment
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            await session.rollback()
            raise

    @staticmethod
    def prepare_comment_stats_data(stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comment stats data for database insertion"""
        data = stats_data.copy()

        # Convert datetime strings to datetime objects
        if 'published_at' in data:
            data['published_at'] = parse_datetime(data['published_at'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        return data

    @staticmethod
    async def create_comment_stats(session: AsyncSession, stats_data: Dict[str, Any], comment_id: int):
        """Create new comment statistics record"""
        try:
            # Import here to avoid circular import
            from news_storage.models import CommentStats

            stats_data['comment_id'] = comment_id
            prepared_data = AsyncDatabaseOperations.prepare_comment_stats_data(
                stats_data)

            stats = CommentStats(**prepared_data)
            session.add(stats)
            await session.commit()
            await session.refresh(stats)
            return stats
        except Exception as e:
            logger.error(f"Error creating comment stats: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def batch_create_comments(
        session: AsyncSession,
        comments_data: List[Dict[str, Any]],
        article_id: int
    ):
        """Batch create comments for an article"""
        try:
            # Import here to avoid circular import
            from news_storage.models import Comment

            comments = []
            for comment_data in comments_data:
                comment_data['article_id'] = article_id
                prepared_data = AsyncDatabaseOperations.prepare_comment_data(
                    comment_data)
                comment = Comment(**prepared_data)
                session.add(comment)
                comments.append(comment)

            await session.commit()

            # Refresh all comments to get their IDs
            for comment in comments:
                await session.refresh(comment)

            return comments
        except Exception as e:
            logger.error(f"Error batch creating comments: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_article_by_naver_link(session: AsyncSession, naver_link: str):
        """Retrieve an article by its Naver link"""
        try:
            # Import here to avoid circular import
            from news_storage.models import Article

            result = await session.execute(
                select(Article).where(Article.naver_link == naver_link)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving article by Naver link: {e}")
            raise

    @classmethod
    async def execute_transaction(cls, transaction_func, *args, **kwargs):
        """
        Execute a database transaction with automatic session management

        :param transaction_func: Async function to execute within a transaction
        :param args: Positional arguments for the transaction function
        :param kwargs: Keyword arguments for the transaction function
        :return: Result of the transaction
        """
        from news_storage.config import AsyncStorageSessionLocal
        async with AsyncStorageSessionLocal() as session:
            async with session.begin():
                return await transaction_func(session, *args, **kwargs)
