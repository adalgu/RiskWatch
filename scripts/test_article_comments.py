"""
Test script for collecting comments from articles.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote, urlencode
import re

from news_collector.collectors.comments import CommentCollector
from news_storage.database import AsyncDatabaseOperations
from news_storage.config import AsyncStorageSessionLocal
from news_storage.models import Article, Comment
from news_collector.core.utils import WebDriverUtils

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')


class ArticleCommentTester:
    """Test article collection and comment collection"""
    
    def __init__(self):
        self.collector = CommentCollector()
        self.driver_utils = WebDriverUtils(
            headless=True,
            use_remote=True,
            remote_url="http://selenium-hub:4444/wd/hub"
        )
        self.driver = None
        self.wait = None

    async def _initialize_browser(self) -> None:
        """Initialize browser if not already initialized"""
        if not self.driver:
            self.driver = self.driver_utils.initialize_driver()
            self.wait = WebDriverWait(self.driver, 20)

    async def _close_browser(self) -> None:
        """Close browser if open"""
        if self.driver:
            self.driver_utils.quit_driver()
            self.driver = None
            self.wait = None

    def _format_date(self, date: datetime) -> str:
        """Format date for Naver News search"""
        return date.strftime('%Y.%m.%d.')

    async def collect_articles(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Collect articles using Naver News search
        """
        articles = []
        page = 1
        
        try:
            await self._initialize_browser()
            
            # 검색 URL 생성
            params = {
                'query': keyword,
                'sort': 'rel.dsc',  # 관련도순
                'ds': self._format_date(start_date),
                'de': self._format_date(end_date),
                'nso': f'so:dd,p:from{start_date.strftime("%Y%m%d")}to{end_date.strftime("%Y%m%d")}',
                'where': 'news'
            }
            search_url = f"https://search.naver.com/search.naver?{urlencode(params)}"
            
            logger.info(f"Accessing search URL: {search_url}")
            self.driver.get(search_url)
            
            while True:
                try:
                    # 뉴스 목록 대기
                    news_list = self.wait.until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "ul.list_news > li")
                        )
                    )
                    
                    for news_item in news_list:
                        try:
                            # 네이버 뉴스 링크 찾기
                            naver_link = news_item.find_element(
                                By.CSS_SELECTOR,
                                "div.info_group > a.info:nth-child(3)"
                            ).get_attribute("href")
                            
                            if not naver_link or 'news.naver.com' not in naver_link:
                                continue
                            
                            # 기사 정보 추출
                            title = news_item.find_element(
                                By.CSS_SELECTOR,
                                "a.news_tit"
                            ).text
                            
                            description = news_item.find_element(
                                By.CSS_SELECTOR,
                                "div.news_dsc"
                            ).text
                            
                            press = news_item.find_element(
                                By.CSS_SELECTOR,
                                "a.press"
                            ).text
                            
                            date_text = news_item.find_element(
                                By.CSS_SELECTOR,
                                "span.info"
                            ).text
                            
                            # 날짜 파싱
                            date_match = re.search(r'(\d{4}\.\d{2}\.\d{2}\.)', date_text)
                            if date_match:
                                pub_date = datetime.strptime(
                                    date_match.group(1),
                                    '%Y.%m.%d.'
                                ).replace(tzinfo=KST)
                            else:
                                continue
                            
                            articles.append({
                                'title': title,
                                'description': description,
                                'naver_link': naver_link,
                                'publisher': press,
                                'published_at': pub_date.isoformat(),
                                'is_naver_news': True,
                                'is_test': True,
                                'is_api_collection': False,
                                'collected_at': datetime.now(KST).isoformat()
                            })
                            
                        except NoSuchElementException:
                            continue
                    
                    # 다음 페이지 버튼 찾기
                    try:
                        next_button = self.driver.find_element(
                            By.CSS_SELECTOR,
                            f"a.btn_next[aria-disabled='false']"
                        )
                        next_button.click()
                        page += 1
                        await asyncio.sleep(1)
                    except NoSuchElementException:
                        break
                    
                except TimeoutException:
                    break
            
            logger.info(f"Collected {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error collecting articles: {e}")
            return articles
        finally:
            await self._close_browser()

    async def store_article(self, article_data: Dict[str, Any], main_keyword: str) -> Optional[Article]:
        """Store article in database"""
        try:
            async with AsyncStorageSessionLocal() as session:
                article = await AsyncDatabaseOperations.create_article(
                    session=session,
                    article_data=article_data,
                    main_keyword=main_keyword
                )
                await session.commit()
                return article
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return None

    async def collect_comments(self, article_url: str) -> Dict[str, Any]:
        """Collect comments for an article"""
        try:
            result = await self.collector.collect(
                article_url=article_url,
                is_test=True,
                include_stats=False
            )
            comments = result.get('comments', [])
            total_count = result.get('total_count', 0)
            logger.info(f"Collected {len(comments)} comments (total count: {total_count})")
            return result
        except Exception as e:
            logger.error(f"Error collecting comments: {e}")
            return {'comments': [], 'total_count': 0}

    async def store_comments(self, article_id: int, comments: List[Dict[str, Any]]) -> bool:
        """Store comments in database"""
        try:
            if not comments:
                logger.info("No comments to store")
                return True

            async with AsyncStorageSessionLocal() as session:
                await AsyncDatabaseOperations.batch_create_comments(
                    session=session,
                    comments_data=comments,
                    article_id=article_id
                )
                await session.commit()
                logger.info(f"Successfully stored {len(comments)} comments")
                return True
        except Exception as e:
            logger.error(f"Error storing comments: {e}")
            return False

    async def run_test(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Run the complete test process"""
        test_results = {
            'success': False,
            'message': '',
            'details': {
                'articles_collected': 0,
                'articles_with_comments': 0,
                'total_comments': 0,
                'articles': []
            }
        }

        try:
            # 기사 수집
            articles = await self.collect_articles(keyword, start_date, end_date)
            test_results['details']['articles_collected'] = len(articles)
            
            if not articles:
                test_results.update({
                    'success': True,
                    'message': 'No articles found for the given criteria'
                })
                return test_results

            # 각 기사의 댓글 수집
            for article in articles:
                # 기사 저장
                stored_article = await self.store_article(article, keyword)
                if not stored_article:
                    continue

                # 댓글 수집
                result = await self.collect_comments(article['naver_link'])
                comments = result.get('comments', [])
                
                # 댓글 저장
                if await self.store_comments(stored_article.id, comments):
                    if comments:
                        test_results['details']['articles_with_comments'] += 1
                        test_results['details']['total_comments'] += len(comments)
                    
                    test_results['details']['articles'].append({
                        'title': article['title'],
                        'naver_link': article['naver_link'],
                        'comment_count': len(comments)
                    })

            test_results.update({
                'success': True,
                'message': '✅ Test completed successfully'
            })

        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            test_results.update({
                'success': False,
                'message': f'Test failed: {str(e)}'
            })
        finally:
            await self.collector.cleanup()

        return test_results


async def main():
    """Run integration tests"""
    logger.info("Starting Article Comment Collection Test")
    
    # 테스트 기간 설정 (2023년으로 변경)
    start_date = datetime(2023, 10, 1, tzinfo=KST)
    end_date = datetime(2023, 10, 3, tzinfo=KST)
    
    tester = ArticleCommentTester()
    try:
        results = await tester.run_test("김건희", start_date, end_date)
        if results['success']:
            logger.info(f"✅ Integration test completed successfully: {results['message']}")
            logger.info("Test details:")
            logger.info(f"- Articles collected: {results['details']['articles_collected']}")
            logger.info(f"- Articles with comments: {results['details']['articles_with_comments']}")
            logger.info(f"- Total comments: {results['details']['total_comments']}")
            logger.info("\nArticles:")
            for article in results['details']['articles']:
                logger.info(f"- {article['title']}: {article['comment_count']} comments")
        else:
            logger.error(f"Integration test failed: {results['message']}")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())
