"""merge heads

Revision ID: bcbe87edf19f
Revises: add_id_sequences, ddcae578c358
Create Date: 2025-12-22 15:57:56.540583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcbe87edf19f'
down_revision: Union[str, Sequence[str], None] = ('add_id_sequences', 'ddcae578c358')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
