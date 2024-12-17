import os
import asyncio
import logging
import psutil
from datetime import datetime, timedelta
import pytz
import json
import random
from typing import Dict, Any, List, Optional, Tuple, Union

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from news_collector.collectors.metadata import MetadataCollector
from news_collector.collectors.comments import CommentCollector
from app.models.collector_models import CollectionStatus, ResourceUsage, format_datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv(
    'RABBITMQ_URL',
    'amqp://guest:guest@localhost:5672/'  # Default to localhost for local development
)
MAX_RECONNECTION_ATTEMPTS = 5
RECONNECTION_DELAY = 5  # seconds

def serialize_datetime(obj: Any) -> Any:
    """Helper function to serialize datetime objects"""
    if isinstance(obj, datetime):
        return format_datetime(obj)
    return obj

class RabbitMQCollector:
    """RabbitMQ-based collector that handles data collection and message publishing"""
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        """Initialize collectors and RabbitMQ connection"""
        self.rabbitmq_url = rabbitmq_url or RABBITMQ_URL
        self.metadata_collector: Optional[MetadataCollector] = None
        self.comment_collector: Optional[CommentCollector] = None
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel = None
        self.active_collections = {}
        self.current_task = None
        logger.info(f"RabbitMQCollector initialized with URL: {self.rabbitmq_url}")
        
    async def initialize_collectors(self) -> None:
        """Asynchronously initialize collectors"""
        try:
            logger.info("Starting collectors initialization...")
            
            # Initialize collectors with configuration
            config = {
                'rabbitmq_url': self.rabbitmq_url,
                'selenium_hub_url': os.getenv('SELENIUM_HUB_URL', 'http://selenium-hub/wd/hub')
            }
            
            # Initialize MetadataCollector
            if not self.metadata_collector:
                logger.info("Creating MetadataCollector instance...")
                self.metadata_collector = MetadataCollector(config)
                logger.info("Initializing MetadataCollector session...")
                await self.metadata_collector.init_session()
                logger.info("Successfully initialized MetadataCollector")
            
            # Initialize CommentCollector
            if not self.comment_collector:
                logger.info("Creating CommentCollector instance...")
                self.comment_collector = CommentCollector(config)
                logger.info("Initializing CommentCollector session...")
                await self.comment_collector.init_session()
                logger.info("Successfully initialized CommentCollector")
            
        except Exception as e:
            logger.error(f"Failed to initialize collectors: {str(e)}", exc_info=True)
            raise
    
    async def connect_rabbitmq(self) -> bool:
        """Connect to RabbitMQ with retry mechanism"""
        for attempt in range(MAX_RECONNECTION_ATTEMPTS):
            try:
                if self.connection and not self.connection.is_closed:
                    return True
                    
                logger.info(f"Attempting to connect to RabbitMQ (attempt {attempt + 1}/{MAX_RECONNECTION_ATTEMPTS})")
                logger.info(f"Using RabbitMQ URL: {self.rabbitmq_url}")
                
                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    loop=asyncio.get_event_loop()
                )
                logger.info("RabbitMQ connection established")
                
                self.channel = await self.connection.channel()
                logger.info("RabbitMQ channel created")
                
                # Declare queues
                queues = ['metadata_queue', 'comments_queue']
                for queue_name in queues:
                    logger.info(f"Declaring {queue_name}...")
                    queue = await self.channel.declare_queue(
                        queue_name,
                        durable=True
                    )
                    logger.info(f"{queue_name} declared. Queue info: {queue}")
                
                logger.info("Successfully connected to RabbitMQ and declared queues")
                return True
                
            except aio_pika.exceptions.AMQPConnectionError as e:
                logger.error(f"AMQP Connection Error: {str(e)}", exc_info=True)
                if attempt == MAX_RECONNECTION_ATTEMPTS - 1:
                    logger.error(f"Failed to connect to RabbitMQ after {MAX_RECONNECTION_ATTEMPTS} attempts")
                    return False
                logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {RECONNECTION_DELAY} seconds...")
                await asyncio.sleep(RECONNECTION_DELAY)
            except Exception as e:
                logger.error(f"Unexpected error during RabbitMQ connection: {str(e)}", exc_info=True)
                if attempt == MAX_RECONNECTION_ATTEMPTS - 1:
                    return False
                await asyncio.sleep(RECONNECTION_DELAY)
        return False
    
    async def publish_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Publish message to RabbitMQ queue"""
        try:
            logger.info(f"Preparing to publish message to queue: {queue_name}")
            
            # Ensure connection is active
            if not await self.connect_rabbitmq():
                logger.error("Failed to establish RabbitMQ connection")
                return False
            
            # Serialize message
            message_json = json.dumps(message, default=serialize_datetime)
            
            # Publish message
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_json.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name
            )
            
            logger.info(f"Successfully published message to {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}", exc_info=True)
            return False

    async def collect_metadata(
        self,
        keyword: str,
        method: str,
        start_date: str,
        end_date: str,
        delay_range: Tuple[float, float] = (1, 3),
        batch_size: int = 10000
    ) -> Dict[str, Any]:
        """Collect metadata and publish to RabbitMQ"""
        logger.info(f"Starting metadata collection for keyword: {keyword}")
        logger.info(f"Method: {method}, Date range: {start_date} to {end_date}")
        
        try:
            # Ensure collectors are initialized
            if not self.metadata_collector:
                await self.initialize_collectors()
            
            # Update current task
            self.current_task = f"metadata_collection_{keyword}"
            
            # Collect metadata
            result = await self.metadata_collector.collect(
                method=method,
                keyword=keyword,
                max_articles=batch_size,
                start_date=start_date,
                end_date=end_date
            )
            
            articles = result.get('articles', [])
            logger.info(f"Collected {len(articles)} articles")
            
            if articles:
                message = {
                    'type': 'metadata',
                    'metadata': {
                        'keyword': keyword,
                        'collection_date': format_datetime(datetime.now(KST))
                    },
                    'articles': articles
                }
                
                if await self.publish_message('metadata_queue', message):
                    logger.info(f"Successfully published {len(articles)} articles")
                else:
                    logger.error("Failed to publish articles")
            
            # Apply delay
            delay = random.uniform(delay_range[0], delay_range[1])
            logger.info(f"Applying delay of {delay} seconds")
            await asyncio.sleep(delay)
            
            return {
                'success': True,
                'message': f'Published {len(articles)} articles to RabbitMQ',
                'total_articles': len(articles),
                'start_date': start_date,
                'end_date': end_date
            }
            
        except Exception as e:
            logger.error(f"Error collecting metadata: {str(e)}", exc_info=True)
            raise
        finally:
            self.current_task = None

    async def collect_comments(
        self,
        article_urls: List[str],
        delay_range: Tuple[float, float] = (2, 5)
    ) -> Dict[str, Any]:
        """Collect comments and publish to RabbitMQ"""
        try:
            logger.info(f"Starting comments collection for {len(article_urls)} articles")
            
            # Ensure collectors are initialized
            if not self.comment_collector:
                await self.initialize_collectors()
            
            # Update current task
            self.current_task = "comments_collection"
            
            total_comments = 0
            
            for article_url in article_urls:
                try:
                    logger.info(f"Collecting comments for article: {article_url}")
                    
                    result = await self.comment_collector.collect(
                        article_url=article_url
                    )
                    
                    comments = result.get('comments', [])
                    logger.info(f"Collected {len(comments)} comments")
                    
                    if comments:
                        message = {
                            'type': 'comments',
                            'article_url': article_url,
                            'comments': comments,
                            'stats': result.get('stats', {}),
                            'total_count': result.get('total_count', 0),
                            'published_at': result.get('published_at'),
                            'collected_at': format_datetime(datetime.now(KST))
                        }
                        
                        if await self.publish_message('comments_queue', message):
                            total_comments += len(comments)
                            logger.info(f"Successfully published {len(comments)} comments")
                        
                        # Apply delay
                        delay = random.uniform(delay_range[0], delay_range[1])
                        logger.info(f"Applying delay of {delay} seconds")
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Error collecting comments for {article_url}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'message': f'Published {total_comments} comments to RabbitMQ',
                'total_comments': total_comments
            }
            
        except Exception as e:
            logger.error(f"Error in collect_comments: {str(e)}", exc_info=True)
            raise
        finally:
            self.current_task = None

    async def get_status(self) -> CollectionStatus:
        """Get current collection status"""
        try:
            status = CollectionStatus(
                is_running=bool(self.current_task),
                current_task=str(self.current_task) if self.current_task else None,
                progress={},
                last_error=None,
                start_time=None,
                end_time=None,
                last_updated=datetime.now(KST)
            )
            logger.info(f"Current status: {status}")
            return status
        except Exception as e:
            logger.error(f"Failed to retrieve status: {str(e)}", exc_info=True)
            raise

    async def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            selenium_nodes = int(os.getenv('SELENIUM_GRID_NODES', '0'))
            active_collections = len([c for c in self.active_collections.values() if c.get('status') == "running"])
            queued_collections = len([c for c in self.active_collections.values() if c.get('status') == "queued"])

            usage = ResourceUsage(
                selenium_nodes=selenium_nodes,
                active_collections=active_collections,
                queued_collections=queued_collections,
                rabbitmq_queue_size=0,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage
            )
            logger.info(f"Current resource usage: {usage}")
            return usage
        except Exception as e:
            logger.error(f"Failed to retrieve resource usage: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Cleanup all resources"""
        cleanup_errors = []
        
        # Reset current task
        self.current_task = None
        
        # Cleanup collectors
        for collector, name in [
            (self.metadata_collector, "metadata collector"),
            (self.comment_collector, "comment collector")
        ]:
            if collector:
                try:
                    logger.info(f"Cleaning up {name}")
                    await collector.cleanup()
                except Exception as e:
                    error_msg = f"Error cleaning up {name}: {str(e)}"
                    logger.error(error_msg)
                    cleanup_errors.append(error_msg)
        
        # Cleanup RabbitMQ
        if self.channel:
            try:
                logger.info("Closing RabbitMQ channel")
                await self.channel.close()
            except Exception as e:
                error_msg = f"Error closing RabbitMQ channel: {str(e)}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        if self.connection and not self.connection.is_closed:
            try:
                logger.info("Closing RabbitMQ connection")
                await self.connection.close()
            except Exception as e:
                error_msg = f"Error closing RabbitMQ connection: {str(e)}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Reset instance variables
        self.metadata_collector = None
        self.comment_collector = None
        self.channel = None
        self.connection = None
        self.active_collections.clear()
        
        if cleanup_errors:
            logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors")
            for error in cleanup_errors:
                logger.warning(f"Cleanup error: {error}")
        else:
            logger.info("Cleanup completed successfully")
