import os
import asyncio
import logging
from aio_pika import connect_robust, Channel, Queue
from aio_pika.exceptions import ChannelClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RabbitMQ URL configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
QUEUES_TO_DELETE = ['metadata_queue', 'comments_queue', 'collection_status_queue']

async def delete_queue(channel: Channel, queue_name: str):
    try:
        queue: Queue = await channel.get_queue(queue_name)
        await queue.delete()
        logger.info(f"Deleted queue: {queue_name}")
        
        # Declare the queue again without x-max-priority
        await channel.declare_queue(
            queue_name,
            durable=True
        )
        logger.info(f"Recreated queue: {queue_name} without x-max-priority")
    except Exception as e:
        logger.error(f"Failed to delete/recreate queue '{queue_name}': {e}")

async def main():
    try:
        connection = await connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        logger.info("Connected to RabbitMQ")

        for queue_name in QUEUES_TO_DELETE:
            await delete_queue(channel, queue_name)

        await connection.close()
        logger.info("Connection closed")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
