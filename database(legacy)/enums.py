"""
Enum definitions for CommentWatch database
"""

import enum


class SentimentCategory(enum.Enum):
    """Sentiment analysis categories"""
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class CollectionMethod(enum.Enum):
    """Article collection methods"""
    API = "api"
    SEARCH = "search"


class ArticleStatus(enum.Enum):
    """Article processing status"""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
