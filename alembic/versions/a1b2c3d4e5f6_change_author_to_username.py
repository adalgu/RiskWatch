"""Change author to username

Revision ID: a1b2c3d4e5f6
Revises: 664dcaa245dc
Create Date: 2023-11-27 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '664dcaa245dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename author column to username
    op.alter_column('comments', 'author', new_column_name='username')


def downgrade() -> None:
    # Rename username column back to author
    op.alter_column('comments', 'username', new_column_name='author')
