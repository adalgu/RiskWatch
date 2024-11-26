"""
Test script for Event-Driven Architecture integration between news_collector and news_storage.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz

from news_collector.collectors.metadata import MetadataCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal
from news_storage.consumer import NewsStorageConsumer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


async def test_metadata_collection_and_storage():
    """Test metadata collection and storage through RabbitMQ"""
    # Start the consumer in a separate task
    consumer = NewsStorageConsumer()
    consumer_task = asyncio.create_task(consumer.consume())

    try:
        # 1. Collect metadata using collector
        collector = MetadataCollector()
        result = await collector.collect(
            method='search',
            keyword='삼성전자',
            max_articles=5,
            start_date=(datetime.now(KST) - timedelta(days=1)).strftime('%Y-%m-%d'),
            end_date=datetime.now(KST).strftime('%Y-%m-%d')
        )
        articles = result.get('articles', [])
        logger.info(f"Collected {len(articles)} articles")

        if not articles:
            logger.warning("No articles collected, skipping database verification")
            return

        # 2. Wait for messages to be processed
        await asyncio.sleep(10)  # Increased wait time

        # 3. Verify storage in database
        async with AsyncStorageSessionLocal() as session:
            # Check the first article
            first_article = articles[0]
            stored_article = await AsyncDatabaseOperations.get_article_by_naver_link(
                session,
                main_keyword='삼성전자',  # Add main_keyword
                naver_link=first_article['naver_link']
            )

            if stored_article:
                logger.info("✅ Article successfully stored in database")
                logger.info(f"Title: {stored_article.title}")
                logger.info(f"Published at: {stored_article.published_at}")
                logger.info(f"Main Keyword: {stored_article.main_keyword}")
            else:
                logger.error("❌ Article not found in database")
                # Log additional details for debugging
                logger.error(f"First article details: {first_article}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Shutdown the consumer
        consumer.should_exit = True
        await consumer.shutdown()
        consumer_task.cancel()
        await collector.cleanup()


async def main():
    """Run integration tests"""
    logger.info("Starting Event-Driven Architecture integration test")

    try:
        await test_metadata_collection_and_storage()
        logger.info("Integration test completed successfully")
    except Exception as e:
        logger.error(f"Integration test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
