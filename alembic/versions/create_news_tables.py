"""create news tables

Revision ID: create_news_tables
Revises: 
Create Date: 2023-12-24 08:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_news_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('naver_link', sa.String(), nullable=False),
        sa.Column('original_link', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('publisher', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_naver_news', sa.Boolean(), nullable=False),
        sa.Column('collection_method', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('naver_link')
    )

    # Create comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('comment_no', sa.String(), nullable=False),
        sa.Column('parent_comment_no', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('profile_url', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dislikes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reply_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_reply', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('delete_type', sa.String(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id']),
        sa.UniqueConstraint('article_id', 'comment_no')
    )

    # Create indexes
    op.create_index('ix_articles_published_at', 'articles', ['published_at'])
    op.create_index('ix_articles_collected_at', 'articles', ['collected_at'])
    op.create_index('ix_comments_timestamp', 'comments', ['timestamp'])
    op.create_index('ix_comments_collected_at', 'comments', ['collected_at'])


def downgrade() -> None:
    op.drop_table('comments')
    op.drop_table('articles')
