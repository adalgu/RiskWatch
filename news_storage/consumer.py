"""
RabbitMQ Consumer for news_storage module.

Handles messages from news_collector and stores them in PostgreSQL database.
Implements retry mechanisms and graceful shutdown.
"""

import os
import json
import asyncio
import signal
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool

from news_storage.config import AsyncStorageSessionLocal
from news_storage.database import AsyncDatabaseOperations

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


class NewsStorageConsumer:
    def __init__(self):
        self.connection_pool: Optional[Pool] = None
        self.channel_pool: Optional[Pool] = None
        self.should_exit = False
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )

    async def get_connection(self) -> AbstractRobustConnection:
        """Create a connection pool"""
        if not self.connection_pool:
            self.connection_pool = Pool(
                self.get_connection_impl,
                max_size=2,
                loop=asyncio.get_event_loop()
            )
        return await self.connection_pool.acquire()

    async def get_connection_impl(self) -> AbstractRobustConnection:
        """Implement connection creation with retry mechanism"""
        for attempt in range(MAX_RECONNECTION_ATTEMPTS):
            try:
                connection = await aio_pika.connect_robust(
                    RABBITMQ_URL,
                    loop=asyncio.get_event_loop()
                )
                logger.info("Successfully connected to RabbitMQ")
                return connection
            except Exception as e:
                if attempt == MAX_RECONNECTION_ATTEMPTS - 1:
                    logger.error(
                        f"Failed to connect to RabbitMQ after {MAX_RECONNECTION_ATTEMPTS} attempts")
                    raise
                logger.warning(
                    f"Connection attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(RECONNECTION_DELAY)

    async def process_metadata(self, data: Dict[str, Any]) -> None:
        """Process metadata message"""
        try:
            articles = data.get('articles', [])
            if not articles:
                logger.warning("No articles found in metadata message")
                return

            for article_data in articles:
                await AsyncDatabaseOperations.execute_transaction(
                    AsyncDatabaseOperations.create_article,
                    article_data
                )
            logger.info(f"Successfully processed {len(articles)} articles")
        except Exception as e:
            logger.error(f"Error processing metadata: {str(e)}")
            raise

    async def process_content(self, data: Dict[str, Any]) -> None:
        """Process content message"""
        try:
            content_data = data.get('content')
            article_id = data.get('article_id')

            if not content_data or not article_id:
                logger.warning("Missing content data or article_id")
                return

            await AsyncDatabaseOperations.execute_transaction(
                AsyncDatabaseOperations.create_content,
                content_data,
                article_id
            )
            logger.info(
                f"Successfully processed content for article {article_id}")
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            raise

    async def process_comments(self, data: Dict[str, Any]) -> None:
        """Process comments message"""
        try:
            comments = data.get('comments', [])
            article_id = data.get('article_id')

            if not comments or not article_id:
                logger.warning("Missing comments data or article_id")
                return

            await AsyncDatabaseOperations.execute_transaction(
                AsyncDatabaseOperations.batch_create_comments,
                comments,
                article_id
            )
            logger.info(
                f"Successfully processed {len(comments)} comments for article {article_id}")
        except Exception as e:
            logger.error(f"Error processing comments: {str(e)}")
            raise

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Process incoming messages based on their type"""
        async with message.process():
            try:
                body = message.body.decode()
                data = json.loads(body)

                message_type = data.get('type', 'metadata')
                logger.info(f"Processing message of type: {message_type}")

                if message_type == 'metadata':
                    await self.process_metadata(data)
                elif message_type == 'content':
                    await self.process_content(data)
                elif message_type == 'comments':
                    await self.process_comments(data)
                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                logger.error("Failed to decode message JSON")
                # Don't requeue malformed messages
                return
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Requeue message on processing error
                await message.reject(requeue=True)
                return

            # Acknowledge message only if processing was successful
            await message.ack()

    async def consume(self) -> None:
        """Start consuming messages from RabbitMQ"""
        while not self.should_exit:
            try:
                connection = await self.get_connection()
                channel = await connection.channel()

                # Declare queues
                metadata_queue = await channel.declare_queue(
                    'metadata_queue',
                    durable=True
                )
                content_queue = await channel.declare_queue(
                    'content_queue',
                    durable=True
                )
                comments_queue = await channel.declare_queue(
                    'comments_queue',
                    durable=True
                )

                # Start consuming from all queues
                await metadata_queue.consume(self.process_message)
                await content_queue.consume(self.process_message)
                await comments_queue.consume(self.process_message)

                logger.info("Started consuming messages from all queues")

                # Keep consumer running
                while not self.should_exit:
                    await asyncio.sleep(1)

            except Exception as e:
                if not self.should_exit:
                    logger.error(f"Consumer error: {str(e)}")
                    await asyncio.sleep(RECONNECTION_DELAY)
                else:
                    break

    async def shutdown(self, signal: Optional[signal.Signals] = None) -> None:
        """Handle graceful shutdown"""
        if signal:
            logger.info(f"Received exit signal {signal.name}")

        logger.info("Shutting down consumer...")
        self.should_exit = True

        # Close connection pools if they exist
        if self.connection_pool:
            await self.connection_pool.close()

        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    consumer = NewsStorageConsumer()
    try:
        await consumer.consume()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await consumer.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
