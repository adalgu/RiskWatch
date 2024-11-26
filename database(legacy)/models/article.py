"""
Article-related models for CommentWatch database
"""

import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from ..config import Base
from ..enums import ArticleStatus, CollectionMethod


KST = pytz.timezone('Asia/Seoul')


class Article(Base):
    """Article model representing news articles"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    naver_link = Column(String)  # 네이버 뉴스 링크
    original_link = Column(String)  # 언론사 원본 링크
    description = Column(Text)

    # 언론사 정보
    publisher = Column(String)  # 언론사 이름 (SearchCollector)
    publisher_domain = Column(String)  # 언론사 도메인 (APICollector)

    # 날짜 정보
    pub_date = Column(Date, nullable=True)  # SearchCollector의 날짜 정보
    # APICollector의 정확한 발행일시 (원본 timezone 유지)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # 검색 키워드 (수집 시 사용된 키워드)
    main_keyword = Column(String)

    # 수집 정보
    collection_method = Column(Enum(CollectionMethod))  # API 또는 SEARCH
    content_status = Column(Enum(ArticleStatus),  # 본문 수집 상태
                            default=ArticleStatus.pending, nullable=False)
    comment_status = Column(Enum(ArticleStatus),  # 댓글 수집 상태
                            default=ArticleStatus.pending, nullable=False)

    # 시간 정보 (내부 생성 시간은 KST 기준)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(KST))  # 메타데이터 수집 시간
    collected_at = Column(DateTime(timezone=True), nullable=True)  # 본문 수집 시간
    comment_collected_at = Column(
        DateTime(timezone=True), nullable=True)  # 댓글 수집 시간
    last_updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(KST),
        onupdate=lambda: datetime.now(KST))

    # Relationships
    comments = relationship("Comment", back_populates="article")
    mappings = relationship("ArticleMapping", back_populates="article")

    # Analysis relationships
    comment_stats = relationship("CommentStats", back_populates="article")
    article_stats = relationship("ArticleStats", back_populates="article")
    sentiment_analysis = relationship(
        "ArticleSentiment", back_populates="article")
    keyword_analysis = relationship(  # 기사 키워드 분석 결과
        "ArticleKeywordAnalysis", back_populates="article")

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            'main_keyword', 'naver_link', name='unique_main_keyword_naver_link'),
    )


class ArticleCollectionLog(Base):
    """Log model for article collection process"""
    __tablename__ = "article_collection_logs"

    id = Column(Integer, primary_key=True)
    keyword = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_articles = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(KST))

    __table_args__ = (
        sqlalchemy.Index('idx_collection_logs_keyword_dates',
                         'keyword', 'start_date', 'end_date'),
    )


class ArticleMapping(Base):
    """Model for mapping articles to keywords"""
    __tablename__ = "article_mappings"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    main_keyword = Column(String)
    sub_keyword = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(KST))

    # Collection fields
    collection_method = Column(Enum(CollectionMethod))
    subset_size = Column(Integer, default=0)  # 해당 키워드 조합으로 검색된 기사 수
    overlap_count = Column(Integer, default=0)  # 다른 서브 키워드와 중복된 기사 수

    # Relationships
    article = relationship("Article", back_populates="mappings")
