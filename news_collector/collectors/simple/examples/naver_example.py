"""
Usage examples for NaverNewsCollector with different storage options.
"""
import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any

from ..storage import PandasStorage, CSVStorage, SQLiteStorage
from ..naver import NaverNewsCollector

async def collect_for_date_range(
    collector: NaverNewsCollector,
    keyword: str,
    start_date: datetime,
    end_date: datetime,
    max_articles: int = 10
) -> List[Dict[str, Any]]:
    """
    Collect news articles for a date range.
    
    Args:
        collector: Initialized NaverNewsCollector
        keyword: Search keyword
        start_date: Start date
        end_date: End date
        max_articles: Maximum articles per day
        
    Returns:
        List of collected articles
    """
    all_articles = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y.%m.%d")
        print(f"\nCollecting articles for {date_str}")
        
        articles = await collector.collect_news(
            keyword=keyword,
            date=date_str,
            max_articles=max_articles
        )
        
        print(f"Found {len(articles)} articles")
        all_articles.extend(articles)
        
        current_date += timedelta(days=1)
        # Add delay between dates
        await asyncio.sleep(2)
        
    return all_articles

async def pandas_example():
    """Example using pandas storage."""
    print("\n=== Pandas Storage Example ===")
    
    # Create collector with pandas storage
    collector = NaverNewsCollector.with_pandas(return_df=True)
    
    # Collect last 3 days of news
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    articles = await collect_for_date_range(
        collector,
        keyword="파이썬",
        start_date=start_date,
        end_date=end_date,
        max_articles=5
    )
    
    # Access pandas DataFrame
    if articles and collector.storage.df is not None:
        print("\nCollected articles DataFrame:")
        print(collector.storage.df[['title', 'press', 'published_at']])

async def csv_example():
    """Example using CSV storage."""
    print("\n=== CSV Storage Example ===")
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    # Create collector with CSV storage
    collector = NaverNewsCollector.with_csv('output/naver_news.csv')
    
    # Collect today's news
    today = datetime.now()
    
    await collect_for_date_range(
        collector,
        keyword="인공지능",
        start_date=today,
        end_date=today,
        max_articles=5
    )
    
    print("\nArticles saved to output/naver_news.csv")

async def sqlite_example():
    """Example using SQLite storage."""
    print("\n=== SQLite Storage Example ===")
    
    # Create collector with SQLite storage
    collector = NaverNewsCollector.with_sqlite(
        'output/news.db',
        'naver_news'
    )
    
    # Collect yesterday's news
    yesterday = datetime.now() - timedelta(days=1)
    
    await collect_for_date_range(
        collector,
        keyword="빅데이터",
        start_date=yesterday,
        end_date=yesterday,
        max_articles=5
    )
    
    print("\nArticles saved to SQLite database output/news.db")

async def main():
    """Run all examples."""
    try:
        await pandas_example()
    except Exception as e:
        print(f"Pandas example error: {e}")
        
    try:
        await csv_example()
    except Exception as e:
        print(f"CSV example error: {e}")
        
    try:
        await sqlite_example()
    except Exception as e:
        print(f"SQLite example error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
