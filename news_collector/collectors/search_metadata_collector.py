import logging
import asyncio
import pytz
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
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
        self.browser_timeout = self.get_config('browser_timeout', 30)  # 타임아웃 증가
        self.scroll_pause = self.get_config('scroll_pause', 2.0)  # 대기 시간 증가

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
            
            # Wait for the main content to load
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

    async def collect(self, **kwargs) -> List[Dict[str, Any]]:
        """웹 검색 기반 메타데이터 수집"""
        logger.info("[SearchMetadata] Starting search-based collection...")
        
        keyword = kwargs.get('keyword')
        if not keyword:
            raise ValueError("Keyword is required for search collection")

        max_articles = kwargs.get('max_articles', 5)
        retry_count = kwargs.get('retry_count', 3)
        
        try:
            # Initialize WebDriver
            await self._initialize_driver()
            
            # Naver News Search URL
            encoded_keyword = quote(keyword)
            url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}&sort=1"
            
            # Navigate to the search page with retries
            for attempt in range(retry_count):
                if await self._navigate_to_page(url):
                    break
                if attempt == retry_count - 1:
                    raise Exception("Failed to load the search page after multiple attempts")
                logger.info(f"[SearchMetadata] Retrying navigation (attempt {attempt + 2}/{retry_count})")
                await asyncio.sleep(2)
            
            # Find news articles
            articles = []
            try:
                news_items = await self._run_in_executor(
                    self.driver.find_elements,
                    By.CSS_SELECTOR,
                    'div.news_wrap'
                )
                logger.info(f"[SearchMetadata] Found {len(news_items)} news items")
                
                for item in news_items[:max_articles]:
                    try:
                        article = await self._extract_article_info(item)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"[SearchMetadata] Error processing article: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"[SearchMetadata] Error finding news items: {e}")
                raise
            
            logger.info(f"[SearchMetadata] Search collection completed. Total articles: {len(articles)}")
            return articles
            
        except Exception as e:
            logger.error(f"[SearchMetadata] Collection failed: {e}")
            raise
        finally:
            await self._close_browser()

    async def _extract_article_info(self, item) -> Optional[Dict[str, Any]]:
        """Extract article information from a news item."""
        try:
            # Extract title and link
            title_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'a.news_tit'
            )
            title = await self._run_in_executor(title_elem.get_attribute, 'title')
            link = await self._run_in_executor(title_elem.get_attribute, 'href')
            
            # Extract description
            desc_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'div.news_dsc'
            )
            description = await self._run_in_executor(desc_elem.get_attribute, 'textContent')
            
            # Extract press and date information
            info_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'div.info_group'
            )
            press = await self._run_in_executor(
                info_elem.find_element,
                By.CSS_SELECTOR,
                'a.press'
            )
            press_name = await self._run_in_executor(press.get_attribute, 'textContent')
            
            # Find date information
            spans = await self._run_in_executor(
                info_elem.find_elements,
                By.CSS_SELECTOR,
                'span.info'
            )
            published_at = ''
            for span in spans:
                text = await self._run_in_executor(span.get_attribute, 'textContent')
                if '분 전' in text or '시간 전' in text or '일 전' in text:
                    published_at = text
                    break
            
            return {
                'title': title,
                'description': description,
                'link': link,
                'press': press_name,
                'published_at': published_at,
                'collected_at': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                )
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
