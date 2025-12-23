"""add_decision_column_to_claims_table

Revision ID: 02bccb97b9ae
Revises: 4b895a667b0b
Create Date: 2025-12-22 10:36:30.136152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '02bccb97b9ae'
down_revision: Union[str, Sequence[str], None] = '4b895a667b0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add decision column to claims table."""
    # Check if column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('claims')]
    
    if 'decision' not in columns:
        # Add decision column as nullable VARCHAR
        op.add_column('claims', sa.Column('decision', sa.String(20), nullable=True))
        print("✅ Added 'decision' column to claims table")
    else:
        print("⏭️  'decision' column already exists, skipping")


def downgrade() -> None:
    """Remove decision column from claims table."""
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('claims')]
    
    if 'decision' in columns:
        op.drop_column('claims', 'decision')
        print("✅ Dropped 'decision' column from claims table")
    else:
        print("⏭️  'decision' column doesn't exist, skipping")
