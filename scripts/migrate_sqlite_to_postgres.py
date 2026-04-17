#!/usr/bin/env python3
"""
scripts/migrate_sqlite_to_postgres.py
--------------------------------------
Migra todos os dados do banco SQLite (engcad.db) para PostgreSQL.
Processa em batches de 500 linhas com barra de progresso.

Uso:
    python scripts/migrate_sqlite_to_postgres.py ^
        --sqlite data/engcad.db ^
        --postgres "postgresql://user:pass@host:5432/engcad"

Pre-requisitos:
    pip install psycopg2-binary tqdm
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[ERRO] psycopg2-binary nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False
    class tqdm:  # type: ignore
        def __init__(self, iterable=None, total=None, desc="", unit=""):
            self._it = iterable; self._total = total; self._desc = desc; self._n = 0
        def __iter__(self):
            for item in self._it:
                yield item
                self._n += 1
                pct = int(self._n / self._total * 100) if self._total else 0
                print(f"\r  {self._desc}: {self._n}/{self._total} ({pct}%)", end="", flush=True)
            print()
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def update(self, n=1):
            self._n += n
            pct = int(self._n / self._total * 100) if self._total else 0
            print(f"\r  {self._desc}: {self._n}/{self._total} ({pct}%)", end="", flush=True)

BATCH_SIZE = 500
TABLES = ["users", "projects", "quality_checks", "uploads", "licenses"]

INSERT_SQL: dict[str, str] = {
    "users": (
        "INSERT INTO users (id,email,username,password_hash,empresa,tier,limite,usado,created_at,last_login) "
        "VALUES (%(id)s,%(email)s,%(username)s,%(password_hash)s,%(empresa)s,%(tier)s,%(limite)s,%(usado)s,%(created_at)s,%(last_login)s) "
        "ON CONFLICT (id) DO NOTHING"
    ),
    "projects": (
        "INSERT INTO projects (id,user_email,code,company,part_name,diameter,length,fluid,"
        "temperature_c,operating_pressure_bar,status,lsp_path,dxf_path,csv_path,"
        "clash_count,norms_checked,norms_passed,piping_spec,created_at,completed_at) "
        "VALUES (%(id)s,%(user_email)s,%(code)s,%(company)s,%(part_name)s,%(diameter)s,%(length)s,%(fluid)s,"
        "%(temperature_c)s,%(operating_pressure_bar)s,%(status)s,%(lsp_path)s,%(dxf_path)s,%(csv_path)s,"
        "%(clash_count)s,%(norms_checked)s,%(norms_passed)s,%(piping_spec)s,%(created_at)s,%(completed_at)s) "
        "ON CONFLICT (id) DO NOTHING"
    ),
    "quality_checks": (
        "INSERT INTO quality_checks (id,project_id,check_type,check_name,passed,details,created_at) "
        "VALUES (%(id)s,%(project_id)s,%(check_type)s,%(check_name)s,%(passed)s,%(details)s,%(created_at)s) "
        "ON CONFLICT (id) DO NOTHING"
    ),
    "uploads": (
        "INSERT INTO uploads (id,user_email,filename,file_path,row_count,projects_generated,status,created_at) "
        "VALUES (%(id)s,%(user_email)s,%(filename)s,%(file_path)s,%(row_count)s,%(projects_generated)s,%(status)s,%(created_at)s) "
        "ON CONFLICT (id) DO NOTHING"
    ),
    "licenses": (
        "INSERT INTO licenses (id,username,hwid,registered_at,last_seen,access_count) "
        "VALUES (%(id)s,%(username)s,%(hwid)s,%(registered_at)s,%(last_seen)s,%(access_count)s) "
        "ON CONFLICT (id) DO NOTHING"
    ),
}


def migrate_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str) -> int:
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total: int = cur.fetchone()[0]
    if total == 0:
        print(f"  {table}: vazia, pulando.")
        return 0
    cur.execute(f"SELECT * FROM {table}")
    pg_cur = pg_conn.cursor()
    sql = INSERT_SQL[table]
    migrated = 0
    with tqdm(total=total, desc=f"  {table}", unit="rows") as bar:
        batch = []
        for row in cur:
            batch.append(dict(row))
            if len(batch) >= BATCH_SIZE:
                psycopg2.extras.execute_batch(pg_cur, sql, batch)
                pg_conn.commit()
                migrated += len(batch)
                bar.update(len(batch))
                batch = []
        if batch:
            psycopg2.extras.execute_batch(pg_cur, sql, batch)
            pg_conn.commit()
            migrated += len(batch)
            bar.update(len(batch))
    return migrated


def reset_sequences(pg_conn) -> None:
    cur = pg_conn.cursor()
    for table in TABLES:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"
        )
    pg_conn.commit()
    print("  Sequences PostgreSQL atualizadas.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--sqlite", default="data/engcad.db")
    parser.add_argument("--postgres", required=True, help="postgresql://user:pass@host/db")
    parser.add_argument("--tables", nargs="+", default=TABLES)
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        print(f"[ERRO] SQLite nao encontrado: {sqlite_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Migracao SQLite -> PostgreSQL")
    print(f"  Origem : {sqlite_path}")
    print(f"  Destino: {args.postgres.split('@')[-1]}")
    print(f"{'='*60}\n")

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    try:
        pg_conn = psycopg2.connect(args.postgres)
    except psycopg2.OperationalError as e:
        print(f"[ERRO] Conexao PostgreSQL falhou: {e}")
        sys.exit(1)

    total_migrated = 0
    start = time.time()

    for table in args.tables:
        if table not in TABLES:
            print(f"  [AVISO] Tabela desconhecida: {table}, pulando.")
            continue
        count = migrate_table(sqlite_conn, pg_conn, table)
        total_migrated += count
        print(f"  OK {table}: {count} linhas")

    reset_sequences(pg_conn)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  Concluido em {elapsed:.1f}s | Total: {total_migrated} linhas")
    print(f"{'='*60}\n")

    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
