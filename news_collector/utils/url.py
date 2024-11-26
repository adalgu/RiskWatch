"""
URL handling and validation utilities.
"""
import re
from typing import Optional, Dict, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, ParseResult


class URLUtils:
    """URL 처리 유틸리티 클래스"""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        URL을 정규화.

        Args:
            url: 정규화할 URL

        Returns:
            정규화된 URL

        Examples:
            >>> URLUtils.normalize_url("https://news.naver.com/main/read.nhn?mode=LSD&mid=shm&sid1=101&oid=001&aid=0012345678")
            "https://news.naver.com/main/read.nhn?aid=0012345678&mid=shm&mode=LSD&oid=001&sid1=101"
        """
        try:
            # URL 파싱
            parsed = urlparse(url)

            # 쿼리 파라미터 정렬
            if parsed.query:
                params = parse_qs(parsed.query)
                # 각 파라미터의 첫 번째 값만 사용
                sorted_params = {k: params[k][0]
                                 for k in sorted(params.keys())}
                # 정렬된 쿼리 문자열 생성
                query = urlencode(sorted_params)
            else:
                query = ''

            # 정규화된 URL 생성
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query,
                ''  # fragment 제거
            )).rstrip('/')

        except Exception as e:
            print(f"URL normalization error: {str(e)}")
            return url.strip()

    @staticmethod
    def is_valid_naver_news_url(url: str) -> bool:
        """
        네이버 뉴스 URL 유효성 검사.

        Args:
            url: 검사할 URL

        Returns:
            bool: 유효한 네이버 뉴스 URL인지 여부

        Examples:
            >>> URLUtils.is_valid_naver_news_url("https://n.news.naver.com/article/001/0012345678")
            True
            >>> URLUtils.is_valid_naver_news_url("https://news.naver.com/main/read.nhn?mode=LSD&mid=shm&sid1=101&oid=001&aid=0012345678")
            True
        """
        if not url:
            return False

        try:
            # URL 파싱
            parsed = urlparse(url)

            # 도메인 검사
            if not any(domain in parsed.netloc
                       for domain in ['news.naver.com', 'n.news.naver.com']):
                return False

            # 새로운 형식 (n.news.naver.com/article/...)
            if 'n.news.naver.com' in parsed.netloc:
                pattern = r'/article/(\d+)/(\d+)'
                return bool(re.search(pattern, parsed.path))

            # 구형식 (news.naver.com/main/read.nhn?...)
            if 'news.naver.com' in parsed.netloc:
                if not parsed.query:
                    return False

                params = parse_qs(parsed.query)
                required_params = ['oid', 'aid']
                return all(param in params for param in required_params)

            return False

        except Exception as e:
            print(f"URL validation error: {str(e)}")
            return False

    @staticmethod
    def extract_article_info(url: str) -> Optional[Dict[str, str]]:
        """
        네이버 뉴스 URL에서 기사 정보 추출.

        Args:
            url: 네이버 뉴스 URL

        Returns:
            Dict containing article info or None if invalid

        Examples:
            >>> URLUtils.extract_article_info("https://n.news.naver.com/article/001/0012345678")
            {'media_id': '001', 'article_id': '0012345678'}
        """
        if not URLUtils.is_valid_naver_news_url(url):
            return None

        try:
            parsed = urlparse(url)

            # 새로운 형식
            if 'n.news.naver.com' in parsed.netloc:
                match = re.search(r'/article/(\d+)/(\d+)', parsed.path)
                if match:
                    return {
                        'media_id': match.group(1),
                        'article_id': match.group(2)
                    }

            # 구형식
            if 'news.naver.com' in parsed.netloc:
                params = parse_qs(parsed.query)
                if 'oid' in params and 'aid' in params:
                    return {
                        'media_id': params['oid'][0],
                        'article_id': params['aid'][0]
                    }

            return None

        except Exception as e:
            print(f"Article info extraction error: {str(e)}")
            return None

    @staticmethod
    def convert_to_mobile_url(url: str) -> Optional[str]:
        """
        PC용 URL을 모바일 URL로 변환.

        Args:
            url: PC용 네이버 뉴스 URL

        Returns:
            Mobile URL or None if conversion fails

        Examples:
            >>> URLUtils.convert_to_mobile_url("https://news.naver.com/main/read.nhn?mode=LSD&mid=shm&sid1=101&oid=001&aid=0012345678")
            "https://n.news.naver.com/article/001/0012345678"
        """
        article_info = URLUtils.extract_article_info(url)
        if not article_info:
            return None

        try:
            return f"https://n.news.naver.com/article/{article_info['media_id']}/{article_info['article_id']}"
        except Exception as e:
            print(f"URL conversion error: {str(e)}")
            return None

    @staticmethod
    def convert_to_comment_url(url: str) -> Optional[str]:
        """
        기사 URL을 댓글 페이지 URL로 변환.

        Args:
            url: 네이버 뉴스 URL

        Returns:
            Comment page URL or None if conversion fails

        Examples:
            >>> URLUtils.convert_to_comment_url("https://n.news.naver.com/article/001/0012345678")
            "https://n.news.naver.com/article/comment/001/0012345678"
        """
        article_info = URLUtils.extract_article_info(url)
        if not article_info:
            return None

        try:
            return f"https://n.news.naver.com/article/comment/{article_info['media_id']}/{article_info['article_id']}"
        except Exception as e:
            print(f"Comment URL conversion error: {str(e)}")
            return None

    @staticmethod
    def build_search_url(keyword: str, params: Optional[Dict] = None) -> str:
        """
        검색 URL 생성.

        Args:
            keyword: 검색 키워드
            params: 추가 검색 파라미터

        Returns:
            Search URL

        Examples:
            >>> URLUtils.build_search_url("검색어", {"sort": "1", "pd": "3"})
            "https://search.naver.com/search.naver?where=news&query=검색어&sort=1&pd=3"
        """
        try:
            base_params = {
                'where': 'news',
                'query': keyword
            }

            if params:
                base_params.update(params)

            query_string = urlencode(base_params)
            return f"https://search.naver.com/search.naver?{query_string}"

        except Exception as e:
            print(f"Search URL building error: {str(e)}")
            return ""

    @staticmethod
    def extract_urls_from_text(text: str) -> List[str]:
        """
        텍스트에서 URL 추출.

        Args:
            text: URL을 포함한 텍스트

        Returns:
            List of extracted URLs

        Examples:
            >>> URLUtils.extract_urls_from_text("뉴스 링크: https://n.news.naver.com/article/001/0012345678")
            ["https://n.news.naver.com/article/001/0012345678"]
        """
        try:
            # URL 패턴
            url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
            return re.findall(url_pattern, text)

        except Exception as e:
            print(f"URL extraction error: {str(e)}")
            return []
