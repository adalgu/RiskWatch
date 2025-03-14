"""change collection_method to is_api_collection

Revision ID: 664dcaa245dc
Revises: 392cfa2fa328
Create Date: 2024-11-27 11:17:17.700488

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '664dcaa245dc'
down_revision = '392cfa2fa328'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # 1. Add is_api_collection as nullable first
    op.add_column('articles', sa.Column('is_api_collection', sa.Boolean(), server_default='true', nullable=False))
    
    # 2. Update existing rows based on collection_method
    op.execute("""
        UPDATE articles 
        SET is_api_collection = CASE 
            WHEN collection_method = 'API' THEN true 
            WHEN collection_method = 'SEARCH' THEN false 
            ELSE true  -- Default to true for any other cases
        END
    """)
    
    # 3. Drop the old column
    op.drop_column('articles', 'collection_method')
    
    # 4. Drop the enum type
    op.execute('DROP TYPE IF EXISTS collectionmethod')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # 1. Create the enum type
    op.execute("CREATE TYPE collectionmethod AS ENUM ('API', 'SEARCH')")
    
    # 2. Add back collection_method column
    op.add_column('articles', sa.Column('collection_method', postgresql.ENUM('API', 'SEARCH', name='collectionmethod'), nullable=True))
    
    # 3. Update collection_method based on is_api_collection
    op.execute("""
        UPDATE articles 
        SET collection_method = CASE 
            WHEN is_api_collection = true THEN 'API'::collectionmethod 
            ELSE 'SEARCH'::collectionmethod 
        END
    """)
    
    # 4. Set collection_method to not null
    op.alter_column('articles', 'collection_method',
                    existing_type=postgresql.ENUM('API', 'SEARCH', name='collectionmethod'),
                    nullable=False)
    
    # 5. Drop is_api_collection
    op.drop_column('articles', 'is_api_collection')
    # ### end Alembic commands ###
