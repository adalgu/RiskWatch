"""
Comment-related models for CommentWatch database
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from ..config import Base
from ..enums import SentimentCategory


KST = pytz.timezone('Asia/Seoul')


class Comment(Base):
    """Comment model representing article comments"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))

    # 기존 필드
    content = Column(Text)
    comment_keywords = Column(JSON)
    sentiment = Column(Enum(SentimentCategory))
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(KST))

    # 새로운 필드
    comment_no = Column(String)
    parent_comment_no = Column(String, nullable=True)
    author = Column(String)
    profile_url = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True))  # 댓글 작성 시간 (KST)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    is_reply = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    delete_type = Column(String, nullable=True)

    # Relationships
    article = relationship("Article", back_populates="comments")

    # Analysis relationships
    sentiment_analysis = relationship(
        "CommentSentiment", back_populates="comment")
    keyword_analysis = relationship(
        "CommentKeywordAnalysis", back_populates="comment")
