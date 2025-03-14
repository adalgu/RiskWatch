"""add_missing_columns_to_comments

Revision ID: 72fc2369fdc7
Revises: dee8149e79c4
Create Date: 2025-02-28 18:32:52.149357

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72fc2369fdc7'
down_revision = 'dee8149e79c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to comments table
    op.add_column('comments', sa.Column('profile_url', sa.String(), nullable=True))
    op.add_column('comments', sa.Column('likes', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('comments', sa.Column('dislikes', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('comments', sa.Column('reply_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('comments', sa.Column('is_reply', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('comments', sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('comments', sa.Column('delete_type', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove added columns from comments table
    op.drop_column('comments', 'delete_type')
    op.drop_column('comments', 'is_deleted')
    op.drop_column('comments', 'is_reply')
    op.drop_column('comments', 'reply_count')
    op.drop_column('comments', 'dislikes')
    op.drop_column('comments', 'likes')
    op.drop_column('comments', 'profile_url')
