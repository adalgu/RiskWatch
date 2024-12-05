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
from sqlalchemy import select

from src.config import AsyncStorageSessionLocal
from src.database import AsyncDatabaseOperations
from src.models import Article, Comment

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
PREFETCH_COUNT = 10

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
                        f"Failed to connect to RabbitMQ after {MAX_RECONNECTION_ATTEMPTS} attempts: {str(e)}"
                    )
                    raise
                logger.warning(
                    f"Connection attempt {attempt + 1} failed: {str(e)}. Retrying in {RECONNECTION_DELAY} seconds..."
                )
                await asyncio.sleep(RECONNECTION_DELAY)

    async def validate_message(self, data: Dict[str, Any], required_fields: list) -> bool:
        """Validate message fields."""
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"Missing or invalid field: {field}")
                return False
        return True

    async def process_metadata(self, data: Dict[str, Any]) -> bool:
        """Process metadata message with retry mechanism"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                articles = data.get('articles', [])
                main_keyword = data.get('metadata', {}).get('keyword', 'default_keyword')

                if not articles:
                    logger.warning("No articles found in metadata message")
                    return True

                if not main_keyword:
                    logger.warning("No keyword found in metadata message")
                    main_keyword = 'default_keyword'

                async with AsyncStorageSessionLocal() as session:
                    async with session.begin():
                        for article_data in articles:
                            await AsyncDatabaseOperations.create_article(session, article_data, main_keyword)

                logger.info(f"Successfully processed {len(articles)} articles with keyword '{main_keyword}'")
                return True
            except Exception as e:
                logger.error(f"Error processing metadata (attempt {attempt + 1}): {str(e)}")
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False
                await asyncio.sleep(2 ** attempt)

    async def process_comments(self, data: Dict[str, Any]) -> bool:
        """Process comments message with retry mechanism"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                article_url = data.get('article_url')
                comments = data.get('comments', [])

                if not article_url or not comments:
                    logger.warning("Missing article_url or comments in message")
                    return True

                async with AsyncStorageSessionLocal() as session:
                    async with session.begin():
                        query = select(Article).where(Article.naver_link == article_url)
                        result = await session.execute(query)
                        article = result.scalar_one_or_none()

                        if not article:
                            logger.warning(f"Article not found for URL: {article_url}")
                            return True

                        for comment_data in comments:
                            username = comment_data.get('username')
                            content = comment_data.get('content')
                            timestamp = comment_data.get('timestamp')

                            if not username or not content or not timestamp:
                                logger.warning("Incomplete comment data. Skipping comment.")
                                continue

                            if not isinstance(username, str) or not isinstance(content, str):
                                logger.error(f"Invalid data types in comment. Skipping comment.")
                                continue

                            if isinstance(timestamp, str):
                                try:
                                    timestamp = datetime.fromisoformat(timestamp)
                                except ValueError:
                                    logger.error(f"Invalid timestamp format: {timestamp}. Skipping comment.")
                                    continue

                            await AsyncDatabaseOperations.create_comment(session, article.id, username, content, timestamp)

                logger.info(f"Successfully processed {len(comments)} comments for article {article_url}")
                return True
            except Exception as e:
                logger.error(f"Error processing comments (attempt {attempt + 1}): {str(e)}")
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False
                await asyncio.sleep(2 ** attempt)

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Process incoming messages with enhanced error handling"""
        async with message.process(requeue=False):
            try:
                body = message.body.decode()
                data = json.loads(body)
                logger.debug(f"Received message: {data}")

                message_type = data.get('type', 'metadata')
                logger.info(f"Processing message of type: {message_type}")

                success = False
                if message_type == 'metadata':
                    if not await self.validate_message(data, ["articles", "metadata"]):
                        logger.warning("Invalid metadata message structure")
                        return
                    success = await self.process_metadata(data)
                elif message_type == 'comments':
                    if not await self.validate_message(data, ["article_url", "comments"]):
                        logger.warning("Invalid comments message structure")
                        return
                    success = await self.process_comments(data)
                else:
                    logger.warning(f"Unsupported message type: {message_type}")
                    return

                if not success:
                    logger.error("Failed to process message after retries. Requeueing message.")
                    await message.reject(requeue=True)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message JSON: {str(e)}. Message body: {message.body}")
                await message.reject(requeue=False)
            except Exception as e:
                logger.error(f"Unexpected error processing message: {str(e)}")
                await message.reject(requeue=True)

    async def setup_queues(self, channel: AbstractChannel):
        """Setup and return all required queues"""
        # 메타데이터 큐 설정
        metadata_queue = await channel.declare_queue(
            'metadata_queue',
            durable=True
        )
        
        # 댓글 큐 설정
        comments_queue = await channel.declare_queue(
            'comments_queue',
            durable=True
        )
        
        return metadata_queue, comments_queue

    async def consume(self) -> None:
        """Start consuming messages from RabbitMQ"""
        while not self.should_exit:
            try:
                self.connection = await self.create_connection()
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=PREFETCH_COUNT)

                metadata_queue, comments_queue = await self.setup_queues(self.channel)

                await metadata_queue.consume(self.process_message)
                await comments_queue.consume(self.process_message)

                logger.info("Started consuming messages from metadata and comments queues")

                while not self.should_exit:
                    await asyncio.sleep(1)

            except Exception as e:
                if not self.should_exit:
                    logger.error(f"Consumer error: {str(e)}")
                    if self.connection and not self.connection.is_closed:
                        await self.connection.close()
                    logger.info(f"Reconnecting in {RECONNECTION_DELAY} seconds...")
                    await asyncio.sleep(RECONNECTION_DELAY)
                else:
                    break

    async def shutdown(self, sig: Optional[signal.Signals] = None) -> None:
        """Handle graceful shutdown"""
        if sig:
            logger.info(f"Received exit signal {sig.name}")

        logger.info("Shutting down consumer...")
        self.should_exit = True

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
