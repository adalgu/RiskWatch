"""
News comment collector with async support and improved error handling.
Collects both comments and comment statistics.

news_collector/collectors/comments.py
"""

import os
import logging
import asyncio
import argparse
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import re
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from bs4 import BeautifulSoup, Tag

from .base import BaseCollector
from .utils.date import DateUtils
from .utils.text import TextUtils
from .utils.url import UrlUtils
from .utils.webdriver_utils import WebDriverUtils
from ..producer import Producer  # Import the new Producer

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
            use_remote=True,
        )
        self.driver = None
        self.wait = None
        
        # Initialize Producer
        self.producer = Producer()
        self.queue_name = 'comments_queue'

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.browser_timeout = self.get_config(
            'browser_timeout', 20)  # Increased timeout
        self.max_retries = self.get_config('max_retries', 50)
        self.retry_delay = self.get_config('retry_delay', 1)

    async def publish_message(self, data: Dict[str, Any]):
        """Publish message to RabbitMQ using Producer"""
        message = {
            'article_url': data.get('article_url'),
            'type': 'comments',
            'comments': data.get('comments', []),
            'stats': data.get('stats', {}),
            'total_count': data.get('total_count', 0),
            'published_at': data.get('published_at'),
            'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
        }
        
        await self.producer.publish(
            message=message,
            queue_name=self.queue_name
        )
        logger.info(f"Published {len(data.get('comments', []))} comments to RabbitMQ")

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """
        Collect comments and statistics.

        Args:
            **kwargs:
                - article_url: URL of the article
                - include_stats: Whether to collect statistics (default: True)

        Returns:
            Dict containing comments and metadata
        """
        article_url = kwargs.get('article_url')
        if not article_url:
            raise ValueError("Article URL is required")

        self.log_collection_start(kwargs)

        try:
            result = await self.collect_comments(**kwargs)

            if await self.validate_async(result):
                # Add article_url to result for publishing
                result['article_url'] = article_url
                
                # Publish to RabbitMQ using Producer
                await self.publish_message(result)

                self.log_collection_end(True, {
                    'total_comments': len(result['comments']),
                    'total_count': result['total_count']
                })
                return result
            else:
                raise ValueError("Validation failed for collected comments")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def collect_comments(self, article_url: str, **kwargs) -> Dict[str, Any]:
        """
        Collect comments from article URL.

        Args:
            article_url: Article URL
            **kwargs: Additional parameters

        Returns:
            Dict containing comments and statistics
        """
        include_stats = kwargs.get('include_stats', True)
        result = {
            'total_count': 0,
            'published_at': None,  # Changed from article_timestamp to published_at
            'stats': self._get_empty_stats(),
            'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST),
            'comments': []
        }

        try:
            await self._initialize_browser()

            # 댓글 페이지 URL로 변환
            comment_url = self._convert_to_comment_url(article_url)
            if not comment_url:
                logger.error(
                    f"Failed to convert to comment URL: {article_url}")
                return result

            logger.info(f"Accessing comment URL: {comment_url}")
            await self._run_in_executor(self.driver.get, comment_url)

            # 댓글 영역 로딩 대기
            if not await self._wait_for_comment_area():
                logger.warning("Comment area not found")
                return result

            # 기사 발행 시간 추출
            published_at = self._extract_article_timestamp(
                self.driver.page_source)
            if published_at:
                result['published_at'] = published_at

            # 댓글 수 추출 (u_cbox_count 태그 사용)
            total_count = self._extract_comment_count(self.driver.page_source)
            result['total_count'] = total_count

            # 댓글이 없는 경우 빈 결과 반환
            if total_count == 0:
                logger.info("No comments found")
                return result

            # 모든 댓글 로드
            await self._load_all_comments()

            # 페이지 파싱
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # 통계 수집 (선택적)
            if include_stats:
                try:
                    result['stats'] = self._extract_comment_stats(soup)
                except Exception as e:
                    logger.warning(f"Failed to extract comment stats: {e}")
                    # 통계 수집 실패해도 계속 진행

            # 댓글 추출
            comments = []
            comment_elements = self._find_comment_elements(soup)

            for element in comment_elements:
                comment_data = self._extract_comment_data(element)
                if comment_data:
                    comments.append(comment_data)

            result['comments'] = comments

            logger.info(
                f"Collected {len(comments)} comments out of {total_count}")
            return result

        except Exception as e:
            logger.error(f"Error collecting comments: {str(e)}")
            return result

        finally:
            await self._close_browser()

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
            logger.error(f"Error extracting article timestamp: {e}")
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
            logger.error(f"Error extracting comment count: {e}")
            return 0

    async def _wait_for_comment_area(self) -> bool:
        """Wait for comment area to load."""
        selectors = [
            '.u_cbox_content_wrap',
            '.u_cbox_list',
            '.cbox_module',
            '.u_cbox_view_comment'
        ]

        logger.info("Waiting for comment area to load...")
        for selector in selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                await self._run_in_executor(
                    lambda: self.driver_utils.wait_for_element(
                        By.CSS_SELECTOR, selector, self.browser_timeout
                    )
                )
                logger.info(f"Found comment area with selector: {selector}")
                return True
            except TimeoutException:
                logger.warning(f"Selector not found: {selector}")
                continue
        return False

    async def _load_all_comments(self) -> None:
        """Load all comments by clicking 'more' button."""
        retry_count = 0
        consecutive_failures = 0
        last_comment_count = 0

        while retry_count < self.max_retries and consecutive_failures < 3:
            current_count = len(self._get_current_comments())

            if current_count == last_comment_count:
                consecutive_failures += 1
            else:
                consecutive_failures = 0
                last_comment_count = current_count

            if not await self._click_more_button():
                break

            retry_count += 1
            await asyncio.sleep(self.retry_delay)

    def _get_current_comments(self) -> List:
        """Get current comment elements."""
        return self.driver.find_elements(
            By.CSS_SELECTOR,
            'div.u_cbox_comment, div.u_cbox_reply_item, li.u_cbox_comment, li.u_cbox_reply_item'
        )

    async def _click_more_button(self) -> bool:
        """Click 'more' button to load additional comments."""
        try:
            # 더보기 버튼 찾기
            selectors = [
                "a.u_cbox_btn_more",
                "span.u_cbox_page_more",
                "span.u_cbox_box_more"
            ]

            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        # 버튼이 보이도록 스크롤
                        await self._run_in_executor(
                            lambda: self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", element))
                        await asyncio.sleep(0.5)

                        try:
                            await self._run_in_executor(element.click)
                        except:
                            await self._run_in_executor(
                                lambda: self.driver.execute_script("arguments[0].click();", element))

                        return True

            return False

        except Exception as e:
            logger.debug(f"Error clicking more button: {e}")
            return False

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
            logger.error(f"Error converting URL: {e}")
            return None

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
            # 댓글 ID 추출
            comment_id = element.get('data-info', '')
            comment_no = None
            parent_comment_no = None

            if comment_id:
                comment_match = re.search(r"commentNo:'([^']+)'", comment_id)
                parent_match = re.search(
                    r"parentCommentNo:'([^']+)'", comment_id)
                comment_no = comment_match.group(1) if comment_match else None
                parent_comment_no = parent_match.group(
                    1) if parent_match else None

            # 삭제 여부 확인
            classes = element.get('class', [])
            is_deleted = 'u_cbox_type_delete' in classes
            delete_type = None
            if is_deleted:
                delete_msg = element.find(
                    'span', {'class': 'u_cbox_delete_contents'})
                if delete_msg:
                    msg_text = delete_msg.get_text(strip=True)
                    delete_type = 'user' if '작성자' in msg_text else 'admin'

            # 내용 추출
            content = None
            for class_name in ['u_cbox_contents', 'u_cbox_text', 'comment_text']:
                content = element.find('span', {'class': class_name})
                if content:
                    break

            if not content and not is_deleted:
                return None

            # 작성자 정보
            username_elem = element.find('span', {'class': 'u_cbox_nick'})
            username = username_elem.get_text(strip=True) if username_elem else '익명'

            profile_img = element.find('img', {'class': 'u_cbox_img_profile'})
            profile_url = profile_img.get('src') if profile_img else None

            # 작성 시간
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

            # 좋아요/싫어요
            likes_elem = element.find('em', {'class': 'u_cbox_cnt_recomm'})
            dislikes_elem = element.find('em', {'class': 'u_cbox_cnt_unrecomm'})
            likes = TextUtils.extract_numbers(likes_elem.get_text(strip=True))[0] if likes_elem else 0
            dislikes = TextUtils.extract_numbers(dislikes_elem.get_text(strip=True))[0] if dislikes_elem else 0

            # 답글 수
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
                'collected_at': DateUtils.format_date(datetime.now(KST), '%Y-%m-%dT%H:%M:%S%z', timezone=KST)
            }

        except Exception as e:
            logger.error(f"Error extracting comment data: {e}")
            return None

    def _extract_comment_stats(self, soup: Tag) -> Dict[str, Any]:
        """Extract comment statistics."""
        try:
            stats = self._get_empty_stats()

            # 댓글 수 통계
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

            # 성별 분포
            male_elem = soup.select_one('.u_cbox_chart_male .u_cbox_chart_per')
            female_elem = soup.select_one('.u_cbox_chart_female .u_cbox_chart_per')
            if male_elem:
                male_percent = TextUtils.extract_numbers(male_elem.get_text(strip=True))
                stats['gender_ratio']['male'] = male_percent[0] if male_percent else 0
            if female_elem:
                female_percent = TextUtils.extract_numbers(female_elem.get_text(strip=True))
                stats['gender_ratio']['female'] = female_percent[0] if female_percent else 0

            # 연령대 분포
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
            logger.error(f"Error extracting comment stats: {e}")
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
    parser = argparse.ArgumentParser(description='네이버 뉴스 댓글 수집기')
    parser.add_argument('--article_url', required=True,
                        help='댓글을 수집할 기사 URL')
    parser.add_argument('--no-stats', action='store_true',
                        help='통계 정보 수집 제외')
    args = parser.parse_args()

    collector = CommentCollector()
    try:
        result = await collector.collect(
            article_url=args.article_url,
            include_stats=not args.no_stats
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await collector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
