import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import pytz
from ..models.collector_models import (
    CollectionStatus,
    CollectionStatusResponse,
    CollectionResult,
    MetadataCollectionRequest
)
from news_collector.producer import Producer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class CollectorService:
    """수집 서비스"""

    def __init__(self):
        """Initialize service."""
        self.producer = Producer()
        self._producer_initialized = False
        self._initialized = False
        self.requests_queue = 'collector_requests_queue'
        self.results_queue = 'collector_results_queue'
        self.status_store: Dict[str, CollectionStatusResponse] = {}

    async def init(self) -> None:
        """Initialize the service and ensure connections are established."""
        if not self._initialized:
            try:
                logger.info("[CollectorService] Initializing service...")
                await self._ensure_producer_initialized()
                self._initialized = True
                logger.info("[CollectorService] Service initialized successfully")
            except Exception as e:
                logger.error(f"[CollectorService] Failed to initialize service: {e}")
                raise

    async def _ensure_producer_initialized(self) -> None:
        """Ensure Producer is initialized and connected"""
        if not self._producer_initialized:
            try:
                logger.info("[CollectorService] Initializing Producer...")
                await self.producer.connect()
                self._producer_initialized = True
                logger.info("[CollectorService] Producer successfully initialized and connected")
            except Exception as e:
                logger.error(f"[CollectorService] Failed to initialize Producer: {e}")
                raise

    async def collect_metadata(self, **kwargs) -> CollectionStatusResponse:
        """
        메타데이터 수집 요청을 큐에 발행
        """
        try:
            await self._ensure_producer_initialized()
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Create collection request message
            message = {
                'request_id': request_id,
                'type': 'metadata',
                'params': {
                    'keyword': kwargs.get('keyword'),
                    'method': kwargs.get('method', 'API'),
                    'max_articles': kwargs.get('max_articles', 100),
                    'start_date': kwargs.get('start_date'),
                    'end_date': kwargs.get('end_date'),
                    'is_test': kwargs.get('is_test', False)
                },
                'queued_at': datetime.now(KST).isoformat()
            }
            
            # Initialize status
            status = CollectionStatusResponse(
                request_id=request_id,
                status=CollectionStatus.PENDING,
                started_at=datetime.now(KST),
                metadata={
                    'type': 'metadata',
                    'keyword': kwargs.get('keyword'),
                    'method': kwargs.get('method', 'API')
                }
            )
            self.status_store[request_id] = status
            
            # Publish message to requests queue
            logger.info(f"[CollectorService] Publishing metadata collection request: {request_id}")
            await self.producer.publish(message, queue_name=self.requests_queue)
            
            return status
            
        except Exception as e:
            logger.error(f"[CollectorService] Failed to start metadata collection: {e}")
            raise

    async def collect_comments(self, **kwargs) -> CollectionStatusResponse:
        """
        댓글 수집 요청을 큐에 발행
        """
        try:
            await self._ensure_producer_initialized()
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Create collection request message
            message = {
                'request_id': request_id,
                'type': 'comments',
                'params': {
                    'article_urls': kwargs.get('article_urls', []),
                    'min_delay': kwargs.get('min_delay', 0.1),
                    'max_delay': kwargs.get('max_delay', 0.5),
                    'batch_size': kwargs.get('batch_size', 10),
                    'is_test': kwargs.get('is_test', False)
                },
                'queued_at': datetime.now(KST).isoformat()
            }
            
            # Initialize status
            status = CollectionStatusResponse(
                request_id=request_id,
                status=CollectionStatus.PENDING,
                started_at=datetime.now(KST),
                metadata={
                    'type': 'comments',
                    'article_count': len(kwargs.get('article_urls', []))
                }
            )
            self.status_store[request_id] = status
            
            # Publish message to requests queue
            logger.info(f"[CollectorService] Publishing comment collection request: {request_id}")
            await self.producer.publish(message, queue_name=self.requests_queue)
            
            return status
            
        except Exception as e:
            logger.error(f"[CollectorService] Failed to start comment collection: {e}")
            raise

    async def update_status(self, request_id: str, status: CollectionStatus, 
                          total_collected: Optional[int] = None,
                          error_message: Optional[str] = None) -> None:
        """
        수집 상태 업데이트
        """
        if request_id in self.status_store:
            current_status = self.status_store[request_id]
            current_status.status = status
            if total_collected is not None:
                current_status.total_collected = total_collected
            if error_message is not None:
                current_status.error_message = error_message
            if status in [CollectionStatus.COMPLETED, CollectionStatus.FAILED]:
                current_status.completed_at = datetime.now(KST)

    async def get_status(self, request_id: str) -> Optional[CollectionStatusResponse]:
        """
        수집 상태 조회
        """
        return self.status_store.get(request_id)

    async def cleanup_old_status(self, max_age_hours: int = 24) -> None:
        """
        오래된 상태 정보 정리
        """
        current_time = datetime.now(KST)
        to_remove = []
        
        for request_id, status in self.status_store.items():
            if status.started_at:
                age = current_time - status.started_at
                if age.total_seconds() > max_age_hours * 3600:
                    to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.status_store[request_id]

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            if self._producer_initialized:
                await self.producer.close()
                self._producer_initialized = False
                self._initialized = False
            logger.info("[CollectorService] Cleanup completed")
        except Exception as e:
            logger.error(f"[CollectorService] Error during cleanup: {e}")

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()
