"""
SQLAlchemy models for news storage
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz
from .database import StorageBase

KST = pytz.timezone('Asia/Seoul')


class Article(StorageBase):
    """News article metadata"""
    __tablename__ = 'articles'

    # Unique constraint on main_keyword and naver_link
    __table_args__ = (
        UniqueConstraint('main_keyword', 'naver_link', name='uq_main_keyword_naver_link'),
    )

    id = Column(Integer, primary_key=True)
    main_keyword = Column(String, nullable=False, server_default='default_keyword')
    naver_link = Column(String, nullable=False)
    title = Column(String, nullable=False)
    original_link = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    publisher = Column(String, nullable=True)
    publisher_domain = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True))
    published_date = Column(String, nullable=True)
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))
    is_naver_news = Column(Boolean, nullable=True, default=True)

    # Relationships
    content = relationship("Content", back_populates="article", uselist=False)
    comments = relationship("Comment", back_populates="article")


class Content(StorageBase):
    """News article content"""
    __tablename__ = 'contents'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), unique=True)
    content = Column(Text)
    published_at = Column(DateTime(timezone=True))
    modified_at = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))

    # Relationships
    article = relationship("Article", back_populates="content")


class Comment(StorageBase):
    """News article comment"""
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    comment_no = Column(String)
    username = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))
    parent_comment_no = Column(String, nullable=True)
    is_reply = Column(Boolean, default=False)

    # Relationships
    article = relationship("Article", back_populates="comments")
    stats = relationship(
        "CommentStats", back_populates="comment", uselist=False)


class CommentStats(StorageBase):
    """Comment statistics"""
    __tablename__ = 'comment_stats'

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), unique=True)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))

    # Relationships
    comment = relationship("Comment", back_populates="stats")
