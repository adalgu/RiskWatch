"""
Comment statistics models for CommentWatch
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from ...config import Base


class CommentStats(Base):
    """댓글 통계 정보 (시계열)"""
    __tablename__ = "comment_stats"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Basic comment counts
    total_count = Column(Integer, default=0)      # 전체 댓글 수
    current_count = Column(Integer, nullable=True)  # 현재 표시 댓글 수
    deleted_count = Column(Integer, default=0)     # 삭제된 댓글 수

    # Deletion details
    user_deleted_count = Column(Integer, nullable=True)   # 사용자 삭제 수
    admin_deleted_count = Column(Integer, nullable=True)  # 관리자 삭제 수
    auto_deleted_count = Column(Integer, nullable=True)   # 자동 삭제 수

    # Demographic analysis
    gender_ratio = Column(JSONB)  # 성별 분포 (확장성 고려)
    male_ratio = Column(Float, nullable=True)
    female_ratio = Column(Float, nullable=True)

    # Age distribution
    age_distribution = Column(JSONB)  # 연령대별 분포 (확장성 고려)
    age_10s = Column(Float, nullable=True)
    age_20s = Column(Float, nullable=True)
    age_30s = Column(Float, nullable=True)
    age_40s = Column(Float, nullable=True)
    age_50s = Column(Float, nullable=True)
    age_60s_above = Column(Float, nullable=True)

    # Interaction metrics
    likes_distribution = Column(JSONB)        # 좋아요 분포
    replies_distribution = Column(JSONB)      # 답글 분포
    avg_likes_per_comment = Column(Float)     # 댓글당 평균 좋아요
    avg_replies_per_comment = Column(Float)   # 댓글당 평균 답글

    # Time-based metrics
    hourly_distribution = Column(JSONB)       # 시간대별 분포
    daily_distribution = Column(JSONB)        # 일별 분포
    peak_hours = Column(JSONB)               # 피크 시간대

    # User behavior
    unique_users = Column(Integer)           # 고유 사용자 수
    user_participation = Column(JSONB)       # 사용자별 참여도
    repeat_commenter_ratio = Column(Float)   # 반복 댓글작성자 비율

    # Content quality
    avg_comment_length = Column(Float)       # 평균 댓글 길이
    quality_metrics = Column(JSONB)          # 품질 지표
    spam_ratio = Column(Float)              # 스팸 비율

    # Sentiment distribution
    sentiment_distribution = Column(JSONB)   # 감성 분포
    controversy_score = Column(Float)        # 논쟁성 점수

    # Relationships
    article = relationship("Article", back_populates="comment_stats")

    # Meta information
    collection_metadata = Column(JSON)       # 수집 관련 메타데이터
    is_complete = Column(Boolean, default=False)  # 수집 완료 여부
    last_updated = Column(DateTime, onupdate=datetime.utcnow)  # 마지막 업데이트
