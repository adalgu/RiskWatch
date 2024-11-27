"""
Unified metadata collector supporting both API and Search-based collection.

Publication Date Handling:

API Collection (published_at):

- Receives RFC822 formatted date from Naver API (e.g., "Wed, 20 Mar 2024 14:30:00 +0900")
- Parses and stores as ISO format with KST timezone (e.g., "2024-03-20T14:30:00+09:00")
- Includes exact timestamp with timezone information

Search Collection (published_date):

a. Articles older than 5 weeks:

- HTML shows absolute dates (e.g., "2024.12.12")
- Dates can be directly extracted using regex
- Entire date range can be searched at once

b. Articles within 5 weeks:

- HTML shows only relative dates (e.g., "1일전", "1주전")
- Must search day-by-day to infer absolute dates
- Searches from end_date backwards to start_date (newest first)
- Uses the search date as the article's publication date

Note: The daily chunking for recent articles (≤5 weeks) is necessary because
Naver only provides relative dates in the HTML for these articles. By searching
one day at a time and using that search date as the publication date, we can
accurately determine when each article was published. The reverse chronological
order (end_date to start_date) ensures we get the newest articles first,
matching Naver's default sorting.

Timestamp Fields:

- published_at: ISO format with timezone (e.g., "2024-03-20T14:30:00+09:00")
  - Set from API collection's pubDate
  - Can be updated from comment collection's article_timestamp

- published_date: YYYY.MM.DD format (e.g., "2024.03.20")
  - Set from search collection's date extraction
  - Used when exact timestamp is not available

Examples:

# API 방식으로 수집

>>> collector = MetadataCollector()

>>> result = await collector.collect(

...     method='api',

...     keyword='검색어',

...     max_articles=10

)

# 검색 방식으로 수집

>>> collector = MetadataCollector()

>>> result = await collector.collect(

...     method='search',

...     keyword='검색어',

...     start_date='2024-01-01',  # Optional

...     end_date='2024-01-31',    # Optional

...     max_articles=10

)

# 명령줄 실행:

$ python -m news_system.news_collector.collectors.metadata --method api --keyword "검색어" --max_articles 10

$ python -m news_system.news_collector.collectors.metadata --method search --keyword "삼성전자" --start_date 2024-11-22 --end_date 2024-11-24 --max_articles 50
"""
import os
import json
import urllib.request
import logging
import asyncio
import argparse
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
import pytz
import aiohttp
import aio_pika
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from .base import BaseCollector
from ..core.utils import WebDriverUtils

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=KST)
    except ValueError as e:
        logger.error(
            f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")
        raise ValueError(
            f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD") from e


def extract_absolute_date(text: str) -> Optional[str]:
    """
    텍스트에서 절대 날짜(YYYY.MM.DD)를 추출합니다.

    Args:
        text (str): 날짜 정보가 포함된 텍스트

    Returns:
        Optional[str]: 추출된 날짜 문자열 (YYYY.MM.DD) 또는 None
    """
    pattern = r'(\d{4})\.(\d{1,2})\.(\d{1,2})'
    match = re.search(pattern, text)
    if match:
        year, month, day = match.groups()
        # 날짜 형식 통일 (한 자리 숫자 앞에 0 추가)
        return f"{year}.{int(month):02d}.{int(day):02d}"
    return None


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
        self.session = aiohttp.ClientSession()
        self._load_publisher_mapping()
        # Initialize RabbitMQ connection
        self.rabbitmq_url = os.getenv(
            'RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        self.queue_name = 'metadata_queue'
        self.loop = asyncio.get_event_loop()
        self.connection = None
        self.channel = None
        self.loop.create_task(self._init_rabbitmq())

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
                                        '..', 'core', 'utils',
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

    async def _init_rabbitmq(self) -> None:
        """Initialize RabbitMQ connection and channel."""
        max_retries = 5
        retry_delay = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self.connection or self.connection.is_closed:
                    self.connection = await aio_pika.connect_robust(
                        self.rabbitmq_url,
                        loop=self.loop
                    )
                    logger.info("Successfully connected to RabbitMQ")

                if not self.channel or self.channel.is_closed:
                    self.channel = await self.connection.channel()
                    await self.channel.declare_queue(self.queue_name, durable=True)
                    logger.info("Successfully created RabbitMQ channel and declared queue")
                
                return
            except Exception as e:
                retry_count += 1
                logger.warning(f"RabbitMQ connection attempt {retry_count} failed: {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to RabbitMQ after maximum retries")
                    raise

    async def publish_message(self, message: Dict[str, Any]) -> None:
        """Publish message to RabbitMQ with retries."""
        max_retries = 3
        retry_delay = 2
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self.channel or self.channel.is_closed:
                    await self._init_rabbitmq()

                await self.channel.default_exchange.publish(
                    aio_pika.Message(body=json.dumps(message).encode()),
                    routing_key=self.queue_name
                )
                logger.info("Successfully published message to RabbitMQ")
                return
            except Exception as e:
                retry_count += 1
                logger.warning(f"Failed to publish message (attempt {retry_count}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to publish message after maximum retries")
                    raise

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect metadata using specified method."""
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
                'collected_at': datetime.now(KST).isoformat(),
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
                # Publish to RabbitMQ with retries
                await self.publish_message(result)
                return result
            else:
                raise ValueError("Validation failed for collected data")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def update_article_timestamp(self, article: Dict[str, Any], article_timestamp: str) -> None:
        """
        Update article's published_at from comment collection's article_timestamp.

        Args:
            article: Article metadata dictionary
            article_timestamp: ISO formatted timestamp from comment collection
        """
        try:
            # Only update if the article doesn't have a published_at or has only published_date
            if not article.get('published_at') or (article.get('published_date') and not article.get('published_at')):
                article['published_at'] = article_timestamp
                logger.info(f"Updated article timestamp: {article_timestamp}")
        except Exception as e:
            logger.error(f"Error updating article timestamp: {e}")

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
            start_date = parse_date(kwargs.get('start_date'))
            end_date = parse_date(kwargs.get('end_date'))

            # 5주 전 날짜 계산
            now = datetime.now(KST)
            five_weeks_ago = now - timedelta(weeks=5)

            # 검색 날짜가 5주 이내인지 확인
            is_within_five_weeks = False
            if start_date and start_date > five_weeks_ago:
                is_within_five_weeks = True

            all_articles = []

            if is_within_five_weeks:
                # 5주 이내 검색: 하루 단위로 수집 (최신순)
                current_date = end_date if end_date else now
                start_date = start_date if start_date else five_weeks_ago

                while current_date >= start_date:
                    logger.info(
                        f"Collecting articles for date: {current_date.strftime('%Y-%m-%d')}")

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
                    By.CLASS_NAME, "list_news", self.browser_timeout)
            )
        except TimeoutException:
            logger.error(
                f"News list not found for date: {date.strftime('%Y-%m-%d')}")
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
                'ds': start_date.strftime('%Y.%m.%d'),
                'de': end_date.strftime('%Y.%m.%d')
            })
        else:
            end_date = datetime.now(KST)
            start_date = end_date - timedelta(days=90)
            params.update({
                'ds': start_date.strftime('%Y.%m.%d'),
                'de': end_date.strftime('%Y.%m.%d')
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

            title = title_elem.get_text(strip=True)
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
            description = desc_elem.get_text(strip=True) if desc_elem else ''

            # 언론사
            press_elem = article_elem.find('a', {'class': 'press'})
            if press_elem:
                for i_tag in press_elem.find_all('i', class_='spnew ico_pick'):
                    i_tag.extract()
                publisher = press_elem.get_text(strip=True)
            else:
                publisher = ''

            # 도메인 추출
            publisher_domain = self._extract_domain(original_link)

            # 날짜 정보 추출
            published_date = None
            info_spans = article_elem.find_all('span', class_='info')

            # 검색 날짜가 있으면 (5주 이내 기사) 해당 날짜 사용
            if search_date:
                published_date = search_date.strftime('%Y.%m.%d')
                published_at = search_date.isoformat()
            else:
                # 5주 이전 기사는 태그에서 절대 날짜 추출
                for span in info_spans:
                    text = span.get_text(strip=True)
                    date = extract_absolute_date(text)
                    if date:
                        published_date = date
                        # Convert YYYY.MM.DD to ISO format
                        dt = datetime.strptime(date, '%Y.%m.%d').replace(tzinfo=KST)
                        published_at = dt.isoformat()
                        break

            return {
                'title': title,
                'naver_link': naver_link,
                'original_link': original_link,
                'description': description,
                'publisher': publisher,
                'publisher_domain': publisher_domain,
                'published_at': published_at,
                'published_date': published_date,
                'collected_at': datetime.now(KST).isoformat(),
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
                        data = await response.json()
                        return data
                    else:
                        logger.error(
                            f"Unexpected status code {response.status} for URL: {url}")
            except Exception as e:
                logger.error(
                    f"API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
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
                domain = self._extract_domain(item.get('originallink', ''))
                publisher = self._get_publisher_from_domain(domain)

                # Parse pubDate to published_at
                published_at = self._parse_datetime(
                    item['pubDate']).isoformat()
                # Extract date part for published_date
                published_date = published_at[:10].replace('-', '.')

                article = {
                    'title': await self._remove_html_tags(item['title']),
                    'naver_link': item['link'],
                    'original_link': item.get('originallink', ''),
                    'description': await self._remove_html_tags(item['description']),
                    'publisher': publisher or '',  # Use mapped publisher name if available
                    'publisher_domain': domain,
                    'published_at': published_at,
                    'published_date': published_date,
                    'collected_at': datetime.now(KST).isoformat(),
                    'is_naver_news': is_naver_news
                }
                processed.append(article)
            except Exception as e:
                logger.error(f"Item processing error: {e}")
                continue
        return processed

    async def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags from text using BeautifulSoup."""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return ""

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse datetime with timezone."""
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S +0900')
        return KST.localize(dt)

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
        await self.session.close()
        # Close RabbitMQ connection
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection.")

    async def __aenter__(self):
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
    parser.add_argument('--method', choices=['API', 'SEARCH'], default='api',
                        help='수집 방식 (API 또는 SEARCH)')
    parser.add_argument('--keyword', required=True, help='검색 키워드')
    parser.add_argument('--max_articles', type=int, default=10,
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
