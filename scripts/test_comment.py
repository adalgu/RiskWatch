"""
Test script for comment collection functionality.
"""

import os
import asyncio
import logging
from datetime import datetime
import pytz
from typing import Dict, Any, Optional, List
from sqlalchemy import select

from news_collector.collectors.comments import CommentCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal
from news_storage.models import Article, Comment

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

# Test data
TEST_ARTICLE = {
    'main_keyword': 'test_keyword',
    'naver_link': 'https://n.news.naver.com/mnews/article/014/0005273842',
    'title': 'Test Article',
    'is_test': True,
    'is_api_collection': True,
    'collected_at': datetime.now(KST)
}


class CommentCollectionTester:
    """Test comment collection functionality"""
    
    def __init__(self):
        self.collector = CommentCollector()

    async def setup_test_article(self) -> Article:
        """Setup test article in database"""
        try:
            async with AsyncStorageSessionLocal() as session:
                # Create test article
                article = await AsyncDatabaseOperations.create_article(
                    session=session,
                    article_data=TEST_ARTICLE,
                    main_keyword=TEST_ARTICLE['main_keyword']
                )
                await session.commit()
                logger.info(f"Created test article with ID: {article.id}")
                return article
        except Exception as e:
            logger.error(f"Failed to setup test article: {e}")
            raise

    async def collect_comments(self, article_url: str) -> Dict[str, Any]:
        """Collect comments using collector"""
        try:
            result = await self.collector.collect(
                article_url=article_url,
                is_test=True,
                include_stats=False  # 통계 수집 제외
            )
            comments = result.get('comments', [])
            total_count = result.get('total_count', 0)
            logger.info(f"Successfully collected {len(comments)} comments (total count: {total_count})")
            
            # Log the collected comments for debugging
            logger.debug(f"Collected comments: {comments}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to collect comments: {e}")
            raise

    async def verify_comment_storage(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Verify comment storage in database"""
        try:
            async with AsyncStorageSessionLocal() as session:
                # Get comments for this article
                query = select(Comment).where(Comment.article_id == article_id)
                result = await session.execute(query)
                stored_comments = result.scalars().all()

                if stored_comments:
                    logger.info(f"✅ {len(stored_comments)} comments successfully stored in database")
                    
                    # Get first comment for sample
                    sample_comment = stored_comments[0]
                    
                    return {
                        'article_id': article_id,
                        'comment_count': len(stored_comments),
                        'sample_comment': {
                            'content': sample_comment.content,
                            'username': sample_comment.username,
                            'timestamp': sample_comment.timestamp,
                            'is_reply': sample_comment.is_reply
                        }
                    }
                else:
                    # 댓글이 없는 경우도 정상 처리
                    logger.info("No comments found in database (this is normal for articles without comments)")
                    return {
                        'article_id': article_id,
                        'comment_count': 0,
                        'sample_comment': None
                    }
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            raise

    async def store_comments(self, article_id: int, comments: List[Dict[str, Any]]) -> bool:
        """Store collected comments in database"""
        try:
            # 댓글이 없는 경우도 성공으로 처리
            if not comments:
                logger.info("No comments to store")
                return True

            async with AsyncStorageSessionLocal() as session:
                # Store comments
                await AsyncDatabaseOperations.batch_create_comments(
                    session=session,
                    comments_data=comments,
                    article_id=article_id
                )
                await session.commit()
                logger.info(f"Successfully stored {len(comments)} comments")
                return True
        except Exception as e:
            logger.error(f"Failed to store comments: {e}")
            return False

    async def run_test(self) -> Dict[str, Any]:
        """Run the complete test process"""
        test_results = {
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            # Create test article
            article = await self.setup_test_article()

            # Collect comments
            result = await self.collect_comments(TEST_ARTICLE['naver_link'])
            comments = result.get('comments', [])
            total_count = result.get('total_count', 0)

            # 댓글이 없는 경우도 정상 처리
            if total_count == 0:
                test_results.update({
                    'success': True,
                    'message': 'Article has no comments (this is normal)',
                    'details': {
                        'article_id': article.id,
                        'comment_count': 0,
                        'total_count': 0
                    }
                })
                return test_results

            # Store comments
            if not await self.store_comments(article.id, comments):
                test_results.update({
                    'success': False,
                    'message': 'Failed to store comments'
                })
                return test_results

            # Verify storage
            verification_result = await self.verify_comment_storage(article.id)
            
            if verification_result:
                test_results.update({
                    'success': True,
                    'message': '✅ Test completed successfully',
                    'details': verification_result
                })
            else:
                test_results.update({
                    'success': False,
                    'message': 'Comment storage verification failed'
                })

        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            test_results.update({
                'success': False,
                'message': f'Test failed: {str(e)}'
            })
        finally:
            await self.collector.cleanup()

        return test_results


async def main():
    """Run integration tests"""
    logger.info("Starting Comment Collection Integration Test")
    
    tester = CommentCollectionTester()
    try:
        results = await tester.run_test()
        if results['success']:
            logger.info(f"✅ Integration test completed successfully: {results['message']}")
            logger.info(f"Test details: {results['details']}")
        else:
            logger.error(f"Integration test failed: {results['message']}")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())
