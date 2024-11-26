"""
Article statistics models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base


class ArticleStats(Base):
    """기사 통계 정보 (시계열)"""
    __tablename__ = "article_stats"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    collected_at = Column(DateTime, default=datetime.utcnow)

    # View metrics
    view_count = Column(Integer, default=0)       # 조회수
    unique_visitors = Column(Integer, default=0)   # 고유 방문자 수
    bounce_rate = Column(Float)                   # 이탈률
    avg_time_spent = Column(Float)                # 평균 체류시간

    # Engagement metrics
    comment_count = Column(Integer, default=0)     # 댓글 수
    share_count = Column(Integer, default=0)       # 공유 수
    like_count = Column(Integer, default=0)        # 좋아요 수
    engagement_rate = Column(Float)                # 참여율

    # Traffic sources
    traffic_sources = Column(JSONB)               # 트래픽 출처
    referral_distribution = Column(JSONB)         # 레퍼러 분포
    device_distribution = Column(JSONB)           # 디바이스 분포

    # Time-based metrics
    hourly_views = Column(JSONB)                 # 시간대별 조회수
    daily_views = Column(JSONB)                  # 일별 조회수
    peak_times = Column(JSONB)                   # 피크 시간대
    view_duration_distribution = Column(JSONB)    # 조회 시간 분포

    # Content performance
    content_score = Column(Float)                # 콘텐츠 점수
    relevance_score = Column(Float)              # 관련성 점수
    quality_metrics = Column(JSONB)              # 품질 지표

    # Keyword performance
    keyword_performance = Column(JSONB)          # 키워드별 성과
    search_visibility = Column(Float)            # 검색 노출도
    keyword_ranking = Column(JSONB)              # 키워드 순위

    # Social metrics
    social_shares = Column(JSONB)                # 소셜 공유 현황
    social_engagement = Column(JSONB)            # 소셜 참여도
    viral_coefficient = Column(Float)            # 바이럴 계수

    # Comment engagement
    comment_velocity = Column(Float)             # 댓글 생성 속도
    comment_depth_distribution = Column(JSONB)   # 댓글 깊이 분포
    discussion_activity = Column(JSONB)          # 토론 활성도

    # Sentiment metrics
    overall_sentiment = Column(Float)            # 전체 감성 점수
    sentiment_trends = Column(JSONB)             # 감성 트렌드
    controversy_index = Column(Float)            # 논쟁 지수

    # Comparative metrics
    category_ranking = Column(Integer)           # 카테고리 내 순위
    relative_performance = Column(JSONB)         # 상대적 성과
    benchmark_metrics = Column(JSONB)            # 벤치마크 지표

    # Collection metadata
    collection_method = Column(String)           # 수집 방법
    collection_frequency = Column(String)        # 수집 주기
    is_complete = Column(Boolean, default=False)  # 수집 완료 여부
    last_updated = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="article_stats")

    # Aggregation flags
    include_in_trends = Column(Boolean, default=True)    # 트렌드 포함 여부
    is_outlier = Column(Boolean, default=False)         # 이상치 여부
    needs_review = Column(Boolean, default=False)       # 검토 필요 여부
