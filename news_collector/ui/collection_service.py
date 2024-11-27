"""
Data collection module for the dashboard application.
Provides functions for collecting articles and comments using parallel processing.

Important Note:
댓글 수집은 네이버 뉴스 기사에서만 가능합니다.
- 네이버 뉴스 URL 형식: 
  - 신형: https://n.news.naver.com/mnews/article/{언론사ID}/{기사ID}
  - 구형: https://news.naver.com/main/read.naver?mode=LSD&mid=shm&sid1=101&oid={언론사ID}&aid={기사ID}
- 타 언론사 사이트나 포털의 기사는 댓글을 수집할 수 없습니다.
- 네이버 뉴스 외 URL은 자동으로 필터링됩니다.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any
import re

from database.operations import Database
from database.models.article import Article
from database.enums import ArticleStatus, CollectionMethod
from news_collector.collectors.comment import NaverCommentCollector
from news_collector.parallel import ParallelArticleCollector
from news_collector.core import CollectorFactory, CollectorType

from .logging_config import get_logger
from .decorators import handle_exceptions, log_execution_time
from .validators import validate_date_range, validate_article_data, validate_comment_data
from .exceptions import CollectionError

logger = get_logger('collectors')


@handle_exceptions("기사 수집 중 오류가 발생했습니다")
@log_execution_time
def collect_articles_parallel(
    keyword: str,
    start_date: datetime,
    end_date: datetime,
    num_processes: int = 4,
    collect_content: bool = True
) -> Tuple[int, int]:
    """
    Collect articles using parallel processing.
    Uses parallel collection functions for efficient multi-process collection.

    Args:
        keyword: Search keyword
        start_date: Start date for collection
        end_date: End date for collection
        num_processes: Number of parallel processes
        collect_content: Whether to collect article content

    Returns:
        Tuple of (saved_count, skipped_count)
    """
    db = Database()
    error_message = None

    try:
        validate_date_range(start_date, end_date)
        logger.info(f"Starting article collection for keyword: {keyword}")

        # 병렬 수집 함수 사용
        collector = ParallelArticleCollector(num_processes=num_processes)
        articles = collector.collect_articles(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date
        )

        if not articles:
            logger.info("No articles found for collection")
            db.log_collection(
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                total_articles=0,
                success_count=0,
                error_count=0,
                error_message="No articles found"
            )
            return 0, 0

        # Process all articles
        all_articles = []
        skipped_count = 0

        for article in articles:
            try:
                # Convert to database format
                db_article = {
                    'title': article['title'],
                    'naver_link': article.get('naver_link', ''),
                    'original_link': article.get('original_link', ''),
                    'description': article.get('description', ''),
                    'pub_date': article['pub_date'],
                    'published_at': article.get('published_at'),
                    'main_keyword': keyword,
                    'publisher': article.get('publisher', ''),
                    'publisher_domain': article.get('publisher_domain', ''),
                    # ParallelArticleCollector uses SearchCollector
                    'collection_method': CollectionMethod.SEARCH,
                    'content_status': ArticleStatus.pending if collect_content else ArticleStatus.completed,
                    'comment_status': ArticleStatus.pending
                }
                validate_article_data(db_article)
                all_articles.append(db_article)
            except Exception as e:
                logger.error(
                    f"Error processing article: {str(e)}\nArticle: {article}")
                skipped_count += 1
                continue

        # Bulk insert/update all articles
        if all_articles:
            try:
                processed_count = db.insert_articles_bulk(all_articles)

                # 본문 수집이 활성화된 경우
                if collect_content:
                    content_collector = CollectorFactory.create(
                        CollectorType.ARTICLE_CONTENT)
                    for article in all_articles:
                        try:
                            content_data = content_collector.collect_content(
                                article['naver_link'])
                            if content_data:
                                db.update_article_content(
                                    article_url=article['naver_link'],
                                    content_data={
                                        'content': content_data.get('content', ''),
                                        'reporter': content_data.get('reporter', ''),
                                        'category': content_data.get('category', ''),
                                        'modified_at': content_data.get('modified_at'),
                                        'published_at': content_data.get('published_at')
                                    }
                                )
                        except Exception as e:
                            logger.error(
                                f"Error collecting content: {str(e)}")
                            continue

                logger.info(
                    f"Successfully processed {processed_count} articles")

                # Log successful collection
                db.log_collection(
                    keyword=keyword,
                    start_date=start_date,
                    end_date=end_date,
                    total_articles=len(all_articles),
                    success_count=processed_count,
                    error_count=skipped_count
                )

                return processed_count, skipped_count
            except Exception as e:
                error_message = f"기사 저장 중 오류가 발생했습니다: {str(e)}"
                logger.error(error_message)
                raise CollectionError(error_message)

        logger.info(
            f"Article collection completed: {len(all_articles)} processed, {skipped_count} skipped")

        # Log collection results
        db.log_collection(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            total_articles=len(all_articles),
            success_count=len(all_articles),
            error_count=skipped_count
        )

        return len(all_articles), skipped_count

    except Exception as e:
        error_message = f"기사 수집 중 오류가 발생했습니다: {str(e)}"
        logger.error(error_message)

        # Log collection error
        db.log_collection(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            total_articles=0,
            success_count=0,
            error_count=1,
            error_message=str(e)
        )

        raise CollectionError(error_message)


@handle_exceptions("댓글 수집 중 오류가 발생했습니다")
@log_execution_time
def collect_comments_parallel(
    articles: List[Article],
    max_workers: int = 4
) -> int:
    """
    네이버 뉴스 기사의 댓글을 병렬로 수집합니다.

    주의사항:
    - 네이버 뉴스 기사의 댓글만 수집 가능합니다.
    - 네이버 뉴스가 아닌 기사(언론사 직접 링크 등)는 자동으로 필터링됩니다.
    - 원문 기사(original_link)와 네이버 뉴스 링크(naver_link)가 동일한 경우는 제외됩니다.
      이는 해당 기사가 네이버 뉴스를 통하지 않고 직접 링크된 경우를 의미합니다.

    지원하는 네이버 뉴스 URL 형식:
    1. 신형: https://n.news.naver.com/mnews/article/{언론사ID}/{기사ID}
    2. 구형: https://news.naver.com/main/read.naver?mode=LSD&mid=shm&sid1=101&oid={언론사ID}&aid={기사ID}

    Args:
        articles: List of articles to collect comments for
        max_workers: Number of parallel workers

    Returns:
        Total number of comments collected
    """
    db = Database()

    try:
        # 네이버 뉴스 URL만 필터링
        naver_articles = [
            {
                'id': str(article.id),
                'url': article.naver_link,
                'keyword': article.main_keyword
            }
            for article in articles
            # 네이버 뉴스 URL이면서 원문 링크와 다른 경우만 선택
            if re.search(r'(n\.)?news\.naver\.com/(m)?news/article/\d+/\d+', article.naver_link)
            and article.naver_link != article.original_link
        ]

        if not naver_articles:
            logger.info("No valid Naver news articles found")
            return 0

        # CommentCollector 사용
        collector = NaverCommentCollector()
        total_comments = 0

        # 각 기사의 댓글 수집
        for article_data in naver_articles:
            try:
                comments = collector.get_comments(  # Changed from get_article_comments to get_comments
                    article_url=article_data['url']
                )

                if comments and comments.get('comments'):
                    article_comments = comments['comments']
                    # 댓글 데이터 검증
                    validate_comment_data(article_comments)

                    # 댓글 저장
                    db.update_article_comments(
                        article_url=article_data['url'],
                        keyword=article_data['keyword'],
                        comment_data={
                            'total_count': len(article_comments),
                            'comments': article_comments,
                            'collected_at': datetime.utcnow().isoformat()
                        }
                    )

                    total_comments += len(article_comments)

            except Exception as e:
                logger.error(
                    f"Error collecting comments for article {article_data['url']}: {str(e)}")
                continue

        logger.info(f"Successfully collected {total_comments} comments")
        return total_comments

    except Exception as e:
        logger.error(f"Comment collection failed: {str(e)}")
        raise CollectionError(f"댓글 수집 중 오류가 발생했습니다: {str(e)}")


@handle_exceptions("데이터 수집 상태 확인 중 오류가 발생했습니다")
def get_collection_status() -> Dict[str, Any]:
    """
    Get current status of data collection.

    Returns:
        Dictionary containing collection status information
    """
    try:
        db = Database()
        total_articles = db.get_total_articles()
        total_comments = db.get_total_comments()
        last_collection = db.get_last_collection_time()

        return {
            'total_articles': total_articles,
            'total_comments': total_comments,
            'last_collection': last_collection,
            'collection_active': False  # This could be updated based on actual collection status
        }
    except Exception as e:
        logger.error(f"Error getting collection status: {str(e)}")
        raise CollectionError("수집 상태 정보를 가져오는데 실패했습니다.")
