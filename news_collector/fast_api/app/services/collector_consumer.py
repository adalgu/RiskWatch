import os
import json
import asyncio
import logging
from datetime import datetime
import pytz
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.services.collector_service import CollectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
MAX_RECONNECTION_ATTEMPTS = 5
RECONNECTION_DELAY = 5  # seconds

class CollectorConsumer:
    def __init__(self):
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel = None
        self.collector_service = CollectorService()
        self.should_exit = False

    async def connect(self) -> bool:
        """Connect to RabbitMQ with retry mechanism"""
        for attempt in range(MAX_RECONNECTION_ATTEMPTS):
            try:
                self.connection = await aio_pika.connect_robust(
                    RABBITMQ_URL,
                    loop=asyncio.get_event_loop()
                )
                self.channel = await self.connection.channel()
                
                # Declare queues without x-max-priority
                await self.channel.declare_queue(
                    'metadata_queue',
                    durable=True
                )
                await self.channel.declare_queue(
                    'comments_queue',
                    durable=True
                )
                await self.channel.declare_queue(
                    'collection_status_queue',
                    durable=True
                )
                
                logger.info("Successfully connected to RabbitMQ")
                
                # Initialize CollectorService
                await self.collector_service.init()
                
                return True
            except Exception as e:
                if attempt == MAX_RECONNECTION_ATTEMPTS - 1:
                    logger.error(f"Failed to connect to RabbitMQ after {MAX_RECONNECTION_ATTEMPTS} attempts: {str(e)}")
                    return False
                logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {RECONNECTION_DELAY} seconds...")
                await asyncio.sleep(RECONNECTION_DELAY)
        return False

    async def update_status(self, collection_id: str, status: str, progress: str = None, **kwargs):
        """Update collection status"""
        try:
            status_update = {
                "collection_id": collection_id,
                "status": status,
                "progress": progress or "0%",
                **kwargs
            }
            
            if status in ["completed", "failed", "stopped"]:
                status_update["end_time"] = datetime.now().isoformat()
    
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(status_update).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='collection_status_queue'
            )
        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")

    async def process_metadata_message(self, message: aio_pika.IncomingMessage):
        """Process metadata collection message"""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                collection_id = body.get('collection_id')
                logger.info(f"Processing metadata request: {body}")

                # Update status to running
                await self.update_status(
                    collection_id=collection_id,
                    status="running",
                    keyword=body['keyword']
                )

                # Extract parameters
                start_date_str = body.get('start_date')
                end_date_str = body.get('end_date')

                if not start_date_str or not end_date_str:
                    raise ValueError("start_date and end_date are required")

                start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=pytz.UTC)
                end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=pytz.UTC)

                # Start collection using CollectorService
                result = await self.collector_service.start_collection(
                    request=body,  # Assuming body matches CollectionRequest structure
                    collection_type='metadata'
                )

                # Update status to completed
                await self.update_status(
                    collection_id=collection_id,
                    status="completed",
                    progress="100%",
                    result=result
                )

                logger.info(f"Metadata collection completed: {result}")

            except Exception as e:
                logger.error(f"Error processing metadata message: {str(e)}")
                if 'collection_id' in locals() and collection_id:
                    await self.update_status(
                        collection_id=collection_id,
                        status="failed",
                        error=str(e)
                    )
                await message.reject(requeue=True)

    async def process_comments_message(self, message: aio_pika.IncomingMessage):
        """Process comments collection message"""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                collection_id = body.get('collection_id')
                logger.info(f"Processing comments request: {body}")

                # Update status to running
                await self.update_status(
                    collection_id=collection_id,
                    status="running",
                    keyword=body.get('keyword', '')
                )

                # Extract article URLs
                article_urls = body.get('article_urls', [])
                if not article_urls:
                    logger.warning("No article URLs provided")
                    await self.update_status(
                        collection_id=collection_id,
                        status="failed",
                        error="No article URLs provided"
                    )
                    return

                # Start comments collection using CollectorService
                result = await self.collector_service.collect_comments(
                    article_urls=article_urls
                )

                # Update status to completed
                await self.update_status(
                    collection_id=collection_id,
                    status="completed",
                    progress="100%",
                    result=result
                )

                logger.info(f"Comments collection completed: {result}")

            except Exception as e:
                logger.error(f"Error processing comments message: {str(e)}")
                if 'collection_id' in locals() and collection_id:
                    await self.update_status(
                        collection_id=collection_id,
                        status="failed",
                        error=str(e)
                    )
                await message.reject(requeue=True)

    async def start(self):
        """Start consuming messages"""
        if not await self.connect():
            return

        try:
            # Setup metadata queue consumer
            metadata_queue = await self.channel.declare_queue(
                'metadata_queue',
                durable=True
            )
            await metadata_queue.consume(self.process_metadata_message)
            logger.info("Started consuming from metadata_queue")

            # Setup comments queue consumer
            comments_queue = await self.channel.declare_queue(
                'comments_queue',
                durable=True
            )
            await comments_queue.consume(self.process_comments_message)
            logger.info("Started consuming from comments_queue")

            # Keep the consumer running
            while not self.should_exit:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        await self.collector_service.cleanup()

async def main():
    """Main entry point"""
    consumer = CollectorConsumer()
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await consumer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
