#!/usr/bin/env python
"""
Engenharia CAD — Script de Migração SQLite → PostgreSQL

Este script exporta dados do SQLite local e importa no PostgreSQL.
Útil para migrar dados de desenvolvimento para produção.

Uso:
    python scripts/migrate_sqlite_to_postgres.py --postgres-url "postgresql://..."
    
    # Ou com variável de ambiente:
    export POSTGRES_URL="postgresql://..."
    python scripts/migrate_sqlite_to_postgres.py
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
import psycopg2.extras

# Caminho padrão do SQLite local
DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[1] / "data" / "engcad.db"

# Tabelas a migrar (ordem importa por causa de FKs)
TABLES_TO_MIGRATE = [
    "users",
    "projects",
    "quality_checks",
    "uploads",
    "licenses",
    "audit_logs",
    "notifications",
    "user_sessions",
    "user_devices",
]


def get_sqlite_conn(db_path: Path) -> sqlite3.Connection:
    """Conecta ao SQLite."""
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres_conn(postgres_url: str):
    """Conecta ao PostgreSQL."""
    return psycopg2.connect(postgres_url)


def get_table_columns(sqlite_conn: sqlite3.Connection, table: str) -> list[str]:
    """Obtém lista de colunas de uma tabela SQLite."""
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row["name"] for row in cursor.fetchall()]


def table_exists_sqlite(sqlite_conn: sqlite3.Connection, table: str) -> bool:
    """Verifica se tabela existe no SQLite."""
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def table_exists_postgres(pg_conn, table: str) -> bool:
    """Verifica se tabela existe no PostgreSQL."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
            (table,)
        )
        return cur.fetchone()[0]


def count_rows(conn, table: str, is_pg: bool = False) -> int:
    """Conta linhas em uma tabela."""
    if is_pg:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]
    else:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table: str,
    batch_size: int = 1000
) -> int:
    """Migra dados de uma tabela SQLite para PostgreSQL."""
    if not table_exists_sqlite(sqlite_conn, table):
        print(f"  ⚠️  Tabela {table} não existe no SQLite, pulando...")
        return 0
    
    if not table_exists_postgres(pg_conn, table):
        print(f"  ⚠️  Tabela {table} não existe no PostgreSQL, pulando...")
        print(f"      Execute 'alembic upgrade head' primeiro para criar as tabelas.")
        return 0
    
    columns = get_table_columns(sqlite_conn, table)
    sqlite_count = count_rows(sqlite_conn, table)
    
    if sqlite_count == 0:
        print(f"  ℹ️  Tabela {table} está vazia no SQLite, pulando...")
        return 0
    
    print(f"  📊 Migrando {sqlite_count} registros de {table}...")
    
    # Limpar tabela destino (opcional - cuidado em produção!)
    # with pg_conn.cursor() as cur:
    #     cur.execute(f"TRUNCATE TABLE {table} CASCADE")
    
    # Preparar query de inserção
    columns_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    
    # Buscar dados do SQLite em batches
    cursor = sqlite_conn.execute(f"SELECT * FROM {table}")
    migrated = 0
    
    with pg_conn.cursor() as pg_cur:
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            
            # Converter para lista de tuplas
            data = [tuple(row) for row in rows]
            
            # Inserir no PostgreSQL
            psycopg2.extras.execute_batch(pg_cur, insert_sql, data)
            migrated += len(data)
            
            print(f"    → {migrated}/{sqlite_count} registros...")
    
    pg_conn.commit()
    
    # Verificar contagem final
    pg_count = count_rows(pg_conn, table, is_pg=True)
    print(f"  ✅ {table}: {pg_count} registros no PostgreSQL")
    
    return migrated


def run_migrations(pg_conn, alembic_config: str = "alembic.ini"):
    """Executa migrations do Alembic no PostgreSQL."""
    print("\n📦 Executando migrations do Alembic...")
    try:
        from alembic.config import Config
        from alembic import command
        
        cfg = Config(alembic_config)
        # Sobrescrever URL do banco
        cfg.set_main_option("sqlalchemy.url", pg_conn.dsn)
        
        command.upgrade(cfg, "head")
        print("✅ Migrations concluídas!")
    except ImportError:
        print("⚠️  Alembic não instalado. Execute manualmente: alembic upgrade head")
    except Exception as e:
        print(f"❌ Erro nas migrations: {e}")
        print("   Execute manualmente: alembic upgrade head")


def main():
    parser = argparse.ArgumentParser(
        description="Migra dados do SQLite local para PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help="Caminho do arquivo SQLite"
    )
    parser.add_argument(
        "--postgres-url",
        type=str,
        default=os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL"),
        help="URL de conexão PostgreSQL"
    )
    parser.add_argument(
        "--run-migrations",
        action="store_true",
        help="Executar migrations do Alembic antes de migrar dados"
    )
    parser.add_argument(
        "--tables",
        type=str,
        nargs="*",
        default=TABLES_TO_MIGRATE,
        help="Tabelas específicas para migrar"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostrar o que seria migrado, sem executar"
    )
    
    args = parser.parse_args()
    
    if not args.postgres_url:
        print("❌ Erro: PostgreSQL URL não fornecida.")
        print("   Use --postgres-url ou defina POSTGRES_URL/DATABASE_URL")
        sys.exit(1)
    
    print("=" * 60)
    print("🔄 MIGRAÇÃO SQLite → PostgreSQL")
    print("=" * 60)
    print(f"📁 SQLite: {args.sqlite_path}")
    print(f"🐘 PostgreSQL: {args.postgres_url.split('@')[-1] if '@' in args.postgres_url else '(url)'}")
    print(f"📋 Tabelas: {', '.join(args.tables)}")
    print()
    
    if args.dry_run:
        print("🔍 MODO DRY-RUN - Nenhuma alteração será feita")
        print()
    
    # Conectar aos bancos
    try:
        sqlite_conn = get_sqlite_conn(args.sqlite_path)
        print("✅ Conectado ao SQLite")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    try:
        pg_conn = get_postgres_conn(args.postgres_url)
        print("✅ Conectado ao PostgreSQL")
    except Exception as e:
        print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
        sys.exit(1)
    
    print()
    
    # Executar migrations se solicitado
    if args.run_migrations and not args.dry_run:
        run_migrations(pg_conn)
    
    # Migrar tabelas
    print("\n📊 MIGRAÇÃO DE DADOS")
    print("-" * 40)
    
    total_migrated = 0
    for table in args.tables:
        if args.dry_run:
            if table_exists_sqlite(sqlite_conn, table):
                count = count_rows(sqlite_conn, table)
                print(f"  [DRY-RUN] {table}: {count} registros seriam migrados")
        else:
            try:
                migrated = migrate_table(sqlite_conn, pg_conn, table)
                total_migrated += migrated
            except Exception as e:
                print(f"  ❌ Erro ao migrar {table}: {e}")
    
    # Resumo
    print()
    print("=" * 60)
    if args.dry_run:
        print("🔍 DRY-RUN CONCLUÍDO - Nenhuma alteração foi feita")
    else:
        print(f"✅ MIGRAÇÃO CONCLUÍDA - {total_migrated} registros migrados")
    print("=" * 60)
    
    # Limpar
    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
