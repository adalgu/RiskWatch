import os
import sys
import asyncio
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_collector.collectors.api_metadata_collector import APIMetadataCollector
from news_collector.collectors.web_metadata_collector import WebMetadataCollector

async def collect_and_compare(keyword: str = "카카오모빌리티", max_articles: int = 10):
    """Collect articles using both collectors and display results in DataFrames."""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize collectors
    api_config = {
        'client_id': os.getenv('NAVER_CLIENT_ID'),
        'client_secret': os.getenv('NAVER_CLIENT_SECRET')
    }
    api_collector = APIMetadataCollector(api_config)
    web_collector = WebMetadataCollector()
    
    try:
        print(f"\nCollecting {max_articles} recent articles for keyword: {keyword}")
        print("-" * 80)
        
        # Collect using Web Collector first
        print("\n[Web Collector]")
        today = datetime.now().strftime('%Y.%m.%d')
        async with web_collector:
            web_result = await web_collector.collect(
                keyword=keyword,
                date=today,
                max_articles=max_articles
            )
        
        # Then collect using API
        print("\n[API Collector]")
        async with api_collector:
            api_result = await api_collector.collect(
                keyword=keyword,
                max_articles=max_articles
            )
        
        # Convert to DataFrames
        api_df = pd.DataFrame(api_result['items'])
        web_df = pd.DataFrame(web_result['items'])
        
        # Display collection info
        print(f"\nWeb collection date: {web_result['date']}")
        print(f"API total available articles: {api_result['total']}")
        
        # Display results
        print("\nAPI Collector Results:")
        print("-" * 80)
        print(api_df)
        
        print("\nWeb Collector Results:")
        print("-" * 80)
        print(web_df)
        
    except Exception as e:
        print(f"Error during collection: {e}")

if __name__ == "__main__":
    asyncio.run(collect_and_compare())
