"""
Article keyword analysis models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Table
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base


class ArticleKeywordAnalysis(Base):
    """기사 키워드 분석 결과"""
    __tablename__ = "article_keywords_analysis"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Metadata
    analyzer_version = Column(String)  # 분석기 버전
    analysis_metadata = Column(JSON)   # 분석 설정 및 파라미터

    # Relationships
    article = relationship("Article", back_populates="keyword_analysis")

    # Extracted keywords with weights
    extracted_keywords = Column(JSONB)  # {keyword: weight}
    keyword_scores = Column(JSONB)     # {keyword: relevance_score}

    # Topic modeling results
    topics = Column(JSONB)            # 토픽 모델링 결과
    topic_distribution = Column(JSONB)  # 토픽 분포도

    # Named Entity Recognition
    named_entities = Column(JSONB)     # 개체명 인식 결과
    entity_relations = Column(JSONB)   # 개체 간 관계

    # Keyword categories
    main_themes = Column(ARRAY(String))  # 주요 테마
    sub_themes = Column(ARRAY(String))   # 부가 테마

    # Time-based analysis
    temporal_keywords = Column(JSONB)   # 시간대별 주요 키워드
    trend_keywords = Column(JSONB)      # 트렌드 키워드

    # Context analysis
    context_keywords = Column(JSONB)    # 맥락 키워드
    semantic_groups = Column(JSONB)     # 의미 그룹

    # Time tracking
    analysis_started_at = Column(DateTime)   # 분석 시작 시간
    analysis_completed_at = Column(DateTime)  # 분석 완료 시간

    # Analysis quality
    confidence_scores = Column(JSONB)   # 키워드별 신뢰도
    coverage_score = Column(Float)      # 분석 커버리지
    quality_score = Column(Float)       # 전반적 품질 점수
