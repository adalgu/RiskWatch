"""
Date utility functions for news collection
"""

from typing import List, Tuple
from datetime import datetime, timedelta


def generate_date_ranges(start_date: datetime, end_date: datetime, days_per_range: int = 1) -> List[Tuple[datetime, datetime]]:
    """
    주어진 시작일과 종료일 사이의 날짜 범위를 생성합니다.

    Args:
        start_date (datetime): 시작일
        end_date (datetime): 종료일
        days_per_range (int): 각 범위의 일수 (기본값: 1)

    Returns:
        List[Tuple[datetime, datetime]]: (시작일, 종료일) 튜플의 리스트

    Example:
        >>> from datetime import datetime
        >>> start = datetime(2024, 1, 1)
        >>> end = datetime(2024, 1, 5)
        >>> ranges = generate_date_ranges(start, end, days_per_range=2)
        >>> for range_start, range_end in ranges:
        ...     print(f"{range_start.date()} ~ {range_end.date()}")
        2024-01-01 ~ 2024-01-02
        2024-01-03 ~ 2024-01-04
        2024-01-05 ~ 2024-01-05
    """
    if start_date > end_date:
        raise ValueError("시작일이 종료일보다 늦을 수 없습니다.")

    date_ranges = []
    current_start = start_date

    while current_start <= end_date:
        # 현재 범위의 종료일 계산
        current_end = min(
            current_start + timedelta(days=days_per_range - 1),
            end_date
        )
        date_ranges.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return date_ranges


def generate_reversed_date_ranges(start_date: datetime, end_date: datetime, days_per_range: int = 1) -> List[Tuple[datetime, datetime]]:
    """
    주어진 시작일과 종료일 사이의 날짜 범위를 역순으로 생성합니다.

    Args:
        start_date (datetime): 시작일
        end_date (datetime): 종료일
        days_per_range (int): 각 범위의 일수 (기본값: 1)

    Returns:
        List[Tuple[datetime, datetime]]: (시작일, 종료일) 튜플의 리스트 (역순)

    Example:
        >>> from datetime import datetime
        >>> start = datetime(2024, 1, 1)
        >>> end = datetime(2024, 1, 5)
        >>> ranges = generate_reversed_date_ranges(start, end, days_per_range=2)
        >>> for range_start, range_end in ranges:
        ...     print(f"{range_start.date()} ~ {range_end.date()}")
        2024-01-04 ~ 2024-01-05
        2024-01-02 ~ 2024-01-03
        2024-01-01 ~ 2024-01-01
    """
    # 정방향으로 날짜 범위 생성 후 역순 정렬
    ranges = generate_date_ranges(start_date, end_date, days_per_range)
    return list(reversed(ranges))
