import asyncio
import logging
from news_collector.producer import Producer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_rabbitmq_connection():
    """Test RabbitMQ connection and message publishing"""
    # Explicitly specify localhost URL
    producer = Producer(rabbitmq_url='amqp://guest:guest@localhost:5672/')
    
    try:
        logger.info("Attempting to connect to RabbitMQ...")
        await producer.connect()
        logger.info("Successfully connected to RabbitMQ")
        
        # Test message that matches metadata_queue requirements
        test_message = {
            "articles": [],  # Empty list of articles
            "collected_at": "2024-01-01T00:00:00+09:00",
            "metadata": {
                "method": "TEST",
                "total_collected": 0,
                "keyword": "test",
                "is_test": True,
                "is_api_collection": False
            }
        }
        
        # Test queue
        queue_name = "metadata_queue"
        
        logger.info(f"Attempting to publish message to queue: {queue_name}")
        await producer.publish(message=test_message, queue_name=queue_name)
        logger.info("Successfully published test message")
        
    except Exception as e:
        logger.error(f"Error during RabbitMQ test: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up connection...")
        await producer.close()
        logger.info("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_rabbitmq_connection())
