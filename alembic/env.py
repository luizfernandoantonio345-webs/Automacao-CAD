"""
Engenharia CAD — Alembic environment configuration.

Suporta tanto PostgreSQL async (asyncpg) quanto SQLite (desenvolvimento).
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

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
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        # Normalizar postgres:// para postgresql:// (algumas plataformas usam postgres://)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        # Para Alembic sync (offline/online síncrono), remover +asyncpg
        url = url.replace("+asyncpg", "")
        return url
    return config.get_main_option("sqlalchemy.url", "sqlite:///data/engcad.db")


def get_async_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    fallback = config.get_main_option("sqlalchemy.url", "sqlite:///data/engcad.db")
    # SQLite não usa asyncpg
    return fallback


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Executa migrations usando engine async (PostgreSQL+asyncpg)."""
    connectable = create_async_engine(get_async_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    async_url = get_async_url()
    if async_url.startswith("postgresql+asyncpg://"):
        # Usar engine async para PostgreSQL
        asyncio.run(run_async_migrations())
    else:
        # SQLite: usar engine síncrono
        configuration = config.get_section(config.config_ini_section, {})
        configuration["sqlalchemy.url"] = get_url()
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
