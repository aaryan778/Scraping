"""Add created_at field to jobs table

Revision ID: 001_add_created_at
Revises:
Create Date: 2025-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001_add_created_at'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add created_at column to jobs table"""
    # Add created_at column (nullable first for existing rows)
    op.add_column('jobs', sa.Column('created_at', sa.DateTime(), nullable=True))

    # Set created_at to scraped_date for existing rows
    op.execute("""
        UPDATE jobs
        SET created_at = scraped_date
        WHERE created_at IS NULL
    """)

    # Make created_at non-nullable and indexed
    op.alter_column('jobs', 'created_at', nullable=False)
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])


def downgrade() -> None:
    """Remove created_at column from jobs table"""
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_column('jobs', 'created_at')
