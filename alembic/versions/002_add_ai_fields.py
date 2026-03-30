"""Add AI fields to draft_feedback table.

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """✓ PROBLEMA #7: Upgrade com idempotência (IF NOT EXISTS)."""
    # Usar SQLite IF NOT EXISTS, PostgreSQL com conditional logic
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # Verificar se as colunas já existem (idempotência)
    inspector = sa.inspect(conn)
    columns = {col['name'] for col in inspector.get_columns('draft_feedback')}
    
    if 'ai_response' not in columns:
        op.add_column('draft_feedback',
                      sa.Column('ai_response', sa.Text(), nullable=True,
                                comment='AI-generated response from Ollama')
                      )
        print("✓ Coluna 'ai_response' adicionada")
    else:
        print("⚠️ Coluna 'ai_response' já existe")
    
    if 'tokens_used' not in columns:
        op.add_column('draft_feedback',
                      sa.Column('tokens_used', sa.Integer(), nullable=True, default=0,
                                comment='Number of tokens used for AI generation')
                      )
        print("✓ Coluna 'tokens_used' adicionada")
    else:
        print("⚠️ Coluna 'tokens_used' já existe")
    
    # ✓ PROBLEMA #14: Adicionar coluna de versão do modelo
    if 'ai_model_version' not in columns:
        op.add_column('draft_feedback',
                      sa.Column('ai_model_version', sa.String(50), nullable=True, default="unknown",
                                comment='Version of AI model used for generation')
                      )
        print("✓ Coluna 'ai_model_version' adicionada")
    else:
        print("⚠️ Coluna 'ai_model_version' já existe")
    
    # ✓ PROBLEMA #7: Log da migração
    op.execute("SELECT 1;")  # Validar conexão
    print("✓ Migração 002 concluída com sucesso")


def downgrade():
    """Remover AI fields (com segurança)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col['name'] for col in inspector.get_columns('draft_feedback')}
    
    if 'ai_response' in columns:
        op.drop_column('draft_feedback', 'ai_response')
        print("✓ Coluna 'ai_response' removida")
    
    if 'tokens_used' in columns:
        op.drop_column('draft_feedback', 'tokens_used')
        print("✓ Coluna 'tokens_used' removida")
    
    print("✓ Downgrade 002 concluído")
