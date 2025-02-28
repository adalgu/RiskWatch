"""
Pydantic schemas for Article model.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Shared properties
class ArticleBase(BaseModel):
    """Base schema for Article with shared properties."""
    main_keyword: str = Field(default="default_keyword")
    naver_link: str
    title: str
    original_link: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_domain: Optional[str] = None
    published_at: Optional[datetime] = None
    published_date: Optional[str] = None
    is_naver_news: Optional[bool] = False
    is_test: bool = False
    is_api_collection: bool = False


# Properties to receive on article creation
class ArticleCreate(ArticleBase):
    """Schema for creating a new Article."""
    collected_at: datetime = Field(default_factory=datetime.now)


# Properties to receive on article update
class ArticleUpdate(BaseModel):
    """Schema for updating an Article."""
    main_keyword: Optional[str] = None
    naver_link: Optional[str] = None
    title: Optional[str] = None
    original_link: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_domain: Optional[str] = None
    published_at: Optional[datetime] = None
    published_date: Optional[str] = None
    is_naver_news: Optional[bool] = None
    is_test: Optional[bool] = None
    is_api_collection: Optional[bool] = None
    collected_at: Optional[datetime] = None


# Properties to return via API
class ArticleInDBBase(ArticleBase):
    """Base schema for Article from database."""
    id: int
    collected_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True  # Allows the model to read data from ORM objects


# Additional properties to return via API
class Article(ArticleInDBBase):
    """Schema for returning an Article."""
    pass


# Schema for returning multiple articles
class ArticlesResponse(BaseModel):
    """Schema for returning multiple Articles."""
    data: list[Article]
    count: int
