"""add AI fields to draft_feedback

Revision ID: 002_add_ai_fields
Revises: 001_initial
Create Date: 2026-03-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_ai_fields'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI response and token usage columns to draft_feedback
    op.add_column('draft_feedback',
        sa.Column('ai_response', sa.Text(), nullable=True)
    )
    op.add_column('draft_feedback',
        sa.Column('tokens_used', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    # Remove AI fields if rolling back
    op.drop_column('draft_feedback', 'tokens_used')
    op.drop_column('draft_feedback', 'ai_response')
