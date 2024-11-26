"""
CommentWatch Database Package

This package provides a comprehensive database structure for collecting, analyzing,
and managing news articles and their comments. The database is designed with
modularity and extensibility in mind, supporting various types of analysis.

Structure:
- Core Models:
  - Article: News article information and collection status
  - Comment: Comment data and basic metrics
  - ArticleMapping: Keyword mapping and collection metadata
  - ArticleCollectionLog: Collection history and statistics

- Analysis Models:
  1. Sentiment Analysis:
     - ArticleSentiment: Article sentiment scores and metadata
     - CommentSentiment: Comment sentiment with detailed emotion analysis
  
  2. Keyword Analysis:
     - ArticleKeywordAnalysis: Article keyword extraction and topic modeling
     - CommentKeywordAnalysis: Comment keyword patterns and opinion analysis
  
  3. Statistical Analysis:
     - ArticleStats: Article performance and engagement metrics
     - CommentStats: Comment patterns and demographic analysis

For detailed documentation, see README.md in the database directory.
"""

from .config import init_db, get_db, Base, engine, SessionLocal
from .operations import Database
from .enums import SentimentCategory, CollectionMethod, ArticleStatus

# Core models
from .models import (
    Article,
    ArticleCollectionLog,
    ArticleMapping,
    Comment
)

# Sentiment analysis models
from .models.sentiment.article_sentiment import ArticleSentiment
from .models.sentiment.comment_sentiment import CommentSentiment

# Keyword analysis models
from .models.keyword.article_keywords import ArticleKeywordAnalysis
from .models.keyword.comment_keywords import CommentKeywordAnalysis

# Statistical analysis models
from .models.stats.article_stats import ArticleStats
from .models.stats.comment_stats import CommentStats

__all__ = [
    # Database setup
    'init_db',
    'get_db',
    'Base',
    'engine',
    'SessionLocal',
    'Database',

    # Enums
    'SentimentCategory',
    'CollectionMethod',
    'ArticleStatus',

    # Core models
    'Article',
    'ArticleCollectionLog',
    'ArticleMapping',
    'Comment',

    # Sentiment analysis models
    'ArticleSentiment',
    'CommentSentiment',

    # Keyword analysis models
    'ArticleKeywordAnalysis',
    'CommentKeywordAnalysis',

    # Statistical analysis models
    'ArticleStats',
    'CommentStats'
]
