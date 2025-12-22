"""add_decision_column_to_claims_table

Revision ID: 02bccb97b9ae
Revises: 4b895a667b0b
Create Date: 2025-12-22 10:36:30.136152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02bccb97b9ae'
down_revision: Union[str, Sequence[str], None] = '4b895a667b0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add decision column to claims table."""
    # Add decision column as nullable VARCHAR
    op.add_column('claims', sa.Column('decision', sa.String(20), nullable=True))


def downgrade() -> None:
    """Remove decision column from claims table."""
    op.drop_column('claims', 'decision')
