import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pytz
import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from news_collector.collectors.metadata import MetadataCollector
from news_collector.collectors.comments import CommentCollector
from ..models.collector_models import CollectionStatus
from .collector_service import CollectorService

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class CollectorConsumer:
    """수집 작업 Consumer"""

    def __init__(self):
        """Initialize consumer."""
        self.requests_queue = 'collector_requests_queue'
        self.results_queue = 'collector_results_queue'
        self.connection = None
        self.channel = None
        self.collector_service = CollectorService()
        self.metadata_collector = None
        self.comment_collector = None

    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            # RabbitMQ 연결 설정
            rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
            rabbitmq_port = os.getenv('RABBITMQ_PORT', '5672')
            rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
            rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'guest')
            
            connection_url = f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}:{rabbitmq_port}/"
            logger.info(f"[Consumer] Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port}")
            
            self.connection = await aio_pika.connect_robust(connection_url)
            self.channel = await self.connection.channel()
            
            # 큐 선언
            await self.channel.declare_queue(
                self.requests_queue,
                durable=True
            )
            await self.channel.declare_queue(
                self.results_queue,
                durable=True
            )
            
            # Initialize collectors
            logger.info("[Consumer] Initializing collectors...")
            self.metadata_collector = MetadataCollector()
            self.comment_collector = CommentCollector()
            
            logger.info("[Consumer] Successfully connected to RabbitMQ and initialized collectors")
            
        except Exception as e:
            logger.error(f"[Consumer] Failed to connect to RabbitMQ: {e}", exc_info=True)
            raise

    async def process_metadata_request(self, request_id: str, params: Dict[str, Any]) -> None:
        """Process metadata collection request."""
        try:
            logger.debug(f"[Consumer] Processing metadata request {request_id} with params: {params}")
            
            # Update status to IN_PROGRESS
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.IN_PROGRESS
            )
            
            # Log collection start
            logger.info(f"[Consumer] Starting metadata collection for request {request_id}")
            logger.debug(f"[Consumer] Collection parameters: {params}")
            
            # Collect metadata
            result = await self.metadata_collector.collect(**params)
            
            # Log collection result
            logger.info(f"[Consumer] Metadata collection completed for request {request_id}")
            logger.debug(f"[Consumer] Collected {len(result['articles'])} articles")
            
            # Update status to COMPLETED
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.COMPLETED,
                total_collected=len(result['articles'])
            )
            
            # Publish result
            await self.publish_result(request_id, result)
            
        except Exception as e:
            logger.error(f"[Consumer] Error processing metadata request {request_id}: {e}", exc_info=True)
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.FAILED,
                error_message=str(e)
            )

    async def process_comment_request(self, request_id: str, params: Dict[str, Any]) -> None:
        """Process comment collection request."""
        try:
            logger.debug(f"[Consumer] Processing comment request {request_id} with params: {params}")
            
            # Update status to IN_PROGRESS
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.IN_PROGRESS
            )
            
            # Log collection start
            logger.info(f"[Consumer] Starting comment collection for request {request_id}")
            logger.debug(f"[Consumer] Collection parameters: {params}")
            
            # Extract parameters
            article_urls = params.get('article_urls', [])
            min_delay = params.get('min_delay', 0.1)
            max_delay = params.get('max_delay', 0.5)
            batch_size = params.get('batch_size', 10)
            is_test = params.get('is_test', False)
            
            # Collect comments
            result = await self.comment_collector.collect(
                article_urls=article_urls,
                min_delay=min_delay,
                max_delay=max_delay,
                batch_size=batch_size,
                is_test=is_test
            )
            
            # Log collection result
            logger.info(f"[Consumer] Comment collection completed for request {request_id}")
            total_comments = sum(len(article['comments']) for article in result['articles'])
            logger.debug(f"[Consumer] Collected {total_comments} comments from {len(result['articles'])} articles")
            
            # Update status to COMPLETED
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.COMPLETED,
                total_collected=total_comments
            )
            
            # Publish result
            await self.publish_result(request_id, result)
            
        except Exception as e:
            logger.error(f"[Consumer] Error processing comment request {request_id}: {e}", exc_info=True)
            await self.collector_service.update_status(
                request_id,
                CollectionStatus.FAILED,
                error_message=str(e)
            )

    async def process_message(self, message: AbstractIncomingMessage) -> None:
        """Process incoming message."""
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())
                request_id = body['request_id']
                request_type = body['type']
                params = body['params']
                
                logger.info(f"[Consumer] Received {request_type} request: {request_id}")
                logger.debug(f"[Consumer] Message body: {body}")
                
                # Process based on request type
                if request_type == 'metadata':
                    await self.process_metadata_request(request_id, params)
                elif request_type == 'comments':
                    await self.process_comment_request(request_id, params)
                else:
                    logger.warning(f"[Consumer] Unknown request type: {request_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"[Consumer] Failed to decode message: {e}", exc_info=True)
            except KeyError as e:
                logger.error(f"[Consumer] Missing required field in message: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"[Consumer] Error processing message: {e}", exc_info=True)

    async def publish_result(self, request_id: str, result: Dict[str, Any]) -> None:
        """Publish collection result."""
        try:
            message = {
                'request_id': request_id,
                'result': result,
                'completed_at': datetime.now(KST).isoformat()
            }
            
            # Log publishing attempt
            logger.info(f"[Consumer] Publishing result for request {request_id}")
            logger.debug(f"[Consumer] Result message: {message}")
            
            # Convert message to bytes
            message_bytes = json.dumps(message).encode()
            
            # Publish to results queue
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_bytes,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=self.results_queue
            )
            
            logger.info(f"[Consumer] Successfully published result for request {request_id}")
            
        except Exception as e:
            logger.error(f"[Consumer] Error publishing result: {e}", exc_info=True)
            raise

    async def run(self) -> None:
        """Run the consumer."""
        try:
            await self.connect()
            
            queue = await self.channel.declare_queue(
                self.requests_queue,
                durable=True
            )
            
            logger.info("[Consumer] Starting to consume messages...")
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self.process_message(message)
                    
        except Exception as e:
            logger.error(f"[Consumer] Error in consumer: {e}", exc_info=True)
            raise
        finally:
            if self.connection:
                await self.connection.close()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            if self.connection:
                await self.connection.close()
            await self.collector_service.cleanup()
            logger.info("[Consumer] Cleanup completed")
        except Exception as e:
            logger.error(f"[Consumer] Error during cleanup: {e}", exc_info=True)

async def main():
    """Main function to run the consumer."""
    consumer = CollectorConsumer()
    try:
        logger.info("[Consumer] Starting collector consumer...")
        await consumer.run()
    except KeyboardInterrupt:
        logger.info("[Consumer] Received shutdown signal")
    except Exception as e:
        logger.error(f"[Consumer] Fatal error: {e}", exc_info=True)
    finally:
        await consumer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
