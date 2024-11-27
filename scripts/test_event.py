"""
Test script for Event-Driven Architecture integration between news_collector and news_storage.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional

from news_collector.collectors.metadata import MetadataCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal
from news_storage.consumer import NewsStorageConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


class EventDrivenTester:
    """Class to handle event-driven architecture testing"""
    
    def __init__(self):
        self.consumer = NewsStorageConsumer()
        self.collector = MetadataCollector()
        self.consumer_task = None

    async def setup(self):
        """Setup the test environment"""
        try:
            self.consumer_task = asyncio.create_task(self.consumer.consume())
            logger.info("Consumer setup completed")
        except Exception as e:
            logger.error(f"Failed to setup consumer: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.consumer:
                self.consumer.should_exit = True
                await self.consumer.shutdown()
            if self.consumer_task:
                self.consumer_task.cancel()
            await self.collector.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

    async def collect_metadata(self, keyword: str, max_articles: int, 
                             start_date: str, end_date: str) -> Dict[str, Any]:
        """Collect metadata using collector"""
        try:
            result = await self.collector.collect(
                # method='SEARCH',
                method='API',
                keyword=keyword,
                max_articles=max_articles,
                start_date=start_date,
                end_date=end_date,
                is_test=True
            )
            articles = result.get('articles', [])
            logger.info(f"Successfully collected {len(articles)} articles")
            return result
        except Exception as e:
            logger.error(f"Failed to collect metadata: {e}")
            raise

    async def verify_storage(self, main_keyword: str, 
                           article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify article storage in database"""
        try:
            async with AsyncStorageSessionLocal() as session:
                stored_article = await AsyncDatabaseOperations.get_article_by_naver_link(
                    session,
                    main_keyword=main_keyword,
                    naver_link=article_data['naver_link']
                )

                if stored_article:
                    logger.info("✅ Article successfully stored in database")
                    return {
                        'title': stored_article.title,
                        'published_at': stored_article.published_at,
                        'main_keyword': stored_article.main_keyword,
                        'is_test': stored_article.is_test
                    }
                else:
                    logger.error("❌ Article not found in database")
                    logger.error(f"Article details: {article_data}")
                    return None
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            raise

    async def run_test(self) -> Dict[str, Any]:
        """Run the complete test process"""
        test_results = {
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            # Setup
            await self.setup()

            # Test parameters
            keyword = '윤석열'
            max_articles = 5
            start_date = (datetime.now(KST) - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = datetime.now(KST).strftime('%Y-%m-%d')

            # Collect metadata
            result = await self.collect_metadata(keyword, max_articles, start_date, end_date)
            articles = result.get('articles', [])

            if not articles:
                test_results.update({
                    'success': False,
                    'message': 'No articles collected'
                })
                return test_results

            # Wait for message processing
            logger.info("Waiting for messages to be processed...")
            await asyncio.sleep(10)

            # Verify storage
            verification_result = await self.verify_storage(keyword, articles[0])
            
            if verification_result:
                test_results.update({
                    'success': True,
                    'message': '✅ Test completed successfully',
                    'details': verification_result
                })
            else:
                test_results.update({
                    'success': False,
                    'message': 'Article storage verification failed'
                })

        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            test_results.update({
                'success': False,
                'message': f'Test failed: {str(e)}'
            })
        finally:
            await self.cleanup()

        return test_results


async def main():
    """Run integration tests"""
    logger.info("Starting Event-Driven Architecture integration test")
    
    tester = EventDrivenTester()
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
"""
Test script for Event-Driven Architecture integration between news_collector and news_storage.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional

from news_collector.collectors.metadata import MetadataCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal
from news_storage.consumer import NewsStorageConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


class EventDrivenTester:
    """Class to handle event-driven architecture testing"""
    
    def __init__(self):
        self.consumer = NewsStorageConsumer()
        self.collector = MetadataCollector()
        self.consumer_task = None

    async def setup(self):
        """Setup the test environment"""
        try:
            self.consumer_task = asyncio.create_task(self.consumer.consume())
            logger.info("Consumer setup completed")
        except Exception as e:
            logger.error(f"Failed to setup consumer: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.consumer:
                self.consumer.should_exit = True
                await self.consumer.shutdown()
            if self.consumer_task:
                self.consumer_task.cancel()
            await self.collector.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

    async def collect_metadata(self, keyword: str, max_articles: int, 
                             start_date: str, end_date: str) -> Dict[str, Any]:
        """Collect metadata using collector"""
        try:
            result = await self.collector.collect(
                # method='SEARCH',
                method='API',
                keyword=keyword,
                max_articles=max_articles,
                start_date=start_date,
                end_date=end_date,
                is_test=True
            )
            articles = result.get('articles', [])
            logger.info(f"Successfully collected {len(articles)} articles")
            return result
        except Exception as e:
            logger.error(f"Failed to collect metadata: {e}")
            raise

    async def verify_storage(self, main_keyword: str, 
                           article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify article storage in database"""
        try:
            async with AsyncStorageSessionLocal() as session:
                stored_article = await AsyncDatabaseOperations.get_article_by_naver_link(
                    session,
                    main_keyword=main_keyword,
                    naver_link=article_data['naver_link']
                )

                if stored_article:
                    logger.info("✅ Article successfully stored in database")
                    return {
                        'title': stored_article.title,
                        'published_at': stored_article.published_at,
                        'main_keyword': stored_article.main_keyword,
                        'is_test': stored_article.is_test
                    }
                else:
                    logger.error("❌ Article not found in database")
                    logger.error(f"Article details: {article_data}")
                    return None
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            raise

    async def run_test(self) -> Dict[str, Any]:
        """Run the complete test process"""
        test_results = {
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            # Setup
            await self.setup()

            # Test parameters
            keyword = '윤석열'
            max_articles = 5
            start_date = (datetime.now(KST) - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = datetime.now(KST).strftime('%Y-%m-%d')

            # Collect metadata
            result = await self.collect_metadata(keyword, max_articles, start_date, end_date)
            articles = result.get('articles', [])

            if not articles:
                test_results.update({
                    'success': False,
                    'message': 'No articles collected'
                })
                return test_results

            # Wait for message processing
            logger.info("Waiting for messages to be processed...")
            await asyncio.sleep(10)

            # Verify storage
            verification_result = await self.verify_storage(keyword, articles[0])
            
            if verification_result:
                test_results.update({
                    'success': True,
                    'message': '✅ Test completed successfully',
                    'details': verification_result
                })
            else:
                test_results.update({
                    'success': False,
                    'message': 'Article storage verification failed'
                })

        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            test_results.update({
                'success': False,
                'message': f'Test failed: {str(e)}'
            })
        finally:
            await self.cleanup()

        return test_results


async def main():
    """Run integration tests"""
    logger.info("Starting Event-Driven Architecture integration test")
    
    tester = EventDrivenTester()
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
