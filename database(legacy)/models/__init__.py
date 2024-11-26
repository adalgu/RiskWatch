"""
CommentWatch Database Models Package

This package contains all database models for the CommentWatch application,
organized into logical groups for better maintainability and scalability.

Model Organization:
------------------

1. Core Models (Direct imports):
   - Article: Main article model with basic information and collection status
   - ArticleCollectionLog: Tracks article collection history and results
   - ArticleMapping: Manages keyword mappings and collection metadata
   - Comment: Stores comment data with basic metrics

2. Analysis Models (Organized by type):
   
   a. Sentiment Analysis (sentiment/):
      - ArticleSentiment: Article-level sentiment analysis
        * Overall sentiment scores
        * Title/content separate analysis
        * Confidence metrics
      - CommentSentiment: Comment-level sentiment analysis
        * Detailed emotion categories
        * Context relevance
        * Spam/offensive detection

   b. Keyword Analysis (keyword/):
      - ArticleKeywordAnalysis: Article keyword processing
        * Extracted keywords with weights
        * Topic modeling results
        * Named Entity Recognition
        * Temporal analysis
      - CommentKeywordAnalysis: Comment keyword processing
        * Opinion/argument analysis
        * User stance detection
        * Context relevance
        * Interaction patterns

   c. Statistical Analysis (stats/):
      - ArticleStats: Article performance metrics
        * View/engagement tracking
        * Traffic analysis
        * Social metrics
        * Performance benchmarks
      - CommentStats: Comment pattern analysis
        * Demographic analysis
        * Temporal patterns
        * User behavior metrics
        * Quality indicators

Model Relationships:
------------------
Article -> Comments (1:N)
Article -> ArticleMapping (1:N)
Article -> ArticleSentiment (1:N)
Article -> ArticleKeywordAnalysis (1:N)
Article -> ArticleStats (1:N)
Article -> CommentStats (1:N)
Comment -> CommentSentiment (1:N)
Comment -> CommentKeywordAnalysis (1:N)

For detailed documentation of each model and its fields,
refer to the individual model files and database/README.md.
"""

from .article import Article, ArticleCollectionLog, ArticleMapping
from .comment import Comment

# Sentiment Analysis Models
from .sentiment.article_sentiment import ArticleSentiment
from .sentiment.comment_sentiment import CommentSentiment

# Keyword Analysis Models
from .keyword.article_keywords import ArticleKeywordAnalysis
from .keyword.comment_keywords import CommentKeywordAnalysis

# Statistical Analysis Models
from .stats.article_stats import ArticleStats
from .stats.comment_stats import CommentStats

__all__ = [
    # Core Models
    'Article',
    'ArticleCollectionLog',
    'ArticleMapping',
    'Comment',

    # Sentiment Analysis
    'ArticleSentiment',
    'CommentSentiment',

    # Keyword Analysis
    'ArticleKeywordAnalysis',
    'CommentKeywordAnalysis',

    # Statistical Analysis
    'ArticleStats',
    'CommentStats'
]
