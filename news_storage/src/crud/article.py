"""
CRUD operations for Article model.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col

from news_storage.src.crud.base import CRUDBase
from news_storage.src.models import Article
from news_storage.src.schemas.article import ArticleCreate, ArticleUpdate


class CRUDArticle(CRUDBase[Article, ArticleCreate, ArticleUpdate]):
    """
    CRUD operations for Article model.
    """
    
    async def get_by_naver_link(
        self, db: AsyncSession, *, main_keyword: str, naver_link: str
    ) -> Optional[Article]:
        """
        Get an article by main_keyword and naver_link.
        
        Args:
            db: Database session
            main_keyword: Main keyword of the article
            naver_link: Naver link of the article
            
        Returns:
            The article if found, None otherwise
        """
        statement = select(Article).where(
            (Article.main_keyword == main_keyword) & 
            (Article.naver_link == naver_link)
        )
        results = await db.execute(statement)
        return results.scalar_one_or_none()
    
    async def create_with_upsert(
        self, db: AsyncSession, *, obj_in: ArticleCreate
    ) -> Article:
        """
        Create an article with upsert logic (update if exists).
        
        Args:
            db: Database session
            obj_in: Article create schema
            
        Returns:
            The created or updated article
        """
        obj_in_data = obj_in.dict()
        
        # Use PostgreSQL's ON CONFLICT clause to handle duplicates
        stmt = insert(Article).values(**obj_in_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['main_keyword', 'naver_link'],
            set_={
                'title': stmt.excluded.title,
                'original_link': stmt.excluded.original_link,
                'description': stmt.excluded.description,
                'publisher': stmt.excluded.publisher,
                'publisher_domain': stmt.excluded.publisher_domain,
                'published_at': stmt.excluded.published_at,
                'published_date': stmt.excluded.published_date,
                'collected_at': stmt.excluded.collected_at,
                'is_naver_news': stmt.excluded.is_naver_news,
                'is_test': stmt.excluded.is_test,
                'is_api_collection': stmt.excluded.is_api_collection
            }
        )
        
        # Execute the statement
        await db.execute(stmt)
        await db.commit()
        
        # Get the article
        return await self.get_by_naver_link(
            db, main_keyword=obj_in_data['main_keyword'], 
            naver_link=obj_in_data['naver_link']
        )
    
    async def get_by_keyword(
        self, db: AsyncSession, *, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """
        Get articles by keyword.
        
        Args:
            db: Database session
            keyword: Keyword to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of articles
        """
        statement = select(Article).where(
            Article.main_keyword == keyword
        ).offset(skip).limit(limit)
        results = await db.execute(statement)
        return results.scalars().all()


# Create a singleton instance
article = CRUDArticle(Article)
