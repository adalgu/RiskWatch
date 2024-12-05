import pytest
from datetime import datetime
from common.models import Article, Content, Comment, CommentStats

def test_article_model():
    article = Article(
        id=1,
        main_keyword="technology",
        naver_link="https://naver.com/article",
        title="Understanding SQLModel Migration",
        collected_at=datetime.now(),
        is_naver_news=True,
        is_test=False,
        is_api_collection=True
    )
    assert article.id == 1
    assert article.main_keyword == "technology"
    assert article.naver_link == "https://naver.com/article"
    assert article.title == "Understanding SQLModel Migration"
    assert article.is_naver_news is True
    assert article.is_test is False
    assert article.is_api_collection is True
    assert article.content is None
    assert isinstance(article.comments, list)

def test_content_model():
    content = Content(
        id=1,
        article_id=1,
        content="This is the content of the article.",
        collected_at=datetime.now()
    )
    assert content.id == 1
    assert content.article_id == 1
    assert content.content == "This is the content of the article."
    assert content.article is None

def test_comment_model():
    comment = Comment(
        id=1,
        article_id=1,
        comment_no="cmt123",
        parent_comment_no=None,
        content="Great article!",
        username="user1",
        collected_at=datetime.now(),
        likes=10,
        dislikes=2,
        reply_count=3,
        is_reply=False,
        is_deleted=False
    )
    assert comment.id == 1
    assert comment.article_id == 1
    assert comment.comment_no == "cmt123"
    assert comment.parent_comment_no is None
    assert comment.content == "Great article!"
    assert comment.username == "user1"
    assert comment.likes == 10
    assert comment.dislikes == 2
    assert comment.reply_count == 3
    assert comment.is_reply is False
    assert comment.is_deleted is False
    assert comment.stats is None

def test_comment_stats_model():
    comment_stats = CommentStats(
        id=1,
        comment_id=1,
        likes=10,
        dislikes=2,
        total_count=15,
        deleted_count=1,
        male_ratio=0.6,
        female_ratio=0.4,
        unique_users=5,
        repeat_commenter_ratio=0.2,
        avg_comment_length=50.5,
        spam_ratio=0.05,
        is_complete=True,
        collected_at=datetime.now()
    )
    assert comment_stats.id == 1
    assert comment_stats.comment_id == 1
    assert comment_stats.likes == 10
    assert comment_stats.dislikes == 2
    assert comment_stats.total_count == 15
    assert comment_stats.deleted_count == 1
    assert comment_stats.male_ratio == 0.6
    assert comment_stats.female_ratio == 0.4
    assert comment_stats.unique_users == 5
    assert comment_stats.repeat_commenter_ratio == 0.2
    assert comment_stats.avg_comment_length == 50.5
    assert comment_stats.spam_ratio == 0.05
    assert comment_stats.is_complete is True
    assert comment_stats.comment is None
