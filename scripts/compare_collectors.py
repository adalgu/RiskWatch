import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_collector.collectors.api_metadata_collector import APIMetadataCollector
from news_collector.collectors.search_metadata_collector import SearchMetadataCollector

async def collect_and_compare(keyword: str = "카카오모빌리티", max_articles: int = 10):
    """Collect articles using both collectors and compare results."""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize collectors
    api_config = {
        'client_id': os.getenv('NAVER_CLIENT_ID'),
        'client_secret': os.getenv('NAVER_CLIENT_SECRET')
    }
    api_collector = APIMetadataCollector(api_config)
    search_collector = SearchMetadataCollector()
    
    try:
        print(f"\nCollecting {max_articles} recent articles for keyword: {keyword}")
        print("-" * 80)
        
        # Collect using API
        print("\n[API Collector]")
        async with api_collector:
            api_result = await api_collector.collect(
                keyword=keyword,
                max_articles=max_articles
            )
        
        # Collect using Search (with today's date)
        print("\n[Search Collector]")
        today = datetime.now().strftime('%Y.%m.%d')
        async with search_collector:
            search_result = await search_collector.collect(
                keyword=keyword,
                date=today,
                max_articles=max_articles
            )
        
        # Compare results
        print("\nResults Comparison:")
        print("-" * 80)
        print(f"API Total: {len(api_result['items'])}")
        print(f"Search Total: {len(search_result['items'])}")
        
        # Compare first article from each
        if api_result['items'] and search_result['items']:
            print("\nFirst Article Comparison:")
            print("\nAPI Article:")
            print(json.dumps(api_result['items'][0], indent=2, ensure_ascii=False))
            print("\nSearch Article:")
            print(json.dumps(search_result['items'][0], indent=2, ensure_ascii=False))
            
            # Compare fields
            print("\nField Comparison:")
            api_fields = set(api_result['items'][0].keys())
            search_fields = set(search_result['items'][0].keys())
            print(f"API fields: {sorted(api_fields)}")
            print(f"Search fields: {sorted(search_fields)}")
            
            if api_fields != search_fields:
                print("\nField differences:")
                print(f"Only in API: {api_fields - search_fields}")
                print(f"Only in Search: {search_fields - api_fields}")
            else:
                print("\nBoth collectors have identical fields!")
                
    except Exception as e:
        print(f"Error during collection: {e}")

if __name__ == "__main__":
    asyncio.run(collect_and_compare())
