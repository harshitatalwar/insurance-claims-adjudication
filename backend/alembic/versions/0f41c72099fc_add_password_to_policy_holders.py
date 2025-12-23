"""add_password_to_policy_holders

Revision ID: 0f41c72099fc
Revises: 02bccb97b9ae
Create Date: 2025-12-22 12:12:26.322099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0f41c72099fc'
down_revision: Union[str, Sequence[str], None] = '02bccb97b9ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('policy_holders')]
    
    # Add hashed_password column if it doesn't exist
    if 'hashed_password' not in columns:
        op.add_column('policy_holders', sa.Column('hashed_password', sa.String(), nullable=True))
        print("✅ Added 'hashed_password' column")
    else:
        print("⏭️  'hashed_password' column already exists, skipping")
    
    # Add is_active column if it doesn't exist
    if 'is_active' not in columns:
        op.add_column('policy_holders', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
        print("✅ Added 'is_active' column")
    else:
        print("⏭️  'is_active' column already exists, skipping")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('policy_holders')]
    
    # Remove columns if they exist
    if 'is_active' in columns:
        op.drop_column('policy_holders', 'is_active')
        print("✅ Dropped 'is_active' column")
    
    if 'hashed_password' in columns:
        op.drop_column('policy_holders', 'hashed_password')
        print("✅ Dropped 'hashed_password' column")
