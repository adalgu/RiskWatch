"""
Pydantic schemas for Comment model.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Shared properties
class CommentBase(BaseModel):
    """Base schema for Comment with shared properties."""
    article_id: int
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    likes: int = 0
    dislikes: int = 0
    reply_count: int = 0
    is_reply: bool = False
    is_deleted: bool = False
    delete_type: Optional[str] = None


# Properties to receive on comment creation
class CommentCreate(CommentBase):
    """Schema for creating a new Comment."""
    collected_at: datetime = Field(default_factory=datetime.now)


# Properties to receive on comment update
class CommentUpdate(BaseModel):
    """Schema for updating a Comment."""
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    reply_count: Optional[int] = None
    is_reply: Optional[bool] = None
    is_deleted: Optional[bool] = None
    delete_type: Optional[str] = None
    collected_at: Optional[datetime] = None


# Properties to return via API
class CommentInDBBase(CommentBase):
    """Base schema for Comment from database."""
    id: int
    collected_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True  # Allows the model to read data from ORM objects


# Additional properties to return via API
class Comment(CommentInDBBase):
    """Schema for returning a Comment."""
    pass


# Schema for returning multiple comments
class CommentsResponse(BaseModel):
    """Schema for returning multiple Comments."""
    data: List[Comment]
    count: int
