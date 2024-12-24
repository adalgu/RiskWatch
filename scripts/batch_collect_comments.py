"""
Batch comment collection script that first collects articles via API and then collects their comments.
"""

import asyncio
import json
from datetime import datetime, timedelta
import pytz
from news_collector.collectors.api_metadata_collector import APIMetadataCollector
from news_collector.collectors.comments import CommentCollector
from news_collector.collectors.utils.date import DateUtils

KST = pytz.timezone('Asia/Seoul')

async def main():
    # Initialize collectors
    api_collector = APIMetadataCollector()
    comment_collector = CommentCollector()

    try:
        print("\n=== Collecting Articles ===")
        # Get yesterday's date range in KST
        end_date = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
        
        # Format dates for API
        start_date_str = DateUtils.format_date(start_date, '%Y%m%d')
        end_date_str = DateUtils.format_date(end_date, '%Y%m%d')
        
        # Collect articles via API with max_articles=10, only Naver News
        # Using "이재명" as keyword since it tends to have more comments
        result = await api_collector.collect(
            keyword="이재명",  # Changed keyword to get articles with more engagement
            max_articles=10,
            include_other_domains=False
        )
        
        if not result.get('items'):
            print("No articles found")
            return
            
        # Filter for Naver News articles only
        naver_articles = [article for article in result['items'] if article.get('is_naver_news')]
        print(f"Found {len(naver_articles)} Naver News articles")
        
        if not naver_articles:
            print("No Naver News articles found")
            return
        
        print("\n=== Collecting Comments ===")
        # Collect comments for Naver articles
        comments_result = await comment_collector.collect(
            articles=naver_articles,
            include_stats=True
        )
        
        # Save results
        timestamp = datetime.now(KST).strftime('%Y%m%d_%H%M%S')
        output_file = f'test_comments_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comments_result, f, ensure_ascii=False, indent=2)
            
        print("\n=== Collection Summary ===")
        print(f"Total articles processed: {comments_result['total_articles']}")
        print(f"Successful collections: {comments_result['successful_collections']}")
        print(f"Articles with comments: {len([r for r in comments_result['items'] if r.get('comments')])}")
        total_comments = sum(len(r.get('comments', [])) for r in comments_result['items'])
        print(f"Total comments collected: {total_comments}")
        print(f"\nResults saved to: {output_file}")

    finally:
        # Clean up both collectors
        await api_collector.cleanup()
        await comment_collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
