from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ArticleBase(SQLModel):
    title: str
    naver_link: str = Field(unique=True)
    original_link: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    is_naver_news: bool
    collection_method: str


class Article(ArticleBase, table=True):
    __tablename__ = "articles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    comments: List["Comment"] = Relationship(back_populates="article")


class CommentBase(SQLModel):
    comment_no: str
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: str
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)
    reply_count: int = Field(default=0)
    is_reply: bool
    is_deleted: bool
    delete_type: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class Comment(CommentBase, table=True):
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    article: Article = Relationship(back_populates="comments")

    class Config:
        arbitrary_types_allowed = True


# Create models for creating items
class ArticleCreate(ArticleBase):
    pass


class CommentCreate(CommentBase):
    pass


# Create models for reading items
class ArticleRead(ArticleBase):
    id: int
    comments: List[CommentBase] = []


class CommentStatsBase(SQLModel):
    current_count: int = Field(default=0)
    user_deleted_count: int = Field(default=0)
    admin_deleted_count: int = Field(default=0)
    male_ratio: float = Field(default=0.0)
    female_ratio: float = Field(default=0.0)
    age_10s: float = Field(default=0.0)
    age_20s: float = Field(default=0.0)
    age_30s: float = Field(default=0.0)
    age_40s: float = Field(default=0.0)
    age_50s: float = Field(default=0.0)
    age_60s_above: float = Field(default=0.0)
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class CommentStats(CommentStatsBase, table=True):
    __tablename__ = "comment_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", unique=True)
    article: Article = Relationship()


class CommentRead(CommentBase):
    id: int
    article_id: int


# Create models for creating items
class CommentStatsCreate(CommentStatsBase):
    pass


# Create models for reading items
class CommentStatsRead(CommentStatsBase):
    id: int
    article_id: int
