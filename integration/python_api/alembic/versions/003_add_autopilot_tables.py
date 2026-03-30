"""add autopilot tables

Revision ID: 003_add_autopilot_tables
Revises: 002
Create Date: 2026-03-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003_add_autopilot_tables'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'materials' not in table_names:
        op.create_table(
            'materials',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('density', sa.Float(), nullable=False),
            sa.Column('price_per_kg', sa.Numeric(10, 2), nullable=False),
            sa.Column('cad_hatch', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )
        op.create_index(op.f('ix_materials_name'), 'materials', ['name'], unique=False)

    if 'project_history' not in table_names:
        op.create_table(
            'project_history',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('code', sa.String(length=120), nullable=False),
            sa.Column('project_name', sa.String(length=100), nullable=False),
            sa.Column('company', sa.String(length=120), nullable=False),
            sa.Column('generated_at', sa.DateTime(), nullable=False),
            sa.Column('parameters_json', sa.Text(), nullable=False),
            sa.Column('estimated_weight', sa.Float(), nullable=False),
            sa.Column('estimated_cost', sa.Numeric(10, 2), nullable=False),
            sa.Column('compliance_status', sa.String(length=50), nullable=False),
            sa.Column('selected_profile', sa.String(length=80), nullable=False),
            sa.Column('material_name', sa.String(length=50), nullable=False),
            sa.Column('report_path', sa.Text(), nullable=True),
            sa.Column('cad_payload_path', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code'),
        )
        op.create_index(op.f('ix_project_history_code'), 'project_history', ['code'], unique=False)
        op.create_index(op.f('ix_project_history_company'), 'project_history', ['company'], unique=False)
        op.create_index(op.f('ix_project_history_compliance_status'), 'project_history', ['compliance_status'], unique=False)
        op.create_index(op.f('ix_project_history_generated_at'), 'project_history', ['generated_at'], unique=False)
        op.create_index(op.f('ix_project_history_project_name'), 'project_history', ['project_name'], unique=False)


def downgrade() -> None:
    op.drop_table('project_history')
    op.drop_table('materials')