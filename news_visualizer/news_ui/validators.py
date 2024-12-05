"""
Validation functions for the dashboard application

Notes on Collector-Specific Fields:
--------------------------------
1. Date/Time Fields:
   - SearchCollector: Uses 'pub_date' (Date without time)
     * Extracts date from Korean text (YYYY.MM.DD or YYYY년 MM월 DD일)
     * Always treated as KST (Korea Standard Time)
   
   - APICollector: Uses 'published_at' (DateTime with timezone)
     * Receives RFC822 formatted date from Naver API
     * Already includes KST timezone (+0900)

2. Publisher Fields:
   - SearchCollector: Uses 'publisher' (언론사 이름)
     * Extracts publisher name from search results
   
   - APICollector: Uses 'publisher_domain' (언론사 도메인)
     * Extracts domain from original article URL

This separation is intentional to maintain the original data format
from each source without unnecessary transformations.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Union
from .exceptions import ValidationError
import pytz
from database.enums import ArticleStatus, CollectionMethod

KST = pytz.timezone('Asia/Seoul')


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Validate date range for data collection.

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        ValidationError: If date range is invalid
    """
    if not isinstance(start_date, (datetime, date)):
        raise ValidationError("시작일이 올바른 날짜 형식이 아닙니다.")

    if not isinstance(end_date, (datetime, date)):
        raise ValidationError("종료일이 올바른 날짜 형식이 아닙니다.")

    if start_date > end_date:
        raise ValidationError("시작일이 종료일보다 늦을 수 없습니다.")

    # 날짜가 datetime인 경우 date로 변환하여 비교
    start = start_date.date() if isinstance(start_date, datetime) else start_date
    end = end_date.date() if isinstance(end_date, datetime) else end_date

    max_range = 365  # 최대 1년
    date_diff = (end - start).days

    if date_diff > max_range:
        raise ValidationError(f"날짜 범위가 너무 큽니다. (최대 {max_range}일)")


