import os
import sys
import asyncio
import logging
from datetime import datetime
import pytz
import asyncpg
from typing import List, Dict, Any, Optional

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_collector.collectors.api_metadata_collector import APIMetadataCollector
from news_collector.collectors.comments import CommentCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class BatchCollector:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'password',
            'database': 'news_db'
        }
        self.pool = None

    async def init_db(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(**self.db_config)

    async def close_db(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        try:
            # Parse ISO format timestamp string
            # Example: 2024-12-24T07:36:00+0900
            return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
            return None

    async def store_article(self, article: Dict[str, Any]) -> int:
        """Store article in database and return its ID"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO articles (
                    title, naver_link, original_link, description, 
                    publisher, published_at, collected_at, 
                    is_naver_news, collection_method
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (naver_link) DO UPDATE SET
                    title = EXCLUDED.title,
                    original_link = EXCLUDED.original_link,
                    description = EXCLUDED.description,
                    publisher = EXCLUDED.publisher,
                    published_at = EXCLUDED.published_at,
                    collected_at = EXCLUDED.collected_at,
                    is_naver_news = EXCLUDED.is_naver_news,
                    collection_method = EXCLUDED.collection_method
                RETURNING id;
            """
            # Parse timestamps
            published_at = self._parse_timestamp(article['published_at'])
            collected_at = self._parse_timestamp(article['collected_at'])
            
            return await conn.fetchval(
                query,
                article['title'],
                article['naver_link'],
                article['original_link'],
                article['description'],
                article['publisher'],
                published_at,
                collected_at,
                article['is_naver_news'],
                article['collection_method']
            )

    async def store_comment_stats(self, article_id: int, stats: Dict[str, Any], collected_at: str):
        """Store comment statistics in database"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO comment_stats (
                    article_id, current_count, user_deleted_count, admin_deleted_count,
                    male_ratio, female_ratio, age_10s, age_20s, age_30s,
                    age_40s, age_50s, age_60s_above, collected_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (article_id) DO UPDATE SET
                    current_count = EXCLUDED.current_count,
                    user_deleted_count = EXCLUDED.user_deleted_count,
                    admin_deleted_count = EXCLUDED.admin_deleted_count,
                    male_ratio = EXCLUDED.male_ratio,
                    female_ratio = EXCLUDED.female_ratio,
                    age_10s = EXCLUDED.age_10s,
                    age_20s = EXCLUDED.age_20s,
                    age_30s = EXCLUDED.age_30s,
                    age_40s = EXCLUDED.age_40s,
                    age_50s = EXCLUDED.age_50s,
                    age_60s_above = EXCLUDED.age_60s_above,
                    collected_at = EXCLUDED.collected_at;
            """
            
            collected_at_dt = self._parse_timestamp(collected_at)
            
            await conn.execute(
                query,
                article_id,
                stats['current_count'],
                stats['user_deleted_count'],
                stats['admin_deleted_count'],
                stats['gender_ratio']['male'],
                stats['gender_ratio']['female'],
                stats['age_distribution']['10s'],
                stats['age_distribution']['20s'],
                stats['age_distribution']['30s'],
                stats['age_distribution']['40s'],
                stats['age_distribution']['50s'],
                stats['age_distribution']['60s_above'],
                collected_at_dt
            )

    async def store_comments(self, article_id: int, comments_data: Dict[str, Any]):
        """Store comments and stats in database"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Store comments
                for comment in comments_data['comments']:
                    query = """
                        INSERT INTO comments (
                            comment_no, article_id, parent_comment_no, content,
                            username, profile_url, timestamp, likes, dislikes,
                            reply_count, is_reply, is_deleted, delete_type, collected_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (comment_no) DO UPDATE SET
                            content = EXCLUDED.content,
                            likes = EXCLUDED.likes,
                            dislikes = EXCLUDED.dislikes,
                            reply_count = EXCLUDED.reply_count,
                            is_deleted = EXCLUDED.is_deleted,
                            delete_type = EXCLUDED.delete_type,
                            collected_at = EXCLUDED.collected_at;
                    """
                    # Parse timestamps
                    timestamp = self._parse_timestamp(comment['timestamp'])
                    collected_at = self._parse_timestamp(comment['collected_at'])
                    
                    await conn.execute(
                        query,
                        comment['comment_no'],
                        article_id,
                        comment['parent_comment_no'],
                        comment['content'],
                        comment['username'],
                        comment['profile_url'],
                        timestamp,
                        comment['likes'],
                        comment['dislikes'],
                        comment['reply_count'],
                        comment['is_reply'],
                        comment['is_deleted'],
                        comment['delete_type'],
                        collected_at
                    )
                
                # Store stats
                if 'stats' in comments_data:
                    await self.store_comment_stats(
                        article_id,
                        comments_data['stats'],
                        comments_data['collected_at']
                    )

    async def collect_and_store(self, keyword: str, max_articles: int = 10):
        """Collect articles and comments, then store in database"""
        try:
            await self.init_db()
            
            # Collect articles
            async with APIMetadataCollector() as collector:
                logger.info(f"Collecting articles for keyword: {keyword}")
                articles_data = await collector.collect(
                    keyword=keyword,
                    max_articles=max_articles
                )
                
                if not articles_data['items']:
                    logger.warning("No articles found")
                    return
                
                logger.info(f"Found {len(articles_data['items'])} articles")
                
                # Store articles and collect comments
                async with CommentCollector() as comment_collector:
                    for article in articles_data['items']:
                        # Store article
                        article_id = await self.store_article(article)
                        logger.info(f"Stored article {article_id}: {article['title']}")
                        
                        # Collect and store comments
                        logger.info(f"Collecting comments for article {article_id}")
                        comments_data = await comment_collector.collect(
                            article_url=article['naver_link'],
                            include_stats=True
                        )
                        
                        if comments_data['collection_status'] == 'success':
                            if comments_data['comments']:
                                await self.store_comments(article_id, comments_data)
                                logger.info(f"Stored {len(comments_data['comments'])} comments for article {article_id}")
                            else:
                                logger.info(f"No comments found for article {article_id}")
                        else:
                            logger.error(f"Failed to collect comments for article {article_id}: {comments_data.get('error', 'Unknown error')}")
                            
        except Exception as e:
            logger.error(f"Error in collect_and_store: {e}")
            raise
        finally:
            await self.close_db()

async def main():
    collector = BatchCollector()
    keyword = input("Enter search keyword: ")
    max_articles = int(input("Enter maximum number of articles to collect (default 10): ") or 10)
    
    try:
        await collector.collect_and_store(keyword, max_articles)
        logger.info("Collection completed successfully")
    except Exception as e:
        logger.error(f"Collection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
