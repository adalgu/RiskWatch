"""
Dashboard package for news article collection and monitoring
"""

from .collection_service import (
    collect_articles_parallel,
    collect_comments_parallel,
    get_collection_status
)
from .app import main

__all__ = [
    'collect_articles_parallel',
    'collect_comments_parallel',
    'get_collection_status',
    'main'
]
