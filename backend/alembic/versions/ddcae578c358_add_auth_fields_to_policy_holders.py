"""add_auth_fields_to_policy_holders

Revision ID: ddcae578c358
Revises: 0f41c72099fc
Create Date: 2025-12-22 12:22:34.728254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'ddcae578c358'
down_revision: Union[str, Sequence[str], None] = '0f41c72099fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('policy_holders')]
    indexes = [idx['name'] for idx in inspector.get_indexes('policy_holders')]
    
    # Add hashed_password column if it doesn't exist
    if 'hashed_password' not in columns:
        op.add_column('policy_holders', sa.Column('hashed_password', sa.String(), nullable=True))
        print("✅ Added 'hashed_password' column")
    else:
        print("⏭️  'hashed_password' column already exists, skipping")
    
    # Add is_active column if it doesn't exist
    if 'is_active' not in columns:
        op.add_column('policy_holders', sa.Column('is_active', sa.Boolean(), nullable=True))
        print("✅ Added 'is_active' column")
    else:
        print("⏭️  'is_active' column already exists, skipping")
    
    # Create email index if it doesn't exist
    if 'ix_policy_holders_email' not in indexes:
        op.create_index(op.f('ix_policy_holders_email'), 'policy_holders', ['email'], unique=True)
        print("✅ Created email index")
    else:
        print("⏭️  Email index already exists, skipping")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('policy_holders')]
    indexes = [idx['name'] for idx in inspector.get_indexes('policy_holders')]
    
    # Drop index if it exists
    if 'ix_policy_holders_email' in indexes:
        op.drop_index(op.f('ix_policy_holders_email'), table_name='policy_holders')
        print("✅ Dropped email index")
    
    # Drop columns if they exist
    if 'is_active' in columns:
        op.drop_column('policy_holders', 'is_active')
        print("✅ Dropped 'is_active' column")
    
    if 'hashed_password' in columns:
        op.drop_column('policy_holders', 'hashed_password')
        print("✅ Dropped 'hashed_password' column")
