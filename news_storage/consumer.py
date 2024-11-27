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
from aio_pika.abc import AbstractRobustConnection, AbstractChannel
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
MAX_RETRY_ATTEMPTS = 3


class NewsStorageConsumer:
    def __init__(self):
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.should_exit = False
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )

    async def create_connection(self) -> AbstractRobustConnection:
        """Create a new connection with retry mechanism"""
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

    async def process_metadata(self, data: Dict[str, Any]) -> bool:
        """Process metadata message with retry mechanism"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                articles = data.get('articles', [])
                # Extract keyword from metadata section
                main_keyword = data.get('metadata', {}).get('keyword', 'default_keyword')
                
                if not articles:
                    logger.warning("No articles found in metadata message")
                    return True

                if not main_keyword:
                    logger.warning("No keyword found in metadata message")
                    main_keyword = 'default_keyword'

                async with AsyncStorageSessionLocal() as session:
                    for article_data in articles:
                        await AsyncDatabaseOperations.create_article(session, article_data, main_keyword)
                    await session.commit()

                logger.info(f"Successfully processed {len(articles)} articles with keyword '{main_keyword}'")
                return True
            except Exception as e:
                logger.error(f"Error processing metadata (attempt {attempt + 1}): {str(e)}")
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False
                await asyncio.sleep(1)

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Process incoming messages with enhanced error handling"""
        try:
            body = message.body.decode()
            data = json.loads(body)

            message_type = data.get('type', 'metadata')
            logger.info(f"Processing message of type: {message_type}")

            success = False
            if message_type == 'metadata':
                success = await self.process_metadata(data)
            else:
                logger.warning(f"Unsupported message type: {message_type}")
                success = True  # Acknowledge unsupported messages

            if success:
                await message.ack()
            else:
                await message.reject(requeue=True)

        except json.JSONDecodeError:
            logger.error("Failed to decode message JSON")
            await message.reject(requeue=False)
        except Exception as e:
            logger.error(f"Unexpected error processing message: {str(e)}")
            await message.reject(requeue=True)

    async def setup_queues(self, channel: AbstractChannel):
        """Setup and return all required queues"""
        metadata_queue = await channel.declare_queue(
            'metadata_queue',
            durable=True
        )
        return metadata_queue

    async def consume(self) -> None:
        """Start consuming messages from RabbitMQ"""
        while not self.should_exit:
            try:
                # Create connection and channel
                self.connection = await self.create_connection()
                self.channel = await self.connection.channel()

                # Setup queues
                metadata_queue = await self.setup_queues(self.channel)

                # Start consuming from queue
                await metadata_queue.consume(self.process_message)

                logger.info("Started consuming messages from metadata queue")

                # Keep consumer running
                while not self.should_exit:
                    await asyncio.sleep(1)

            except Exception as e:
                if not self.should_exit:
                    logger.error(f"Consumer error: {str(e)}")
                    if self.connection:
                        await self.connection.close()
                    await asyncio.sleep(RECONNECTION_DELAY)
                else:
                    break

    async def shutdown(self, signal: Optional[signal.Signals] = None) -> None:
        """Handle graceful shutdown"""
        if signal:
            logger.info(f"Received exit signal {signal.name}")

        logger.info("Shutting down consumer...")
        self.should_exit = True

        # Close connection and channel if they exist
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

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
