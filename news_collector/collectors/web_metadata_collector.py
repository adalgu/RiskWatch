"""
Web-based metadata collector for Naver News.
Focuses on date-based article collection using web crawling.
"""
import logging
import asyncio
import pytz
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.webdriver_utils import WebDriverUtils
from .utils.url import UrlUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class WebMetadataCollector(BaseCollector):
    """웹 크롤링 기반 메타데이터 수집기"""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize collector with configuration."""
        super().__init__(config)
        self.proxy = self.get_config('proxy')
        self.user_agent = self.get_config('user_agent')
        self.driver_utils = WebDriverUtils(
            headless=True,
            proxy=self.proxy,
            user_agent=self.user_agent,
            use_remote=True
        )
        self.driver = None
        self.browser_timeout = self.get_config('browser_timeout', 30)

    def _build_search_url(self, keyword: str, date: str) -> str:
        """Build Naver news search URL for a specific date."""
        params = {
            'where': 'news',
            'query': keyword,
            'sm': 'tab_opt',
            'sort': 1,  # Recent first
            'photo': 0,
            'field': 0,
            'pd': 3,    # Custom date range
            'ds': date, # Start date
            'de': date, # End date
            'start': 1,
            'refresh_start': 0
        }
        query_string = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"https://search.naver.com/search.naver?{query_string}"

    async def _initialize_driver(self):
        """Initialize WebDriver with proper error handling."""
        if self.driver is None:
            try:
                logger.info("[WebMetadata] Initializing WebDriver...")
                self.driver = await self._run_in_executor(self.driver_utils.initialize_driver)
                logger.info("[WebMetadata] WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"[WebMetadata] Failed to initialize WebDriver: {e}")
                raise

    async def _navigate_to_page(self, url: str) -> bool:
        """Navigate to the given URL with proper error handling."""
        try:
            logger.info(f"[WebMetadata] Navigating to URL: {url}")
            await self._run_in_executor(self.driver.get, url)
            
            # Wait for content to load
            await self._run_in_executor(
                WebDriverWait(self.driver, self.browser_timeout).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.news_wrap'))
            )
            
            logger.info("[WebMetadata] Successfully loaded the page")
            return True
        except TimeoutException:
            logger.error("[WebMetadata] Timeout waiting for page to load")
            return False
        except WebDriverException as e:
            logger.error(f"[WebMetadata] WebDriver error during navigation: {e}")
            return False
        except Exception as e:
            logger.error(f"[WebMetadata] Unexpected error during navigation: {e}")
            return False

    async def _load_all_articles(self, max_articles: Optional[int] = None) -> None:
        """Load articles by scrolling down if needed."""
        # Get initial articles count
        news_items = await self._run_in_executor(
            self.driver.find_elements,
            By.CSS_SELECTOR,
            'div.news_wrap'
        )
        current_count = len(news_items)
        logger.info(f"[WebMetadata] Initially found {current_count} articles")
        
        # If we have enough articles or no max specified, return
        if max_articles and current_count >= max_articles:
            logger.info(f"[WebMetadata] First page has enough articles ({current_count})")
            return
            
        # Need to scroll for more articles
        last_count = current_count
        last_height = await self._run_in_executor(
            lambda: self.driver.execute_script("return document.body.scrollHeight")
        )
        no_change_count = 0
        max_no_change = 2
        
        while True:
            # Scroll down
            await self._run_in_executor(
                self.driver.execute_script,
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            
            # Short wait for content load
            await asyncio.sleep(0.2)
            
            # Get new state
            news_items = await self._run_in_executor(
                self.driver.find_elements,
                By.CSS_SELECTOR,
                'div.news_wrap'
            )
            current_count = len(news_items)
            current_height = await self._run_in_executor(
                lambda: self.driver.execute_script("return document.body.scrollHeight")
            )
            
            logger.info(f"[WebMetadata] Found {current_count} articles after scroll")
            
            # If we have enough articles, stop scrolling
            if max_articles and current_count >= max_articles:
                logger.info(f"[WebMetadata] Reached target count of {max_articles} articles")
                break
            
            # Check if anything changed
            if current_count == last_count and current_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    logger.info("[WebMetadata] No new articles found after scrolling")
                    break
            else:
                no_change_count = 0
                
            last_count = current_count
            last_height = current_height

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """웹 크롤링 기반 메타데이터 수집"""
        logger.info("[WebMetadata] Starting web-based collection...")
        
        # Validate required parameters
        keyword = kwargs.get('keyword')
        date = kwargs.get('date')  # Required date in YYYY.MM.DD format
        if not keyword or not date:
            raise ValueError("Both keyword and date are required for web collection")

        max_articles = kwargs.get('max_articles', 5)
        retry_count = kwargs.get('retry_count', 3)
        
        try:
            # Initialize WebDriver
            await self._initialize_driver()
            
            # Build and navigate to search URL
            url = self._build_search_url(keyword, date)
            
            # Navigate to the search page with retries
            for attempt in range(retry_count):
                if await self._navigate_to_page(url):
                    break
                if attempt == retry_count - 1:
                    raise Exception("Failed to load the search page after multiple attempts")
                logger.info(f"[WebMetadata] Retrying navigation (attempt {attempt + 2}/{retry_count})")
                await asyncio.sleep(2)
            
            # Load articles by scrolling
            await self._load_all_articles(max_articles)
            
            # Get page source and parse with BeautifulSoup
            html = await self._run_in_executor(lambda: self.driver.page_source)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract articles
            articles = []
            article_elements = soup.select('div.news_wrap')[:max_articles]
            
            for article_elem in article_elements:
                try:
                    article = self._extract_article_info(article_elem, date)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"[WebMetadata] Error processing article: {e}")
                    continue
            
            logger.info(f"[WebMetadata] Web collection completed. Total articles: {len(articles)}")
            
            # Return web collection result
            return {
                'items': articles,
                'keyword': keyword,
                'date': date,
                'search_timestamp': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                )
            }
            
        except Exception as e:
            logger.error(f"[WebMetadata] Collection failed: {e}")
            raise
        finally:
            await self._close_browser()

    def _extract_article_info(self, article_elem: BeautifulSoup, date: str) -> Optional[Dict[str, Any]]:
        """Extract article information using BeautifulSoup."""
        try:
            # Extract title and original link
            title_elem = article_elem.select_one('a.news_tit')
            if not title_elem:
                return None
                
            title = title_elem.get('title', '').strip()
            original_link = title_elem.get('href', '')
            
            # Extract description
            desc_elem = article_elem.select_one('div.news_dsc')
            description = desc_elem.text.strip() if desc_elem else ''
            
            # Extract press info
            press_elem = article_elem.select_one('a.info.press')
            publisher = press_elem.text.strip() if press_elem else ''
            
            # Find Naver News link
            naver_link = None
            is_naver_news = False
            info_group = article_elem.select_one('div.info_group')
            if info_group:
                for link in info_group.select('a.info'):
                    href = link.get('href', '')
                    if 'news.naver.com' in href:
                        naver_link = href
                        is_naver_news = True
                        break
            
            # If no Naver link found, use original link
            if not naver_link:
                naver_link = original_link
            
            # Set published_at with date and dummy time (00:00:00)
            published_at = DateUtils.parse_date(f"{date} 00:00:00")
            
            return {
                'title': title,
                'naver_link': naver_link,
                'original_link': original_link,
                'description': description,
                'publisher': publisher,
                'published_at': DateUtils.format_date(
                    published_at,
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                ),
                'collected_at': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                ),
                'is_naver_news': is_naver_news,
                'collection_method': 'WEB'
            }
            
        except Exception as e:
            logger.error(f"[WebMetadata] Error extracting article info: {e}")
            return None

    async def _close_browser(self) -> None:
        """Close browser safely"""
        if self.driver:
            try:
                logger.info("[WebMetadata] Closing browser...")
                await self._run_in_executor(self.driver_utils.quit_driver)
                self.driver = None
                logger.info("[WebMetadata] Browser closed successfully")
            except Exception as e:
                logger.error(f"[WebMetadata] Error closing browser: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info("[WebMetadata] Starting cleanup...")
            await self._close_browser()
            logger.info("[WebMetadata] Cleanup completed")
        except Exception as e:
            logger.error(f"[WebMetadata] Error during cleanup: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
