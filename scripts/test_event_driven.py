"""
Test script for Event-Driven Architecture integration between news_collector and news_storage.
"""

import os
import asyncio
import logging
from datetime import datetime
import pytz

from news_collector.collectors.metadata import MetadataCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


async def test_metadata_collection_and_storage():
    """Test metadata collection and storage through RabbitMQ"""
    try:
        # 1. Collect metadata using collector
        collector = MetadataCollector()
        result = await collector.collect(
            method='api',
            keyword='삼성전자',
            max_articles=5
        )
        logger.info(f"Collected {len(result['articles'])} articles")

        # 2. Wait for consumer to process messages
        await asyncio.sleep(5)

        # 3. Verify storage in database
        async with AsyncStorageSessionLocal() as session:
            # Check the first article
            first_article = result['articles'][0]
            stored_article = await AsyncDatabaseOperations.get_article_by_naver_link(
                session,
                first_article['naver_link']
            )

            if stored_article:
                logger.info("✅ Article successfully stored in database")
                logger.info(f"Title: {stored_article.title}")
                logger.info(f"Published at: {stored_article.published_at}")
            else:
                logger.error("❌ Article not found in database")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
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
