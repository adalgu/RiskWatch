"""
Updated news comment collector combining features from comments_old.py and web_metadata_collector.py.
Collects comments and statistics, handles input/output structures, and uses improved web driver methods.

news_collector/collectors/comments.py
"""

import logging
import asyncio
import pytz
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.text import TextUtils
from .utils.webdriver_utils import WebDriverUtils
from .utils.url import UrlUtils
from ..producer import Producer  # Import the Producer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

class CommentCollector(BaseCollector):
    """
    뉴스 댓글 수집기.
    댓글과 통계 정보를 함께 수집합니다.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize comment collector."""
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
        self.browser_timeout = self.get_config('browser_timeout', 30)
        
        # Initialize Producer
        self.producer = Producer()

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.max_retries = self.get_config('max_retries', 3)
        self.retry_delay = self.get_config('retry_delay', 2)
        self.batch_size = self.get_config('batch_size', 5)

    async def collect(self, article_url: str, **kwargs) -> Dict[str, Any]:
        """
        Collect comments and statistics for a given article URL.

        Args:
            article_url: URL of the article
            **kwargs:
                - include_stats: Whether to collect statistics (default: True)

        Returns:
            Dict containing comments and metadata
        """
        include_stats = kwargs.get('include_stats', True)
        result = {
            'article_url': article_url,
            'total_count': 0,
            'published_at': None,
            'stats': self._get_empty_stats(),
            'collected_at': DateUtils.format_date(
                datetime.now(KST),
                '%Y-%m-%dT%H:%M:%S%z',
                timezone=KST
            ),
            'comments': [],
            'collection_status': 'success'
        }

        try:
            # Initialize WebDriver
            await self._initialize_driver()

            # Convert to comment URL
            comment_url = self._convert_to_comment_url(article_url)
            if not comment_url:
                logger.error(f"[Comments] Failed to convert to comment URL: {article_url}")
                result['collection_status'] = 'failed'
                result['error'] = 'Invalid article URL'
                return result

            # Navigate to the comment page
            if not await self._navigate_to_page(comment_url):
                result['collection_status'] = 'failed'
                result['error'] = 'Failed to load comment page'
                return result

            # Check if comments exist
            if not await self._comments_exist():
                logger.info("[Comments] No comments found on the page")
                return result

            # Extract article timestamp and comment count
            html = await self._run_in_executor(lambda: self.driver.page_source)
            result['published_at'] = self._extract_article_timestamp(html)
            total_count = self._extract_comment_count(html)
            result['total_count'] = total_count

            # Load all comments
            await self._load_all_comments()

            # Parse comments and stats
            html = await self._run_in_executor(lambda: self.driver.page_source)
            soup = BeautifulSoup(html, 'html.parser')

            if include_stats:
                try:
                    result['stats'] = self._extract_comment_stats(soup)
                except Exception as e:
                    logger.warning(f"[Comments] Failed to extract stats: {e}")

            # Extract comments
            comments = []
            comment_elements = self._find_comment_elements(soup)
            for element in comment_elements:
                comment_data = self._extract_comment_data(element)
                if comment_data:
                    comments.append(comment_data)
            result['comments'] = comments

            logger.info(f"[Comments] Collected {len(comments)} comments from {article_url}")
            return result

        except Exception as e:
            logger.error(f"[Comments] Error collecting comments from {article_url}: {e}")
            result['collection_status'] = 'failed'
            result['error'] = str(e)
            return result
        finally:
            await self._close_browser()

    async def _initialize_driver(self):
        """Initialize WebDriver with proper error handling."""
        if self.driver is None:
            try:
                logger.info("[Comments] Initializing WebDriver...")
                self.driver = await self._run_in_executor(self.driver_utils.initialize_driver)
                logger.info("[Comments] WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"[Comments] Failed to initialize WebDriver: {e}")
                raise

    async def _navigate_to_page(self, url: str) -> bool:
        """Navigate to the given URL and ensure the page loads."""
        try:
            logger.info(f"[Comments] Navigating to URL: {url}")
            await self._run_in_executor(self.driver.get, url)

            # Wait for the comment section to load
            await self._run_in_executor(
                WebDriverWait(self.driver, self.browser_timeout).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, '#cbox_module'))
            )

            logger.info("[Comments] Successfully loaded the page")
            return True
        except TimeoutException:
            logger.error("[Comments] Timeout waiting for page to load")
            return False
        except WebDriverException as e:
            logger.error(f"[Comments] WebDriver error during navigation: {e}")
            return False
        except Exception as e:
            logger.error(f"[Comments] Unexpected error during navigation: {e}")
            return False

    async def _comments_exist(self) -> bool:
        """Check if the comments section has comments."""
        try:
            # Check if the 'No comments' message exists
            no_comments_elem = await self._run_in_executor(
                self.driver.find_elements, By.CSS_SELECTOR, '.u_cbox_none'
            )
            if no_comments_elem:
                return False
            return True
        except Exception as e:
            logger.error(f"[Comments] Error checking for comments: {e}")
            return False

    async def _load_all_comments(self):
        """Load all comments by clicking 'More' buttons."""
        try:
            retry_count = 0
            while retry_count < self.max_retries:
                more_buttons = await self._run_in_executor(
                    self.driver.find_elements, By.CSS_SELECTOR, '.u_cbox_btn_more'
                )
                if not more_buttons:
                    break
                for button in more_buttons:
                    try:
                        await self._run_in_executor(
                            lambda: self.driver.execute_script("arguments[0].click();", button)
                        )
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"[Comments] Error clicking 'More' button: {e}")
                        continue
                retry_count += 1
                await asyncio.sleep(self.retry_delay)
        except Exception as e:
            logger.error(f"[Comments] Error loading all comments: {e}")

    def _extract_article_timestamp(self, html: str) -> Optional[str]:
        """Extract article publication timestamp."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            timestamp_element = soup.find(
                'span', {'class': '_ARTICLE_DATE_TIME'})

            if timestamp_element:
                raw_timestamp = timestamp_element.get('data-date-time')
                if raw_timestamp:
                    dt = DateUtils.parse_date(raw_timestamp, timezone=KST)
                    if dt:
                        return DateUtils.format_date(dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
            return None

        except Exception as e:
            logger.error(f"[Comments] Error extracting article timestamp: {e}")
            return None

    def _extract_comment_count(self, html: str) -> int:
        """Extract comment count from page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            count_element = soup.find('span', {'class': 'u_cbox_count'})
            if count_element:
                return int(TextUtils.extract_numbers(count_element.get_text(strip=True))[0])
            return 0

        except Exception as e:
            logger.error(f"[Comments] Error extracting comment count: {e}")
            return 0

    def _find_comment_elements(self, soup: BeautifulSoup) -> List[Tag]:
        """Find all comment elements in page."""
        elements = []
        for selector in [
            'div.u_cbox_comment',
            'div.u_cbox_reply_item',
            'li.u_cbox_comment',
            'li.u_cbox_reply_item'
        ]:
            elements.extend(soup.select(selector))
        return elements

    def _extract_comment_data(self, element: Tag) -> Optional[Dict[str, Any]]:
        """Extract data from comment element."""
        try:
            # Extract comment ID
            comment_id = element.get('data-info', '')
            comment_no = None
            parent_comment_no = None

            if comment_id:
                comment_match = re.search(r"commentNo:'([^']+)'", comment_id)
                parent_match = re.search(r"parentCommentNo:'([^']+)'", comment_id)
                comment_no = comment_match.group(1) if comment_match else None
                parent_comment_no = parent_match.group(1) if parent_match else None

            # Check if comment is deleted or hidden
            classes = element.get('class', [])
            is_deleted = 'u_cbox_type_delete' in classes
            delete_type = None
            if is_deleted:
                delete_msg = element.find('span', {'class': 'u_cbox_delete_contents'})
                if delete_msg:
                    msg_text = delete_msg.get_text(strip=True)
                    delete_type = 'user' if '작성자' in msg_text else 'admin'

            # Extract content
            content = None
            for class_name in ['u_cbox_contents', 'u_cbox_text', 'comment_text']:
                content = element.find('span', {'class': class_name})
                if content:
                    break

            if not content and not is_deleted:
                return None

            # Extract user info
            username_elem = element.find('span', {'class': 'u_cbox_nick'})
            username = username_elem.get_text(strip=True) if username_elem else '익명'

            profile_img = element.find('img', {'class': 'u_cbox_img_profile'})
            profile_url = profile_img.get('src') if profile_img else None

            # Extract timestamp
            timestamp_elem = element.find('span', {'class': 'u_cbox_date'})
            timestamp_value = None
            if timestamp_elem:
                raw_timestamp = timestamp_elem.get('data-value')
                if raw_timestamp:
                    dt = DateUtils.parse_date(raw_timestamp, timezone=KST)
                    if dt:
                        timestamp_value = DateUtils.format_date(dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
                else:
                    # Fallback to text extraction
                    raw_text = timestamp_elem.get_text(strip=True)
                    dt = DateUtils.parse_date(raw_text, timezone=KST)
                    if dt:
                        timestamp_value = DateUtils.format_date(dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)

            # Extract likes/dislikes
            likes_elem = element.find('em', {'class': 'u_cbox_cnt_recomm'})
            dislikes_elem = element.find('em', {'class': 'u_cbox_cnt_unrecomm'})
            likes = TextUtils.extract_numbers(likes_elem.get_text(strip=True))[0] if likes_elem else 0
            dislikes = TextUtils.extract_numbers(dislikes_elem.get_text(strip=True))[0] if dislikes_elem else 0

            # Extract reply count
            reply_count_elem = element.find('span', {'class': 'u_cbox_reply_cnt'})
            reply_count = TextUtils.extract_numbers(reply_count_elem.get_text(strip=True))[0] if reply_count_elem else 0

            return {
                'comment_no': comment_no,
                'parent_comment_no': parent_comment_no,
                'content': TextUtils.clean_html(content.get_text(strip=True)) if content else None,
                'username': username,
                'profile_url': profile_url,
                'timestamp': timestamp_value,
                'likes': likes,
                'dislikes': dislikes,
                'reply_count': reply_count,
                'is_reply': 'u_cbox_reply_item' in classes,
                'is_deleted': is_deleted,
                'delete_type': delete_type,
                'collected_at': DateUtils.format_date(
                    datetime.now(KST),
                    '%Y-%m-%dT%H:%M:%S%z',
                    timezone=KST
                )
            }

        except Exception as e:
            logger.error(f"[Comments] Error extracting comment data: {e}")
            return None

    def _extract_comment_stats(self, soup: Tag) -> Dict[str, Any]:
        """Extract comment statistics."""
        try:
            stats = self._get_empty_stats()

            # Extract comment count stats
            count_info = soup.select_one('.u_cbox_comment_count_wrap')
            if count_info:
                for info in count_info.select('.u_cbox_count_info'):
                    title_elem = info.select_one('.u_cbox_info_title')
                    count_elem = info.select_one('.u_cbox_info_txt')
                    if title_elem and count_elem:
                        title_text = TextUtils.clean_html(title_elem.get_text(strip=True))
                        count_numbers = TextUtils.extract_numbers(count_elem.get_text(strip=True))
                        count_value = count_numbers[0] if count_numbers else 0
                        if '현재' in title_text:
                            stats['current_count'] = count_value
                        elif '작성자' in title_text:
                            stats['user_deleted_count'] = count_value
                        elif '규정' in title_text:
                            stats['admin_deleted_count'] = count_value

            # Extract gender distribution
            male_elem = soup.select_one('.u_cbox_chart_male .u_cbox_chart_per')
            female_elem = soup.select_one('.u_cbox_chart_female .u_cbox_chart_per')
            if male_elem:
                male_percent = TextUtils.extract_numbers(male_elem.get_text(strip=True))
                stats['gender_ratio']['male'] = male_percent[0] if male_percent else 0
            if female_elem:
                female_percent = TextUtils.extract_numbers(female_elem.get_text(strip=True))
                stats['gender_ratio']['female'] = female_percent[0] if female_percent else 0

            # Extract age distribution
            age_progress_elems = soup.select('.u_cbox_chart_progress')
            age_keys = list(stats['age_distribution'].keys())
            for i, progress in enumerate(age_progress_elems):
                if i < len(age_keys):
                    per_elem = progress.select_one('.u_cbox_chart_per')
                    if per_elem:
                        age_percent = TextUtils.extract_numbers(per_elem.get_text(strip=True))
                        stats['age_distribution'][age_keys[i]] = age_percent[0] if age_percent else 0

            return stats

        except Exception as e:
            logger.error(f"[Comments] Error extracting comment stats: {e}")
            return self._get_empty_stats()

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics structure."""
        return {
            'current_count': 0,
            'user_deleted_count': 0,
            'admin_deleted_count': 0,
            'gender_ratio': {'male': 0, 'female': 0},
            'age_distribution': {
                '10s': 0, '20s': 0, '30s': 0,
                '40s': 0, '50s': 0, '60s_above': 0
            }
        }

    def _convert_to_comment_url(self, article_url: str) -> Optional[str]:
        """Convert article URL to comment page URL."""
        try:
            article_url = article_url.split('?')[0].rstrip('/')
            # Updated pattern to handle both mnews and regular URLs
            pattern = r'(https://n\.news\.naver\.com)/(?:(mnews|news)/)?article(?:/view)?/(\d+)/(\d+)(?:\?.*)?$'
            match = re.search(pattern, article_url)

            if match:
                domain = match.group(1)
                url_type = match.group(2) or 'news'  # Default to 'news' if not specified
                media_id = match.group(3)
                article_id = match.group(4)
                return f"{domain}/{url_type}/article/comment/{media_id}/{article_id}"

            return None

        except Exception as e:
            logger.error(f"[Comments] Error converting URL: {e}")
            return None

    async def _close_browser(self) -> None:
        """Close browser safely"""
        if self.driver:
            try:
                logger.info("[Comments] Closing browser...")
                await self._run_in_executor(self.driver_utils.quit_driver)
                self.driver = None
                logger.info("[Comments] Browser closed successfully")
            except Exception as e:
                logger.error(f"[Comments] Error closing browser: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info("[Comments] Starting cleanup...")
            await self._close_browser()
            logger.info("[Comments] Cleanup completed")
        except Exception as e:
            logger.error(f"[Comments] Error during cleanup: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# Example usage
async def main():
    """간단한 사용 예시"""
    article_url = "https://n.news.naver.com/article/123/4567890"

    collector = CommentCollector()
    try:
        result = await collector.collect(
            article_url=article_url,
            include_stats=True
        )
        print(result)
    finally:
        await collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
