"""
사용법: 
python -m news_collector.parallel.parallel_metadata_collector --method search --keyword "하이닉스" --max_articles 20000 --start_date 2024-11-14 --end_date 2024-11-24
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import pytz
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import os
import threading
import uuid

from news_collector.collectors.base import BaseCollector
from news_collector.core.utils import WebDriverUtils

# 로그 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
    """Extract absolute date (YYYY.MM.DD) from text."""
    pattern = r'(\d{4})\.(\d{1,2})\.(\d{1,2})'
    match = re.search(pattern, text)
    if match:
        year, month, day = match.groups()
        return f"{year}.{int(month):02d}.{int(day):02d}"
    return None


class ParallelMetadataCollector(BaseCollector):
    """
    병렬 메타데이터 수집기.
    API와 Search 방식을 모두 지원하며, Search 방식에 병렬 처리를 도입합니다.
    """

    def __init__(self, config: Optional[Dict] = None, max_workers: int = 5):
        """Initialize collector with configuration."""
        super().__init__(config)
        self._init_config()
        self.proxy = self.get_config('proxy')
        self.user_agent = self.get_config('user_agent')
        self.driver_utils = WebDriverUtils(
            headless=True,
            proxy=self.proxy,
            user_agent=self.user_agent,
            use_remote=True,
            remote_url="http://localhost:4444/wd/hub"
        )
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = aiohttp.ClientSession()

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

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect metadata using specified method."""
        method = kwargs.get('method', 'api')
        self.log_collection_start(kwargs)

        try:
            if method == 'api':
                articles = await self.collect_from_api(**kwargs)
            else:
                articles = await self.collect_from_search(**kwargs)

            result = {
                'articles': articles,
                'collected_at': datetime.now(KST).isoformat(),
                'metadata': {
                    'method': method,
                    'total_collected': len(articles),
                    'keyword': kwargs.get('keyword')
                }
            }

            if await self.validate_async(result):
                self.log_collection_end(True, {'article_count': len(articles)})
                return result
            else:
                raise ValueError("Validation failed for collected data")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def collect_from_search(self, **kwargs) -> List[Dict[str, Any]]:
        """검색 기반 메타데이터 수집 (병렬 처리 도입)"""
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

            tasks = []
            while current_date >= start_date:
                tasks.append(self._collect_single_day(
                    keyword, current_date, max_articles))
                current_date -= timedelta(days=1)

            # 동시성 제한을 위해 Semaphore 사용 (예: 동시에 5개 작업)
            semaphore = asyncio.Semaphore(5)

            async def semaphore_wrapper(task):
                async with semaphore:
                    return await task

            tasks = [semaphore_wrapper(task) for task in tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in collecting single day: {result}")
                else:
                    all_articles.extend(result)
                    if max_articles and len(all_articles) >= max_articles:
                        all_articles = all_articles[:max_articles]
                        break

        else:
            # 5주 이전 검색: 일반적인 방식으로 수집
            search_url = self._build_search_url(keyword, start_date, end_date)
            logger.info(
                f"Accessing search URL: {search_url} for date range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

            try:
                driver = await self._initialize_browser()
                await self._run_in_executor(driver.get, search_url)
                await asyncio.sleep(2)

                try:
                    await self._run_in_executor(
                        lambda: self.driver_utils.wait_for_element(
                            By.CLASS_NAME, "list_news", self.browser_timeout)
                    )
                except TimeoutException:
                    logger.error("News list not found")
                    return []

                # date_info로 날짜 범위 전달
                articles = await self._collect_search_articles(driver, max_articles, date_info=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                all_articles.extend(articles)

            except Exception as e:
                logger.error(f"Error during search collection: {e}")
            finally:
                await self._close_browser()

        # 날짜순 정렬 (최신순)
        def sort_key(x):
            date_str = x.get('pub_date') or x.get('published_at')
            if date_str:
                try:
                    return datetime.strptime(date_str, '%Y.%m.%d')
                except ValueError:
                    logger.warning(
                        f"Invalid date format for sorting: {date_str}")
                    return datetime.min
            else:
                return datetime.min  # 또는 datetime.max

        all_articles.sort(key=sort_key, reverse=True)

        # 최대 기사 수 제한
        if max_articles and len(all_articles) > max_articles:
            all_articles = all_articles[:max_articles]

        logger.info(f"총 수집 기사: {len(all_articles)}개")
        return all_articles

    async def _collect_single_day(self, keyword: str, date: datetime, max_articles: Optional[int] = None) -> List[Dict[str, Any]]:
        """하루 단위로 기사 수집 (병렬 처리) with 재시도 로직"""
        retries = self.max_retries
        backoff_factor = self.retry_delay
        task_id = uuid.uuid4()

        for attempt in range(1, retries + 1):
            try:
                search_url = self._build_search_url(
                    keyword, start_date=date, end_date=date)
                logger.info(
                    f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] Starting collection for this date")

                driver = await self._initialize_browser()
                await self._run_in_executor(driver.get, search_url)
                await asyncio.sleep(2)

                try:
                    await self._run_in_executor(
                        lambda: self.driver_utils.wait_for_element(
                            By.CLASS_NAME, "list_news", self.browser_timeout)
                    )
                except TimeoutException:
                    logger.error(
                        f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] News list not found")
                    return []

                articles = await self._collect_search_articles(driver, max_articles, search_date=date, date_info=date.strftime('%Y-%m-%d'))
                logger.info(
                    f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] Completed collection for this date with {len(articles)} articles")
                return articles

            except Exception as e:
                logger.error(
                    f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] Attempt {attempt} - Error: {e}")
                if attempt < retries:
                    wait_time = backoff_factor * (2 ** (attempt - 1))
                    logger.info(
                        f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] Retrying after {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[{date.strftime('%Y-%m-%d')}] [Worker-{threading.get_ident()}] [Task-{task_id}] All retries failed")
                    return []

    def _build_search_url(self, keyword: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> str:
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
            start_date = end_date - timedelta(days=365)  # 1년치 데이터 수집
            params.update({
                'ds': start_date.strftime('%Y.%m.%d'),
                'de': end_date.strftime('%Y.%m.%d')
            })

        query_string = urlencode(params)
        return f"https://search.naver.com/search.naver?{query_string}"

    async def _collect_search_articles(self, driver: webdriver.Chrome, max_articles: Optional[int] = None, search_date: Optional[datetime] = None, date_info: Optional[str] = None) -> List[Dict[str, Any]]:
        """스크롤하며 기사 수집"""
        last_count = 0
        no_new_articles_count = 0
        max_retries = 2
        articles = []

        while no_new_articles_count < max_retries:
            current_count = await self._get_current_article_count(driver)

            if max_articles and current_count >= max_articles:
                break

            if current_count > last_count:
                logger.info(
                    f"Found {current_count - last_count} new articles (Total: {current_count}) for date range {date_info}")
                last_count = current_count
                no_new_articles_count = 0
            else:
                no_new_articles_count += 1

            await self._scroll_to_bottom(driver)
            await asyncio.sleep(self.scroll_pause)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        article_elements = soup.select('ul.list_news > li.bx')

        for article in article_elements[:max_articles]:
            try:
                article_data = self._extract_article_data(article, search_date)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                logger.error(f"Error extracting article data: {e}")

        return articles

    def _extract_article_data(self, article_elem: BeautifulSoup, search_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
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

            # 날짜 정보 추출
            pub_date = None
            info_spans = article_elem.find_all('span', class_='info')

            # 검색 날짜가 있으면 (5주 이내 기사) 해당 날짜 사용
            if search_date:
                pub_date = search_date.strftime('%Y.%m.%d')
            else:
                # 5주 이전 기사는 태그에서 절대 날짜 추출
                for span in info_spans:
                    text = span.get_text(strip=True)
                    date = extract_absolute_date(text)
                    if date:
                        pub_date = date
                        break

            # pub_date 확인 및 로그
            if not pub_date:
                logger.warning(
                    f"Missing pub_date and published_at for article: {title}")

            return {
                'title': title,
                'naver_link': naver_link,
                'original_link': original_link,
                'description': description,
                'publisher': publisher,
                'pub_date': pub_date,  # YYYY.MM.DD 형식의 문자열
                'collected_at': datetime.now(KST).isoformat(),
                'is_naver_news': 'news.naver.com' in naver_link
            }

        except Exception as e:
            logger.error(f"Error processing article element: {e}")
            return None

    async def _get_current_article_count(self, driver: webdriver.Chrome) -> int:
        """현재 로드된 기사 수 반환"""
        elements = await self._run_in_executor(driver.find_elements, By.CSS_SELECTOR, 'ul.list_news > li.bx')
        return len(elements)

    async def _scroll_to_bottom(self, driver: webdriver.Chrome) -> None:
        """페이지 맨 아래로 스크롤"""
        await self._run_in_executor(driver.execute_script, "window.scrollTo(0, document.body.scrollHeight);")

    async def _initialize_browser(self) -> webdriver.Chrome:
        """Initialize browser for search collection."""
        if not hasattr(self, 'driver') or self.driver is None:
            self.driver = await self._run_in_executor(self.driver_utils.initialize_driver)
            return self.driver
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
        self.executor.shutdown(wait=True)

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)


# 사용 예시
async def main():
    """병렬 처리된 검색 방식 사용 예시"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='네이버 뉴스 메타데이터 수집기 (병렬 처리)')
    parser.add_argument('--method', choices=['api', 'search'], default='search',
                        help='수집 방식 (api 또는 search)')
    parser.add_argument('--keyword', required=True, help='검색 키워드')
    parser.add_argument('--max_articles', type=int, default=1000,
                        help='수집할 최대 기사 수')
    parser.add_argument('--start_date', help='검색 시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end_date', help='검색 종료 날짜 (YYYY-MM-DD)')
    args = parser.parse_args()

    collector = ParallelMetadataCollector(max_workers=10)  # 동시에 10개의 작업 실행
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


if __name__ == '__main__':
    asyncio.run(main())
