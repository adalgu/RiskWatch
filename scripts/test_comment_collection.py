"""
Test script for comment collection and storage.
This script demonstrates how to collect comments from a Naver news article and store them in the database.
"""

import asyncio
import logging
from datetime import datetime
import pytz

from scripts.collect_and_store_comments import collect_and_store_comments
from scripts.collect_and_store_metadata import collect_and_store_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


async def test_comment_collection_with_existing_article():
    """
    Test comment collection with an existing article.
    
    This test:
    1. Collects metadata for a keyword to ensure we have articles in the database
    2. Uses the first article URL to collect and store comments
    """
    # Step 1: Collect metadata for a keyword
    keyword = "인공지능"
    max_articles = 3
    
    logger.info(f"Collecting metadata for keyword: {keyword}")
    await collect_and_store_metadata(keyword, max_articles)
    
    # For demonstration purposes, we'll use a hardcoded URL
    # In a real scenario, you would query the database to get article URLs
    article_url = "https://n.news.naver.com/mnews/article/001/0014189012"
    
    # Step 2: Collect and store comments for the article
    logger.info(f"Collecting comments for article: {article_url}")
    result = await collect_and_store_comments(article_url)
    
    # Log the results
    if result['success']:
        logger.info(f"Successfully collected and stored {result['stored_comments']} comments")
        logger.info(f"Article ID: {result['article_id']}")
    else:
        logger.error(f"Failed to collect and store comments: {result['error']}")


async def test_comment_collection_with_new_article():
    """
    Test comment collection with a new article.
    
    This test:
    1. Collects metadata for a specific article URL to ensure it's in the database
    2. Collects and stores comments for the same article
    """
    # Step 1: Collect metadata for a specific article
    keyword = "테스트"
    max_articles = 1
    
    # For demonstration purposes, we'll use a hardcoded URL
    article_url = "https://n.news.naver.com/mnews/article/001/0014189012"
    
    # Step 2: Collect and store comments for the article
    logger.info(f"Collecting comments for article: {article_url}")
    result = await collect_and_store_comments(article_url)
    
    # Log the results
    if result['success']:
        logger.info(f"Successfully collected and stored {result['stored_comments']} comments")
        logger.info(f"Article ID: {result['article_id']}")
    else:
        logger.error(f"Failed to collect and store comments: {result['error']}")
        logger.info("This might be because the article is not in the database yet.")
        logger.info("Try running the metadata collection first with the article's URL.")


async def main():
    """Main function."""
    # Choose which test to run
    test_type = input("Choose test type (1: with existing article, 2: with new article): ")
    
    if test_type == "1":
        await test_comment_collection_with_existing_article()
    elif test_type == "2":
        await test_comment_collection_with_new_article()
    else:
        logger.error("Invalid test type. Please choose 1 or 2.")


if __name__ == "__main__":
    asyncio.run(main())
