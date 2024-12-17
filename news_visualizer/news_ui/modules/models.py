from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Column, DateTime, MetaData
from sqlalchemy.dialects.postgresql import JSONB, JSON
import pytz

# 한국 표준시(KST) 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """Return current time in KST"""
    return datetime.now(KST)

# Create a single MetaData instance
metadata = MetaData()

class Article(SQLModel, table=True):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint('main_keyword', 'naver_link', name='uq_main_keyword_naver_link'),
        {'extend_existing': True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    main_keyword: str = Field(default="default_keyword", nullable=False)
    naver_link: str = Field(nullable=False)
    title: str = Field(nullable=False)
    original_link: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_domain: Optional[str] = None
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    published_date: Optional[str] = None
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )
    is_naver_news: Optional[bool] = Field(default=False)
    is_test: bool = Field(default=True)
    is_api_collection: bool = Field(default=False)

    content: Optional["Content"] = Relationship(
        back_populates="article",
        sa_relationship_kwargs={
            "uselist": False,
            "primaryjoin": "Article.id==Content.article_id"
        }
    )
    comments: List["Comment"] = Relationship(
        back_populates="article",
        sa_relationship_kwargs={
            "primaryjoin": "Article.id==Comment.article_id"
        }
    )


class Content(SQLModel, table=True):
    __tablename__ = "contents"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", unique=True)
    content: Optional[str] = None
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    modified_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )

    article: Optional["Article"] = Relationship(
        back_populates="content",
        sa_relationship_kwargs={
            "primaryjoin": "Content.article_id==Article.id"
        }
    )


class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp of the comment"
    )
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)
    reply_count: int = Field(default=0)
    is_reply: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    delete_type: Optional[str] = None

    article: Optional["Article"] = Relationship(
        back_populates="comments",
        sa_relationship_kwargs={
            "primaryjoin": "Comment.article_id==Article.id"
        }
    )
    stats: Optional["CommentStats"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={
            "uselist": False,
            "primaryjoin": "Comment.id==CommentStats.comment_id"
        }
    )


class CommentStats(SQLModel, table=True):
    __tablename__ = "comment_stats"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    comment_id: int = Field(foreign_key="comments.id", unique=True)
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)
    total_count: int = Field(default=0)
    current_count: Optional[int] = None
    deleted_count: int = Field(default=0)
    user_deleted_count: Optional[int] = None
    admin_deleted_count: Optional[int] = None
    auto_deleted_count: Optional[int] = None
    gender_ratio: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    male_ratio: Optional[float] = None
    female_ratio: Optional[float] = None
    age_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    age_10s: Optional[float] = None
    age_20s: Optional[float] = None
    age_30s: Optional[float] = None
    age_40s: Optional[float] = None
    age_50s: Optional[float] = None
    age_60s_above: Optional[float] = None
    likes_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    replies_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    avg_likes_per_comment: Optional[float] = None
    avg_replies_per_comment: Optional[float] = None
    hourly_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    daily_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    peak_hours: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    unique_users: Optional[int] = None
    user_participation: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    repeat_commenter_ratio: Optional[float] = None
    avg_comment_length: Optional[float] = None
    quality_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    spam_ratio: Optional[float] = None
    sentiment_distribution: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    controversy_score: Optional[float] = None
    collection_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_complete: bool = Field(default=False)
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=get_kst_now)
    )

    comment: Optional["Comment"] = Relationship(
        back_populates="stats",
        sa_relationship_kwargs={
            "primaryjoin": "CommentStats.comment_id==Comment.id"
        }
    )
