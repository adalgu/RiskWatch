"""
News content collector with async support and improved error handling.
news_collector/collectors/content.py


Examples:
# 본문 수집
>>> collector = ContentCollector()
>>> result = await collector.collect(
...     article_url='https://n.news.naver.com/article/001/0012345678'
... )

# 명령줄 실행:
$ python -m news_system.news_collector.collectors.content --article_url "https://n.news.naver.com/mnews/article/008/0005118577"
"""
import logging
import json
import argparse
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
import pytz
from bs4 import BeautifulSoup, NavigableString
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from .base import BaseCollector
from .utils.webdriver_utils import WebDriverUtils
from ..producer import Producer  # Import the new Producer
from .utils.date import DateUtils
from .utils.text import TextUtils

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


class ContentCollector(BaseCollector):
    """
    뉴스 본문 수집기.
    기사의 상세 내용을 수집합니다.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize content collector.
        """
        super().__init__(config)
        self._init_config()
        self.proxy = self.get_config('proxy')
        self.user_agent = self.get_config('user_agent')
        self.driver_utils = WebDriverUtils(
            headless=True,
            proxy=self.proxy,
            user_agent=self.user_agent,
            use_remote=True,
            remote_url="http://selenium-hub/wd/hub"
        )
        self.driver = None
        self.wait = None
        
        # Initialize Producer
        self.producer = Producer()
        self.queue_name = 'content_queue'

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.retry_count = self.get_config('retry_count', 3)
        self.retry_delay = self.get_config('retry_delay', 2)
        self.browser_timeout = self.get_config('browser_timeout', 10)

    async def publish_message(self, message: Dict[str, Any]) -> None:
        """Publish message to RabbitMQ using Producer"""
        await self.producer.publish(
            message=message,
            queue_name=self.queue_name
        )
        logger.info(f"Published message to RabbitMQ queue '{self.queue_name}'")

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """
        Collect article content.

        Args:
            **kwargs:
                - article_url: URL of the article to collect
                - include_comments: Whether to collect comments (default: False)

        Returns:
            Dict containing article content and metadata
        """
        article_url = kwargs.get('article_url')
        if not article_url:
            raise ValueError("Article URL is required")

        self.log_collection_start(kwargs)

        try:
            content = await self.collect_content(article_url)

            result = {
                'article_url': article_url,
                'full_text': content.get('content', ''),
                'title': content.get('title', ''),
                'metadata': {
                    'media': content.get('media', ''),
                    'reporter': content.get('reporter', ''),
                    'category': content.get('category', ''),
                    'published_at': content.get('published_at', ''),
                    'modified_at': content.get('modified_at', '')
                },
                'subheadings': content.get('subheadings', []),
                'images': content.get('images', []),
                'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
            }

            if await self.validate_async(result):
                # Publish to RabbitMQ using new Producer
                await self.publish_message(result)
                
                self.log_collection_end(True)
                return result
            else:
                raise ValueError("Validation failed for collected content")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def collect_content(self, article_url: str) -> Optional[Dict[str, Any]]:
        """
        Collect article content from URL.

        Args:
            article_url: URL of the article

        Returns:
            Dict containing article content and metadata
        """
        try:
            await self._initialize_browser()

            for attempt in range(self.retry_count):
                try:
                    await self._run_in_executor(self.driver.get, article_url)

                    # 본문 영역 로딩 대기
                    await self._run_in_executor(
                        lambda: self.driver_utils.wait_for_element(
                            By.ID, "dic_area", self.browser_timeout
                        )
                    )
                    await asyncio.sleep(1)  # 추가 컨텐츠 로딩 대기

                    return await self._extract_content()

                except TimeoutException:
                    if attempt < self.retry_count - 1:
                        logger.warning(
                            f"Retry {attempt + 1}/{self.retry_count} for URL: {article_url}")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error(f"Content loading timeout: {article_url}")
                        return None

        except Exception as e:
            logger.error(f"Error collecting content: {str(e)}")
            return None

        finally:
            await self._close_browser()

    def _process_content_element(self, element: Any) -> str:
        """Process a content element and return its text."""
        if isinstance(element, NavigableString):
            return str(element)

        # Skip certain elements
        if element.name in ['script', 'style']:
            return ''

        # Process text content
        text = ''
        for child in element.children:
            if isinstance(child, NavigableString):
                text += str(child)
            else:
                child_text = self._process_content_element(child)
                if child.name == 'br':
                    text += '\n'
                elif child_text:
                    text += child_text
                    if child.name in ['p', 'div']:
                        text += '\n'

        return text.strip()

    def _extract_image_info(self, img_elem: Any) -> Dict[str, str]:
        """Extract image information including caption."""
        image_info = {
            'url': img_elem.get('src', ''),
            'caption': '',
            'alt': img_elem.get('alt', '')
        }

        # Find associated caption
        caption_elem = img_elem.find_next('em', class_='img_desc')
        if caption_elem:
            image_info['caption'] = caption_elem.get_text(strip=True)

        return image_info

    async def _extract_content(self) -> Dict[str, Any]:
        """Extract content from loaded page."""
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # 제목
        title = ''
        title_elem = soup.find('h2', {'id': 'title_area'})
        if title_elem:
            title_span = title_elem.find('span')
            if title_span:
                title = TextUtils.clean_html(title_span.get_text(strip=True))

        # 본문
        content = ''
        subheadings = []
        content_elem = soup.find('article', {'id': 'dic_area'})
        if content_elem:
            # 서브헤딩 (strong 태그) 처리
            strong_tags = content_elem.find_all('strong')
            for strong in strong_tags:
                subheading = TextUtils.clean_html(strong.get_text(strip=True))
                if subheading:
                    subheadings.append(subheading)
                    strong.extract()  # 본문에서 제거

            # 본문 텍스트 처리
            content = self._process_content_element(content_elem)

        # 기자 정보
        reporter = ''
        reporter_elem = soup.find('span', {'class': 'byline_s'})
        if reporter_elem:
            reporter = TextUtils.clean_html(reporter_elem.get_text(strip=True))

        # 언론사
        media = ''
        media_elem = soup.find('a', {'class': 'media_end_head_top_logo'})
        if media_elem:
            img = media_elem.find('img')
            if img and img.has_attr('alt'):
                media = TextUtils.clean_html(img['alt'].strip())

        # 작성일시
        published_at = ''
        date_elem = soup.find(
            'span', {'class': 'media_end_head_info_datestamp_time'})
        if date_elem:
            raw_date = date_elem.get('data-date-time', '')
            dt = DateUtils.parse_date(raw_date, timezone=KST)
            if dt:
                published_at = DateUtils.format_date(dt, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)

        # 수정일시
        modified_at = ''
        mod_elem = soup.find(
            'span', {'class': 'media_end_head_info_datestamp_time _MODIFY_DATE_TIME'})
        if mod_elem:
            raw_mod_date = mod_elem.get('data-modify-date-time', '')
            dt_mod = DateUtils.parse_date(raw_mod_date, timezone=KST)
            if dt_mod:
                modified_at = DateUtils.format_date(dt_mod, '%Y-%m-%dT%H:%M:%S%z', timezone=KST)

        # 카테고리 (em 태그에서 직접 추출)
        category = ''
        category_elem = soup.find('em', {'class': 'media_end_categorize_item'})
        if category_elem:
            category = TextUtils.clean_html(category_elem.get_text(strip=True))

        # 이미지
        images = []
        if content_elem:
            img_elems = content_elem.find_all('img')
            for img in img_elems:
                if img.has_attr('src'):
                    image_info = self._extract_image_info(img)
                    images.append(image_info)

        return {
            'title': title,
            'subheadings': subheadings,
            'content': content,
            'reporter': reporter,
            'media': media,
            'published_at': published_at,
            'modified_at': modified_at,
            'category': category,
            'images': images
        }

    async def collect_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Collect content from multiple URLs.

        Args:
            urls: List of article URLs

        Returns:
            List of article contents
        """
        results = []
        for url in urls:
            try:
                content = await self.collect_content(url)
                if content:
                    results.append(content)
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error collecting from {url}: {e}")
                continue
        return results

    async def _initialize_browser(self) -> None:
        """Initialize browser if not already initialized."""
        if not self.driver:
            self.driver = self.driver_utils.initialize_driver()
            self.wait = WebDriverWait(self.driver, self.browser_timeout)

    async def _close_browser(self) -> None:
        """Close browser if open."""
        if self.driver:
            await self._run_in_executor(self.driver.quit)
            self.driver = None
            self.wait = None
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._close_browser()
        # Close Producer connection
        await self.producer.close()

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
    parser = argparse.ArgumentParser(description='네이버 뉴스 본문 수집기')
    parser.add_argument('--article_url', required=True,
                        help='본문을 수집할 기사 URL')
    args = parser.parse_args()

    collector = ContentCollector()
    try:
        result = await collector.collect(
            article_url=args.article_url
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await collector.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
