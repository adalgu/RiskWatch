"""
Naver news collector implementation using Selenium WebDriver.
"""
import logging
import asyncio
import pytz
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException

from .collector import SimpleCollector
from ..utils.date import DateUtils
from ..utils.webdriver_utils import WebDriverUtils

KST = pytz.timezone('Asia/Seoul')

class NaverNewsCollector(SimpleCollector):
    """Naver news collector with date-aware search capabilities."""
    
    def __init__(
        self,
        storage=None,
        config: Optional[Dict] = None,
        headless: bool = True
    ):
        """Initialize collector with WebDriver setup."""
        super().__init__(storage, config)
        
        # WebDriver configuration
        self.driver_utils = WebDriverUtils(
            headless=headless,
            proxy=self.config.get('proxy'),
            user_agent=self.config.get('user_agent'),
            use_remote=True
        )
        self.driver = None
        self.browser_timeout = self.config.get('browser_timeout', 30)
        
    async def _initialize_driver(self):
        """Initialize WebDriver with error handling."""
        if self.driver is None:
            try:
                self.logger.info("Initializing WebDriver...")
                self.driver = await self._run_in_executor(
                    self.driver_utils.initialize_driver
                )
                self.logger.info("WebDriver initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize WebDriver: {e}")
                raise
                
    def _build_search_url(
        self,
        keyword: str,
        date: str
    ) -> str:
        """
        Build Naver news search URL for a specific date.
        
        Args:
            keyword: Search keyword
            date: Date in YYYY.MM.DD format
            
        Returns:
            Search URL with parameters
        """
        params = {
            'where': 'news',
            'query': keyword,
            'sm': 'tab_opt',
            'sort': 1,  # Recent first
            'photo': 0,
            'field': 0,
            'pd': 3,  # Custom date range
            'ds': date,  # Start date
            'de': date,  # End date
            'start': 1,
            'refresh_start': 0
        }
        
        query_string = '&'.join(
            f"{k}={quote(str(v))}" for k, v in params.items()
        )
        return f"https://search.naver.com/search.naver?{query_string}"
        
    async def _navigate_to_page(self, url: str) -> bool:
        """Navigate to URL with proper error handling."""
        try:
            self.logger.info(f"Navigating to URL: {url}")
            await self._run_in_executor(self.driver.get, url)
            
            # Wait for content to load
            await self._run_in_executor(
                WebDriverWait(self.driver, self.browser_timeout).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.news_wrap'))
            )
            
            self.logger.info("Page loaded successfully")
            return True
            
        except TimeoutException:
            self.logger.error("Timeout waiting for page to load")
            return False
        except WebDriverException as e:
            self.logger.error(f"WebDriver error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False

    async def _load_all_articles(self, max_articles: Optional[int] = None) -> List:
        """
        Load all articles by scrolling down until no more new articles appear.
        
        Args:
            max_articles: Maximum number of articles to load (None for all articles)
            
        Returns:
            List of WebElement representing news articles
        """
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
            self.logger.info(f"Found {current_count} articles")
            
            # If we have enough articles, stop scrolling
            if max_articles and current_count >= max_articles:
                self.logger.info(f"Reached target count of {max_articles} articles")
                break
            
            # Check if anything changed
            if current_count == last_count and current_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    self.logger.info("No new articles found after multiple attempts")
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
            
            # Wait for potential new content using WebDriverWait
            try:
                await self._run_in_executor(
                    WebDriverWait(self.driver, 1).until,
                    lambda d: d.execute_script("return document.body.scrollHeight") > current_height
                )
            except TimeoutException:
                # No height change after 1 second
                continue
            
        return news_items
            
    async def _extract_article_info(self, item) -> Optional[Dict[str, Any]]:
        """Extract article information with smart date parsing."""
        try:
            # Extract basic info
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
            description = await self._run_in_executor(
                desc_elem.get_attribute,
                'textContent'
            )
            
            # Extract press and date
            info_elem = await self._run_in_executor(
                item.find_element,
                By.CSS_SELECTOR,
                'div.info_group'
            )
            
            # Get press name
            press = await self._run_in_executor(
                info_elem.find_element,
                By.CSS_SELECTOR,
                'a.press'
            )
            press_name = await self._run_in_executor(
                press.get_attribute,
                'textContent'
            )
            
            # Smart date extraction
            spans = await self._run_in_executor(
                info_elem.find_elements,
                By.CSS_SELECTOR,
                'span.info'
            )
            
            published_at = None
            date_text = None
            
            for span in spans:
                try:
                    # text = await self._run_in_executor(
                    #     span.get_attribute,
                    #     'textContent'
                    # )
                    
                    # # First try absolute date
                    # absolute_date = DateUtils.extract_absolute_date(text)
                    # if absolute_date:
                    #     date_text = absolute_date
                    #     published_at = DateUtils.parse_date(absolute_date)
                    #     break
                        
                    # # If not absolute date, treat as relative date
                    # date_text = text
                    # # Get current URL and extract ds/de parameters
                    current_url = await self._run_in_executor(lambda: self.driver.current_url)
                    ds_match = re.search(r'ds=([\d.]+)', current_url)
                    de_match = re.search(r'de=([\d.]+)', current_url)
                    
                    if ds_match and de_match and ds_match.group(1) == de_match.group(1):
                        # If ds=de, use this date as the published date
                        published_at = DateUtils.parse_date(ds_match.group(1))
                    else:
                        # Otherwise, mark as unknown
                        published_at = None
                    break
                except StaleElementReferenceException:
                    # Element might have become stale, skip it
                    continue
            
            return {
                'title': title,
                'description': description,
                'link': link,
                'press': press_name,
                'published_at': DateUtils.format_date(
                    published_at,
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                ) if published_at else None,
                # 'date_text': date_text,
                'collected_at': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting article info: {e}")
            return None
            
    async def collect_news(
        self,
        keyword: str,
        date: str,
        max_articles: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect news for a specific date.
        
        Args:
            keyword: Search keyword
            date: Target date (YYYY.MM.DD format)
            max_articles: Maximum number of articles to collect (None for all articles)
            
        Returns:
            List of collected articles
        """
        try:
            await self._initialize_driver()
            
            url = self._build_search_url(keyword, date)
            if not await self._navigate_to_page(url):
                return []

            # Load articles (with max_articles limit if specified)
            news_items = await self._load_all_articles(max_articles)
            
            # Process articles
            articles = []
            items_to_process = news_items[:max_articles] if max_articles else news_items
            
            for item in items_to_process:
                article = await self._extract_article_info(item)
                if article:
                    articles.append(article)
                    
            if self.storage:
                self.storage.save(articles)
                
            return articles
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            return []
        finally:
            await self._cleanup()
            
    async def _cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                await self._run_in_executor(self.driver_utils.quit_driver)
                self.driver = None
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
                
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
