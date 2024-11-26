"""
Comment sentiment analysis models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, Enum, ForeignKey, String, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base
from ...enums import SentimentCategory


class CommentSentiment(Base):
    """댓글 감성분석 결과"""
    __tablename__ = "comment_sentiment"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id"))
    sentiment_score = Column(Float)
    sentiment_category = Column(Enum(SentimentCategory))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Metadata
    analyzer_version = Column(String)  # 분석기 버전
    confidence_score = Column(Float)   # 신뢰도 점수
    analysis_metadata = Column(JSON)   # 추가 메타데이터 (분석 파라미터 등)

    # Relationships
    comment = relationship("Comment", back_populates="sentiment_analysis")

    # Detailed sentiment scores
    positive_score = Column(Float)     # 긍정 점수
    neutral_score = Column(Float)      # 중립 점수
    negative_score = Column(Float)     # 부정 점수

    # Contextual analysis
    context_relevance = Column(Float)  # 맥락 관련성 점수
    parent_influence = Column(Float)   # 부모 댓글 영향도

    # Emotion categories
    anger_score = Column(Float)        # 분노 점수
    joy_score = Column(Float)         # 기쁨 점수
    sadness_score = Column(Float)     # 슬픔 점수
    fear_score = Column(Float)        # 두려움 점수

    # Time tracking
    analysis_started_at = Column(DateTime)  # 분석 시작 시간
    analysis_completed_at = Column(DateTime)  # 분석 완료 시간

    # Analysis flags
    is_spam = Column(Boolean, default=False)  # 스팸 여부
    is_offensive = Column(Boolean, default=False)  # 공격적 내용 여부
    needs_review = Column(Boolean, default=False)  # 검토 필요 여부
