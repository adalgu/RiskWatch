import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Union

import aio_pika
from aio_pika import DeliveryMode, Message, ExchangeType

logger = logging.getLogger(__name__)

class Producer:
    """
    Flexible RabbitMQ Producer supporting multiple data types and collection methods.
    
    Key Features:
    - Support for different message types (metadata, comments, content, stats)
    - Configurable queue and exchange handling
    - Robust error handling and retry mechanism
    - Async message publishing
    """

    def __init__(
        self, 
        rabbitmq_url: Optional[str] = None, 
        max_retries: int = 3, 
        retry_delay: float = 2.0
    ):
        """
        Initialize RabbitMQ Producer.

        Args:
            rabbitmq_url (str, optional): RabbitMQ connection URL. 
                Defaults to environment variable or default RabbitMQ URL.
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
            retry_delay (float, optional): Delay between retry attempts. Defaults to 2.0 seconds.
        """
        self.rabbitmq_url = rabbitmq_url or os.getenv(
            'RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        
        # Predefined queue configurations
        self.queue_configs = {
            'metadata_queue': {
                'durable': True,
                'description': 'Queue for article metadata',
                'required_fields': [
                    'articles',  # List of article metadata
                    'collected_at',  # Collection timestamp
                    'metadata'  # Collection metadata (method, total_collected, etc.)
                ]
            },
            'comments_queue': {
                'durable': True,
                'description': 'Queue for article comments and comment statistics',
                'required_fields': [
                    'article_url',
                    'type',
                    'comments',
                    'stats',
                    'total_count',
                    'collected_at'
                ]
            },
            'content_queue': {
                'durable': True,
                'description': 'Queue for full article content',
                'required_fields': [
                    'article_url',
                    'full_text',
                    'title',
                    'metadata',
                    'subheadings',
                    'images',
                    'collected_at'
                ]
            },
            'stats_queue': {
                'durable': True,
                'description': 'Queue for article and comment statistics',
                'required_fields': [
                    'article_url',
                    'type',
                    'stats',
                    'collected_at'
                ]
            }
        }

    async def connect(self) -> None:
        """Establish connection to RabbitMQ with robust error handling."""
        for attempt in range(self.max_retries):
            try:
                if not self.connection or self.connection.is_closed:
                    self.connection = await aio_pika.connect_robust(
                        self.rabbitmq_url
                    )
                    logger.info("Successfully connected to RabbitMQ")

                if not self.channel or self.channel.is_closed:
                    self.channel = await self.connection.channel()
                    logger.info("Successfully created RabbitMQ channel")
                
                return
            except Exception as e:
                logger.warning(f"RabbitMQ connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Failed to connect to RabbitMQ after maximum retries")
                    raise

    def _validate_message(self, message: Dict[str, Any], queue_name: str) -> bool:
        """
        Validate message against queue-specific requirements.

        Args:
            message (Dict[str, Any]): Message to validate
            queue_name (str): Target queue name

        Returns:
            bool: Whether message meets validation requirements
        """
        if queue_name not in self.queue_configs:
            logger.warning(f"No configuration found for queue: {queue_name}")
            return True  # Allow custom queues without strict validation

        config = self.queue_configs[queue_name]
        required_fields = config.get('required_fields', [])

        for field in required_fields:
            if field not in message:
                logger.error(f"Missing required field '{field}' for {queue_name}")
                return False

        # Additional validation for metadata_queue
        if queue_name == 'metadata_queue':
            if not isinstance(message['articles'], list):
                logger.error("'articles' field must be a list")
                return False
            if not isinstance(message['metadata'], dict):
                logger.error("'metadata' field must be a dictionary")
                return False
            required_metadata_fields = {
                'method', 'total_collected', 'keyword', 
                'is_test', 'is_api_collection'
            }
            if not all(field in message['metadata'] for field in required_metadata_fields):
                logger.error(f"Missing required metadata fields. Required: {required_metadata_fields}")
                return False

        return True

    async def publish(
        self, 
        message: Dict[str, Any], 
        queue_name: str = 'default_queue', 
        routing_key: Optional[str] = None,
        exchange_name: Optional[str] = None,
        persistent: bool = True
    ) -> None:
        """
        Publish a message to a queue or exchange with robust error handling.

        Args:
            message (Dict[str, Any]): Message payload to publish
            queue_name (str, optional): Queue to publish to. Defaults to 'default_queue'.
            routing_key (str, optional): Routing key for exchange publishing
            exchange_name (str, optional): Exchange to publish to
            persistent (bool, optional): Whether message should survive broker restart
        """
        # Validate message against queue requirements
        if not self._validate_message(message, queue_name):
            raise ValueError(f"Message does not meet requirements for {queue_name}")

        for attempt in range(self.max_retries):
            try:
                if not self.channel:
                    await self.connect()

                # Serialize message
                body = json.dumps(message, ensure_ascii=False).encode('utf-8')

                # Prepare message
                delivery_mode = (
                    DeliveryMode.PERSISTENT if persistent else DeliveryMode.NON_PERSISTENT
                )
                amqp_message = Message(
                    body=body,
                    delivery_mode=delivery_mode
                )

                # Declare queue if not exists
                await self.channel.declare_queue(queue_name, durable=True)

                # Publish to queue or exchange
                if exchange_name:
                    exchange = await self.channel.declare_exchange(
                        exchange_name, 
                        type=ExchangeType.DIRECT
                    )
                    await exchange.publish(
                        message=amqp_message,
                        routing_key=routing_key or queue_name
                    )
                else:
                    await self.channel.default_exchange.publish(
                        message=amqp_message,
                        routing_key=queue_name
                    )

                logger.info(f"Successfully published message to {queue_name}")
                return

            except Exception as e:
                logger.warning(f"Message publish attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Failed to publish message after maximum retries")
                    raise

    async def close(self) -> None:
        """Close RabbitMQ connection and channel gracefully."""
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
            logger.info("RabbitMQ channel closed")

        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

        self.channel = None
        self.connection = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
