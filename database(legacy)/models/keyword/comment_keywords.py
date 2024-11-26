"""
Comment keyword analysis models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Table, Boolean
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base


class CommentKeywordAnalysis(Base):
    """댓글 키워드 분석 결과"""
    __tablename__ = "comment_keywords_analysis"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Metadata
    analyzer_version = Column(String)  # 분석기 버전
    analysis_metadata = Column(JSON)   # 분석 설정 및 파라미터

    # Relationships
    comment = relationship("Comment", back_populates="keyword_analysis")

    # Extracted keywords with weights
    extracted_keywords = Column(JSONB)  # {keyword: weight}
    keyword_scores = Column(JSONB)     # {keyword: relevance_score}

    # Comment-specific analysis
    sentiment_keywords = Column(JSONB)  # 감성 관련 키워드
    opinion_keywords = Column(JSONB)    # 의견 관련 키워드
    argument_keywords = Column(JSONB)   # 논쟁점 관련 키워드

    # Topic and theme analysis
    topics = Column(JSONB)             # 토픽 분석 결과
    main_themes = Column(ARRAY(String))  # 주요 테마
    sub_themes = Column(ARRAY(String))  # 부가 테마

    # Interaction analysis
    reply_context = Column(JSONB)      # 답글 맥락 분석
    interaction_keywords = Column(JSONB)  # 상호작용 관련 키워드

    # User behavior analysis
    user_stance = Column(String)       # 사용자 입장/태도
    behavior_patterns = Column(JSONB)  # 행동 패턴 분석

    # Content classification
    is_constructive = Column(Boolean, default=True)  # 건설적 의견 여부
    is_off_topic = Column(Boolean, default=False)    # 주제 이탈 여부
    content_type = Column(String)      # 내용 유형 (질문/주장/반론 등)

    # Named Entity Recognition
    named_entities = Column(JSONB)     # 개체명 인식 결과
    entity_relations = Column(JSONB)   # 개체 간 관계

    # Context analysis
    article_relevance = Column(JSONB)  # 원문 관련성 분석
    context_keywords = Column(JSONB)   # 맥락 키워드
    semantic_groups = Column(JSONB)    # 의미 그룹

    # Time tracking
    analysis_started_at = Column(DateTime)   # 분석 시작 시간
    analysis_completed_at = Column(DateTime)  # 분석 완료 시간

    # Analysis quality
    confidence_scores = Column(JSONB)   # 키워드별 신뢰도
    coverage_score = Column(Float)      # 분석 커버리지
    quality_score = Column(Float)       # 전반적 품질 점수

    # Aggregation flags
    include_in_summary = Column(Boolean, default=True)  # 요약에 포함 여부
    is_representative = Column(Boolean, default=False)  # 대표성 여부
