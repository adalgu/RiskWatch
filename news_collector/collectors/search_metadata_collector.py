"""
Search-based metadata collector for Naver News.
Focuses on date-based article collection using web crawling.
"""
import logging
import asyncio
import pytz
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.webdriver_utils import WebDriverUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class SearchMetadataCollector(BaseCollector):
    """웹 검색 기반 메타데이터 수집기"""

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
                logger.info("[SearchMetadata] Initializing WebDriver...")
                self.driver = await self._run_in_executor(self.driver_utils.initialize_driver)
                logger.info("[SearchMetadata] WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"[SearchMetadata] Failed to initialize WebDriver: {e}")
                raise

    async def _navigate_to_page(self, url: str) -> bool:
        """Navigate to the given URL with proper error handling."""
        try:
            logger.info(f"[SearchMetadata] Navigating to URL: {url}")
            await self._run_in_executor(self.driver.get, url)
            
            # Wait for content to load
            await self._run_in_executor(
                WebDriverWait(self.driver, self.browser_timeout).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.news_wrap'))
            )
            
            logger.info("[SearchMetadata] Successfully loaded the page")
            return True
        except TimeoutException:
            logger.error("[SearchMetadata] Timeout waiting for page to load")
            return False
        except WebDriverException as e:
            logger.error(f"[SearchMetadata] WebDriver error during navigation: {e}")
            return False
        except Exception as e:
            logger.error(f"[SearchMetadata] Unexpected error during navigation: {e}")
            return False

    async def _load_all_articles(self, max_articles: Optional[int] = None) -> List:
        """Load all articles by scrolling down until no more new articles appear."""
        last_count = 0
        last_height = 0
        no_change_count = 0
        max_no_change = 3  # 변화가 없는 상태가 3번 연속되면 중단
        
        while True:
            # Get current state
            news_items = await self._run_in_executor(
                self.driver.find_elements,
                By.CSS_SELECTOR,
                'div.news_wrap'
            )
            current_count = len(news_items)
            current_height = await self._run_in_executor(
                lambda: self.driver.execute_script("return document.body.scrollHeight")
            )
            
            # Log progress
            logger.info(f"[SearchMetadata] Found {current_count} articles")
            
            # If we have enough articles, stop scrolling
            if max_articles and current_count >= max_articles:
                logger.info(f"[SearchMetadata] Reached target count of {max_articles} articles")
                break
            
            # Check if anything changed
            if current_count == last_count and current_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    logger.info("[SearchMetadata] No new articles found after multiple attempts")
                    break
            else:
                no_change_count = 0
                
            last_count = current_count
            last_height = current_height
            
            # Scroll down
            await self._run_in_executor(
                self.driver.execute_script,
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            
            # Wait for potential new content
            try:
                await self._run_in_executor(
                    WebDriverWait(self.driver, 1).until,
                    lambda d: d.execute_script("return document.body.scrollHeight") > current_height
                )
            except TimeoutException:
                # No height change after 1 second
                continue
            
        return news_items

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """웹 검색 기반 메타데이터 수집"""
        logger.info("[SearchMetadata] Starting search-based collection...")
        
        # Validate required parameters
        keyword = kwargs.get('keyword')
        date = kwargs.get('date')  # Required date in YYYY.MM.DD format
        if not keyword or not date:
            raise ValueError("Both keyword and date are required for search collection")

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
                logger.info(f"[SearchMetadata] Retrying navigation (attempt {attempt + 2}/{retry_count})")
                await asyncio.sleep(2)
            
            # Load articles
            news_items = await self._load_all_articles(max_articles)
            
            # Process articles
            articles = []
            items_to_process = news_items[:max_articles] if max_articles else news_items
            
            for item in items_to_process:
                try:
                    article = await self._extract_article_info(item, date)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"[SearchMetadata] Error processing article: {e}")
                    continue
            
            logger.info(f"[SearchMetadata] Search collection completed. Total articles: {len(articles)}")
            
            # Return in same format as API collector
            return {
                'total': len(articles),
                'items': articles,
                'keyword': keyword,
                'search_timestamp': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                )
            }
            
        except Exception as e:
            logger.error(f"[SearchMetadata] Collection failed: {e}")
            raise
        finally:
            await self._close_browser()

    async def _extract_article_info(self, item, date: str) -> Optional[Dict[str, Any]]:
        """Extract article information from a news item."""
        try:
            # Extract title and original link from news_tit
            title_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'a.news_tit'
            )
            title = await self._run_in_executor(title_elem.get_attribute, 'title')
            original_link = await self._run_in_executor(title_elem.get_attribute, 'href')
            
            # Extract description
            desc_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'div.news_dsc'
            )
            description = await self._run_in_executor(
                desc_elem.get_attribute,
                'textContent'
            )
            
            # Extract info group (contains press, naver link, etc)
            info_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'div.info_group'
            )
            
            # Get press name (publisher)
            press_elem = await self._run_in_executor(
                info_elem.find_element,
                By.CSS_SELECTOR,
                'a.info.press'
            )
            publisher = await self._run_in_executor(press_elem.get_attribute, 'textContent')
            
            # Find Naver News link if exists
            naver_link = None
            is_naver_news = False
            try:
                naver_elem = await self._run_in_executor(
                    info_elem.find_element,
                    By.CSS_SELECTOR,
                    'a.info[href*="news.naver.com"]'
                )
                naver_link = await self._run_in_executor(naver_elem.get_attribute, 'href')
                is_naver_news = True
            except:
                # No Naver News link found, use original link
                naver_link = original_link
            
            # Set published_at with date and dummy time (00:00:00)
            published_at = DateUtils.parse_date(f"{date} 00:00:00")
            
            return {
                'title': title.strip(),
                'naver_link': naver_link,
                'original_link': original_link,
                'description': description.strip(),
                'publisher': publisher.strip(),
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
                'is_naver_news': is_naver_news
            }
            
        except Exception as e:
            logger.error(f"[SearchMetadata] Error extracting article info: {e}")
            return None

    async def _close_browser(self) -> None:
        """Close browser safely"""
        if self.driver:
            try:
                logger.info("[SearchMetadata] Closing browser...")
                await self._run_in_executor(self.driver_utils.quit_driver)
                self.driver = None
                logger.info("[SearchMetadata] Browser closed successfully")
            except Exception as e:
                logger.error(f"[SearchMetadata] Error closing browser: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info("[SearchMetadata] Starting cleanup...")
            await self._close_browser()
            logger.info("[SearchMetadata] Cleanup completed")
        except Exception as e:
            logger.error(f"[SearchMetadata] Error during cleanup: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
