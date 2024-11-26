"""
Article sentiment analysis models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, Enum, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base
from ...enums import SentimentCategory


class ArticleSentiment(Base):
    """기사 감성분석 결과"""
    __tablename__ = "article_sentiment"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    sentiment_score = Column(Float)
    sentiment_category = Column(Enum(SentimentCategory))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Metadata
    analyzer_version = Column(String)  # 분석기 버전
    confidence_score = Column(Float)   # 신뢰도 점수
    analysis_metadata = Column(JSON)   # 추가 메타데이터 (분석 파라미터 등)

    # Relationships
    article = relationship("Article", back_populates="sentiment_analysis")

    # Detailed sentiment scores
    positive_score = Column(Float)     # 긍정 점수
    neutral_score = Column(Float)      # 중립 점수
    negative_score = Column(Float)     # 부정 점수

    # Analysis breakdown
    title_sentiment = Column(Float)    # 제목 감성 점수
    content_sentiment = Column(Float)  # 본문 감성 점수

    # Time tracking
    analysis_started_at = Column(DateTime)  # 분석 시작 시간
    analysis_completed_at = Column(DateTime)  # 분석 완료 시간
