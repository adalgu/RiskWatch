"""add comment stats table

Revision ID: add_comment_stats_table
Revises: create_news_tables
Create Date: 2024-01-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_comment_stats_table'
down_revision: str = 'create_news_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create comment_stats table
    op.create_table(
        'comment_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('current_count', sa.Integer(), nullable=False),
        sa.Column('user_deleted_count', sa.Integer(), nullable=False),
        sa.Column('admin_deleted_count', sa.Integer(), nullable=False),
        sa.Column('male_ratio', sa.Float(), nullable=False),
        sa.Column('female_ratio', sa.Float(), nullable=False),
        sa.Column('age_10s', sa.Float(), nullable=False),
        sa.Column('age_20s', sa.Float(), nullable=False),
        sa.Column('age_30s', sa.Float(), nullable=False),
        sa.Column('age_40s', sa.Float(), nullable=False),
        sa.Column('age_50s', sa.Float(), nullable=False),
        sa.Column('age_60s_above', sa.Float(), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id']),
        sa.UniqueConstraint('article_id')
    )

    # Create index for collected_at
    op.create_index('ix_comment_stats_collected_at', 'comment_stats', ['collected_at'])


def downgrade() -> None:
    op.drop_table('comment_stats')
