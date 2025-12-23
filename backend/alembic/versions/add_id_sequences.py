"""Add sequences for atomic ID generation

Revision ID: add_id_sequences
Revises: 4b895a667b0b
Create Date: 2025-12-22 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_id_sequences'
down_revision = '4b895a667b0b'
branch_labels = None
depends_on = None


def upgrade():
    # Create sequences for atomic ID generation
    # These sequences are thread-safe and prevent race conditions
    
    # Claim ID sequence (CLM000001, CLM000002, ...)
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS claim_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;
    """)
    
    # Policy Holder ID sequence (PH000001, PH000002, ...)
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS policy_holder_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;
    """)
    
    # Document ID sequence (DOC000001, DOC000002, ...)
    # Note: Currently using UUIDs, but adding sequence for future use
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS document_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;
    """)
    
    # Initialize sequences with current max values to avoid conflicts
    # This ensures new IDs start after existing ones
    
    # Set claim_id_seq to max existing claim number
    op.execute("""
        SELECT setval('claim_id_seq', 
            COALESCE(
                (SELECT MAX(CAST(SUBSTRING(claim_id FROM 4) AS INTEGER))
                 FROM claims
                 WHERE claim_id ~ '^CLM[0-9]+$'),
                1
            )
        );
    """)
    
    # Set policy_holder_id_seq to max existing policy holder number
    op.execute("""
        SELECT setval('policy_holder_id_seq', 
            COALESCE(
                (SELECT MAX(CAST(SUBSTRING(policy_holder_id FROM 3) AS INTEGER))
                 FROM policy_holders
                 WHERE policy_holder_id ~ '^PH[0-9]+$'),
                1
            )
        );
    """)


def downgrade():
    # Drop sequences
    op.execute("DROP SEQUENCE IF EXISTS claim_id_seq;")
    op.execute("DROP SEQUENCE IF EXISTS policy_holder_id_seq;")
    op.execute("DROP SEQUENCE IF EXISTS document_id_seq;")
