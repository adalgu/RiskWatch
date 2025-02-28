"""
Dependency injection utilities for FastAPI.
Based on the Full Stack FastAPI Template pattern.
"""

from typing import Annotated, Generator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from news_storage.src.database import get_db

# Type annotation for database session dependency
SessionDep = Annotated[AsyncSession, Depends(get_db)]

# Example of how to create additional dependencies
# that build on the database session

# async def get_article_by_id(
#     session: SessionDep,
#     article_id: int,
# ) -> Article:
#     """
#     Get an article by ID or raise 404.
#     Usage:
#         @app.get("/articles/{article_id}")
#         async def read_article(article: Article = Depends(get_article_by_id)):
#             return article
#     """
#     from news_storage.src.models import Article
#     article = await session.get(Article, article_id)
#     if not article:
#         from fastapi import HTTPException
#         raise HTTPException(status_code=404, detail="Article not found")
#     return article
