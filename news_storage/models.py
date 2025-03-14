"""
SQLAlchemy models for news storage
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import pytz
from .base import StorageBase

KST = pytz.timezone('Asia/Seoul')

# TODO: 향후 감성분석 기능 구현시 활성화
# class SentimentCategory(enum.Enum):
#     """감성 분석 카테고리"""
#     POSITIVE = "positive"
#     NEGATIVE = "negative"
#     NEUTRAL = "neutral"
#     MIXED = "mixed"

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
    is_test = Column(Boolean, nullable=False, default=True)
    is_api_collection = Column(Boolean, nullable=False, default=True)

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
    
    # 기본 정보
    comment_no = Column(String)
    parent_comment_no = Column(String, nullable=True)
    content = Column(Text)
    username = Column(String)  # author를 username으로 변경
    profile_url = Column(String, nullable=True)
    
    # 시간 정보
    timestamp = Column(DateTime(timezone=True))  # 댓글 작성 시간
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))
    
    # 상호작용 정보
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    # 상태 정보
    is_reply = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    delete_type = Column(String, nullable=True)
    
    # TODO: 향후 분석 기능 구현시 활성화
    # comment_keywords = Column(JSON)
    # sentiment = Column(Enum(SentimentCategory))

    # Relationships
    article = relationship("Article", back_populates="comments")
    stats = relationship("CommentStats", back_populates="comment", uselist=False)
    # TODO: 향후 분석 기능 구현시 활성화
    # sentiment_analysis = relationship("CommentSentiment", back_populates="comment")
    # keyword_analysis = relationship("CommentKeywordAnalysis", back_populates="comment")


class CommentStats(StorageBase):
    """Comment statistics with enhanced metrics"""
    __tablename__ = 'comment_stats'

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), unique=True)
    
    # Basic metrics (from original)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    
    # Comment counts
    total_count = Column(Integer, default=0)
    current_count = Column(Integer, nullable=True)
    deleted_count = Column(Integer, default=0)

    # Deletion details
    user_deleted_count = Column(Integer, nullable=True)
    admin_deleted_count = Column(Integer, nullable=True)
    auto_deleted_count = Column(Integer, nullable=True)

    # Demographic analysis
    gender_ratio = Column(JSONB)
    male_ratio = Column(Float, nullable=True)
    female_ratio = Column(Float, nullable=True)

    # Age distribution
    age_distribution = Column(JSONB)
    age_10s = Column(Float, nullable=True)
    age_20s = Column(Float, nullable=True)
    age_30s = Column(Float, nullable=True)
    age_40s = Column(Float, nullable=True)
    age_50s = Column(Float, nullable=True)
    age_60s_above = Column(Float, nullable=True)

    # Interaction metrics
    likes_distribution = Column(JSONB)
    replies_distribution = Column(JSONB)
    avg_likes_per_comment = Column(Float)
    avg_replies_per_comment = Column(Float)

    # Time-based metrics
    hourly_distribution = Column(JSONB)
    daily_distribution = Column(JSONB)
    peak_hours = Column(JSONB)

    # User behavior
    unique_users = Column(Integer)
    user_participation = Column(JSONB)
    repeat_commenter_ratio = Column(Float)

    # Content quality
    avg_comment_length = Column(Float)
    quality_metrics = Column(JSONB)
    spam_ratio = Column(Float)

    # Sentiment analysis
    sentiment_distribution = Column(JSONB)
    controversy_score = Column(Float)

    # Meta information
    collection_metadata = Column(JSON)
    is_complete = Column(Boolean, default=False)
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))
    last_updated = Column(DateTime(timezone=True),
                          onupdate=lambda: datetime.now(KST))

    # Relationships
    comment = relationship("Comment", back_populates="stats")

# TODO: 향후 감성분석 기능 구현시 활성화
# class CommentSentiment(StorageBase):
#     """Comment sentiment analysis results"""
#     __tablename__ = 'comment_sentiments'

#     id = Column(Integer, primary_key=True)
#     comment_id = Column(Integer, ForeignKey('comments.id'), unique=True)
    
#     # Sentiment scores
#     positive_score = Column(Float)
#     negative_score = Column(Float)
#     neutral_score = Column(Float)
#     compound_score = Column(Float)
    
#     # Final classification
#     sentiment_category = Column(Enum(SentimentCategory))
    
#     # Meta information
#     collected_at = Column(DateTime(timezone=True),
#                           default=lambda: datetime.now(KST))
    
#     # Relationships
#     comment = relationship("Comment", back_populates="sentiment_analysis")


# TODO: 향후 키워드 분석 기능 구현시 활성화
# class CommentKeywordAnalysis(StorageBase):
#     """Comment keyword analysis results"""
#     __tablename__ = 'comment_keyword_analyses'

#     id = Column(Integer, primary_key=True)
#     comment_id = Column(Integer, ForeignKey('comments.id'), unique=True)
    
#     # Keyword analysis
#     keywords = Column(JSON)  # List of extracted keywords with scores
#     entities = Column(JSON)  # Named entities found in the comment
#     topics = Column(JSON)    # Topic classification results
    
#     # Meta information
#     collected_at = Column(DateTime(timezone=True),
#                           default=lambda: datetime.now(KST))
    
#     # Relationships
#     comment = relationship("Comment", back_populates="keyword_analysis")
