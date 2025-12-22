"""add_password_to_policy_holders

Revision ID: 0f41c72099fc
Revises: 02bccb97b9ae
Create Date: 2025-12-22 12:12:26.322099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f41c72099fc'
down_revision: Union[str, Sequence[str], None] = '02bccb97b9ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hashed_password column to policy_holders
    op.add_column('policy_holders', sa.Column('hashed_password', sa.String(), nullable=True))
    op.add_column('policy_holders', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    # Remove the columns
    op.drop_column('policy_holders', 'is_active')
    op.drop_column('policy_holders', 'hashed_password')
