"""
Date handling utilities with timezone support.
"""
import re
from datetime import datetime, timedelta
import pytz
from typing import Optional, Union, Tuple

# 기본 타임존 설정
KST = pytz.timezone('Asia/Seoul')
UTC = pytz.UTC


class DateUtils:
    """날짜 처리 유틸리티 클래스"""

    @staticmethod
    def parse_date(date_str: str,
                   reference_date: Optional[datetime] = None,
                   timezone: Optional[pytz.timezone] = KST) -> Optional[datetime]:
        """
        다양한 형식의 날짜 문자열을 파싱.

        Args:
            date_str: 날짜 문자열
            reference_date: 상대적 날짜 계산을 위한 기준 날짜
            timezone: 사용할 타임존 (기본값: KST)

        Returns:
            Parsed datetime object or None if parsing fails

        Examples:
            >>> DateUtils.parse_date("2024-03-21 14:30:00")
            datetime(2024, 3, 21, 14, 30, tzinfo=<DstTzInfo 'Asia/Seoul' KST+9:00:00 STD>)
            >>> DateUtils.parse_date("3시간 전")  # reference_date 필요
            datetime(2024, 3, 21, 11, 30, tzinfo=<DstTzInfo 'Asia/Seoul' KST+9:00:00 STD>)
        """
        if not date_str:
            return None

        try:
            # 1. 정확한 날짜/시간 형식
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y.%m.%d %H:%M:%S',
                '%Y.%m.%d %H:%M',
                '%Y.%m.%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d'
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return timezone.localize(dt) if timezone else dt
                except ValueError:
                    continue

            # 2. 상대적 시간 표현
            if reference_date:
                # 시간 단위
                if '시간 전' in date_str:
                    hours = int(re.search(r'(\d+)시간 전', date_str).group(1))
                    return reference_date - timedelta(hours=hours)

                # 분 단위
                if '분 전' in date_str:
                    minutes = int(re.search(r'(\d+)분 전', date_str).group(1))
                    return reference_date - timedelta(minutes=minutes)

                # 일 단위
                if '일 전' in date_str:
                    days = int(re.search(r'(\d+)일 전', date_str).group(1))
                    return reference_date - timedelta(days=days)

            # 3. "Wed, 20 Mar 2024 14:30:00 +0900" 형식
            try:
                dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S +0900')
                return timezone.localize(dt) if timezone else dt
            except ValueError:
                pass

            return None

        except Exception as e:
            print(f"Date parsing error: {str(e)}")
            return None

    @staticmethod
    def format_date(dt: datetime,
                    fmt: str = '%Y-%m-%d %H:%M:%S',
                    timezone: Optional[pytz.timezone] = KST) -> str:
        """
        날짜/시간을 지정된 형식으로 포맷팅.

        Args:
            dt: datetime 객체
            fmt: 출력 형식
            timezone: 변환할 타임존

        Returns:
            Formatted date string
        """
        if not dt:
            return ''

        try:
            # 타임존이 없는 경우 지정된 타임존 적용
            if dt.tzinfo is None:
                dt = timezone.localize(dt) if timezone else dt
            # 다른 타임존인 경우 변환
            elif timezone and dt.tzinfo != timezone:
                dt = dt.astimezone(timezone)

            return dt.strftime(fmt)

        except Exception as e:
            print(f"Date formatting error: {str(e)}")
            return ''

    @staticmethod
    def get_date_range(days: int = 7,
                       end_date: Optional[datetime] = None,
                       timezone: Optional[pytz.timezone] = KST) -> Tuple[datetime, datetime]:
        """
        지정된 일수만큼의 날짜 범위를 반환.

        Args:
            days: 일수 (기본값: 7일)
            end_date: 종료 날짜 (기본값: 현재)
            timezone: 사용할 타임존

        Returns:
            Tuple of (start_date, end_date)
        """
        if not end_date:
            end_date = datetime.now(timezone) if timezone else datetime.now()
        elif end_date.tzinfo is None and timezone:
            end_date = timezone.localize(end_date)

        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    @staticmethod
    def is_same_day(dt1: datetime,
                    dt2: datetime,
                    timezone: Optional[pytz.timezone] = KST) -> bool:
        """
        두 날짜가 같은 날인지 확인.

        Args:
            dt1: First datetime
            dt2: Second datetime
            timezone: 비교할 타임존

        Returns:
            True if same day, False otherwise
        """
        if not dt1 or not dt2:
            return False

        try:
            # 타임존 처리
            if dt1.tzinfo is None and timezone:
                dt1 = timezone.localize(dt1)
            if dt2.tzinfo is None and timezone:
                dt2 = timezone.localize(dt2)

            return dt1.date() == dt2.date()

        except Exception as e:
            print(f"Date comparison error: {str(e)}")
            return False
        
    @staticmethod
    def extract_absolute_date(text: str) -> Optional[str]:
        """
        텍스트에서 절대 날짜(YYYY.MM.DD)를 추출합니다.

        Args:
            text (str): 날짜 정보가 포함된 텍스트

        Returns:
            Optional[str]: 추출된 날짜 문자열 (YYYY.MM.DD) 또는 None
        """
        pattern = r'(\d{4})\.(\d{1,2})\.(\d{1,2})'
        match = re.search(pattern, text)
        if match:
            year, month, day = match.groups()
            # 날짜 형식 통일 (한 자리 숫자 앞에 0 추가)
            return f"{year}.{int(month):02d}.{int(day):02d}"
        return None

    @staticmethod
    def get_relative_time(dt: datetime,
                          reference_date: Optional[datetime] = None,
                          timezone: Optional[pytz.timezone] = KST) -> str:
        """
        상대적 시간 표현을 반환.

        Args:
            dt: Target datetime
            reference_date: 기준 날짜 (기본값: 현재)
            timezone: 사용할 타임존

        Returns:
            Relative time string (e.g., "3시간 전", "2일 전")
        """
        if not dt:
            return ''

        try:
            if not reference_date:
                reference_date = datetime.now(
                    timezone) if timezone else datetime.now()

            # 타임존 처리
            if dt.tzinfo is None and timezone:
                dt = timezone.localize(dt)
            if reference_date.tzinfo is None and timezone:
                reference_date = timezone.localize(reference_date)

            diff = reference_date - dt
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            if days > 0:
                return f"{days}일 전"
            elif hours > 0:
                return f"{hours}시간 전"
            elif minutes > 0:
                return f"{minutes}분 전"
            else:
                return "방금 전"

        except Exception as e:
            print(f"Relative time calculation error: {str(e)}")
            return ''
