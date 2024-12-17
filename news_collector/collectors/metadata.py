import logging
import pytz
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .base import BaseCollector
from .api_metadata_collector import APIMetadataCollector
from .search_metadata_collector import SearchMetadataCollector
from .utils.date import DateUtils
from ..producer import Producer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class MetadataCollector(BaseCollector):
    """통합 메타데이터 수집기 (오케스트레이터)"""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize collector with configuration."""
        super().__init__(config)
        
        # Initialize Producer
        self.producer = Producer()
        self.queue_name = 'metadata_queue'
        self._producer_initialized = False

    async def _ensure_producer_initialized(self) -> None:
        """Ensure Producer is initialized and connected"""
        if not self._producer_initialized:
            try:
                logger.info("[Metadata] Initializing Producer...")
                await self.producer.connect()
                self._producer_initialized = True
                logger.info("[Metadata] Producer successfully initialized and connected")
            except Exception as e:
                logger.error(f"[Metadata] Failed to initialize Producer: {e}")
                raise

    async def publish_message(self, message: Dict[str, Any]) -> None:
        """Publish message to RabbitMQ using Producer"""
        try:
            await self._ensure_producer_initialized()
            
            if 'metadata' not in message:
                message['metadata'] = {}
            
            metadata = message['metadata']
            if 'is_test' not in metadata:
                metadata['is_test'] = True
            if 'is_api_collection' not in metadata:
                metadata['is_api_collection'] = False
            if 'total_collected' not in metadata:
                metadata['total_collected'] = len(message.get('articles', []))
            
            logger.info(f"[Metadata] Publishing message to queue '{self.queue_name}'...")
            await self.producer.publish(
                message=message,
                queue_name=self.queue_name
            )
            logger.info(f"[Metadata] Successfully published message to queue '{self.queue_name}'")
        except Exception as e:
            logger.error(f"[Metadata] Failed to publish message: {e}", exc_info=True)
            try:
                await self.producer.connect()
                await self.producer.publish(
                    message=message,
                    queue_name=self.queue_name
                )
                logger.info(f"[Metadata] Successfully published message after reconnection")
            except Exception as retry_error:
                logger.error(f"[Metadata] Failed to publish message after reconnection: {retry_error}", exc_info=True)
                raise

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect metadata using specified method."""
        logger.info("[Metadata] Starting collection process...")
        method = kwargs.get('method', 'API').upper()
        is_test = kwargs.get('is_test', True)
        self.log_collection_start(kwargs)

        try:
            logger.info(f"[Metadata] Using collection method: {method}")
            
            # Choose collector based on method
            if method == 'API':
                collector = APIMetadataCollector(self.config)
                is_api = True
            elif method == 'SEARCH':
                collector = SearchMetadataCollector(self.config)
                is_api = False
            else:
                raise ValueError(f"Invalid collection method: {method}")

            # Collect articles using the appropriate collector
            async with collector:
                articles = await collector.collect(**kwargs)

            for article in articles:
                article['is_test'] = is_test
                article['is_api_collection'] = is_api

            result = {
                'articles': articles,
                'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
                'metadata': {
                    'method': method,
                    'total_collected': len(articles),
                    'keyword': kwargs.get('keyword'),
                    'is_test': is_test,
                    'is_api_collection': is_api
                }
            }

            if await self.validate_async(result):
                self.log_collection_end(True, {'article_count': len(articles)})
                await self.publish_message(result)
                return result
            else:
                raise ValueError("Validation failed for collected data")

        except Exception as e:
            logger.error(f"[Metadata] Collection failed: {str(e)}", exc_info=True)
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info("[Metadata] Starting cleanup...")
            if self._producer_initialized:
                await self.producer.close()
                self._producer_initialized = False
                logger.info("[Metadata] Closed Producer connection")
            logger.info("[Metadata] Cleanup completed")
        except Exception as e:
            logger.error(f"[Metadata] Error during cleanup: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()
