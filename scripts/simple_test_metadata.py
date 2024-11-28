"""
Simplified test script for metadata collection and storage
"""

import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any

from news_collector.collectors.metadata import MetadataCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


async def collect_and_store_metadata(keyword: str, max_articles: int = 5) -> Dict[str, Any]:
    """Collect metadata and store directly to database"""
    collector = MetadataCollector()
    
    try:
        # 수집 기간 설정
        end_date = datetime.now(KST)
        start_date = end_date - timedelta(days=1)
        
        # 메타데이터 수집
        result = await collector.collect(
            method='SEARCH',
            keyword=keyword,
            max_articles=max_articles,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            is_test=True
        )
        
        articles = result.get('articles', [])
        if not articles:
            return {'success': False, 'message': 'No articles found'}
            
        # DB에 저장
        async with AsyncStorageSessionLocal() as session:
            for article in articles:
                await AsyncDatabaseOperations.create_article(
                    session=session,
                    article_data=article,
                    main_keyword=keyword
                )
            await session.commit()
            
        return {
            'success': True,
            'message': f'Successfully collected and stored {len(articles)} articles',
            'article_count': len(articles)
        }
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return {'success': False, 'message': str(e)}
    finally:
        await collector.cleanup()


async def main():
    """Run simplified test"""
    logger.info("Starting simplified metadata collection test")
    
    result = await collect_and_store_metadata('윤석열')
    
    if result['success']:
        logger.info(f"✅ Test completed successfully: {result['message']}")
    else:
        logger.error(f"❌ Test failed: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