def validate_article_data(article: Dict[str, Any]) -> None:
    """
    Validate article data before saving to database.

    Note on Date/Time Handling:
    -------------------------
    1. pub_date (SearchCollector):
       - Simple date without time information
       - Implicitly represents a date in KST
       - Stored as Date in database

    2. published_at (APICollector):
       - Full datetime with timezone
       - Must include KST timezone information
       - Stored as DateTime(timezone=True) in database

    Args:
        article: Article data dictionary

    Raises:
        ValidationError: If article data is invalid
    """
    required_fields = {
        'title': '제목',
        'naver_link': '네이버 링크',
        'main_keyword': '검색 키워드'
    }

    # 필수 필드 검증
    for field, name in required_fields.items():
        if field not in article or not article[field]:
            raise ValidationError(f"필수 필드가 누락되었습니다: {name}")

    # URL 형식 검증
    url_fields = ['naver_link', 'original_link']
    for field in url_fields:
        if field in article and article[field]:
            if not isinstance(article[field], str) or not article[field].startswith(('http://', 'https://')):
                raise ValidationError(f"올바르지 않은 URL 형식: {field}")

    # 수집기별 날짜 필드 검증
    if 'pub_date' in article:  # SearchCollector
        if isinstance(article['pub_date'], str):
            try:
                # 문자열을 date 객체로 변환
                article['pub_date'] = datetime.strptime(
                    article['pub_date'], '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError("올바르지 않은 발행 날짜 형식 (YYYY-MM-DD)")
        elif isinstance(article['pub_date'], datetime):
            # datetime을 date로 변환 (시간 정보 제거)
            article['pub_date'] = article['pub_date'].date()
        elif not isinstance(article['pub_date'], date):
            raise ValidationError("올바르지 않은 발행 날짜 형식")

    if 'published_at' in article and article['published_at']:  # APICollector
        if isinstance(article['published_at'], str):
            try:
                dt = datetime.fromisoformat(article['published_at'])
                if dt.tzinfo is None:
                    # timezone 없는 경우 KST 적용
                    dt = KST.localize(dt)
                article['published_at'] = dt
            except ValueError:
                raise ValidationError("올바르지 않은 발행일시 형식")
        elif isinstance(article['published_at'], datetime):
            if article['published_at'].tzinfo is None:
                # timezone 없는 경우 KST 적용
                article['published_at'] = KST.localize(article['published_at'])
        else:
            raise ValidationError("올바르지 않은 발행일시 형식")

    # 수집기별 출판사 정보 검증
    if 'publisher' in article and article['publisher']:  # SearchCollector
        if not isinstance(article['publisher'], str):
            raise ValidationError("출판사명은 문자열이어야 합니다")

    # APICollector
    if 'publisher_domain' in article and article['publisher_domain']:
        if not isinstance(article['publisher_domain'], str):
            raise ValidationError("출판사 도메인은 문자열이어야 합니다")

    # 키워드 검증
    if 'main_keyword' in article:
        if not isinstance(article['main_keyword'], str):
            raise ValidationError("키워드는 문자열이어야 합니다")
        if not article['main_keyword'].strip():
            raise ValidationError("키워드는 비어있을 수 없습니다")

    # Enum 필드 검증
    if 'collection_method' in article:
        if not isinstance(article['collection_method'], CollectionMethod):
            try:
                if isinstance(article['collection_method'], str):
                    article['collection_method'] = CollectionMethod[article['collection_method'].upper()]
                else:
                    raise ValidationError("올바르지 않은 수집 방법 형식")
            except KeyError:
                raise ValidationError("올바르지 않은 수집 방법 값")

    if 'content_status' in article:
        if not isinstance(article['content_status'], ArticleStatus):
            try:
                if isinstance(article['content_status'], str):
                    article['content_status'] = ArticleStatus[article['content_status'].lower()]
                else:
                    raise ValidationError("올바르지 않은 본문 상태 형식")
            except KeyError:
                raise ValidationError("올바르지 않은 본문 상태 값")

    if 'comment_status' in article:
        if not isinstance(article['comment_status'], ArticleStatus):
            try:
                if isinstance(article['comment_status'], str):
                    article['comment_status'] = ArticleStatus[article['comment_status'].lower()]
                else:
                    raise ValidationError("올바르지 않은 댓글 상태 형식")
            except KeyError:
                raise ValidationError("올바르지 않은 댓글 상태 값")


def validate_comment_data(comments: List[Dict[str, Any]]) -> None:
    """
    Validate comment data before saving to database.

    Note on Timestamp Handling:
    -------------------------
    Comment timestamps are always in KST as they are collected from
    Korean news websites. The timestamp is stored with timezone
    information to maintain consistency.

    Args:
        comments: List of comment dictionaries

    Raises:
        ValidationError: If comment data is invalid
    """
    if not isinstance(comments, (list, tuple)):
        raise ValidationError("댓글 데이터는 리스트 형식이어야 합니다")

    required_fields = {
        'article_id': '기사 ID',
        'content': '내용',
        'timestamp': '작성 시간'
    }

    for comment in comments:
        # 필수 필드 검증
        for field, name in required_fields.items():
            if field not in comment or not comment[field]:
                raise ValidationError(f"댓글의 필수 필드가 누락되었습니다: {name}")

        # 타입 검증
        if not isinstance(comment['article_id'], str):
            raise ValidationError("기사 ID는 문자열이어야 합니다")

        if not isinstance(comment['content'], str):
            raise ValidationError("댓글 내용은 문자열이어야 합니다")

        # 타임스탬프 검증 (KST 기준)
        try:
            if isinstance(comment['timestamp'], str):
                dt = datetime.fromisoformat(comment['timestamp'])
                if dt.tzinfo is None:
                    # timezone 없는 경우 KST 적용
                    dt = KST.localize(dt)
                comment['timestamp'] = dt
            elif isinstance(comment['timestamp'], datetime):
                if comment['timestamp'].tzinfo is None:
                    # timezone 없는 경우 KST 적용
                    comment['timestamp'] = KST.localize(comment['timestamp'])
            else:
                raise ValueError("Invalid timestamp type")
        except (ValueError, TypeError):
            raise ValidationError("올바르지 않은 작성 시간 형식")

        # 옵션 필드 검증
        if 'writer' in comment and not isinstance(comment['writer'], str):
            raise ValidationError("작성자명은 문자열이어야 합니다")

        if 'likes' in comment and not isinstance(comment['likes'], int):
            raise ValidationError("좋아요 수는 정수여야 합니다")

        if 'dislikes' in comment and not isinstance(comment['dislikes'], int):
            raise ValidationError("싫어요 수는 정수여야 합니다")


def validate_collection_config(config: Dict[str, Any]) -> None:
    """
    Validate collection configuration.

    Args:
        config: Collection configuration dictionary

    Raises:
        ValidationError: If configuration is invalid
    """
    required_fields = {
        'keywords': '검색 키워드',
        'start_date': '시작일',
        'end_date': '종료일'
    }

    # 필수 필드 검증
    for field, name in required_fields.items():
        if field not in config:
            raise ValidationError(f"필수 설정이 누락되었습니다: {name}")

    # 키워드 검증
    if not isinstance(config['keywords'], (list, tuple)):
        raise ValidationError("키워드는 리스트 형식이어야 합니다")

    if not config['keywords']:
        raise ValidationError("최소 하나의 키워드가 필요합니다")

    for keyword in config['keywords']:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValidationError("올바르지 않은 키워드 형식")

    # 날짜 검증
    try:
        start_date = datetime.fromisoformat(config['start_date'])
        end_date = datetime.fromisoformat(config['end_date'])
        validate_date_range(start_date, end_date)
    except (ValueError, TypeError):
        raise ValidationError("올바르지 않은 날짜 형식")

    # 옵션 필드 검증
    if 'max_articles' in config:
        if not isinstance(config['max_articles'], int):
            raise ValidationError("최대 기사 수는 정수여야 합니다")
        if config['max_articles'] < 1:
            raise ValidationError("최대 기사 수는 1 이상이어야 합니다")

    if 'collect_comments' in config:
        if not isinstance(config['collect_comments'], bool):
            raise ValidationError("댓글 수집 여부는 불리언이어야 합니다")
