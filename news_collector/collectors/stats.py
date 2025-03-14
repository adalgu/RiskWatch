"""
Statistics collector for articles and comments.
Collects various statistics including view counts, comment counts, and engagement metrics.
"""
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

from .base import BaseCollector
from ..core.utils import (
    initialize_driver,
    is_valid_naver_news_url
)

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


class StatsCollector(BaseCollector):
    """
    통계 수집기.
    기사와 댓글의 통계 정보를 수집합니다.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize stats collector.

        Args:
            config: Optional configuration containing:
                - browser_timeout: Browser wait timeout
                - retry_count: Maximum retry attempts
                - retry_delay: Delay between retries
        """
        super().__init__(config)
        self._init_config()
        self.driver = None
        self.wait = None

    def _init_config(self) -> None:
        """Initialize configuration with defaults."""
        self.browser_timeout = self.get_config('browser_timeout', 10)
        self.retry_count = self.get_config('retry_count', 3)
        self.retry_delay = self.get_config('retry_delay', 1)

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """
        Collect statistics.

        Args:
            **kwargs:
                - article_url: URL of the article
                - stats_type: Type of stats to collect ('article' or 'comment')

        Returns:
            Dict containing collected statistics
        """
        article_url = kwargs.get('article_url')
        if not article_url:
            raise ValueError("Article URL is required")

        stats_type = kwargs.get('stats_type', 'all')
        self.log_collection_start(kwargs)

        try:
            if stats_type == 'article':
                stats = await self.collect_article_stats(article_url)
            elif stats_type == 'comment':
                stats = await self.collect_comment_stats(article_url)
            else:
                # Collect both by default
                article_stats = await self.collect_article_stats(article_url)
                comment_stats = await self.collect_comment_stats(article_url)
                stats = {
                    'article': article_stats,
                    'comment': comment_stats,
                    'collected_at': datetime.now(KST).isoformat()
                }

            if await self.validate_async(stats):
                self.log_collection_end(True)
                return stats
            else:
                raise ValueError("Validation failed for collected stats")

        except Exception as e:
            self.log_collection_end(False, {'error': str(e)})
            raise

    async def collect_article_stats(self, article_url: str) -> Dict[str, Any]:
        """
        Collect article statistics.

        Args:
            article_url: Article URL

        Returns:
            Dict containing article statistics
        """
        if not is_valid_naver_news_url(article_url):
            logger.error(f"Invalid Naver News URL: {article_url}")
            return self._get_empty_article_stats()

        try:
            await self._initialize_browser()
            self.driver.get(article_url)

            # 기사 영역 로딩 대기
            try:
                await self.wait.until(
                    EC.presence_of_element_located((By.ID, "articleBody"))
                )
            except TimeoutException:
                logger.error("Article body not found")
                return self._get_empty_article_stats()

            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            return await self._extract_article_stats(soup)

        except Exception as e:
            logger.error(f"Error collecting article stats: {e}")
            return self._get_empty_article_stats()

        finally:
            await self._close_browser()

    async def collect_comment_stats(self, article_url: str) -> Dict[str, Any]:
        """
        Collect comment statistics.

        Args:
            article_url: Article URL

        Returns:
            Dict containing comment statistics
        """
        if not is_valid_naver_news_url(article_url):
            logger.error(f"Invalid Naver News URL: {article_url}")
            return self._get_empty_comment_stats()

        try:
            await self._initialize_browser()

            # 댓글 페이지로 변환
            comment_url = article_url.replace('/article/', '/article/comment/')
            self.driver.get(comment_url)

            # 댓글 영역 로딩 대기
            try:
                await self.wait.until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "u_cbox_content_wrap"))
                )
            except TimeoutException:
                logger.error("Comment area not found")
                return self._get_empty_comment_stats()

            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            return await self._extract_comment_stats(soup)

        except Exception as e:
            logger.error(f"Error collecting comment stats: {e}")
            return self._get_empty_comment_stats()

        finally:
            await self._close_browser()

    async def _extract_article_stats(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract article statistics from page."""
        stats = self._get_empty_article_stats()

        try:
            # 조회수
            view_count = soup.select_one('.press_view_count')
            if view_count:
                stats['view_count'] = int(
                    view_count.get_text(strip=True).replace(',', ''))

            # 좋아요/싫어요
            reaction_area = soup.select_one('.press_reaction')
            if reaction_area:
                like_count = reaction_area.select_one('.like_count')
                if like_count:
                    stats['like_count'] = int(
                        like_count.get_text(strip=True).replace(',', ''))

                dislike_count = reaction_area.select_one('.dislike_count')
                if dislike_count:
                    stats['dislike_count'] = int(
                        dislike_count.get_text(strip=True).replace(',', ''))

            # 공유
            share_count = soup.select_one('.share_count')
            if share_count:
                stats['share_count'] = int(
                    share_count.get_text(strip=True).replace(',', ''))

            stats['collected_at'] = datetime.now(KST).isoformat()
            return stats

        except Exception as e:
            logger.error(f"Error extracting article stats: {e}")
            return stats

    async def _extract_comment_stats(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract comment statistics from page."""
        stats = self._get_empty_comment_stats()

        try:
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

            # 댓글 반응
            stats['reactions'] = {
                'total_likes': 0,
                'total_dislikes': 0,
                'avg_likes_per_comment': 0,
                'avg_dislikes_per_comment': 0
            }

            like_counts = soup.select('.u_cbox_cnt_recomm')
            dislike_counts = soup.select('.u_cbox_cnt_unrecomm')

            total_likes = sum(int(like.get_text(strip=True))
                              for like in like_counts if like.get_text(strip=True).isdigit())
            total_dislikes = sum(int(dislike.get_text(
                strip=True)) for dislike in dislike_counts if dislike.get_text(strip=True).isdigit())

            stats['reactions']['total_likes'] = total_likes
            stats['reactions']['total_dislikes'] = total_dislikes

            if stats['current_count'] > 0:
                stats['reactions']['avg_likes_per_comment'] = round(
                    total_likes / stats['current_count'], 2)
                stats['reactions']['avg_dislikes_per_comment'] = round(
                    total_dislikes / stats['current_count'], 2)

            stats['collected_at'] = datetime.now(KST).isoformat()
            return stats

        except Exception as e:
            logger.error(f"Error extracting comment stats: {e}")
            return stats

    def _get_empty_article_stats(self) -> Dict[str, Any]:
        """Get empty article statistics structure."""
        return {
            'view_count': 0,
            'like_count': 0,
            'dislike_count': 0,
            'share_count': 0,
            'collected_at': datetime.now(KST).isoformat()
        }

    def _get_empty_comment_stats(self) -> Dict[str, Any]:
        """Get empty comment statistics structure."""
        return {
            'current_count': 0,
            'user_deleted_count': 0,
            'admin_deleted_count': 0,
            'gender_ratio': {
                'male': 0,
                'female': 0
            },
            'age_distribution': {
                '10s': 0,
                '20s': 0,
                '30s': 0,
                '40s': 0,
                '50s': 0,
                '60s_above': 0
            },
            'reactions': {
                'total_likes': 0,
                'total_dislikes': 0,
                'avg_likes_per_comment': 0,
                'avg_dislikes_per_comment': 0
            },
            'collected_at': datetime.now(KST).isoformat()
        }

    async def _initialize_browser(self) -> None:
        """Initialize browser if not already initialized."""
        if not self.driver:
            self.driver = initialize_driver()
            self.wait = WebDriverWait(self.driver, self.browser_timeout)

    async def _close_browser(self) -> None:
        """Close browser if open."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._close_browser()
