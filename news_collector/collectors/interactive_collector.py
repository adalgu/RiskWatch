import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import json
import random
from typing import Dict, Any, List, Optional, Tuple

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from news_collector.collectors.metadata import MetadataCollector
from news_collector.collectors.comments import CommentCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
MAX_RECONNECTION_ATTEMPTS = 5
RECONNECTION_DELAY = 5  # seconds

class RabbitMQCollector:
    """RabbitMQ-based collector that handles data collection and message publishing"""
    
    def __init__(self):
        """Initialize collectors and RabbitMQ connection"""
        self.metadata_collector: Optional[MetadataCollector] = None
        self.comment_collector: Optional[CommentCollector] = None
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel = None
        
    async def initialize_collectors(self) -> None:
        """Asynchronously initialize MetadataCollector and CommentCollector"""
        self.metadata_collector = MetadataCollector()
        await self.metadata_collector.init_session()
        
        self.comment_collector = CommentCollector()
        await self.comment_collector.init_session()
    
    async def connect_rabbitmq(self) -> bool:
        """
        Connect to RabbitMQ with retry mechanism
        
        Returns:
            bool: True if connection successful, False otherwise
        """
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
                
                logger.info("Successfully connected to RabbitMQ")
                
                # Initialize collectors after successful connection
                await self.initialize_collectors()
                
                return True
            except Exception as e:
                if attempt == MAX_RECONNECTION_ATTEMPTS - 1:
                    logger.error(f"Failed to connect to RabbitMQ after {MAX_RECONNECTION_ATTEMPTS} attempts: {str(e)}")
                    return False
                logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {RECONNECTION_DELAY} seconds...")
                await asyncio.sleep(RECONNECTION_DELAY)
        return False
    
    async def publish_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to RabbitMQ queue
        
        Args:
            queue_name: Name of the queue to publish to
            message: Message data to publish
            
        Returns:
            bool: True if publish successful, False otherwise
        """
        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            return False

    async def collect_metadata(
        self,
        keyword: str,
        method: str,
        start_date: datetime,
        end_date: datetime,
        delay_range: Tuple[float, float] = (1, 3),
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Collect metadata and publish to RabbitMQ
        
        Args:
            keyword: Search keyword
            method: Collection method ('SEARCH' or 'API')
            start_date: Start date
            end_date: End date
            delay_range: Tuple of (min_delay, max_delay) in seconds
            batch_size: Number of articles per batch
            
        Returns:
            Dict containing collection results
        """
        if not self.metadata_collector:
            await self.initialize_collectors()
        
        total_articles = 0
        current_date = start_date
        
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            try:
                # Collect one day's articles
                result = await self.metadata_collector.collect(
                    method=method,
                    keyword=keyword,
                    max_articles=batch_size,
                    start_date=current_date.strftime('%Y-%m-%d'),
                    end_date=current_date.strftime('%Y-%m-%d')
                )
                
                articles = result.get('articles', [])
                
                if articles:
                    # Prepare message
                    message = {
                        'type': 'metadata',
                        'metadata': {
                            'keyword': keyword,
                            'collection_date': datetime.now(KST).isoformat()
                        },
                        'articles': articles
                    }
                    
                    # Publish to RabbitMQ
                    if await self.publish_message('metadata_queue', message):
                        total_articles += len(articles)
                        logger.info(f"Published {len(articles)} articles to RabbitMQ")
                
                # Human-like delay
                delay = random.uniform(delay_range[0], delay_range[1])
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error collecting metadata for {current_date}: {e}")
            
            current_date = next_date
        
        return {
            'success': True,
            'message': f'Published {total_articles} articles to RabbitMQ',
            'total_articles': total_articles
        }

    async def collect_comments(
        self,
        article_urls: List[str],
        delay_range: Tuple[float, float] = (2, 5)
    ) -> Dict[str, Any]:
        """
        Collect comments for articles and publish to RabbitMQ
        
        Args:
            article_urls: List of article URLs to collect comments from
            delay_range: Tuple of (min_delay, max_delay) in seconds
            
        Returns:
            Dict containing collection results
        """
        if not self.comment_collector:
            await self.initialize_collectors()
        
        total_comments = 0
        
        for article_url in article_urls:
            try:
                # Collect comments
                result = await self.comment_collector.collect(
                    article_url=article_url
                )
                
                comments = result.get('comments', [])
                
                if comments:
                    # Prepare message
                    message = {
                        'type': 'comments',
                        'article_url': article_url,
                        'comments': comments
                    }
                    
                    # Publish to RabbitMQ
                    if await self.publish_message('comments_queue', message):
                        total_comments += len(comments)
                        logger.info(f"Published {len(comments)} comments to RabbitMQ")
                
                # Human-like delay
                delay = random.uniform(delay_range[0], delay_range[1])
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error collecting comments for {article_url}: {e}")
        
        return {
            'success': True,
            'message': f'Published {total_comments} comments to RabbitMQ',
            'total_comments': total_comments
        }

    async def cleanup(self):
        """Cleanup resources"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        if self.metadata_collector:
            await self.metadata_collector.cleanup()
        if self.comment_collector:
            await self.comment_collector.cleanup()

async def main():
    """Example usage"""
    collector = RabbitMQCollector()
    try:
        connected = await collector.connect_rabbitmq()
        if not connected:
            logger.error("Could not establish RabbitMQ connection. Exiting.")
            return

        # Example metadata collection
        result = await collector.collect_metadata(
            keyword="카카오모빌리티",
            method="SEARCH",
            start_date=datetime(2024, 1, 1, tzinfo=KST),
            end_date=datetime(2024, 1, 2, tzinfo=KST),
            batch_size=10
        )
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Example comments collection
        comments_result = await collector.collect_comments(
            article_urls=["http://example.com/article1", "http://example.com/article2"],
            batch_size=5
        )
        logger.info(json.dumps(comments_result, ensure_ascii=False, indent=2))
        
    finally:
        await collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
