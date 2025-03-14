"""
Script to collect metadata for a specific article URL and then collect comments for it.
This is useful when you want to collect comments for an article that is not yet in the database.
"""

import asyncio
import logging
import argparse
from datetime import datetime
import pytz
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from news_collector.collectors.search_metadata_collector import SearchMetadataCollector
from news_storage.src.deps import get_db
from news_storage.src.crud.article import article
from news_storage.src.schemas.article import ArticleCreate
from news_storage.src.models import Article
from scripts.collect_and_store_comments import collect_and_store_comments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


async def collect_and_store_article_metadata(article_url: str) -> Optional[int]:
    """
    Collect metadata for a specific article URL and store it in the database.
    
    Args:
        article_url: URL of the article
        
    Returns:
        Article ID if successful, None otherwise
    """
    logger.info(f"Collecting metadata for article: {article_url}")
    
    # Extract domain and article ID from URL for keyword
    parts = article_url.split('/')
    if len(parts) >= 6:
        publisher_code = parts[-2]
        article_code = parts[-1].split('?')[0]
        keyword = f"{publisher_code}_{article_code}"
    else:
        keyword = "article_metadata"
    
    # Initialize collector
    collector = SearchMetadataCollector()
    
    try:
        # Create a simple metadata entry for this article
        article_data = {
            'main_keyword': keyword,
            'naver_link': article_url.split('?')[0].rstrip('/'),
            'title': f"Article from {article_url}",
            'description': f"Automatically collected for comment collection",
            'publisher': "Naver News",
            'published_at': None,
            'published_date': datetime.now(KST).strftime('%Y-%m-%d'),
            'collected_at': datetime.now(KST),
            'is_naver_news': True,
            'is_test': False,
            'is_api_collection': False
        }
        
        # Store in database
        article_id = None
        async for db in get_db():
            # Create article schema
            article_in = ArticleCreate(**article_data)
            
            # Store in database using upsert
            db_article = await article.create_with_upsert(db, obj_in=article_in)
            
            if db_article:
                article_id = db_article.id
                logger.info(f"Successfully stored article in database with ID: {article_id}")
            else:
                logger.error("Failed to store article in database")
            
            break
        
        return article_id
        
    except Exception as e:
        logger.error(f"Error collecting or storing article metadata: {e}")
        return None
    finally:
        # Cleanup collector resources
        await collector.cleanup()


async def collect_article_with_comments(article_url: str, include_stats: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """
    Collect metadata for a specific article URL and then collect comments for it.
    
    Args:
        article_url: URL of the article
        include_stats: Whether to collect comment statistics
        max_retries: Maximum number of retries for collection
        
    Returns:
        Dictionary with collection results
    """
    result = {
        'success': False,
        'article_url': article_url,
        'article_id': None,
        'metadata_collected': False,
        'comments_collected': False,
        'total_comments': 0,
        'stored_comments': 0,
        'error': None
    }
    
    try:
        # Step 1: Collect and store article metadata
        article_id = await collect_and_store_article_metadata(article_url)
        
        if not article_id:
            result['error'] = "Failed to collect and store article metadata"
            return result
        
        result['article_id'] = article_id
        result['metadata_collected'] = True
        
        # Step 2: Collect and store comments
        comments_result = await collect_and_store_comments(
            article_url=article_url,
            include_stats=include_stats,
            max_retries=max_retries
        )
        
        result['comments_collected'] = comments_result['success']
        result['total_comments'] = comments_result['total_comments']
        result['stored_comments'] = comments_result['stored_comments']
        
        if not comments_result['success']:
            result['error'] = comments_result['error']
            return result
        
        result['success'] = True
        
    except Exception as e:
        error_msg = f"Error in collect_article_with_comments: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
    
    return result


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='네이버 뉴스 기사 및 댓글 수집')
    parser.add_argument('--article_url', required=True, help='수집할 기사 URL')
    parser.add_argument('--no-stats', action='store_true', help='통계 정보 수집 제외')
    parser.add_argument('--retries', type=int, default=3, help='수집 재시도 횟수')
    args = parser.parse_args()
    
    result = await collect_article_with_comments(
        article_url=args.article_url,
        include_stats=not args.no_stats,
        max_retries=args.retries
    )
    
    if result['success']:
        logger.info(f"Successfully collected article and {result['stored_comments']} comments")
        logger.info(f"Article ID: {result['article_id']}")
    else:
        logger.error(f"Failed to collect article and comments: {result['error']}")
        if result['metadata_collected']:
            logger.info(f"Article metadata was collected successfully with ID: {result['article_id']}")
        if result['comments_collected']:
            logger.info(f"Comments were collected successfully: {result['stored_comments']} comments")


if __name__ == "__main__":
    asyncio.run(main())
