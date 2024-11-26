"""Text processing utilities for cleaning and normalizing text data."""

import re
from typing import List, Dict
from bs4 import BeautifulSoup


class TextUtils:
    """텍스트 처리 유틸리티 클래스."""

    @staticmethod
    def remove_html_tags(text: str) -> str:
        if not text:
            return ""
        try:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(strip=True)
        except Exception:
            return re.sub(r'<[^>]+>', '', text).strip()

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        if not text:
            return ""
        return ' '.join(text.split())

    @staticmethod
    def clean_text(text: str, remove_html: bool = True, normalize_spaces: bool = True, remove_urls: bool = False, remove_emails: bool = False) -> str:
        if not text:
            return ""

        result = text

        if remove_html:
            result = TextUtils.remove_html_tags(result)

        if remove_urls:
            result = re.sub(r'https?://\S+|www\.\S+', '', result)

        if remove_emails:
            result = re.sub(r'\S+@\S+\.\S+', '', result)

        if normalize_spaces:
            result = TextUtils.normalize_whitespace(result)

        return result

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        if not text:
            return []

        number_pattern = r'[\d,]+'
        numbers = re.findall(number_pattern, text)
        return [num.replace(',', '') for num in numbers if num]

    @staticmethod
    def extract_korean_text(text: str) -> str:
        if not text:
            return ""

        korean_pattern = r'[ㄱ-ㅎㅏ-ㅣ가-힣]+'
        korean_text = re.findall(korean_pattern, text)
        return ' '.join(korean_text)

    @staticmethod
    def count_chars(text: str) -> Dict[str, int]:
        if not text:
            return {
                'korean': 0,
                'english': 0,
                'number': 0,
                'space': 0,
                'special': 0
            }

        counts = {
            'korean': len(re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', text)),
            'english': len(re.findall(r'[a-zA-Z]', text)),
            'number': len(re.findall(r'\d', text)),
            'space': len(re.findall(r'\s', text)),
            'special': len(re.findall(r'[^\w\s가-힣]', text))
        }

        return counts

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def has_meaningful_content(text: str, min_length: int = 10, min_korean_ratio: float = 0.3) -> bool:
        if not text or len(text) < min_length:
            return False

        cleaned_text = TextUtils.normalize_whitespace(text)
        if len(cleaned_text) < min_length:
            return False

        char_counts = TextUtils.count_chars(cleaned_text)
        total_chars = sum(char_counts.values()) - char_counts['space']
        if total_chars == 0:
            return False

        korean_ratio = char_counts['korean'] / total_chars
        return korean_ratio >= min_korean_ratio


@staticmethod
def normalize_news_text(text: str) -> str:
    if not text:
        return ""

    result = TextUtils.clean_text(
        text, remove_html=True, normalize_spaces=True, remove_urls=True, remove_emails=True)

    # 특수한 이중 인용부호를 표준 이중 인용부호로 변환합니다.
    result = re.sub(r'[“”]', '"', result)
    # 특수한 단일 인용부호를 표준 단일 인용부호로 변환합니다.
    result = re.sub(r"[‘’]", "'", result)
    # 제로 폭 문자를 제거합니다.
    result = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', result)
    # 연속된 마침표를 줄임표로 변환합니다.
    result = re.sub(r'\.{2,}', '...', result)
    # 구두점 앞의 공백을 제거합니다.
    result = re.sub(r'\s+([.!?])', r'\1', result)
    # 연속된 개행을 두 개로 줄입니다.
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()
