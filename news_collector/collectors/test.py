"""
Test script for RabbitMQ-based collector
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import click

from news_collector.collectors.interactive_collector import RabbitMQCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

def validate_date(ctx, param, value):
    """Validate date format"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=KST)
    except ValueError:
        raise click.BadParameter('Date must be in YYYY-MM-DD format')

@click.group()
def cli():
    """Test RabbitMQ-based collector"""
    pass

@cli.command()
@click.option('--keyword', prompt='Search keyword', help='Keyword to search for')
@click.option('--method', type=click.Choice(['SEARCH', 'API']), prompt='Collection method', help='Collection method')
@click.option('--start-date', prompt='Start date (YYYY-MM-DD)', callback=validate_date, help='Start date')
@click.option('--end-date', prompt='End date (YYYY-MM-DD)', callback=validate_date, help='End date')
@click.option('--min-delay', default=1, help='Minimum delay between requests (seconds)')
@click.option('--max-delay', default=3, help='Maximum delay between requests (seconds)')
@click.option('--batch-size', default=10, help='Number of articles per batch')
def test_metadata(keyword, method, start_date, end_date, min_delay, max_delay, batch_size):
    """Test metadata collection with RabbitMQ"""
    async def run():
        collector = RabbitMQCollector()
        try:
            # Connect to RabbitMQ
            if not await collector.connect_rabbitmq():
                logger.error("Failed to connect to RabbitMQ")
                return
            
            # Collect metadata
            result = await collector.collect_metadata(
                keyword=keyword,
                method=method,
                start_date=start_date,
                end_date=end_date,
                delay_range=(min_delay, max_delay),
                batch_size=batch_size
            )
            
            logger.info(f"Collection result: {result['message']}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await collector.cleanup()
    
    asyncio.run(run())

@cli.command()
@click.option('--urls-file', prompt='File containing article URLs (one per line)', help='File with article URLs')
@click.option('--min-delay', default=2, help='Minimum delay between requests (seconds)')
@click.option('--max-delay', default=5, help='Maximum delay between requests (seconds)')
def test_comments(urls_file, min_delay, max_delay):
    """Test comments collection with RabbitMQ"""
    async def run():
        collector = RabbitMQCollector()
        try:
            # Read URLs from file
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if not urls:
                logger.error("No URLs found in file")
                return
            
            # Connect to RabbitMQ
            if not await collector.connect_rabbitmq():
                logger.error("Failed to connect to RabbitMQ")
                return
            
            # Collect comments
            result = await collector.collect_comments(
                article_urls=urls,
                delay_range=(min_delay, max_delay)
            )
            
            logger.info(f"Collection result: {result['message']}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await collector.cleanup()
    
    asyncio.run(run())

if __name__ == '__main__':
    cli()
