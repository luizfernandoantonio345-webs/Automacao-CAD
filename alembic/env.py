"""
Engenharia CAD — Alembic environment configuration.

Este arquivo configura o Alembic para usar a variável de ambiente DATABASE_URL
quando disponível, permitindo fácil migração entre SQLite e PostgreSQL.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configuração do Alembic
config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Não usamos metadata do SQLAlchemy ORM (projeto usa conexões raw)
target_metadata = None


def get_url() -> str:
    """
    Obtém a URL do banco de dados.
    
    Prioridade:
    1. Variável de ambiente DATABASE_URL (produção)
    2. Variável de ambiente POSTGRES_URL (alternativa)
    3. Configuração do alembic.ini (desenvolvimento)
    """
    # Verificar variáveis de ambiente (produção)
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    
    if url:
        # Normalizar postgres:// para postgresql:// (algumas plataformas usam postgres://)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    # Fallback para configuração do alembic.ini
    return config.get_main_option("sqlalchemy.url", "sqlite:///data/engcad.db")


def run_migrations_offline() -> None:
    """
    Executa migrations em modo 'offline'.
    
    Neste modo, apenas o SQL é gerado, sem conexão real ao banco.
    Útil para revisão de scripts antes de aplicar.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrations em modo 'online'.
    
    Conecta ao banco de dados e aplica as migrations.
    """
    # Sobrescrever URL com valor dinâmico
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
