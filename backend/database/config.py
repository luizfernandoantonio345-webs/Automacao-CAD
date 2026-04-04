# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DO BANCO DE DADOS - PRODUÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
"""
Configuração de banco de dados com suporte a:
- SQLite (desenvolvimento local)
- PostgreSQL (produção / Vercel)
- Connection pooling
- Health checks

IMPORTANTE: Em produção (Vercel), configure DATABASE_URL para PostgreSQL.
SQLite no Vercel é EFÊMERO - dados serão perdidos entre deploys!

Opções de PostgreSQL para Vercel:
1. Vercel Postgres (nativo): vercel.com/docs/storage/vercel-postgres
2. Supabase: supabase.com
3. Neon: neon.tech
4. Railway: railway.app
5. Render: render.com

Exemplo de DATABASE_URL:
postgresql://user:password@host:5432/database
postgres://user:password@host:5432/database?sslmode=require
"""
from __future__ import annotations

import os
import logging
from typing import Optional
from functools import lru_cache
from dataclasses import dataclass

logger = logging.getLogger("engcad.db_config")


@dataclass
class DatabaseConfig:
    """Configuração do banco de dados."""
    
    # URL de conexão (SQLite ou PostgreSQL)
    url: str
    
    # Tipo de engine
    engine_type: str  # 'sqlite' ou 'postgresql'
    
    # Se estamos em produção
    is_production: bool
    
    # Se estamos no Vercel
    is_vercel: bool
    
    # Se o banco é efêmero (dados podem ser perdidos)
    is_ephemeral: bool
    
    # Pool de conexões (apenas PostgreSQL)
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800  # 30 minutos
    
    # Timeouts
    connect_timeout: int = 10
    statement_timeout: int = 30000  # 30 segundos em ms
    
    def __post_init__(self):
        if self.is_production and self.is_ephemeral:
            logger.warning(
                "⚠️  ATENÇÃO: Banco de dados EFÊMERO em PRODUÇÃO!\n"
                "    Dados serão PERDIDOS entre deploys.\n"
                "    Configure DATABASE_URL para PostgreSQL.\n"
                "    Veja: vercel.com/docs/storage/vercel-postgres"
            )


@lru_cache(maxsize=1)
def get_database_config() -> DatabaseConfig:
    """
    Obtém configuração do banco de dados baseada no ambiente.
    
    Prioridade:
    1. DATABASE_URL (PostgreSQL ou SQLite)
    2. ENGCAD_DB_PATH (SQLite local)
    3. Default SQLite (data/engcad.db ou /tmp/engcad.db no Vercel)
    """
    database_url = os.getenv("DATABASE_URL", "").strip()
    is_vercel = bool(os.getenv("VERCEL"))
    is_production = bool(os.getenv("VERCEL_ENV") == "production") or is_vercel
    
    # Detectar tipo de engine
    if database_url.startswith(("postgresql://", "postgres://")):
        engine_type = "postgresql"
        is_ephemeral = False
        url = database_url
        
        # Adicionar SSL se necessário (Vercel Postgres requer)
        if is_vercel and "sslmode" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
            
    else:
        engine_type = "sqlite"
        is_ephemeral = is_vercel  # SQLite no Vercel é efêmero
        
        # Determinar path do SQLite
        custom_path = os.getenv("ENGCAD_DB_PATH", "").strip()
        if custom_path:
            sqlite_path = custom_path
        elif is_vercel:
            sqlite_path = "/tmp/engcad.db"
        else:
            from pathlib import Path
            sqlite_path = str(Path(__file__).resolve().parents[1] / "data" / "engcad.db")
        
        url = f"sqlite:///{sqlite_path}"
    
    config = DatabaseConfig(
        url=url,
        engine_type=engine_type,
        is_production=is_production,
        is_vercel=is_vercel,
        is_ephemeral=is_ephemeral,
    )
    
    logger.info(
        f"Database Config: engine={config.engine_type}, "
        f"production={config.is_production}, "
        f"ephemeral={config.is_ephemeral}"
    )
    
    return config


def get_sqlalchemy_url() -> str:
    """Retorna URL formatada para SQLAlchemy."""
    config = get_database_config()
    return config.url


def get_connection_args() -> dict:
    """Retorna argumentos de conexão para SQLAlchemy."""
    config = get_database_config()
    
    if config.engine_type == "postgresql":
        return {
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
            "pool_recycle": config.pool_recycle,
            "pool_pre_ping": True,  # Verificar conexão antes de usar
            "connect_args": {
                "connect_timeout": config.connect_timeout,
                "options": f"-c statement_timeout={config.statement_timeout}"
            }
        }
    else:
        return {
            "connect_args": {
                "timeout": config.connect_timeout,
                "check_same_thread": False
            }
        }


def check_database_health() -> dict:
    """Verifica saúde do banco de dados."""
    config = get_database_config()
    
    result = {
        "engine": config.engine_type,
        "is_ephemeral": config.is_ephemeral,
        "is_production": config.is_production,
        "connected": False,
        "error": None
    }
    
    try:
        if config.engine_type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(config.url, connect_timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            result["connected"] = True
        else:
            import sqlite3
            conn = sqlite3.connect(config.url.replace("sqlite:///", ""), timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            result["connected"] = True
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


# Exportar configuração para uso direto
DATABASE_CONFIG = get_database_config()
