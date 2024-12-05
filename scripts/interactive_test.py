"""
Interactive test script for news collection and storage
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List, Optional
import random
import click
from tqdm import tqdm

from sqlalchemy import text
from news_collector.collectors.metadata import MetadataCollector
from news_collector.collectors.comments import CommentCollector
from news_storage.src.database import AsyncDatabaseOperations
from news_storage.src.config import AsyncStorageSessionLocal
from news_storage.src.models import Article

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

class InteractiveNewsTester:
    """Interactive news collection and storage tester"""
    
    def __init__(self):
        self.metadata_collector = MetadataCollector()
        self.comment_collector = CommentCollector()
        
    async def cleanup(self):
        """Cleanup resources"""
        await self.metadata_collector.cleanup()
        await self.comment_collector.cleanup()

    async def collect_metadata(
        self,
        keyword: str,
        method: str,
        start_date: datetime,
        end_date: datetime,
        delay_range: tuple = (1, 3),
        batch_size: int = 10,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Collect metadata with human-like delays
        
        Args:
            keyword: Search keyword
            method: Collection method ('SEARCH' or 'API')
            start_date: Start date
            end_date: End date
            delay_range: Tuple of (min_delay, max_delay) in seconds
            batch_size: Number of articles per batch
            show_progress: Whether to show progress bar
        """
        total_articles = []
        current_date = start_date
        
        # Calculate total days for progress bar
        total_days = (end_date - start_date).days + 1
        
        with tqdm(total=total_days, disable=not show_progress) as pbar:
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                
                try:
                    # Collect one day's articles
                    result = await self.metadata_collector.collect(
                        method=method,
                        keyword=keyword,
                        max_articles=batch_size,
                        start_date=current_date.strftime('%Y-%m-%d'),
                        end_date=current_date.strftime('%Y-%m-%d'),   # 하루씩 검색
                        is_test=True
                    )
                    
                    articles = result.get('articles', [])
                    total_articles.extend(articles)
                    
                    # Store articles
                    async with AsyncStorageSessionLocal() as session:
                        for article in articles:
                            await AsyncDatabaseOperations.create_article(
                                session=session,
                                article_data=article,
                                main_keyword=keyword
                            )
                        await session.commit()
                    
                    # Human-like delay
                    delay = random.uniform(delay_range[0], delay_range[1])
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error collecting metadata for {current_date}: {e}")
                
                current_date = next_date
                pbar.update(1)
                
        return {
            'success': True,
            'message': f'Collected {len(total_articles)} articles',
            'articles': total_articles
        }

    async def collect_comments(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime,
        delay_range: tuple = (2, 5),
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Collect comments for articles within date range
        
        Args:
            keyword: Search keyword
            start_date: Start date
            end_date: End date
            delay_range: Tuple of (min_delay, max_delay) in seconds
            show_progress: Whether to show progress bar
        """
        total_comments = 0
        
        try:
            # Get articles from database
            async with AsyncStorageSessionLocal() as session:
                query = text("""
                    SELECT * FROM articles 
                    WHERE main_keyword = :keyword 
                    AND published_at BETWEEN :start_date AND :end_date
                    AND is_naver_news = true
                """)
                result = await session.execute(query, {
                    'keyword': keyword,
                    'start_date': start_date,
                    'end_date': end_date
                })
                articles = result.fetchall()
            
            if not articles:
                return {
                    'success': False,
                    'message': 'No articles found for the given criteria'
                }
            
            with tqdm(total=len(articles), disable=not show_progress) as pbar:
                for article in articles:
                    try:
                        # Collect comments
                        result = await self.comment_collector.collect(
                            article_url=article.naver_link,
                            is_test=True
                        )
                        
                        comments = result.get('comments', [])
                        
                        # Store comments
                        if comments:
                            async with AsyncStorageSessionLocal() as session:
                                await AsyncDatabaseOperations.batch_create_comments(
                                    session=session,
                                    comments_data=comments,
                                    article_id=article.id
                                )
                                await session.commit()
                                
                        total_comments += len(comments)
                        
                        # Human-like delay
                        delay = random.uniform(delay_range[0], delay_range[1])
                        await asyncio.sleep(delay)
                        
                    except Exception as e:
                        logger.error(f"Error collecting comments for article {article.id}: {e}")
                    
                    pbar.update(1)
            
            return {
                'success': True,
                'message': f'Collected {total_comments} comments from {len(articles)} articles',
                'total_comments': total_comments,
                'processed_articles': len(articles)
            }
            
        except Exception as e:
            logger.error(f"Error in comment collection: {e}")
            return {
                'success': False,
                'message': str(e)
            }

def validate_date(ctx, param, value):
    """Validate date format"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=KST)
    except ValueError:
        raise click.BadParameter('Date must be in YYYY-MM-DD format')

@click.group()
def cli():
    """Interactive news collection test script"""
    pass

@cli.command()
@click.option('--keyword', prompt='Search keyword', help='Keyword to search for')
@click.option('--method', type=click.Choice(['SEARCH', 'API']), prompt='Collection method', help='Collection method')
@click.option('--start-date', prompt='Start date (YYYY-MM-DD)', callback=validate_date, help='Start date')
@click.option('--end-date', prompt='End date (YYYY-MM-DD)', callback=validate_date, help='End date')
@click.option('--min-delay', default=1, help='Minimum delay between requests (seconds)')
@click.option('--max-delay', default=3, help='Maximum delay between requests (seconds)')
@click.option('--batch-size', default=10, help='Number of articles per batch')
@click.option('--auto', is_flag=True, help='Run in automatic mode without confirmation')
def metadata(keyword, method, start_date, end_date, min_delay, max_delay, batch_size, auto):
    """Collect metadata interactively"""
    async def run():
        tester = InteractiveNewsTester()
        try:
            if not auto:
                click.echo(f"\nCollection parameters:")
                click.echo(f"Keyword: {keyword}")
                click.echo(f"Method: {method}")
                click.echo(f"Date range: {start_date.date()} to {end_date.date()}")
                click.echo(f"Delay range: {min_delay}-{max_delay} seconds")
                click.echo(f"Batch size: {batch_size}")
                
                if not click.confirm('\nProceed with collection?'):
                    return
            
            result = await tester.collect_metadata(
                keyword=keyword,
                method=method,
                start_date=start_date,
                end_date=end_date,
                delay_range=(min_delay, max_delay),
                batch_size=batch_size
            )
            
            click.echo(f"\n{result['message']}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await tester.cleanup()
    
    asyncio.run(run())

@cli.command()
@click.option('--keyword', prompt='Search keyword', help='Keyword to search for')
@click.option('--start-date', prompt='Start date (YYYY-MM-DD)', callback=validate_date, help='Start date')
@click.option('--end-date', prompt='End date (YYYY-MM-DD)', callback=validate_date, help='End date')
@click.option('--min-delay', default=2, help='Minimum delay between requests (seconds)')
@click.option('--max-delay', default=5, help='Maximum delay between requests (seconds)')
@click.option('--auto', is_flag=True, help='Run in automatic mode without confirmation')
def comments(keyword, start_date, end_date, min_delay, max_delay, auto):
    """Collect comments interactively"""
    async def run():
        tester = InteractiveNewsTester()
        try:
            if not auto:
                click.echo(f"\nCollection parameters:")
                click.echo(f"Keyword: {keyword}")
                click.echo(f"Date range: {start_date.date()} to {end_date.date()}")
                click.echo(f"Delay range: {min_delay}-{max_delay} seconds")
                
                if not click.confirm('\nProceed with collection?'):
                    return
            
            result = await tester.collect_comments(
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                delay_range=(min_delay, max_delay)
            )
            
            click.echo(f"\n{result['message']}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await tester.cleanup()
    
    asyncio.run(run())

if __name__ == '__main__':
    cli()
