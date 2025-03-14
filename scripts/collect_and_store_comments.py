"""
Script to collect comments and store them in the database using the new database components.
"""

import asyncio
import logging
import argparse
from datetime import datetime
import pytz
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from news_collector.collectors.comments import CommentCollector
from news_storage.src.deps import get_db
from news_storage.src.crud.article import article
from news_storage.src.crud.comment import comment
from news_storage.src.schemas.comment import CommentCreate
from news_storage.src.models import Article

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


async def get_article_by_url(db: AsyncSession, url: str) -> Optional[Article]:
    """
    Get article by URL.
    
    Args:
        db: Database session
        url: Article URL
        
    Returns:
        Article if found, None otherwise
    """
    # Clean URL by removing query parameters
    clean_url = url.split('?')[0].rstrip('/')
    
    # Query for article with matching URL
    statement = select(Article).where(Article.naver_link == clean_url)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def store_comments_in_db(db: AsyncSession, article_id: int, comments_data: List[Dict[str, Any]]) -> int:
    """
    Store comments in the database.
    
    Args:
        db: Database session
        article_id: ID of the article
        comments_data: List of comment data
        
    Returns:
        Number of comments stored
    """
    logger.info(f"Storing {len(comments_data)} comments for article ID {article_id}")
    
    # Prepare comment create objects
    comments_to_create = []
    for item in comments_data:
        try:
            # Convert timestamp string to datetime if it exists
            timestamp = None
            if item.get('timestamp'):
                try:
                    timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse timestamp: {item.get('timestamp')}")
            
            # Create comment data
            comment_data = {
                'article_id': article_id,
                'comment_no': item.get('comment_no'),
                'parent_comment_no': item.get('parent_comment_no'),
                'content': item.get('content'),
                'username': item.get('username'),
                'profile_url': item.get('profile_url'),
                'timestamp': timestamp,
                'likes': item.get('likes', 0),
                'dislikes': item.get('dislikes', 0),
                'reply_count': item.get('reply_count', 0),
                'is_reply': item.get('is_reply', False),
                'is_deleted': item.get('is_deleted', False),
                'delete_type': item.get('delete_type'),
                'collected_at': datetime.now(KST)
            }
            
            # Create comment schema
            comment_in = CommentCreate(**comment_data)
            comments_to_create.append(comment_in)
            
        except Exception as e:
            logger.error(f"Error preparing comment data: {e}")
            logger.error(f"Comment data: {item}")
            continue
    
    # Batch create comments
    if comments_to_create:
        try:
            created_comments = await comment.batch_create(db, comments_data=comments_to_create)
            logger.info(f"Successfully stored {len(created_comments)} comments in database")
            return len(created_comments)
        except Exception as e:
            logger.error(f"Error batch creating comments: {e}")
            return 0
    else:
        logger.warning("No valid comments to store")
        return 0


async def collect_and_store_comments(article_url: str, include_stats: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """
    Collect comments from an article and store them in the database.
    
    Args:
        article_url: URL of the article
        include_stats: Whether to collect statistics
        max_retries: Maximum number of retries for collection
        
    Returns:
        Dictionary with collection results
    """
    logger.info(f"Starting comment collection for article: {article_url}")
    
    # Initialize collector
    collector = CommentCollector()
    
    result = {
        'success': False,
        'article_url': article_url,
        'article_id': None,
        'total_comments': 0,
        'stored_comments': 0,
        'error': None
    }
    
    try:
        # Collect comments with retries
        retry_count = 0
        collection_result = None
        
        while retry_count < max_retries:
            try:
                logger.info(f"Collecting comments (attempt {retry_count + 1}/{max_retries})...")
                collection_result = await collector.collect(
                    article_url=article_url,
                    include_stats=include_stats
                )
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Collection attempt failed: {e}. Retrying...")
                await asyncio.sleep(2)
        
        if not collection_result:
            raise Exception("Failed to collect comments after multiple attempts")
        
        logger.info(f"Collected {len(collection_result['comments'])} comments")
        result['total_comments'] = len(collection_result['comments'])
        
        # Get article from database
        article_found = False
        async for db in get_db():
            db_article = await get_article_by_url(db, article_url)
            if db_article:
                article_found = True
                result['article_id'] = db_article.id
                
                # Store comments in database
                stored_count = await store_comments_in_db(
                    db, 
                    db_article.id, 
                    collection_result['comments']
                )
                result['stored_comments'] = stored_count
                break
        
        if not article_found:
            result['error'] = f"Article not found in database: {article_url}"
            logger.error(result['error'])
        else:
            result['success'] = True
            logger.info(f"Comment collection and storage completed successfully")
        
    except Exception as e:
        error_msg = f"Error collecting or storing comments: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
    finally:
        # Cleanup collector resources
        await collector.cleanup()
    
    return result


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='네이버 뉴스 댓글 수집 및 저장')
    parser.add_argument('--article_url', required=True, help='댓글을 수집할 기사 URL')
    parser.add_argument('--no-stats', action='store_true', help='통계 정보 수집 제외')
    parser.add_argument('--retries', type=int, default=3, help='수집 재시도 횟수')
    args = parser.parse_args()
    
    result = await collect_and_store_comments(
        article_url=args.article_url,
        include_stats=not args.no_stats,
        max_retries=args.retries
    )
    
    if result['success']:
        logger.info(f"Successfully collected and stored {result['stored_comments']} comments")
        logger.info(f"Article ID: {result['article_id']}")
    else:
        logger.error(f"Failed to collect and store comments: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
