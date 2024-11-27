"""
Initialize database and run tests
"""
import asyncio
import logging
from news_storage.config import init_storage
from scripts.test_article_comments import main as run_tests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Initialize database and run tests"""
    try:
        logger.info("Initializing database...")
        await init_storage()
        logger.info("Database initialized successfully")
        
        logger.info("Running tests...")
        await run_tests()
    except Exception as e:
        logger.error(f"Error during initialization or testing: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
