"""
CRUD operations for Comment model.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from news_storage.src.crud.base import CRUDBase
from news_storage.src.models import Comment
from news_storage.src.schemas.comment import CommentCreate, CommentUpdate


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):
    """
    CRUD operations for Comment model.
    """
    
    async def get_by_comment_no(
        self, db: AsyncSession, *, article_id: int, comment_no: str
    ) -> Optional[Comment]:
        """
        Get a comment by article_id and comment_no.
        
        Args:
            db: Database session
            article_id: ID of the article
            comment_no: Comment number
            
        Returns:
            The comment if found, None otherwise
        """
        statement = select(Comment).where(
            (Comment.article_id == article_id) & 
            (Comment.comment_no == comment_no)
        )
        results = await db.execute(statement)
        return results.scalar_one_or_none()
    
    async def get_by_article_id(
        self, db: AsyncSession, *, article_id: int, skip: int = 0, limit: int = 100
    ) -> List[Comment]:
        """
        Get comments by article_id.
        
        Args:
            db: Database session
            article_id: ID of the article
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of comments
        """
        statement = select(Comment).where(
            Comment.article_id == article_id
        ).offset(skip).limit(limit)
        results = await db.execute(statement)
        return results.scalars().all()
    
    async def batch_create(
        self, db: AsyncSession, *, comments_data: List[CommentCreate]
    ) -> List[Comment]:
        """
        Batch create comments.
        
        Args:
            db: Database session
            comments_data: List of comment create schemas
            
        Returns:
            List of created comments
        """
        comments = []
        for comment_data in comments_data:
            comment = Comment(**comment_data.model_dump())
            db.add(comment)
            comments.append(comment)
        
        await db.commit()
        
        # Refresh all comments to get their IDs
        for comment in comments:
            await db.refresh(comment)
        
        return comments
    
    async def count_by_article_id(self, db: AsyncSession, *, article_id: int) -> int:
        """
        Count comments by article_id.
        
        Args:
            db: Database session
            article_id: ID of the article
            
        Returns:
            Number of comments
        """
        from sqlalchemy import func
        statement = select(func.count()).select_from(Comment).where(
            Comment.article_id == article_id
        )
        result = await db.execute(statement)
        return result.scalar_one()


# Create a singleton instance
comment = CRUDComment(Comment)
