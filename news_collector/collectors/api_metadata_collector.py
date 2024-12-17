import os
import logging
import asyncio
import pytz
from typing import List, Dict, Any, Optional
from urllib.parse import quote
import aiohttp
from datetime import datetime

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.text import TextUtils
from .utils.url import UrlUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class APIMetadataCollector(BaseCollector):
    """API 기반 메타데이터 수집기"""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize collector with configuration."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.publisher_mapping = {}
        
        # Initialize configuration
        self._init_config()
        # Load publisher mapping
        self._load_publisher_mapping()

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        logger.info("[APIMetadata] Initializing configuration...")
        self.client_id = self.get_config(
            'client_id') or os.getenv('NAVER_CLIENT_ID')
        self.client_secret = self.get_config(
            'client_secret') or os.getenv('NAVER_CLIENT_SECRET')
        self.max_retries = self.get_config('max_retries', 3)
        self.retry_delay = self.get_config('retry_delay', 1)
        self.max_display = self.get_config('max_display', 100)
        self.max_start = self.get_config('max_start', 1000)
        logger.info("[APIMetadata] Configuration initialized")

    def _load_publisher_mapping(self) -> None:
        """Load publisher domain mapping from JSON file."""
        try:
            mapping_path = os.path.join(os.path.dirname(__file__),
                                        'utils',
                                        'publisher_domain_mapping.json')
            with open(mapping_path, 'r', encoding='utf-8') as f:
                self.publisher_mapping = json.load(f)['mapping']
            logger.info("[APIMetadata] Successfully loaded publisher mapping")
        except Exception as e:
            logger.error(f"[APIMetadata] Failed to load publisher mapping: {e}")
            self.publisher_mapping = {}

    def _get_publisher_from_domain(self, domain: str) -> Optional[str]:
        """Get publisher name from domain using mapping."""
        domain = domain.replace('www.', '')
        return self.publisher_mapping.get(domain)

    async def init_session(self) -> None:
        """Initialize the aiohttp ClientSession."""
        logger.info("[APIMetadata] Initializing session...")
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("[APIMetadata] Session initialized")

    async def collect(self, **kwargs) -> List[Dict[str, Any]]:
        """API 기반 메타데이터 수집"""
        logger.info("[APIMetadata] Starting API collection...")
        await self.init_session()
        
        keyword = kwargs.get('keyword')
        if not keyword:
            raise ValueError("Keyword is required for API collection")

        max_articles = min(kwargs.get('max_articles', self.max_start), self.max_start)
        include_other_domains = kwargs.get('include_other_domains', True)

        if not self.client_id or not self.client_secret:
            raise ValueError("API credentials not configured")

        all_articles = []
        start = 1

        initial_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(keyword)}&display=1&start=1&sort=date"
        logger.info(f"[APIMetadata] Making initial API request to: {initial_url}")
        result = await self._make_api_request(initial_url)

        if not result:
            logger.warning("[APIMetadata] Initial API request returned no results")
            return all_articles

        total = int(result.get('total', 0))
        available = min(total, self.max_start)

        logger.info(
            f"[APIMetadata] API Collection - Total available: {total}, Will collect: {min(available, max_articles)}")

        while start <= min(self.max_start, max_articles):
            url = f"https://openapi.naver.com/v1/search/news.json?query={quote(keyword)}&display={self.max_display}&start={start}&sort=date"
            logger.info(f"[APIMetadata] Making API request to: {url}")
            result = await self._make_api_request(url)

            if not result or 'items' not in result:
                logger.warning("[APIMetadata] API request returned no items")
                break

            articles = await self._process_api_items(result['items'], include_other_domains)
            if articles:
                all_articles.extend(articles)
                logger.info(f"[APIMetadata] Collected {len(articles)} articles (Total: {len(all_articles)})")
                if len(all_articles) >= max_articles:
                    all_articles = all_articles[:max_articles]
                    break

            if len(result['items']) < self.max_display:
                break

            start += self.max_display
            await asyncio.sleep(0.1)

        logger.info(f"[APIMetadata] API collection completed. Total articles: {len(all_articles)}")
        return all_articles

    async def _make_api_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make API request with retries using aiohttp."""
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"[APIMetadata] API request attempt {attempt + 1}/{self.max_retries}")
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("[APIMetadata] API request successful")
                        return result
                    else:
                        logger.warning(f"[APIMetadata] API request failed with status {response.status}")
            except Exception as e:
                logger.error(f"[APIMetadata] API request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        return None

    async def _process_api_items(self, items: List[Dict], include_other_domains: bool) -> List[Dict]:
        """Process API response items."""
        processed = []
        for item in items:
            try:
                is_naver_news = 'news.naver.com' in item['link']
                if not is_naver_news and not include_other_domains:
                    continue

                domain = UrlUtils.extract_domain(item.get('originallink', ''))
                publisher = self._get_publisher_from_domain(domain)

                published_at_dt = DateUtils.parse_date(item['pubDate'], timezone=KST)
                published_at = DateUtils.format_date(published_at_dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST) if published_at_dt else ''
                published_date = DateUtils.format_date(published_at_dt, '%Y.%m.%d', timezone=KST) if published_at_dt else ''

                article = {
                    'title': TextUtils.clean_html(item['title']),
                    'naver_link': item['link'],
                    'original_link': item.get('originallink', ''),
                    'description': TextUtils.clean_html(item['description']),
                    'publisher': publisher or '',
                    'publisher_domain': domain,
                    'published_at': published_at,
                    'published_date': published_date,
                    'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
                    'is_naver_news': is_naver_news
                }
                processed.append(article)
            except Exception as e:
                logger.error(f"[APIMetadata] Item processing error: {e}")
                continue
        return processed

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info("[APIMetadata] Starting cleanup...")
            if self.session:
                await self.session.close()
            logger.info("[APIMetadata] Cleanup completed")
        except Exception as e:
            logger.error(f"[APIMetadata] Error during cleanup: {e}")

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()
