import os
import json
import urllib.request
import logging
import asyncio
import argparse
import re
import pytz
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse, quote
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.text import TextUtils
from .utils.url import UrlUtils
from .utils.webdriver_utils import WebDriverUtils
from ..producer import Producer  # Import the Producer class

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class MetadataCollector(BaseCollector):
    """
    통합 메타데이터 수집기.
    API와 웹 검색 방식을 모두 지원합니다.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize collector with configuration."""
        super().__init__(config)
        self._init_config()
        self.proxy = self.get_config('proxy')
        self.user_agent = self.get_config('user_agent')
        self.driver_utils = WebDriverUtils(
            headless=True,
            proxy=self.proxy,
            user_agent=self.user_agent,
            use_remote=True
        )
        self.driver = None
        self.session: Optional[aiohttp.ClientSession] = None  # Initialize as None
        self._load_publisher_mapping()
        
        # Initialize Producer
        self.producer = Producer()
        self.queue_name = 'metadata_queue'

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.client_id = self.get_config(
            'client_id') or os.getenv('NAVER_CLIENT_ID')
        self.client_secret = self.get_config(
            'client_secret') or os.getenv('NAVER_CLIENT_SECRET')
        self.max_retries = self.get_config('max_retries', 3)
        self.retry_delay = self.get_config('retry_delay', 1)
        self.max_display = self.get_config('max_display', 100)
        self.max_start = self.get_config('max_start', 1000)
        self.browser_timeout = self.get_config('browser_timeout', 10)
        self.scroll_pause = self.get_config('scroll_pause', 1.0)

    def _load_publisher_mapping(self) -> None:
        """Load publisher domain mapping from JSON file."""
        try:
            mapping_path = os.path.join(os.path.dirname(__file__),
                                        'utils',
                                        'publisher_domain_mapping.json')
            with open(mapping_path, 'r', encoding='utf-8') as f:
                self.publisher_mapping = json.load(f)['mapping']
        except Exception as e:
            logger.error(f"Failed to load publisher mapping: {e}")
            self.publisher_mapping = {}

    def _get_publisher_from_domain(self, domain: str) -> Optional[str]:
        """Get publisher name from domain using mapping."""
        # Remove 'www.' prefix if present
        domain = domain.replace('www.', '')
        return self.publisher_mapping.get(domain)

    async def init_session(self) -> None:
        """Initialize the aiohttp ClientSession."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def publish_message(self, message: Dict[str, Any]) -> None:
        """Publish message to RabbitMQ using Producer"""
        await self.producer.publish(
            message=message,
            queue_name=self.queue_name
        )
        logger.info(f"Published message to RabbitMQ queue '{self.queue_name}'")

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect metadata using specified method."""
        await self.init_session()  # Ensure session is initialized
        method = kwargs.get('method', 'API').upper()
        is_test = kwargs.get('is_test', True)
        self.log_collection_start(kwargs)

        try:
            if method == 'API':
                articles = await self.collect_from_api(**kwargs)
                is_api = True
            elif method == 'SEARCH':
                articles = await self.collect_from_search(**kwargs)
                is_api = False
            else:
                raise ValueError(f"Invalid collection method: {method}")

            # Add is_test and is_api_collection flags to each article
            for article in articles:
                article['is_test'] = is_test
                article['is_api_collection'] = is_api

            result = {
                'articles': articles,
                'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
                'metadata': {
                    'method': method,
                    'total_collected': len(articles),
                    'keyword': kwargs.get('keyword'),
                    'is_test': is_test,
                    'is_api_collection': is_api
                }
            }

            if await self.validate_async(result):
                self.log_collection_end(True, {'article_count': len(articles)})
                # Publish to RabbitMQ using Producer
                await self.publish_message(result)
                return result
            else:
                raise ValueError("Validation failed for collected data")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def collect_from_api(self, **kwargs) -> List[Dict[str, Any]]:
        """API 기반 메타데이터 수집"""
        keyword = kwargs.get('keyword')
        if not keyword:
            raise ValueError("Keyword is required for API collection")

        max_articles = kwargs.get('max_articles', self.max_start)
        include_other_domains = kwargs.get('include_other_domains', True)

        if not self.client_id or not self.client_secret:
            raise ValueError("API credentials not configured")

        all_articles = []
        start = 1

        initial_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(keyword)}&display=1&start=1&sort=date"
        result = await self._make_api_request(initial_url)

        if not result:
            return all_articles

        total = int(result.get('total', 0))
        available = min(total, self.max_start)

        logger.info(
            f"API Collection - Total available: {total}, Will collect: {min(available, max_articles)}")

        while start <= min(self.max_start, max_articles):
            url = f"https://openapi.naver.com/v1/search/news.json?query={quote(keyword)}&display={self.max_display}&start={start}&sort=date"
            result = await self._make_api_request(url)

            if not result or 'items' not in result:
                break

            articles = await self._process_api_items(result['items'], include_other_domains)
            if articles:
                all_articles.extend(articles)
                if len(all_articles) >= max_articles:
                    all_articles = all_articles[:max_articles]
                    break

            if len(result['items']) < self.max_display:
                break

            start += self.max_display
            await asyncio.sleep(0.1)

        return all_articles

    async def collect_from_search(self, **kwargs) -> List[Dict[str, Any]]:
        """검색 기반 메타데이터 수집"""
        try:
            keyword = kwargs.get('keyword')
            if not keyword:
                raise ValueError("Keyword is required for search collection")

            max_articles = kwargs.get('max_articles')

            # Parse date strings to datetime objects
            start_date = DateUtils.parse_date(kwargs.get('start_date'), timezone=KST)
            end_date = DateUtils.parse_date(kwargs.get('end_date'), timezone=KST)

            # 5주 전 날짜 계산
            now = datetime.now(KST)
            five_weeks_ago = now - timedelta(weeks=5)

            # 검색 날짜가 5주 이내인지 확인
            is_within_five_weeks = False
            if start_date and end_date > five_weeks_ago:
                is_within_five_weeks = True

            all_articles = []

            if is_within_five_weeks:
                # 5주 이내 검색: 하루 단위로 수집 (최신순)
                current_date = end_date if end_date else now
                start_date = start_date if start_date else five_weeks_ago

                while current_date >= start_date:
                    logger.info(
                        f"Collecting articles for date: {DateUtils.format_date(current_date, '%Y-%m-%d', timezone=KST)}")

                    # 하루 단위로 검색
                    articles = await self._collect_single_day(
                        keyword=keyword,
                        date=current_date,
                        max_articles=max_articles
                    )
                    all_articles.extend(articles)

                    # 이전 날짜로 이동
                    current_date -= timedelta(days=1)

                    # 최대 기사 수 체크
                    if max_articles and len(all_articles) >= max_articles:
                        all_articles = all_articles[:max_articles]
                        break

            else:
                # 5주 이전 검색: 일반적인 방식으로 수집
                self.driver = await self._initialize_browser()
                search_url = self._build_search_url(
                    keyword, start_date, end_date)
                logger.info(f"Accessing search URL: {search_url}")

                await self._run_in_executor(self.driver.get, search_url)
                await asyncio.sleep(2)

                try:
                    await self._run_in_executor(
                        lambda: self.driver_utils.wait_for_element(
                            By.CLASS_NAME, "list_news", self.browser_timeout)
                    )
                except TimeoutException:
                    logger.error("News list not found")
                    return []

                articles = await self._collect_search_articles(max_articles)
                all_articles.extend(articles)

            return all_articles

        finally:
            await self._close_browser()

    async def _collect_single_day(self, keyword: str, date: datetime, max_articles: Optional[int] = None) -> List[Dict[str, Any]]:
        """하루 단위로 기사 수집"""
        self.driver = await self._initialize_browser()

        # 시작일과 종료일을 동일하게 설정
        search_url = self._build_search_url(
            keyword,
            start_date=date,
            end_date=date
        )

        await self._run_in_executor(self.driver.get, search_url)
        await asyncio.sleep(2)

        try:
            await self._run_in_executor(
                lambda: self.driver_utils.wait_for_element(
                    By.CLASS_NAME, "list_news", self.browser_timeout
                )
            )
        except TimeoutException:
            logger.error(
                f"News list not found for date: {DateUtils.format_date(date, '%Y-%m-%d', timezone=KST)}")
            return []

        articles = await self._collect_search_articles(max_articles, date)
        await self._close_browser()
        return articles

    def _build_search_url(self,
                          keyword: str,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> str:
        """검색 URL 생성"""
        params = {
            'where': 'news',
            'query': keyword,
            'sort': '1',  # 최신순 정렬
            'pd': '3',    # 기간 검색 활성화
            'start': '1',
            'refresh_start': '0'
        }

        if start_date and end_date:
            params.update({
                'ds': DateUtils.format_date(start_date, '%Y.%m.%d', timezone=KST),
                'de': DateUtils.format_date(end_date, '%Y.%m.%d', timezone=KST)
            })
        else:
            end_date = datetime.now(KST)
            start_date = end_date - timedelta(days=90)
            params.update({
                'ds': DateUtils.format_date(start_date, '%Y.%m.%d', timezone=KST),
                'de': DateUtils.format_date(end_date, '%Y.%m.%d', timezone=KST)
            })

        query_string = urllib.parse.urlencode(params)
        return f"https://search.naver.com/search.naver?{query_string}"

    async def _collect_search_articles(self,
                                       max_articles: Optional[int] = None,
                                       search_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """스크롤하며 기사 수집"""
        last_count = 0
        no_new_articles_count = 0
        max_retries = 2
        articles = []

        while no_new_articles_count < max_retries:
            current_count = await self._get_current_article_count()

            if max_articles and current_count >= max_articles:
                break

            if current_count > last_count:
                logger.info(
                    f"Found {current_count - last_count} new articles (Total: {current_count})")
                last_count = current_count
                no_new_articles_count = 0
            else:
                no_new_articles_count += 1

            await self._scroll_to_bottom()
            await asyncio.sleep(self.scroll_pause)

        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        article_elements = soup.select('ul.list_news > li.bx')

        for article in article_elements[:max_articles]:
            try:
                article_data = await self._extract_article_data(article, search_date)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                logger.error(f"Error extracting article data: {e}")

        return articles

    async def _get_current_article_count(self) -> int:
        """현재 로드된 기사 수 반환"""
        articles = self.driver.find_elements(
            By.CSS_SELECTOR, 'ul.list_news > li.bx')
        return len(articles)

    async def _scroll_to_bottom(self) -> None:
        """페이지 맨 아래로 스크롤"""
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

    async def _extract_article_data(self, article_elem: BeautifulSoup, search_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """기사 요소에서 데이터 추출"""
        try:
            # 제목과 링크
            title_elem = article_elem.find(
                'a', {'class': ['news_tit', 'title_link']})
            if not title_elem:
                return None

            title = TextUtils.clean_html(title_elem.get_text(strip=True))
            original_link = title_elem['href']

            # 네이버 뉴스 링크
            naver_link = None
            for link_class in ['info', 'news_source']:
                link_elem = article_elem.find(
                    'a', {'class': link_class}, string='네이버뉴스')
                if link_elem and link_elem.has_attr('href'):
                    naver_link = link_elem['href']
                    break

            naver_link = naver_link or original_link

            # 설명
            desc_elem = article_elem.find('div', {'class': 'news_dsc'})
            description = TextUtils.clean_html(desc_elem.get_text(strip=True)) if desc_elem else ''

            # 언론사
            press_elem = article_elem.find('a', {'class': 'press'})
            if press_elem:
                for i_tag in press_elem.find_all('i', class_='spnew ico_pick'):
                    i_tag.extract()
                publisher = TextUtils.clean_html(press_elem.get_text(strip=True))
            else:
                publisher = ''

            # 도메인 추출
            publisher_domain = UrlUtils.extract_domain(original_link)

            # 날짜 정보 추출
            published_date = None
            if search_date:
                published_date = DateUtils.format_date(search_date, '%Y.%m.%d', timezone=KST)
                published_at = DateUtils.format_date(search_date, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
            else:
                # 5주 이전 기사는 태그에서 절대 날짜 추출
                info_spans = article_elem.find_all('span', class_='info')
                for span in info_spans:
                    text = span.get_text(strip=True)
                    date = DateUtils.extract_absolute_date(text)
                    if date:
                        dt = DateUtils.parse_date(date, timezone=KST)
                        if dt:
                            published_date = DateUtils.format_date(dt, '%Y.%m.%d', timezone=KST)
                            published_at = DateUtils.format_date(dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
                            break

            return {
                'title': title,
                'naver_link': naver_link,
                'original_link': original_link,
                'description': description,
                'publisher': publisher or '',  # Use mapped publisher name if available
                'publisher_domain': publisher_domain,
                'published_at': published_at,
                'published_date': published_date,
                'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
                'is_naver_news': 'news.naver.com' in naver_link
            }

        except Exception as e:
            logger.error(f"Error processing article element: {e}")
            return None

    async def _make_api_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make API request with retries using aiohttp."""
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"API request failed with status {response.status}")
            except Exception as e:
                logger.error(f"API request attempt {attempt + 1} failed: {e}")
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

                # Extract domain and get publisher name from mapping
                domain = UrlUtils.extract_domain(item.get('originallink', ''))
                publisher = self._get_publisher_from_domain(domain)

                # Parse pubDate to published_at
                published_at_dt = DateUtils.parse_date(item['pubDate'], timezone=KST)
                published_at = DateUtils.format_date(published_at_dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST) if published_at_dt else ''
                # Extract date part for published_date
                published_date = DateUtils.format_date(published_at_dt, '%Y.%m.%d', timezone=KST) if published_at_dt else ''

                article = {
                    'title': TextUtils.clean_html(item['title']),
                    'naver_link': item['link'],
                    'original_link': item.get('originallink', ''),
                    'description': TextUtils.clean_html(item['description']),
                    'publisher': publisher or '',  # Use mapped publisher name if available
                    'publisher_domain': domain,
                    'published_at': published_at,
                    'published_date': published_date,
                    'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
                    'is_naver_news': is_naver_news
                }
                processed.append(article)
            except Exception as e:
                logger.error(f"Item processing error: {e}")
                continue
        return processed

    async def _initialize_browser(self) -> webdriver.Chrome:
        """Initialize browser for search collection."""
        if not self.driver:
            self.driver = self.driver_utils.initialize_driver()
            return self.driver

    async def _close_browser(self) -> None:
        """Close browser if open."""
        if self.driver:
            await self._run_in_executor(self.driver.quit)
            self.driver = None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._close_browser()
        if self.session:
            await self.session.close()
        # Close Producer connection
        await self.producer.close()
        logger.info("Closed Producer connection")

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)


async def main():
    """간단한 사용 예시"""
    parser = argparse.ArgumentParser(description='네이버 뉴스 메타데이터 수집기')
    parser.add_argument('--method', choices=['API', 'SEARCH'], default='SEARCH',
                        help='수집 방식 (API 또는 SEARCH)')
    parser.add_argument('--keyword', required=True, help='검색 키워드')
    parser.add_argument('--max_articles', type=int, default=10000,
                        help='수집할 최대 기사 수')
    parser.add_argument('--start_date', help='검색 시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end_date', help='검색 종료 날짜 (YYYY-MM-DD)')
    args = parser.parse_args()

    collector = MetadataCollector()

    try:
        result = await collector.collect(
            method=args.method,
            keyword=args.keyword,
            max_articles=args.max_articles,
            start_date=args.start_date,
            end_date=args.end_date
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
