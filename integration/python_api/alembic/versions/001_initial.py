"""create initial tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=120), nullable=False),
        sa.Column('usage_limit', sa.Integer(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)

    # Create project_events table
    op.create_table('project_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=120), nullable=False),
        sa.Column('company', sa.String(length=120), nullable=False),
        sa.Column('part_name', sa.String(length=120), nullable=False),
        sa.Column('diameter', sa.Float(), nullable=False),
        sa.Column('length', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('result_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_events_code'), 'project_events', ['code'], unique=False)
    op.create_index(op.f('ix_project_events_company'), 'project_events', ['company'], unique=False)
    op.create_index(op.f('ix_project_events_part_name'), 'project_events', ['part_name'], unique=False)
    op.create_index(op.f('ix_project_events_created_at'), 'project_events', ['created_at'], unique=False)

    # Create draft_feedback table
    op.create_table('draft_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('feedback', sa.String(length=20), nullable=False),
        sa.Column('company', sa.String(length=120), nullable=False),
        sa.Column('part_name', sa.String(length=120), nullable=False),
        sa.Column('code', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_draft_feedback_feedback'), 'draft_feedback', ['feedback'], unique=False)
    op.create_index(op.f('ix_draft_feedback_created_at'), 'draft_feedback', ['created_at'], unique=False)

    # Create project_stats table
    op.create_table('project_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('total_projects', sa.Integer(), nullable=False),
        sa.Column('seed_projects', sa.Integer(), nullable=False),
        sa.Column('real_projects', sa.Integer(), nullable=False),
        sa.Column('top_part_names', sa.Text(), nullable=False),
        sa.Column('top_companies', sa.Text(), nullable=False),
        sa.Column('diameter_min', sa.Float(), nullable=False),
        sa.Column('diameter_max', sa.Float(), nullable=False),
        sa.Column('length_min', sa.Float(), nullable=False),
        sa.Column('length_max', sa.Float(), nullable=False),
        sa.Column('draft_feedback_accepted', sa.Integer(), nullable=False),
        sa.Column('draft_feedback_rejected', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('project_stats')
    op.drop_table('draft_feedback')
    op.drop_table('project_events')
    op.drop_table('users')