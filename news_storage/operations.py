"""
News Storage Operations Module

Provides specialized storage operations for managing news-related data
within the CommentWatch project.
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Float
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .config import StorageBase


logger = logging.getLogger(__name__)


class MetadataStorage(StorageBase):
    """
    Model for storing news article metadata from collectors.
    """
    __tablename__ = 'metadata_storage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    naver_link = Column(String(500), unique=True, nullable=False)
    original_link = Column(String(500))
    description = Column(Text)
    publisher = Column(String(100))
    publisher_domain = Column(String(100))
    published_date = Column(String(20))
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    is_naver_news = Column(Boolean, default=False)
    collection_method = Column(String(20))  # 'api' or 'search'
    metadata = Column(JSON)


class CommentStorage(StorageBase):
    """
    Model for storing news article comments and statistics.
    """
    __tablename__ = 'comment_storage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_url = Column(String(500), nullable=False)
    total_comments = Column(Integer, default=0)
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    comments = Column(JSON)
    stats = Column(JSON)


class ContentStorage(StorageBase):
    """
    Model for storing detailed news article content.
    """
    __tablename__ = 'content_storage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_url = Column(String(500), unique=True, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    subheadings = Column(JSON)
    reporter = Column(String(100))
    media = Column(String(100))
    published_at = Column(DateTime)
    modified_at = Column(DateTime)
    category = Column(String(50))
    images = Column(JSON)
    collected_at = Column(DateTime, default=datetime.utcnow)


class NewsStorage:
    """
    Specialized storage system for managing news-related data
    with advanced tracking and management capabilities.
    """

    def __init__(self, session: Session):
        """
        Initialize NewsStorage with a database session.

        :param session: SQLAlchemy database session
        """
        self.session = session

    def __del__(self):
        """
        Ensure session is closed when the object is deleted.
        """
        if hasattr(self, 'session'):
            self.session.close()

    def store_metadata(self, metadata: Dict[str, Any]) -> MetadataStorage:
        """
        Store article metadata from collectors.

        :param metadata: Metadata dictionary from MetadataCollector
        :return: Stored MetadataStorage instance
        """
        try:
            # Normalize URL
            naver_link = metadata.get('naver_link', '')
            original_link = metadata.get(
                'original_link', '') if metadata.get('original_link') else None

            # Check for existing entry
            existing = self.session.query(MetadataStorage).filter_by(
                naver_link=naver_link).first()

            if existing:
                # Update existing entry
                for key, value in metadata.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new entry
                metadata_entry = MetadataStorage(
                    title=metadata.get('title', ''),
                    naver_link=naver_link,
                    original_link=original_link,
                    description=metadata.get('description', ''),
                    publisher=metadata.get('publisher', ''),
                    publisher_domain=metadata.get('publisher_domain', ''),
                    published_date=metadata.get('published_date'),
                    published_at=metadata.get('published_at'),
                    is_naver_news=metadata.get('is_naver_news', False),
                    collection_method=metadata.get('collection_method', ''),
                    metadata=metadata
                )
                self.session.add(metadata_entry)
                existing = metadata_entry

            self.session.commit()
            return existing

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error storing metadata: {str(e)}")
            raise

    def normalize_url(url: str) -> str:
        """URL을 정규화"""
        parsed = urlparse(url)
        if parsed.query:
            params = parse_qs(parsed.query)
            sorted_params = {k: v[0] for k, v in sorted(params.items())}
            query = urlencode(sorted_params)
        else:
            query = ''
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query,
            ''
        ))

    def store_comments(self, comments_data: Dict[str, Any]) -> CommentStorage:
        """
        Store comments and comment statistics.

        :param comments_data: Comments dictionary from CommentCollector
        :return: Stored CommentStorage instance
        """
        try:
            # Normalize URL
            article_url = comments_data.get('article_url', '')

            # Check for existing entry
            existing = self.session.query(CommentStorage).filter_by(
                article_url=article_url).first()

            if existing:
                # Update existing entry
                existing.total_comments = comments_data.get('total_count', 0)
                existing.published_at = comments_data.get('published_at')
                existing.comments = comments_data.get('comments', [])
                existing.stats = comments_data.get('stats', {})
                existing.collected_at = datetime.utcnow()
            else:
                # Create new entry
                comment_entry = CommentStorage(
                    article_url=article_url,
                    total_comments=comments_data.get('total_count', 0),
                    published_at=comments_data.get('published_at'),
                    comments=comments_data.get('comments', []),
                    stats=comments_data.get('stats', {})
                )
                self.session.add(comment_entry)
                existing = comment_entry

            self.session.commit()
            return existing

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error storing comments: {str(e)}")
            raise

    def store_content(self, content_data: Dict[str, Any]) -> ContentStorage:
        """
        Store article content details.

        :param content_data: Content dictionary from ContentCollector
        :return: Stored ContentStorage instance
        """
        try:
            # Normalize URL
            article_url = content_data.get('article_url', '')

            # Check for existing entry
            existing = self.session.query(ContentStorage).filter_by(
                article_url=article_url).first()

            if existing:
                # Update existing entry
                for key, value in content_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new entry
                content_entry = ContentStorage(
                    article_url=article_url,
                    title=content_data.get('title', ''),
                    content=content_data.get('content', ''),
                    subheadings=content_data.get('subheadings', []),
                    reporter=content_data.get('reporter', ''),
                    media=content_data.get('media', ''),
                    published_at=content_data.get('published_at'),
                    modified_at=content_data.get('modified_at'),
                    category=content_data.get('category', ''),
                    images=content_data.get('images', [])
                )
                self.session.add(content_entry)
                existing = content_entry

            self.session.commit()
            return existing

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error storing content: {str(e)}")
            raise

    def get_metadata_by_url(self, url: str) -> Optional[MetadataStorage]:
        """
        Retrieve metadata by normalized URL.

        :param url: Article URL
        :return: MetadataStorage instance or None
        """
        try:
            normalized_url = url
            return self.session.query(MetadataStorage).filter_by(naver_link=normalized_url).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving metadata: {str(e)}")
            return None

    def get_comments_by_url(self, url: str) -> Optional[CommentStorage]:
        """
        Retrieve comments by normalized URL.

        :param url: Article URL
        :return: CommentStorage instance or None
        """
        try:
            normalized_url = url
            return self.session.query(CommentStorage).filter_by(article_url=normalized_url).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving comments: {str(e)}")
            return None

    def get_content_by_url(self, url: str) -> Optional[ContentStorage]:
        """
        Retrieve content by normalized URL.

        :param url: Article URL
        :return: ContentStorage instance or None
        """
        try:
            normalized_url = url
            return self.session.query(ContentStorage).filter_by(article_url=normalized_url).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving content: {str(e)}")
            return None
