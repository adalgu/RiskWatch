"""
Database operations module
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import func, or_, and_, case, literal, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models.article import Article, ArticleCollectionLog
from .models.comment import Comment
from .models.keyword.article_keywords import ArticleKeywordAnalysis
from .models.keyword.comment_keywords import CommentKeywordAnalysis
from .models.sentiment.article_sentiment import ArticleSentiment
from .models.sentiment.comment_sentiment import CommentSentiment
from .models.stats.article_stats import ArticleStats
from .models.stats.comment_stats import CommentStats
from .enums import ArticleStatus, CollectionMethod

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """URL을 정규화"""
    parsed = urlparse(url)
    if parsed.query:
        params = parse_qs(parsed.query)
        sorted_params = {k: v[0] for k, v in sorted(params.items())}
        query = urlencode(sorted_params)
    else:
        query = ''
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query,
        ''
    ))


class Database:
    def __init__(self):
        from . import SessionLocal
        self.session: Session = SessionLocal()

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

    def log_collection(self, keyword: str, start_date: datetime, end_date: datetime,
                       total_articles: int, success_count: int, error_count: int,
                       error_message: Optional[str] = None) -> None:
        """수집 로그를 저장합니다."""
        try:
            log_entry = ArticleCollectionLog(
                keyword=keyword,
                start_date=start_date.date(),
                end_date=end_date.date(),
                total_articles=total_articles,
                success_count=success_count,
                error_count=error_count,
                error_message=error_message
            )
            self.session.add(log_entry)
            self.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error logging collection: {str(e)}")
            self.session.rollback()

    def get_collection_logs(self, keyword: Optional[str] = None,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            limit: int = 100) -> List[ArticleCollectionLog]:
        """수집 로그를 조회합니다."""
        try:
            query = self.session.query(ArticleCollectionLog)

            if keyword:
                query = query.filter(ArticleCollectionLog.keyword == keyword)
            if start_date:
                query = query.filter(
                    ArticleCollectionLog.start_date >= start_date.date())
            if end_date:
                query = query.filter(
                    ArticleCollectionLog.end_date <= end_date.date())

            return query.order_by(ArticleCollectionLog.collected_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting collection logs: {str(e)}")
            return []

    def get_total_articles(self) -> int:
        """전체 기사 수 조회"""
        try:
            return self.session.query(Article).count()
        except SQLAlchemyError as e:
            logger.error(f"Error getting total articles: {str(e)}")
            return 0

    def get_total_comments(self) -> int:
        """전체 댓글 수 조회"""
        try:
            return self.session.query(Comment).count()
        except SQLAlchemyError as e:
            logger.error(f"Error getting total comments: {str(e)}")
            return 0

    def get_last_collection_time(self) -> Optional[datetime]:
        """마지막 수집 시간 조회"""
        try:
            last_article = self.session.query(Article).order_by(
                Article.collected_at.desc()).first()
            return last_article.collected_at if last_article else None
        except SQLAlchemyError as e:
            logger.error(f"Error getting last collection time: {str(e)}")
            return None

    def insert_articles_bulk(self, articles: List[Dict]) -> int:
        """기사 일괄 삽입 - 배치 처리 및 enum 캐스팅 적용"""
        try:
            processed_count = 0
            batch_size = 50  # Reduced batch size to avoid parameter limit

            # Process articles in batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]

                for article_data in batch:
                    # URL 정규화
                    article_data['naver_link'] = normalize_url(
                        article_data['naver_link'])
                    if article_data.get('original_link'):
                        article_data['original_link'] = normalize_url(
                            article_data['original_link'])

                    # Ensure collection_method is an enum instance
                    if isinstance(article_data.get('collection_method'), str):
                        article_data['collection_method'] = CollectionMethod[article_data['collection_method'].upper(
                        )]
                    elif not isinstance(article_data.get('collection_method'), CollectionMethod):
                        article_data['collection_method'] = CollectionMethod.SEARCH

                    # Ensure content_status is an enum instance
                    if isinstance(article_data.get('content_status'), str):
                        article_data['content_status'] = ArticleStatus[article_data['content_status'].upper(
                        )]
                    elif not isinstance(article_data.get('content_status'), ArticleStatus):
                        article_data['content_status'] = ArticleStatus.pending

                    # Ensure comment_status is an enum instance
                    if isinstance(article_data.get('comment_status'), str):
                        article_data['comment_status'] = ArticleStatus[article_data['comment_status'].upper(
                        )]
                    elif not isinstance(article_data.get('comment_status'), ArticleStatus):
                        article_data['comment_status'] = ArticleStatus.pending

                    # 기존 기사 검색
                    existing = self.session.query(Article).filter(
                        Article.naver_link == article_data['naver_link']
                    ).first()

                    if existing:
                        # 기존 기사 업데이트
                        for key, value in article_data.items():
                            setattr(existing, key, value)
                        processed_count += 1
                    else:
                        # 새 기사 추가
                        new_article = Article(**article_data)
                        self.session.add(new_article)
                        processed_count += 1

                # Commit each batch
                self.session.commit()

            return processed_count

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error inserting articles: {str(e)}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error inserting articles: {str(e)}")
            raise

    def update_article_content(self, article_url: str, content_data: Dict) -> bool:
        """기사 본문 정보 업데이트"""
        try:
            article = self.session.query(Article).filter(
                Article.naver_link == normalize_url(article_url)
            ).first()

            if article:
                for key, value in content_data.items():
                    setattr(article, key, value)
                article.content_collected_at = datetime.now()
                self.session.commit()
                return True
            return False

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating article content: {str(e)}")
            return False

    def update_article_comments(self, article_url: str, keyword: str, comment_data: Dict) -> bool:
        """기사 댓글 정보 업데이트"""
        try:
            article = self.session.query(Article).filter(
                Article.naver_link == normalize_url(article_url),
                Article.main_keyword == keyword
            ).first()

            if not article:
                logger.error(f"Article not found: {article_url}")
                return False

            # 댓글 정보 업데이트
            article.comment_count = comment_data.get('total_count', 0)
            article.comment_collected_at = datetime.now()

            # 기존 댓글 삭제
            self.session.query(Comment).filter(
                Comment.article_id == article.id).delete()

            # 새 댓글 추가
            for comment in comment_data.get('comments', []):
                new_comment = Comment(
                    article_id=article.id,
                    content=comment.get('content'),
                    author=comment.get('author'),
                    likes=comment.get('likes', 0),
                    dislikes=comment.get('dislikes', 0),
                    created_at=comment.get('timestamp'),
                    parent_comment_no=comment.get('parent_comment_no'),
                    is_reply=comment.get('is_reply', False),
                    is_deleted=comment.get('is_deleted', False),
                    delete_type=comment.get('delete_type')
                )
                self.session.add(new_comment)

            self.session.commit()
            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating article comments: {str(e)}")
            return False

    def get_articles_without_content(self, limit: int = 100) -> List[Article]:
        """본문이 수집되지 않은 기사 조회"""
        try:
            return self.session.query(Article).filter(
                Article.content.is_(None),
                Article.content_collected_at.is_(None)
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles without content: {str(e)}")
            return []

    def get_articles_without_comments(self, limit: int = 100) -> List[Article]:
        """댓글이 수집되지 않은 기사 조회"""
        try:
            return self.session.query(Article).filter(
                Article.comment_count.is_(None),
                Article.comment_collected_at.is_(None)
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles without comments: {str(e)}")
            return []

    def get_articles_by_keyword(self,
                                keyword: str,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                limit: int = 100) -> List[Article]:
        """키워드로 기사 검색"""
        try:
            query = self.session.query(Article).filter(
                Article.main_keyword == keyword
            )

            if start_date:
                query = query.filter(Article.published_at >= start_date)
            if end_date:
                query = query.filter(Article.published_at <= end_date)

            return query.order_by(Article.published_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles by keyword: {str(e)}")
            return []

    def get_article_stats(self,
                          keyword: Optional[str] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """기사 통계 정보 조회"""
        try:
            query = self.session.query(Article)

            if keyword:
                query = query.filter(Article.main_keyword == keyword)
            if start_date:
                query = query.filter(Article.published_at >= start_date)
            if end_date:
                query = query.filter(Article.published_at <= end_date)

            total_articles = query.count()
            articles_with_comments = query.filter(
                Article.comment_count > 0).count()
            total_comments = self.session.query(func.sum(Article.comment_count))\
                .filter(Article.comment_count.isnot(None))\
                .scalar() or 0

            return {
                'total_articles': total_articles,
                'articles_with_comments': articles_with_comments,
                'total_comments': total_comments,
                'avg_comments_per_article': round(total_comments / total_articles if total_articles > 0 else 0, 2)
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting article stats: {str(e)}")
            return {
                'total_articles': 0,
                'articles_with_comments': 0,
                'total_comments': 0,
                'avg_comments_per_article': 0
            }

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """기사의 날짜 범위 조회"""
        try:
            result = self.session.query(
                func.min(Article.pub_date).label('min_date'),
                func.max(Article.pub_date).label('max_date')
            ).first()

            if not result.min_date or not result.max_date:
                today = datetime.now()
                return today - timedelta(days=30), today

            return result.min_date, result.max_date
        except SQLAlchemyError as e:
            logger.error(f"Error getting date range: {str(e)}")
            today = datetime.now()
            return today - timedelta(days=30), today

    def get_keywords_summary(self) -> List[Dict[str, Any]]:
        """키워드 요약 정보 조회"""
        try:
            result = self.session.query(
                Article.main_keyword,
                func.count(Article.id).label('article_count'),
                func.sum(CommentStats.total_count).label('total_comments'),
                func.avg(CommentStats.total_count).label('avg_comments')
            ).outerjoin(
                CommentStats
            ).group_by(
                Article.main_keyword
            ).all()

            return [
                {
                    'main_keyword': r.main_keyword,
                    'article_count': r.article_count,
                    'total_comments': r.total_comments or 0,
                    'avg_comments': float(r.avg_comments or 0)
                }
                for r in result
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting keywords summary: {str(e)}")
            return []

    def get_articles_by_date(self,
                             start_date: datetime,
                             end_date: datetime,
                             keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """날짜별 기사 통계 조회"""
        try:
            query = self.session.query(
                func.date_trunc('day', Article.pub_date).label('date'),
                func.count(Article.id).label('total_article_count'),
                func.sum(case(
                    (Article.naver_link.like('%news.naver.com%'), literal(1)),
                    else_=literal(0)
                )).label('naver_article_count'),
                func.sum(CommentStats.total_count).label('comment_count')
            ).outerjoin(
                CommentStats
            ).filter(
                Article.pub_date.between(start_date, end_date)
            )

            if keyword:
                query = query.filter(Article.main_keyword == keyword)

            result = query.group_by(
                func.date_trunc('day', Article.pub_date)
            ).all()

            return [
                {
                    'date': r.date,
                    'total_article_count': r.total_article_count,
                    'naver_article_count': r.naver_article_count or 0,
                    'comment_count': r.comment_count or 0
                }
                for r in result
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles by date: {str(e)}")
            return []

    def get_articles_details_by_date(self,
                                     date: datetime,
                                     keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """특정 날짜의 기사 상세 정보 조회"""
        try:
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = datetime.combine(date, datetime.max.time())

            query = self.session.query(
                Article,
                CommentStats.total_count
            ).outerjoin(
                CommentStats
            ).filter(
                Article.pub_date.between(start_datetime, end_datetime)
            )

            if keyword:
                query = query.filter(Article.main_keyword == keyword)

            articles = query.all()

            return [
                {
                    'title': article.title or "제목 없음",
                    'url': article.naver_link,
                    'original_url': article.original_link,
                    'published_at': article.published_at,
                    'total_comments': total_comments or 0,
                    'main_keyword': article.main_keyword,
                    'description': article.description
                }
                for article, total_comments in articles
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting article details by date: {str(e)}")
            return []

    def get_articles_for_comment_collection(self,
                                            start_date: datetime,
                                            end_date: datetime,
                                            keyword: Optional[str] = None) -> List[Article]:
        """댓글 수집이 필요한 기사 조회"""
        try:
            query = self.session.query(Article).outerjoin(
                CommentStats
            ).filter(
                and_(
                    Article.pub_date.between(start_date, end_date),
                    or_(
                        CommentStats.total_count.is_(None),
                        CommentStats.total_count == 0
                    ),
                    Article.naver_link.like('%news.naver.com%')
                )
            )

            if keyword:
                query = query.filter(Article.main_keyword == keyword)

            return query.all()
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting articles for comment collection: {str(e)}")
            return []
