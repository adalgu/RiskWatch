"""
SQLAlchemy models for news storage
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz
from .database import StorageBase

KST = pytz.timezone('Asia/Seoul')


class Article(StorageBase):
    """News article metadata"""
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    naver_link = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    published_at = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))

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
