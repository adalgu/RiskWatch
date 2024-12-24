"""
Test script to verify max_articles parameter in APIMetadataCollector
"""

import asyncio
import json
from news_collector.collectors.api_metadata_collector import APIMetadataCollector

async def main():
    collector = APIMetadataCollector()
    
    try:
        print("\n=== Testing API Collection with max_articles=10 ===")
        result = await collector.collect(
            keyword="코스피",
            max_articles=10,
            include_other_domains=True
        )
        
        print(f"\nTotal articles available: {result['total']}")
        print(f"Articles collected: {len(result['items'])}")
        
        # Save results for inspection
        output_file = 'test_api_max_articles.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"\nResults saved to: {output_file}")
        
    finally:
        await collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
