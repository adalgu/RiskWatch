"""
Core utilities for news collection
"""

from .date import generate_date_ranges, generate_reversed_date_ranges
from .user_agent import get_random_user_agent
from .webdriver_utils import WebDriverUtils

__all__ = [
    'generate_date_ranges',
    'generate_reversed_date_ranges',
    'get_random_user_agent',
    'WebDriverUtils'
]
