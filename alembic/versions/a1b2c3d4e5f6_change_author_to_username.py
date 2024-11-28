"""change author to username

Revision ID: a1b2c3d4e5f6
Revises: 99b95b58f884
Create Date: 2024-11-27 12:00:00.000000

Note: This migration is a no-op as the 'username' column is already present in the model.
The change from 'author' to 'username' has been made in the SQLAlchemy model.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '99b95b58f884'  # Changed to previous head revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op migration: column already renamed in model
    pass


def downgrade() -> None:
    # No-op migration: column already renamed in model
    pass
