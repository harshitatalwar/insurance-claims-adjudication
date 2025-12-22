"""Create API usage log table

Revision ID: create_usage_log
Revises: 
Create Date: 2024-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'create_usage_log'
down_revision = '1aa9ceb7ea31'  # Depends on existing migration
branch_labels = None
depends_on = None


def upgrade():
    # Create api_usage_logs table
    op.create_table(
        'api_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('document_id', sa.String(), nullable=True),
        sa.Column('document_type', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for fast queries
    op.create_index('ix_api_usage_logs_timestamp', 'api_usage_logs', ['timestamp'])
    op.create_index('ix_api_usage_logs_endpoint', 'api_usage_logs', ['endpoint'])
    op.create_index('ix_api_usage_logs_document_id', 'api_usage_logs', ['document_id'])
    op.create_index('ix_api_usage_logs_id', 'api_usage_logs', ['id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_api_usage_logs_document_id', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_endpoint', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_timestamp', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_id', table_name='api_usage_logs')
    
    # Drop table
    op.drop_table('api_usage_logs')
