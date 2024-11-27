"""
News comment collector with async support and improved error handling.
Collects both comments and comment statistics.
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
import aio_pika

from ..collectors.base import BaseCollector
from ..core.utils import WebDriverUtils

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')


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
            remote_url="http://selenium-hub:4444/wd/hub"
        )
        self.driver = None
        self.wait = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.browser_timeout = self.get_config(
            'browser_timeout', 20)  # Increased timeout
        self.max_retries = self.get_config('max_retries', 50)
        self.retry_delay = self.get_config('retry_delay', 1)

    async def setup_rabbitmq(self):
        """Setup RabbitMQ connection and channel"""
        if not self.rabbitmq_connection:
            self.rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            await self.rabbitmq_channel.declare_queue('comments_queue', durable=True)

    async def publish_message(self, data: Dict[str, Any]):
        """Publish message to RabbitMQ"""
        try:
            await self.setup_rabbitmq()
            message = {
                'type': 'comments',
                'article_url': data.get('article_url'),
                'comments': data.get('comments', [])
            }
            await self.rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='comments_queue'
            )
            logger.info(f"Published {len(data.get('comments', []))} comments to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}")
            raise

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
            # Changed to pass kwargs directly instead of article_url separately
            result = await self.collect_comments(**kwargs)

            if await self.validate_async(result):
                # Publish comments to RabbitMQ
                await self.publish_message({
                    'article_url': article_url,
                    'comments': result.get('comments', [])
                })

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
            'collected_at': datetime.now(KST).isoformat(),
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
            self.driver.get(comment_url)

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
                    dt = datetime.strptime(raw_timestamp, '%Y-%m-%d %H:%M:%S')
                    return KST.localize(dt).isoformat()
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
                return int(count_element.get_text(strip=True))
            return 0

        except Exception as e:
            logger.error(f"Error extracting comment count: {e}")
            return 0

    async def _wait_for_comment_area(self) -> bool:
        """Wait for comment area to load."""
        selectors = [
            'u_cbox_content_wrap',
            'u_cbox_list',
            'cbox_module',
            'u_cbox_view_comment'
        ]

        logger.info("Waiting for comment area to load...")
        for selector in selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                await self._run_in_executor(
                    lambda: self.driver_utils.wait_for_element(
                        By.CLASS_NAME, selector, self.browser_timeout
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
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.5)

                        try:
                            element.click()
                        except:
                            self.driver.execute_script(
                                "arguments[0].click();", element)

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
            pattern = r'/(?:m)?(?:news|mnews)/(?:article|article/view)/(\d+)/(\d+)(?:\?.*)?$'
            match = re.search(pattern, article_url)

            if match:
                media_id = match.group(1)
                article_id = match.group(2)
                return f"https://n.news.naver.com/article/comment/{media_id}/{article_id}"

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
            is_deleted = 'u_cbox_type_delete' in element.get('class', [])
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
            username = element.find('span', {'class': 'u_cbox_nick'})
            profile_img = element.find('img', {'class': 'u_cbox_img_profile'})
            profile_url = profile_img.get('src') if profile_img else None

            # 작성 시간
            timestamp = element.find('span', {'class': 'u_cbox_date'})
            timestamp_value = None
            if timestamp:
                raw_timestamp = timestamp.get('data-value')
                if raw_timestamp:
                    try:
                        # 타임존 정보가 포함된 경우 (예: 2024-11-25T06:45:36+0900)
                        if '+0900' in raw_timestamp:
                            dt = datetime.strptime(
                                raw_timestamp, '%Y-%m-%dT%H:%M:%S%z')
                            timestamp_value = dt.isoformat()
                        else:
                            # 타임존 정보가 없는 경우
                            dt = datetime.strptime(
                                raw_timestamp, '%Y-%m-%d %H:%M:%S')
                            timestamp_value = KST.localize(dt).isoformat()
                    except ValueError:
                        timestamp_value = timestamp.get_text(strip=True)

            # 좋아요/싫어요
            likes = element.find('em', {'class': 'u_cbox_cnt_recomm'})
            dislikes = element.find('em', {'class': 'u_cbox_cnt_unrecomm'})

            # 답글 수
            reply_count = element.find('span', {'class': 'u_cbox_reply_cnt'})
            reply_count = int(reply_count.get_text(
                strip=True)) if reply_count else 0

            return {
                'comment_no': comment_no,
                'parent_comment_no': parent_comment_no,
                'content': content.get_text(strip=True) if content else None,
                'username': username.get_text(strip=True) if username else '익명',
                'profile_url': profile_url,
                'timestamp': timestamp_value,
                'likes': int(likes.get_text(strip=True)) if likes else 0,
                'dislikes': int(dislikes.get_text(strip=True)) if dislikes else 0,
                'reply_count': reply_count,
                'is_reply': 'u_cbox_reply_item' in element.get('class', []),
                'is_deleted': is_deleted,
                'delete_type': delete_type,
                'collected_at': datetime.now(KST).isoformat()
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
                    title = info.select_one('.u_cbox_info_title')
                    count = info.select_one('.u_cbox_info_txt')
                    if title and count:
                        title_text = title.get_text(strip=True)
                        count_value = int(count.get_text(
                            strip=True).replace(',', ''))
                        if '현재' in title_text:
                            stats['current_count'] = count_value
                        elif '작성자' in title_text:
                            stats['user_deleted_count'] = count_value
                        elif '규정' in title_text:
                            stats['admin_deleted_count'] = count_value

            # 성별 분포
            male = soup.select_one('.u_cbox_chart_male .u_cbox_chart_per')
            female = soup.select_one('.u_cbox_chart_female .u_cbox_chart_per')
            if male:
                stats['gender_ratio']['male'] = int(
                    male.get_text(strip=True).replace('%', ''))
            if female:
                stats['gender_ratio']['female'] = int(
                    female.get_text(strip=True).replace('%', ''))

            # 연령대 분포
            age_progress = soup.select('.u_cbox_chart_progress')
            age_keys = list(stats['age_distribution'].keys())
            for i, progress in enumerate(age_progress):
                if i < len(age_keys):
                    per = progress.select_one('.u_cbox_chart_per')
                    if per:
                        stats['age_distribution'][age_keys[i]] = int(
                            per.get_text(strip=True).replace('%', ''))

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
            self.driver_utils.quit_driver()
            self.driver = None
            self.wait = None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._close_browser()
        if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
            await self.rabbitmq_connection.close()

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
