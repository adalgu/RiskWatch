"""
Collector service for managing collection tasks
"""

import os
import json
import asyncio
import logging
from datetime import datetime
import pytz
from typing import Dict, List, Optional

import aio_pika
import psutil
from aio_pika.abc import AbstractRobustConnection
from app.models.collector_models import (
    CollectionRequest,
    CollectionStatus,
    ResourceUsage
)
from news_collector.collectors.interactive_collector import RabbitMQCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CollectorService:
    _instance = None
    _initialized = False
    _collector: Optional[RabbitMQCollector] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CollectorService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 환경 변수에서 RabbitMQ 설정 가져오기
            self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
            self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))
            self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
            self.rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'guest')
            self.active_collections: Dict[str, CollectionStatus] = {}
            CollectorService._initialized = True

    async def init(self):
        """Asynchronously initialize RabbitMQCollector"""
        if not self._collector:
            self._collector = RabbitMQCollector()
            connected = await self._collector.connect_rabbitmq()
            if not connected:
                logger.error("Failed to initialize RabbitMQCollector")
                raise ConnectionError("Could not connect to RabbitMQ")

    async def start_collection(self, request: CollectionRequest, collection_type: str) -> str:
        """수집 작업 시작"""
        try:
            if not self._collector:
                await self.init()

            collection_id = f"{collection_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 수집 작업 수행
            if collection_type == 'metadata':
                result = await self._collector.collect_metadata(
                    keyword=request.keyword,
                    method=request.method,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    batch_size=10  # Example batch size
                )

                # 메시지 생성
                message = {
                    "type": "metadata",
                    "metadata": {
                        "keyword": request.keyword,
                        "collection_id": collection_id
                    },
                    "articles": result.get('articles', [])
                }

                # RabbitMQ에 발행
                publish_success = await self._collector.publish_message('metadata_queue', message)

                if publish_success:
                    # 상태 업데이트
                    self.active_collections[collection_id] = CollectionStatus(
                        id=collection_id,
                        status="completed",
                        keyword=request.keyword,
                        progress="100%",
                        start_time=datetime.now(pytz.timezone('Asia/Seoul'))
                    )
                else:
                    raise Exception("Failed to publish message to RabbitMQ")

            return collection_id

        except Exception as e:
            logger.error(f"수집 시작 실패: {str(e)}")
            raise Exception(f"수집 시작 실패: {str(e)}")

    async def stop_collection(self, collection_id: str) -> bool:
        """수집 작업 중지"""
        try:
            if collection_id not in self.active_collections:
                raise Exception("Collection not found")

            # 상태 업데이트
            self.active_collections[collection_id].status = "stopped"
            self.active_collections[collection_id].end_time = datetime.now(pytz.timezone('Asia/Seoul'))

            return True
        except Exception as e:
            logger.error(f"수집 중지 실패: {str(e)}")
            raise Exception(f"수집 중지 실패: {str(e)}")

    async def get_collection_status(self, collection_id: Optional[str] = None) -> List[CollectionStatus]:
        """수집 상태 조회"""
        try:
            if collection_id:
                if collection_id not in self.active_collections:
                    raise Exception("Collection not found")
                return [self.active_collections[collection_id]]
            return list(self.active_collections.values())
        except Exception as e:
            logger.error(f"상태 조회 실패: {str(e)}")
            raise Exception(f"상태 조회 실패: {str(e)}")

    async def get_resource_usage(self) -> ResourceUsage:
        """리소스 사용량 조회"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            if not self._collector:
                await self.init()

            metadata_queue_size = await self._collector._get_queue_size('metadata_queue')
            comments_queue_size = await self._collector._get_queue_size('comments_queue')
            total_queue_size = metadata_queue_size + comments_queue_size

            selenium_nodes = int(os.getenv('SELENIUM_GRID_NODES', '0'))

            active_collections = len([c for c in self.active_collections.values() if c.status == "running"])
            queued_collections = len([c for c in self.active_collections.values() if c.status == "queued"])

            return ResourceUsage(
                selenium_nodes=selenium_nodes,
                active_collections=active_collections,
                queued_collections=queued_collections,
                rabbitmq_queue_size=total_queue_size,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage
            )
        except Exception as e:
            logger.error(f"리소스 사용량 조회 실패: {str(e)}")
            raise Exception(f"리소스 사용량 조회 실패: {str(e)}")
