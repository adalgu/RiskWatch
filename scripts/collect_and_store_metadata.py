"""
Script to collect metadata and store it in the database using the new database components.
"""

import asyncio
import logging
from datetime import datetime
import pytz

from sqlalchemy.ext.asyncio import AsyncSession

from news_collector.collectors.search_metadata_collector import SearchMetadataCollector
from news_storage.src.deps import get_db
from news_storage.src.crud.article import article
from news_storage.src.schemas.article import ArticleCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


async def collect_and_store_metadata(keyword: str, max_articles: int = 10):
    """
    Collect metadata using SearchMetadataCollector and store it in the database.
    
    Args:
        keyword: Search keyword
        max_articles: Maximum number of articles to collect
    """
    logger.info(f"Starting metadata collection for keyword: {keyword}")
    
    # Initialize collector
    collector = SearchMetadataCollector()
    
    try:
        # Collect metadata
        logger.info("Collecting metadata...")
        metadata_results = await collector.collect(
            keyword=keyword,
            max_articles=max_articles
        )
        
        logger.info(f"Collected {len(metadata_results)} articles")
        
        # Get database session
        async for db in get_db():
            # Store metadata in database
            await store_metadata_in_db(db, metadata_results, keyword)
            break
            
        logger.info("Metadata collection and storage completed successfully")
        
    except Exception as e:
        logger.error(f"Error collecting or storing metadata: {e}")
        raise
    finally:
        # Cleanup collector resources
        await collector.cleanup()


async def store_metadata_in_db(db: AsyncSession, metadata_results: list, keyword: str):
    """
    Store metadata in the database using the new CRUD operations.
    
    Args:
        db: Database session
        metadata_results: List of metadata results
        keyword: Search keyword
    """
    logger.info(f"Storing {len(metadata_results)} articles in database")
    
    stored_count = 0
    
    for item in metadata_results:
        try:
            # Convert metadata to ArticleCreate schema
            article_data = {
                'main_keyword': keyword,
                'naver_link': item.get('link', ''),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'publisher': item.get('press', ''),
                'published_at': None,  # Will be parsed from published_at string
                'published_date': item.get('published_at', ''),
                'collected_at': datetime.now(KST),
                'is_naver_news': True,
                'is_test': False,
                'is_api_collection': False
            }
            
            # Create article schema
            article_in = ArticleCreate(**article_data)
            
            # Store in database using upsert
            db_article = await article.create_with_upsert(db, obj_in=article_in)
            
            stored_count += 1
            
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            logger.error(f"Article data: {item}")
            continue
    
    logger.info(f"Successfully stored {stored_count} articles in database")


async def main():
    """Main function."""
    # Example usage
    keyword = "인공지능"
    max_articles = 20
    
    await collect_and_store_metadata(keyword, max_articles)


if __name__ == "__main__":
    asyncio.run(main())
