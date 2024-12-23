"""
Complete example script for using NaverNewsCollector.
Includes all necessary setup and configuration.
"""
import asyncio
import os
from datetime import datetime
import pandas as pd

# Add project root to Python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_collector.collectors.simple.naver import NaverNewsCollector
from news_collector.collectors.simple.storage import PandasStorage

async def main():
    """
    Simple example of collecting Naver news articles.
    """
    try:
        # Create collector with pandas storage
        collector = NaverNewsCollector(
            storage=PandasStorage(return_df=True),
            # WebDriver configuration
            config={
                'browser_timeout': 10,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            headless=True  # Run browser in headless mode
        )
        
        # Get today's date
        date = datetime.now().strftime("%Y.%m.%d")
        date = "2023.12.01"
        print(f"\nCollecting news for {date}")
        
        # For quick testing, collect only 5 articles
        articles = await collector.collect_news(
            keyword="윤석열",
            date=date,
            max_articles=52  # Limit articles for testing
        )
        
        # Print results
        print(f"\nCollected {len(articles)} articles:")
        for article in articles:
            print(f"\nTitle: {article['title']}")
            print(f"Press: {article['press']}")
            print(f"Date: {article['published_at']}")
            print(f"Link: {article['link']}")
            
        # Access as pandas DataFrame
        if collector.storage.df is not None:
            print("\nPandas DataFrame:")
            pd.set_option('display.max_columns', None)
            print(collector.storage.df)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
