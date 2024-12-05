"""
Database configuration for news_storage module using SQLAlchemy with async support.
"""

from typing import Dict, Any, List
import logging
import pytz
from datetime import datetime
from sqlalchemy import update, delete, text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

# Import models directly from src.models
from src.models import Article, Content, Comment, CommentStats

KST = pytz.timezone('Asia/Seoul')
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object with KST timezone"""
    try:
        if isinstance(dt_str, datetime):
            # If already a datetime, ensure it has timezone
            return dt_str if dt_str.tzinfo else dt_str.replace(tzinfo=KST)
        if not dt_str:
            return None
            
        # Remove timezone info from string if present
        dt_str = dt_str.split('+')[0]
        # Parse the string to datetime and add KST timezone
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=KST) if not dt.tzinfo else dt
    except Exception as e:
        logger.error(f"Error parsing datetime {dt_str}: {e}")
        return None


class AsyncDatabaseOperations:
    """Async database operations for news storage"""

    @staticmethod
    def prepare_article_data(article_data: Dict[str, Any], main_keyword: str) -> Dict[str, Any]:
        """Prepare article data for database insertion"""
        # Whitelist allowed fields for Article model
        allowed_fields = [
            'naver_link', 'title', 'original_link', 'description', 
            'publisher', 'publisher_domain', 'published_at', 
            'published_date', 'collected_at', 'is_naver_news',
            'is_test', 'is_api_collection'
        ]
        
        data = {
            key: article_data.get(key) 
            for key in allowed_fields 
            if key in article_data
        }

        # Add main_keyword
        data['main_keyword'] = main_keyword or 'default_keyword'

        # Convert datetime strings to datetime objects with timezone
        if 'published_at' in data:
            data['published_at'] = parse_datetime(data['published_at'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        # Set default value for is_api_collection if not present
        if 'is_api_collection' not in data:
            data['is_api_collection'] = True

        return data

    @staticmethod
    async def create_article(session: AsyncSession, article_data: Dict[str, Any], main_keyword: str = 'default_keyword'):
        """Create a new article record with upsert logic"""
        # Initialize prepared_data before try block
        prepared_data = None
        try:
            # Prepare data with only allowed fields and main_keyword
            prepared_data = AsyncDatabaseOperations.prepare_article_data(
                article_data, main_keyword)

            # Use PostgreSQL's ON CONFLICT clause to handle duplicates
            stmt = insert(Article).values(**prepared_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['main_keyword', 'naver_link'],
                set_={
                    'title': stmt.excluded.title,
                    'original_link': stmt.excluded.original_link,
                    'description': stmt.excluded.description,
                    'publisher': stmt.excluded.publisher,
                    'publisher_domain': stmt.excluded.publisher_domain,
                    'published_at': stmt.excluded.published_at,
                    'published_date': stmt.excluded.published_date,
                    'collected_at': stmt.excluded.collected_at,
                    'is_naver_news': stmt.excluded.is_naver_news,
                    'is_test': stmt.excluded.is_test,
                    'is_api_collection': stmt.excluded.is_api_collection
                }
            )

            # Execute the statement
            await session.execute(stmt)
                
            # Get the article
            query = select(Article).where(
                (Article.main_keyword == main_keyword) & 
                (Article.naver_link == article_data['naver_link'])
            )
            result = await session.execute(query)
            return result.scalar_one()

        except Exception as e:
            logger.error(f"Error creating/updating article: {e}")
            if prepared_data:
                logger.error(f"Attempted data: {prepared_data}")
            raise

    @staticmethod
    def prepare_content_data(content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content data for database insertion"""
        data = content_data.copy()

        # Convert datetime strings to datetime objects with timezone
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
        # Initialize prepared_data before try block
        prepared_data = None
        try:
            content_data['article_id'] = article_id
            prepared_data = AsyncDatabaseOperations.prepare_content_data(
                content_data)

            content = Content(**prepared_data)
            session.add(content)
            await session.refresh(content)
            return content
        except Exception as e:
            logger.error(f"Error creating content: {e}")
            if prepared_data:
                logger.error(f"Attempted data: {prepared_data}")
            raise

    @staticmethod
    def prepare_comment_data(comment_data: Dict[str, Any], article_id: int) -> Dict[str, Any]:
        """Prepare comment data for database insertion"""
        data = comment_data.copy()

        # Add article_id
        data['article_id'] = article_id

        # Convert datetime strings to datetime objects with timezone
        if 'timestamp' in data:
            data['timestamp'] = parse_datetime(data['timestamp'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        # Map fields from collector to database model
        field_mapping = {
            'username': 'username',
            'profile_url': 'profile_url',
            'content': 'content',
            'timestamp': 'timestamp',
            'comment_no': 'comment_no',
            'parent_comment_no': 'parent_comment_no',
            'likes': 'likes',
            'dislikes': 'dislikes',
            'reply_count': 'reply_count',
            'is_reply': 'is_reply',
            'is_deleted': 'is_deleted',
            'delete_type': 'delete_type',
            'collected_at': 'collected_at'
        }

        prepared_data = {}
        for collector_field, db_field in field_mapping.items():
            if collector_field in data:
                prepared_data[db_field] = data[collector_field]

        # Add article_id
        prepared_data['article_id'] = article_id

        return prepared_data

    @staticmethod
    async def create_comment(session: AsyncSession, article_id: int, comment_data: Dict[str, Any]):
        """Create a new comment record"""
        # Initialize prepared_data before try block
        prepared_data = None
        try:
            prepared_data = AsyncDatabaseOperations.prepare_comment_data(
                comment_data, article_id)

            comment = Comment(**prepared_data)
            session.add(comment)
            await session.refresh(comment)
            return comment
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            if prepared_data:
                logger.error(f"Attempted data: {prepared_data}")
            raise

    @staticmethod
    def prepare_comment_stats_data(stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comment stats data for database insertion"""
        data = stats_data.copy()

        # Convert datetime strings to datetime objects with timezone
        if 'published_at' in data:
            data['published_at'] = parse_datetime(data['published_at'])
        if 'collected_at' in data:
            data['collected_at'] = parse_datetime(data['collected_at'])

        return data

    @staticmethod
    async def create_comment_stats(session: AsyncSession, stats_data: Dict[str, Any], comment_id: int):
        """Create new comment statistics record"""
        # Initialize prepared_data before try block
        prepared_data = None
        try:
            stats_data['comment_id'] = comment_id
            prepared_data = AsyncDatabaseOperations.prepare_comment_stats_data(
                stats_data)

            stats = CommentStats(**prepared_data)
            session.add(stats)
            await session.refresh(stats)
            return stats
        except Exception as e:
            logger.error(f"Error creating comment stats: {e}")
            if prepared_data:
                logger.error(f"Attempted data: {prepared_data}")
            raise

    @staticmethod
    async def batch_create_comments(
        session: AsyncSession,
        comments_data: List[Dict[str, Any]],
        article_id: int
    ):
        """Batch create comments for an article"""
        # Initialize comments list before try block
        comments = []
        try:
            for comment_data in comments_data:
                prepared_data = AsyncDatabaseOperations.prepare_comment_data(
                    comment_data, article_id)
                comment = Comment(**prepared_data)
                session.add(comment)
                comments.append(comment)

            # Refresh all comments to get their IDs
            for comment in comments:
                await session.refresh(comment)

            return comments
        except Exception as e:
            logger.error(f"Error batch creating comments: {e}")
            if comments:
                logger.error(f"Failed after processing {len(comments)} comments")
            raise

    @staticmethod
    async def get_article_by_naver_link(session: AsyncSession, main_keyword: str, naver_link: str):
        """Retrieve an article by its Naver link"""
        try:
            query = select(Article).where(
                (Article.main_keyword == main_keyword) & 
                (Article.naver_link == naver_link)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving article by main keyword and Naver link: {e}")
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
