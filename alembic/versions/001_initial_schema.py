"""001_initial_schema - Schema inicial do banco de dados Engenharia CAD

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-15

Este migration cria todas as tabelas fundamentais do sistema:
- users: Usuários e autenticação
- projects: Projetos de engenharia
- quality_checks: Verificações de qualidade
- uploads: Arquivos enviados
- licenses: Licenças de software
- audit_logs: Logs de auditoria
- notifications: Sistema de notificações
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: users
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('empresa', sa.String(255), default=''),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('limite', sa.Integer(), default=100),
        sa.Column('usado', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('last_login', sa.Float(), nullable=True),
        sa.Column('preferences', sa.Text(), default='{}'),
    )
    
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: projects
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), sa.ForeignKey('users.email'), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('company', sa.String(255), default=''),
        sa.Column('part_name', sa.String(255), default=''),
        sa.Column('refinery_id', sa.String(50), nullable=True),
        
        # Parâmetros de tubulação
        sa.Column('diameter', sa.Float(), default=6),
        sa.Column('length', sa.Float(), default=1000),
        sa.Column('fluid', sa.String(50), default=''),
        sa.Column('material', sa.String(50), default=''),
        sa.Column('temperature_c', sa.Float(), default=25),
        sa.Column('operating_pressure_bar', sa.Float(), default=10),
        
        # Status e arquivos
        sa.Column('status', sa.String(50), default='created'),
        sa.Column('lsp_path', sa.String(500), nullable=True),
        sa.Column('dxf_path', sa.String(500), nullable=True),
        sa.Column('csv_path', sa.String(500), nullable=True),
        sa.Column('gcode_path', sa.String(500), nullable=True),
        
        # Qualidade e normas
        sa.Column('clash_count', sa.Integer(), default=0),
        sa.Column('norms_checked', sa.Text(), default='[]'),
        sa.Column('norms_passed', sa.Text(), default='[]'),
        sa.Column('piping_spec', sa.Text(), default='{}'),
        
        # AI fields
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('ai_suggestions', sa.Text(), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=True),
        sa.Column('completed_at', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_projects_user_email', 'projects', ['user_email'])
    op.create_index('ix_projects_code', 'projects', ['code'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_created_at', 'projects', ['created_at'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: quality_checks
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'quality_checks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('check_type', sa.String(100), nullable=False),
        sa.Column('check_name', sa.String(255), nullable=False),
        sa.Column('passed', sa.Boolean(), default=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('details', sa.Text(), default=''),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
    )
    
    op.create_index('ix_quality_checks_project_id', 'quality_checks', ['project_id'])
    op.create_index('ix_quality_checks_check_type', 'quality_checks', ['check_type'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: uploads
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), default=0),
        sa.Column('projects_generated', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), default='uploaded'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('processed_at', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_uploads_user_email', 'uploads', ['user_email'])
    op.create_index('ix_uploads_status', 'uploads', ['status'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: licenses
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'licenses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('license_key', sa.String(255), nullable=True),
        sa.Column('hwid', sa.String(255), nullable=True),
        sa.Column('machine_name', sa.String(255), nullable=True),
        sa.Column('max_machines', sa.Integer(), default=2),
        sa.Column('machines_used', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('expires_at', sa.Float(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('last_validated', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_licenses_username', 'licenses', ['username'])
    op.create_index('ix_licenses_hwid', 'licenses', ['hwid'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: audit_logs
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
    )
    
    op.create_index('ix_audit_logs_user_email', 'audit_logs', ['user_email'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: notifications
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('read_at', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_notifications_user_email', 'notifications', ['user_email'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: cam_jobs (Trabalhos de corte CNC)
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'cam_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('job_name', sa.String(255), nullable=False),
        sa.Column('material', sa.String(50), nullable=False),
        sa.Column('thickness', sa.Float(), nullable=False),
        sa.Column('sheet_width', sa.Float(), nullable=True),
        sa.Column('sheet_height', sa.Float(), nullable=True),
        sa.Column('piece_count', sa.Integer(), default=0),
        sa.Column('total_cutting_length', sa.Float(), nullable=True),
        sa.Column('estimated_time_min', sa.Float(), nullable=True),
        sa.Column('efficiency_percent', sa.Float(), nullable=True),
        sa.Column('gcode_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('cnc_profile', sa.String(100), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('started_at', sa.Float(), nullable=True),
        sa.Column('completed_at', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_cam_jobs_user_email', 'cam_jobs', ['user_email'])
    op.create_index('ix_cam_jobs_status', 'cam_jobs', ['status'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABELA: cam_pieces (Peças para biblioteca)
    # ═══════════════════════════════════════════════════════════════════════════
    op.create_table(
        'cam_pieces',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=True),  # NULL = biblioteca global
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('geometry_type', sa.String(50), nullable=False),
        sa.Column('geometry_data', sa.Text(), nullable=False),  # JSON
        sa.Column('bounding_width', sa.Float(), nullable=True),
        sa.Column('bounding_height', sa.Float(), nullable=True),
        sa.Column('area', sa.Float(), nullable=True),
        sa.Column('perimeter', sa.Float(), nullable=True),
        sa.Column('tags', sa.Text(), default='[]'),  # JSON array
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=True),
    )
    
    op.create_index('ix_cam_pieces_category', 'cam_pieces', ['category'])
    op.create_index('ix_cam_pieces_is_public', 'cam_pieces', ['is_public'])


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting FKs)
    op.drop_table('cam_pieces')
    op.drop_table('cam_jobs')
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('licenses')
    op.drop_table('uploads')
    op.drop_table('quality_checks')
    op.drop_table('projects')
    op.drop_table('users')
