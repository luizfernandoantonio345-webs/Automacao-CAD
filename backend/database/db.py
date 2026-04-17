"""
Engenharia CAD — Camada de persistência (PostgreSQL async / SQLite fallback).

Usa SQLAlchemy async com asyncpg para PostgreSQL em produção.
SQLite síncrono é mantido apenas para desenvolvimento local.

Pool de conexões (PostgreSQL):
  pool_size=20, max_overflow=40, pool_pre_ping=True
  pool_recycle=1800  (evita conexões obsoletas após NAT timeout)

Retry automático: até 3 tentativas em deadlocks / serialization failures.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger("engcad.db")

# ── Engine selection ─────────────────────────────────────────────────────────
_RAW_URL: str = os.getenv("DATABASE_URL", "").strip()

# Decodificar URL-encoded characters (%26 -> &, etc.)
from urllib.parse import unquote, urlparse, urlunparse, parse_qs, urlencode
_RAW_URL = unquote(_RAW_URL)

# Normalizar postgres:// → postgresql+asyncpg://
if _RAW_URL.startswith("postgres://"):
    _RAW_URL = _RAW_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif _RAW_URL.startswith("postgresql://") and "+asyncpg" not in _RAW_URL:
    _RAW_URL = _RAW_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Fix malformed URLs where query params use & instead of ?
# E.g., /neondb&sslmode=require should be /neondb?sslmode=require
# Use urlparse to properly handle path vs query separation
if _RAW_URL:
    _parsed = urlparse(_RAW_URL)
    if "&" in _parsed.path and not _parsed.query:
        # Path contains & but no query string - fix the malformed URL
        _path_parts = _parsed.path.split("&", 1)
        _new_path = _path_parts[0]
        _new_query = _path_parts[1] if len(_path_parts) > 1 else ""
        _parsed = _parsed._replace(path=_new_path, query=_new_query)
        _RAW_URL = urlunparse(_parsed)
        logger.info("Fixed DATABASE_URL malformed path (v3): %s", _new_path)

# Remove channel_binding que causa erro em algumas versões do asyncpg
if "channel_binding" in _RAW_URL:
    import re
    _RAW_URL = re.sub(r"[?&]channel_binding=[^&]*", "", _RAW_URL)
    # Se removeu ?channel_binding e sobrou &param, corrige para ?param
    _RAW_URL = re.sub(r"\?&", "?", _RAW_URL)
    _RAW_URL = re.sub(r"&+", "&", _RAW_URL).rstrip("&?")  # limpa separadores extras

_DATABASE_URL = _RAW_URL  # alias para compatibilidade
_USE_PG: bool = _RAW_URL.startswith("postgresql+asyncpg://")
_IS_VERCEL = bool(os.getenv("VERCEL"))
_IS_PRODUCTION = os.getenv("VERCEL_ENV") == "production" or os.getenv("APP_ENV") == "production"
_ALLOW_EPHEMERAL = os.getenv("ALLOW_EPHEMERAL_DB", "").strip().lower() in ("true", "1", "yes")
_EPHEMERAL_MODE = False

# If DATABASE_URL is malformed (path contains &), force fallback to SQLite
_URL_MALFORMED = False
if _USE_PG and _RAW_URL:
    _check_parsed = urlparse(_RAW_URL)
    if "&" in _check_parsed.path:
        logger.error("DATABASE_URL still malformed after fix attempt: path contains &")
        _URL_MALFORMED = True
        _USE_PG = False  # Force fallback to SQLite

if _IS_PRODUCTION and not _USE_PG and not _ALLOW_EPHEMERAL:
    if _IS_VERCEL or _URL_MALFORMED:
        # Vercel serverless: aceita SQLite efêmero quando DATABASE_URL não configurada.
        # Dados são perdidos entre reinicializações, mas o sistema funciona.
        logger.warning(
            "⚠️ PRODUÇÃO SEM DATABASE_URL: Usando SQLite efêmero no Vercel. "
            "Configure DATABASE_URL para PostgreSQL para persistência real."
        )
        _EPHEMERAL_MODE = True
    else:
        raise RuntimeError(
            "DATABASE_URL é obrigatório em produção e deve apontar para PostgreSQL. "
            "SQLite local/efêmero não é permitido nesse ambiente. "
            "Para demo/MVP, defina ALLOW_EPHEMERAL_DB=true (dados serão perdidos entre deploys)."
        )

if _USE_PG:
    logger.info("Usando PostgreSQL async (asyncpg): %s", _RAW_URL.split("@")[-1] if "@" in _RAW_URL else "(url)")
else:
    _DB_PATH = Path(os.getenv("ENGCAD_DB_PATH", ""))
    if not _DB_PATH.name:
        if _IS_VERCEL:
            # Vercel serverless requer /tmp para SQLite
            _DB_PATH = Path("/tmp/engcad.db")  # nosec B108
            _EPHEMERAL_MODE = True
            if _IS_PRODUCTION:
                logger.warning(
                    "⚠️ AVISO: SQLite efêmero em produção Vercel! "
                    "Configure DATABASE_URL para PostgreSQL para persistência real."
                )
        else:
            _DB_PATH = Path(__file__).resolve().parents[2] / "data" / "engcad.db"
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Usando SQLite: %s (efêmero=%s)", _DB_PATH, _EPHEMERAL_MODE)

# ── Async Engine (PostgreSQL) ─────────────────────────────────────────────────
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker | None = None

if _USE_PG:
    _pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    # connect_args sem channel_binding para compatibilidade com asyncpg mais antigo
    _connect_args = {
        "server_settings": {"application_name": "engcad"},
    }
    _async_engine = create_async_engine(
        _RAW_URL,
        pool_size=_pool_size,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
        connect_args=_connect_args,
    )
    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    logger.info("Pool configurado: pool_size=%d, max_overflow=40", _pool_size)

# ── SQLite thread-local (desenvolvimento) ────────────────────────────────────
_LOCAL = threading.local()

# ── Pool de conexões integrado ───────────────────────────────────────────────
try:
    from backend.database.connection_pool import get_pool, SQLitePool
    _POOL_AVAILABLE = True
except ImportError:
    _POOL_AVAILABLE = False

# ── Retry helper para deadlocks ───────────────────────────────────────────────
_DEADLOCK_CODES = {"40001", "40P01"}  # serialization_failure, deadlock_detected
_MAX_RETRIES = 3


def _is_deadlock(exc: Exception) -> bool:
    msg = str(exc)
    return any(code in msg for code in _DEADLOCK_CODES)


def with_retry(max_retries: int = _MAX_RETRIES):
    """Decorador: reexecuta funções async em caso de deadlock."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    if attempt < max_retries and _is_deadlock(exc):
                        wait = 2 ** (attempt - 1) * 0.1
                        logger.warning(
                            "Deadlock detectado (tentativa %d/%d), retry em %.1fs",
                            attempt, max_retries, wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
        return wrapper
    return decorator


def is_ephemeral() -> bool:
    """Retorna True se o banco é temporário (perderá dados entre deploys)."""
    return _EPHEMERAL_MODE and not _USE_PG


# ── Contextos de sessão ──────────────────────────────────────────────────────

@asynccontextmanager
async def get_async_session():
    """Context manager para AsyncSession (PostgreSQL).

    Uso:
        async with get_async_session() as session:
            result = await session.execute(text("SELECT ..."), {...})
    """
    if not _USE_PG or _async_session_factory is None:
        raise RuntimeError(
            "get_async_session() requer DATABASE_URL apontando para PostgreSQL."
        )
    async with _async_session_factory() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


@asynccontextmanager
async def get_async_connection():
    """Context manager para AsyncConnection direta (bulk inserts, DDL)."""
    if not _USE_PG or _async_engine is None:
        raise RuntimeError(
            "get_async_connection() requer DATABASE_URL apontando para PostgreSQL."
        )
    async with _async_engine.begin() as conn:
        yield conn


def _get_sqlite_conn() -> sqlite3.Connection:
    conn = getattr(_LOCAL, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(_DB_PATH), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _LOCAL.conn = conn
    return conn


@contextmanager
def get_db():
    """Context manager síncrono (SQLite apenas — desenvolvimento).

    Em produção com PostgreSQL, use get_async_session() ou get_async_connection().
    """
    if _USE_PG:
        raise RuntimeError(
            "get_db() não suporta PostgreSQL async. Use get_async_session()."
        )
    if _POOL_AVAILABLE:
        pool = get_pool()
        if isinstance(pool, SQLitePool):
            with pool.acquire() as conn:
                yield conn
            return
    conn = _get_sqlite_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _q(sql: str) -> str:
    """Compatibilidade placeholder (não necessário com SQLAlchemy text())."""
    return sql


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT UNIQUE NOT NULL,
    username    TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    empresa     TEXT DEFAULT '',
    tier        TEXT DEFAULT 'demo',
    limite      INTEGER DEFAULT 100,
    usado       INTEGER DEFAULT 0,
    created_at  REAL NOT NULL,
    last_login  REAL
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT NOT NULL,
    code        TEXT NOT NULL,
    company     TEXT DEFAULT '',
    part_name   TEXT DEFAULT '',
    diameter    REAL DEFAULT 6,
    length      REAL DEFAULT 1000,
    fluid       TEXT DEFAULT '',
    temperature_c   REAL DEFAULT 25,
    operating_pressure_bar REAL DEFAULT 10,
    status      TEXT DEFAULT 'created',
    lsp_path    TEXT,
    dxf_path    TEXT,
    csv_path    TEXT,
    clash_count INTEGER DEFAULT 0,
    norms_checked TEXT DEFAULT '[]',
    norms_passed  TEXT DEFAULT '[]',
    piping_spec TEXT DEFAULT '{}',
    created_at  REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY (user_email) REFERENCES users(email)
);

CREATE TABLE IF NOT EXISTS quality_checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    check_type  TEXT NOT NULL,
    check_name  TEXT NOT NULL,
    passed      INTEGER NOT NULL DEFAULT 0,
    details     TEXT DEFAULT '',
    created_at  REAL NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS uploads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT NOT NULL,
    filename    TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    row_count   INTEGER DEFAULT 0,
    projects_generated INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'uploaded',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS licenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    hwid        TEXT NOT NULL,
    registered_at REAL NOT NULL,
    last_seen   REAL,
    access_count INTEGER DEFAULT 1
);
"""

_PG_TABLES = [
    """CREATE TABLE IF NOT EXISTS users (
        id          SERIAL PRIMARY KEY,
        email       TEXT UNIQUE NOT NULL,
        username    TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        empresa     TEXT DEFAULT '',
        tier        TEXT DEFAULT 'demo',
        limite      INTEGER DEFAULT 100,
        usado       INTEGER DEFAULT 0,
        created_at  DOUBLE PRECISION NOT NULL,
        last_login  DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS projects (
        id          SERIAL PRIMARY KEY,
        user_email  TEXT NOT NULL REFERENCES users(email),
        code        TEXT NOT NULL,
        company     TEXT DEFAULT '',
        part_name   TEXT DEFAULT '',
        diameter    DOUBLE PRECISION DEFAULT 6,
        length      DOUBLE PRECISION DEFAULT 1000,
        fluid       TEXT DEFAULT '',
        temperature_c   DOUBLE PRECISION DEFAULT 25,
        operating_pressure_bar DOUBLE PRECISION DEFAULT 10,
        status      TEXT DEFAULT 'created',
        lsp_path    TEXT,
        dxf_path    TEXT,
        csv_path    TEXT,
        clash_count INTEGER DEFAULT 0,
        norms_checked TEXT DEFAULT '[]',
        norms_passed  TEXT DEFAULT '[]',
        piping_spec TEXT DEFAULT '{}',
        created_at  DOUBLE PRECISION NOT NULL,
        completed_at DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS quality_checks (
        id          SERIAL PRIMARY KEY,
        project_id  INTEGER NOT NULL REFERENCES projects(id),
        check_type  TEXT NOT NULL,
        check_name  TEXT NOT NULL,
        passed      INTEGER NOT NULL DEFAULT 0,
        details     TEXT DEFAULT '',
        created_at  DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS uploads (
        id          SERIAL PRIMARY KEY,
        user_email  TEXT NOT NULL,
        filename    TEXT NOT NULL,
        file_path   TEXT NOT NULL,
        row_count   INTEGER DEFAULT 0,
        projects_generated INTEGER DEFAULT 0,
        status      TEXT DEFAULT 'uploaded',
        created_at  DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS licenses (
        id          SERIAL PRIMARY KEY,
        username    TEXT UNIQUE NOT NULL,
        hwid        TEXT NOT NULL,
        registered_at DOUBLE PRECISION NOT NULL,
        last_seen   DOUBLE PRECISION,
        access_count INTEGER DEFAULT 1
    )""",
]

# Compatibilidade: em alguns ambientes o schema inicial de Alembic é mais antigo
# e não contém todas as colunas usadas pelo backend atual.
_PG_COMPAT_ALTERS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'demo'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS limite INTEGER DEFAULT 100",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS usado INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS empresa TEXT DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login DOUBLE PRECISION",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS piping_spec TEXT DEFAULT '{}'",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS completed_at DOUBLE PRECISION",
    "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS row_count INTEGER DEFAULT 0",
    "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS projects_generated INTEGER DEFAULT 0",
    "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'uploaded'",
]


# ── Helpers internos ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    import hmac as _hmac
    parts = stored_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt = bytes.fromhex(parts[0])
    expected = bytes.fromhex(parts[1])
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(h, expected)


    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    import hmac as _hmac
    parts = stored_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt = bytes.fromhex(parts[0])
    expected = bytes.fromhex(parts[1])
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return _hmac.compare_digest(h, expected)


# ── DDL / init ───────────────────────────────────────────────────────────────

async def _seed_owner_enterprise_user() -> None:
    """Cria usuário enterprise fixo do dono do sistema (conta ilimitada para testes)."""
    owner_email = "santossod345@gmail.com"
    owner_user = "santossod345"
    owner_pass = "Santos14!"
    pw_hash = _hash_password(owner_pass)
    now = time.time()
    try:
        async with get_async_session() as session:
            # Verifica se já existe
            result = await session.execute(
                text("SELECT email FROM users WHERE email = :email"),
                {"email": owner_email}
            )
            exists = result.first() is not None
            if exists:
                # Atualiza para garantir tier enterprise e limite ilimitado
                await session.execute(
                    text("UPDATE users SET tier = 'enterprise', limite = 9999999, password_hash = :pw WHERE email = :email"),
                    {"pw": pw_hash, "email": owner_email}
                )
                logger.info(f"Usuário dono {owner_email} atualizado para enterprise ilimitado")
            else:
                # Cria novo usuário enterprise
                await session.execute(
                    text(
                        "INSERT INTO users (email, username, password_hash, empresa, tier, limite, created_at) "
                        "VALUES (:email, :username, :pw_hash, :empresa, :tier, :limite, :now)"
                    ),
                    {"email": owner_email, "username": owner_user, "pw_hash": pw_hash,
                     "empresa": "Sistema EngCAD - Dono", "tier": "enterprise", "limite": 9999999, "now": now}
                )
                logger.info(f"Usuário dono {owner_email} criado com plano enterprise ilimitado")
    except Exception as e:
        logger.warning(f"Seed owner enterprise: {e}")


async def init_db_async() -> None:
    """Cria tabelas PostgreSQL se não existirem (async)."""
    async with get_async_connection() as conn:
        for ddl in _PG_DDL:
            await conn.execute(text(ddl))
        for alter in _PG_COMPAT_ALTERS:
            await conn.execute(text(alter))
    # Seed do usuário dono com enterprise ilimitado
    await _seed_owner_enterprise_user()
    logger.info("Engenharia CAD DB inicializado (PostgreSQL async)")


def _sqlite_migrate_columns(conn) -> None:
    """Adiciona colunas faltantes em bancos SQLite existentes."""
    # Mapeia tabela -> colunas a adicionar (nome, tipo, default)
    migrations = [
        ("users", "tier", "TEXT", "'demo'"),
        ("users", "limite", "INTEGER", "100"),
        ("users", "usado", "INTEGER", "0"),
        ("users", "empresa", "TEXT", "''"),
        ("users", "last_login", "REAL", "NULL"),
        ("projects", "piping_spec", "TEXT", "'{}'"),
        ("projects", "completed_at", "REAL", "NULL"),
        ("uploads", "row_count", "INTEGER", "0"),
        ("uploads", "projects_generated", "INTEGER", "0"),
        ("uploads", "status", "TEXT", "'uploaded'"),
    ]
    for table, col, col_type, default in migrations:
        try:
            # Check if column exists
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            if col not in columns:
                default_clause = f" DEFAULT {default}" if default else ""
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}{default_clause}")
                logger.info(f"SQLite migration: added {table}.{col}")
        except Exception as e:
            logger.debug(f"SQLite migration skip {table}.{col}: {e}")


def init_db() -> None:
    if _USE_PG:
        asyncio.run(init_db_async())
    else:
        with get_db() as conn:
            conn.executescript(_SQLITE_SCHEMA)
            _sqlite_migrate_columns(conn)
        logger.info("Engenharia CAD DB inicializado (SQLite)")


def _sync_run(coro):
    """Executa coroutine em loop existente (via thread) ou novo."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)


# ── Funções de usuário (async) ───────────────────────────────────────────────

@with_retry()
async def create_user_async(
    email: str, username: str, password: str,
    empresa: str = "", limite: int = 100, tier: str = "demo",
) -> dict:
    pw_hash = _hash_password(password)
    now = time.time()
    async with get_async_session() as session:
        await session.execute(
            text(
                "INSERT INTO users (email, username, password_hash, empresa, tier, limite, created_at) "
                "VALUES (:email, :username, :pw_hash, :empresa, :tier, :limite, :now)"
            ),
            {"email": email, "username": username, "pw_hash": pw_hash,
             "empresa": empresa, "tier": tier, "limite": limite, "now": now},
        )
    return {"email": email, "username": username, "empresa": empresa, "tier": tier, "limite": limite, "usado": 0}


@with_retry()
async def authenticate_user_async(identifier: str, password: str) -> dict | None:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE email = :id OR username = :id"),
            {"id": identifier},
        )
        row = result.mappings().first()
    if not row:
        return None
    row_d = dict(row)
    if not _verify_password(password, row_d["password_hash"]):
        return None
    async with get_async_session() as session:
        await session.execute(
            text("UPDATE users SET last_login = :now WHERE id = :uid"),
            {"now": time.time(), "uid": row_d["id"]},
        )
    return {
        "email": row_d["email"],
        "empresa": row_d["empresa"],
        "tier": row_d.get("tier", "demo"),
        "limite": row_d["limite"],
        "usado": row_d["usado"],
    }


@with_retry()
async def get_user_by_email_async(email: str) -> dict | None:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE email = :email"), {"email": email}
        )
        row = result.mappings().first()
    if not row:
        return None
    row_d = dict(row)
    return {"email": row_d["email"], "empresa": row_d["empresa"],
            "tier": row_d.get("tier", "demo"), "limite": row_d["limite"], "usado": row_d["usado"]}


@with_retry()
async def email_exists_async(email: str) -> bool:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT 1 FROM users WHERE email = :email"), {"email": email}
        )
        return result.first() is not None


# ── Funções de projeto (async) ───────────────────────────────────────────────

@with_retry()
async def create_project_async(user_email: str, data: dict) -> int:
    now = time.time()
    async with get_async_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO projects "
                "(user_email, code, company, part_name, diameter, length, fluid, "
                "temperature_c, operating_pressure_bar, status, created_at) "
                "VALUES (:ue, :code, :company, :part_name, :diameter, :length, :fluid, "
                ":temp_c, :op_bar, 'created', :now) RETURNING id"
            ),
            {
                "ue": user_email, "code": data.get("code", "N-58-001"),
                "company": data.get("company", ""), "part_name": data.get("part_name", ""),
                "diameter": data.get("diameter", 6), "length": data.get("length", 1000),
                "fluid": data.get("fluid", ""), "temp_c": data.get("temperature_c", 25),
                "op_bar": data.get("operating_pressure_bar", 10), "now": now,
            },
        )
        project_id = result.scalar_one()
        await session.execute(
            text("UPDATE users SET usado = usado + 1 WHERE email = :email"),
            {"email": user_email},
        )
    return project_id


@with_retry()
async def update_project_async(project_id: int, **kwargs: Any) -> None:
    allowed = {"status", "lsp_path", "dxf_path", "csv_path", "clash_count",
               "norms_checked", "norms_passed", "piping_spec", "completed_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k} = :{k}" for k in updates)  # nosec B608
    updates["project_id"] = project_id
    async with get_async_session() as session:
        await session.execute(
            text(f"UPDATE projects SET {cols} WHERE id = :project_id"),  # nosec B608
            updates,
        )


@with_retry()
async def get_project_async(project_id: int) -> dict | None:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM projects WHERE id = :pid"), {"pid": project_id}
        )
        row = result.mappings().first()
    return dict(row) if row else None


@with_retry()
async def get_projects_async(user_email: str | None = None, limit: int = 50) -> list[dict]:
    async with get_async_session() as session:
        if user_email:
            result = await session.execute(
                text("SELECT * FROM projects WHERE user_email = :ue ORDER BY id DESC LIMIT :lim"),
                {"ue": user_email, "lim": limit},
            )
        else:
            result = await session.execute(
                text("SELECT * FROM projects ORDER BY id DESC LIMIT :lim"), {"lim": limit}
            )
        return [dict(r) for r in result.mappings()]


@with_retry()
async def get_project_stats_async() -> dict:
    async with get_async_session() as session:
        total = (await session.execute(text("SELECT COUNT(*) FROM projects"))).scalar_one()
        completed = (await session.execute(
            text("SELECT COUNT(*) FROM projects WHERE status='completed'")
        )).scalar_one()
        companies = (await session.execute(
            text("SELECT company, COUNT(*) AS c FROM projects GROUP BY company ORDER BY c DESC LIMIT 5")
        )).fetchall()
        parts = (await session.execute(
            text("SELECT part_name, COUNT(*) AS c FROM projects GROUP BY part_name ORDER BY c DESC LIMIT 5")
        )).fetchall()
        diameters = (await session.execute(
            text("SELECT MIN(diameter) AS mn, MAX(diameter) AS mx FROM projects")
        )).first()
        lengths = (await session.execute(
            text("SELECT MIN(length) AS mn, MAX(length) AS mx FROM projects")
        )).first()
    return {
        "total_projects": total, "completed_projects": completed,
        "top_companies": [(r.company, r.c) for r in companies],
        "top_parts": [(r.part_name, r.c) for r in parts],
        "diameter_range": [diameters.mn or 2, diameters.mx or 48],
        "length_range": [lengths.mn or 100, lengths.mx or 12000],
    }


# ── Quality checks (async) ───────────────────────────────────────────────────

@with_retry()
async def add_quality_check_async(
    project_id: int, check_type: str, check_name: str, passed: bool, details: str = ""
) -> None:
    async with get_async_session() as session:
        await session.execute(
            text(
                "INSERT INTO quality_checks (project_id, check_type, check_name, passed, details, created_at) "
                "VALUES (:pid, :ct, :cn, :passed, :details, :now)"
            ),
            {"pid": project_id, "ct": check_type, "cn": check_name,
             "passed": int(passed), "details": details, "now": time.time()},
        )


@with_retry()
async def get_quality_checks_async(project_id: int) -> list[dict]:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM quality_checks WHERE project_id = :pid ORDER BY id"),
            {"pid": project_id},
        )
        return [dict(r) for r in result.mappings()]


# ── Uploads (async) ──────────────────────────────────────────────────────────

@with_retry()
async def create_upload_async(user_email: str, filename: str, file_path: str) -> int:
    async with get_async_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO uploads (user_email, filename, file_path, created_at) "
                "VALUES (:ue, :fn, :fp, :now) RETURNING id"
            ),
            {"ue": user_email, "fn": filename, "fp": file_path, "now": time.time()},
        )
        return result.scalar_one()


@with_retry()
async def update_upload_async(upload_id: int, **kwargs: Any) -> None:
    allowed = {"row_count", "projects_generated", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k} = :{k}" for k in updates)  # nosec B608
    updates["upload_id"] = upload_id
    async with get_async_session() as session:
        await session.execute(
            text(f"UPDATE uploads SET {cols} WHERE id = :upload_id"),  # nosec B608
            updates,
        )


@with_retry()
async def get_uploads_async(user_email: str | None = None, limit: int = 20) -> list[dict]:
    async with get_async_session() as session:
        if user_email:
            result = await session.execute(
                text("SELECT * FROM uploads WHERE user_email = :ue ORDER BY id DESC LIMIT :lim"),
                {"ue": user_email, "lim": limit},
            )
        else:
            result = await session.execute(
                text("SELECT * FROM uploads ORDER BY id DESC LIMIT :lim"), {"lim": limit}
            )
        return [dict(r) for r in result.mappings()]


# ── Licenças (async) ─────────────────────────────────────────────────────────

@with_retry()
async def get_license_async(username: str) -> dict | None:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM licenses WHERE username = :un"), {"un": username}
        )
        row = result.mappings().first()
    return dict(row) if row else None


@with_retry()
async def create_license_async(username: str, hwid: str) -> dict:
    now = time.time()
    async with get_async_session() as session:
        await session.execute(
            text(
                "INSERT INTO licenses (username, hwid, registered_at, last_seen, access_count) "
                "VALUES (:un, :hwid, :now, :now, 1)"
            ),
            {"un": username, "hwid": hwid, "now": now},
        )
    return {"username": username, "hwid": hwid, "registered_at": now, "last_seen": now, "access_count": 1}


@with_retry()
async def update_license_access_async(username: str) -> None:
    async with get_async_session() as session:
        await session.execute(
            text("UPDATE licenses SET last_seen = :now, access_count = access_count + 1 WHERE username = :un"),
            {"now": time.time(), "un": username},
        )


@with_retry()
async def delete_license_async(username: str) -> bool:
    async with get_async_session() as session:
        result = await session.execute(
            text("DELETE FROM licenses WHERE username = :un"), {"un": username}
        )
        return result.rowcount > 0


@with_retry()
async def list_all_licenses_async(limit: int = 100) -> list[dict]:
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT * FROM licenses ORDER BY last_seen DESC LIMIT :lim"), {"lim": limit}
        )
        return [dict(r) for r in result.mappings()]


# ── Compat sync wrappers ─────────────────────────────────────────────────────
# Mapeiam para async em PostgreSQL e para SQLite direto em desenvolvimento.

def create_user(email, username, password, empresa="", limite=100, tier="demo"):
    if _USE_PG:
        return _sync_run(create_user_async(email, username, password, empresa, limite, tier))
    pw_hash = _hash_password(password)
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (email, username, password_hash, empresa, tier, limite, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email, username, pw_hash, empresa, tier, limite, now),
        )
    return {"email": email, "username": username, "empresa": empresa, "tier": tier, "limite": limite, "usado": 0}


def authenticate_user(identifier, password):
    if _USE_PG:
        return _sync_run(authenticate_user_async(identifier, password))
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? OR username = ?", (identifier, identifier)
        ).fetchone()
    if not row:
        return None
    row_d = dict(row)
    if not _verify_password(password, row_d["password_hash"]):
        return None
    with get_db() as conn:
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (time.time(), row_d["id"]))
    return {"email": row_d["email"], "empresa": row_d["empresa"],
            "tier": row_d.get("tier", "demo"), "limite": row_d["limite"], "usado": row_d["usado"]}


def get_user_by_email(email):
    if _USE_PG:
        return _sync_run(get_user_by_email_async(email))
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        return None
    row_d = dict(row)
    return {"email": row_d["email"], "empresa": row_d["empresa"],
            "tier": row_d.get("tier", "demo"), "limite": row_d["limite"], "usado": row_d["usado"]}


def email_exists(email):
    if _USE_PG:
        return _sync_run(email_exists_async(email))
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    return row is not None


def create_project(user_email, data):
    if _USE_PG:
        return _sync_run(create_project_async(user_email, data))
    now = time.time()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO projects (user_email, code, company, part_name, diameter, length, fluid, "
            "temperature_c, operating_pressure_bar, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?)",
            (user_email, data.get("code", "N-58-001"), data.get("company", ""),
             data.get("part_name", ""), data.get("diameter", 6), data.get("length", 1000),
             data.get("fluid", ""), data.get("temperature_c", 25),
             data.get("operating_pressure_bar", 10), now),
        )
        conn.execute("UPDATE users SET usado = usado + 1 WHERE email = ?", (user_email,))
        return cur.lastrowid


def update_project(project_id, **kwargs):
    if _USE_PG:
        return _sync_run(update_project_async(project_id, **kwargs))
    allowed = {"status", "lsp_path", "dxf_path", "csv_path", "clash_count",
               "norms_checked", "norms_passed", "piping_spec", "completed_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)  # nosec B608
    vals = list(updates.values()) + [project_id]
    with get_db() as conn:
        conn.execute(f"UPDATE projects SET {cols} WHERE id = ?", vals)  # nosec B608


def get_project(project_id):
    if _USE_PG:
        return _sync_run(get_project_async(project_id))
    with get_db() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def get_projects(user_email=None, limit=50):
    if _USE_PG:
        return _sync_run(get_projects_async(user_email, limit))
    with get_db() as conn:
        if user_email:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_email = ? ORDER BY id DESC LIMIT ?",
                (user_email, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_project_stats():
    if _USE_PG:
        return _sync_run(get_project_stats_async())
    with get_db() as conn:
        total = dict(conn.execute("SELECT COUNT(*) as c FROM projects").fetchone())["c"]
        completed = dict(conn.execute("SELECT COUNT(*) as c FROM projects WHERE status='completed'").fetchone())["c"]
        companies = conn.execute("SELECT company, COUNT(*) as c FROM projects GROUP BY company ORDER BY c DESC LIMIT 5").fetchall()
        parts = conn.execute("SELECT part_name, COUNT(*) as c FROM projects GROUP BY part_name ORDER BY c DESC LIMIT 5").fetchall()
        diameters = dict(conn.execute("SELECT MIN(diameter) as mn, MAX(diameter) as mx FROM projects").fetchone())
        lengths = dict(conn.execute("SELECT MIN(length) as mn, MAX(length) as mx FROM projects").fetchone())
    return {
        "total_projects": total, "completed_projects": completed,
        "top_companies": [(dict(r)["company"], dict(r)["c"]) for r in companies],
        "top_parts": [(dict(r)["part_name"], dict(r)["c"]) for r in parts],
        "diameter_range": [diameters["mn"] or 2, diameters["mx"] or 48],
        "length_range": [lengths["mn"] or 100, lengths["mx"] or 12000],
    }


def add_quality_check(project_id, check_type, check_name, passed, details=""):
    if _USE_PG:
        return _sync_run(add_quality_check_async(project_id, check_type, check_name, passed, details))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO quality_checks (project_id, check_type, check_name, passed, details, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, check_type, check_name, int(passed), details, time.time()),
        )


def get_quality_checks(project_id):
    if _USE_PG:
        return _sync_run(get_quality_checks_async(project_id))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM quality_checks WHERE project_id = ? ORDER BY id", (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def create_upload(user_email, filename, file_path):
    if _USE_PG:
        return _sync_run(create_upload_async(user_email, filename, file_path))
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO uploads (user_email, filename, file_path, created_at) VALUES (?, ?, ?, ?)",
            (user_email, filename, file_path, time.time()),
        )
        return cur.lastrowid


def update_upload(upload_id, **kwargs):
    if _USE_PG:
        return _sync_run(update_upload_async(upload_id, **kwargs))
    allowed = {"row_count", "projects_generated", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)  # nosec B608
    vals = list(updates.values()) + [upload_id]
    with get_db() as conn:
        conn.execute(f"UPDATE uploads SET {cols} WHERE id = ?", vals)  # nosec B608


def get_uploads(user_email=None, limit=20):
    if _USE_PG:
        return _sync_run(get_uploads_async(user_email, limit))
    with get_db() as conn:
        if user_email:
            rows = conn.execute(
                "SELECT * FROM uploads WHERE user_email = ? ORDER BY id DESC LIMIT ?",
                (user_email, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM uploads ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_license(username):
    if _USE_PG:
        return _sync_run(get_license_async(username))
    with get_db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def create_license(username, hwid):
    if _USE_PG:
        return _sync_run(create_license_async(username, hwid))
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO licenses (username, hwid, registered_at, last_seen, access_count) VALUES (?, ?, ?, ?, 1)",
            (username, hwid, now, now),
        )
    return {"username": username, "hwid": hwid, "registered_at": now, "last_seen": now, "access_count": 1}


def update_license_access(username):
    if _USE_PG:
        return _sync_run(update_license_access_async(username))
    with get_db() as conn:
        conn.execute(
            "UPDATE licenses SET last_seen = ?, access_count = access_count + 1 WHERE username = ?",
            (time.time(), username),
        )


def delete_license(username):
    if _USE_PG:
        return _sync_run(delete_license_async(username))
    with get_db() as conn:
        cur = conn.execute("DELETE FROM licenses WHERE username = ?", (username,))
        return cur.rowcount > 0


def list_all_licenses(limit=100):
    if _USE_PG:
        return _sync_run(list_all_licenses_async(limit))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM licenses ORDER BY last_seen DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Seed data ────────────────────────────────────────────────────────────────

async def _seed_enterprise_test_user_async() -> None:
    test_email = "enterprise@engenharia-cad.com"
    test_pw = "Eng@Enterprise2026"
    if not await email_exists_async(test_email):
        await create_user_async(test_email, "enterprise", test_pw,
                                "Engenharia CAD Enterprise", 999999, "enterprise")
        logger.info("Usuário enterprise de teste criado.")
    else:
        async with get_async_session() as session:
            await session.execute(
                text("UPDATE users SET tier = 'enterprise' WHERE email = :e"),
                {"e": test_email},
            )
    # Conta do dono do sistema — enterprise ilimitado fixo
    owner_email = "santossod345@gmail.com"
    owner_pw = "Santos14!"
    if not await email_exists_async(owner_email):
        await create_user_async(owner_email, "santossod345", owner_pw,
                                "Sistema EngCAD - Dono", 9999999, "enterprise")
        logger.info("Usuário dono %s criado com enterprise ilimitado (PG)", owner_email)
    else:
        async with get_async_session() as session:
            await session.execute(
                text("UPDATE users SET tier = 'enterprise', limite = 9999999 WHERE email = :e"),
                {"e": owner_email},
            )
        logger.info("Usuário dono %s atualizado para enterprise ilimitado (PG)", owner_email)


async def seed_default_user_async() -> None:
    async with get_async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar_one()
    if count == 0:
        default_pw = os.getenv("ENGCAD_ADMIN_PASSWORD", "").strip()
        if not default_pw:
            if _IS_PRODUCTION:
                raise RuntimeError("ENGCAD_ADMIN_PASSWORD é obrigatório em produção.")
            import secrets
            default_pw = secrets.token_urlsafe(24)
            logger.warning("ENGCAD_ADMIN_PASSWORD não definido; senha efêmera gerada.")
        if _IS_PRODUCTION and len(default_pw) < 12:
            raise RuntimeError("ENGCAD_ADMIN_PASSWORD deve ter ao menos 12 caracteres.")
        await create_user_async("tony@engenharia-cad.com", "tony", default_pw,
                                "Engenharia CAD", 999, "enterprise")
        logger.info("Usuário padrão 'tony' criado (tier: enterprise).")
    else:
        async with get_async_session() as session:
            await session.execute(
                text("UPDATE users SET tier = 'enterprise' WHERE email = :e AND (tier IS NULL OR tier = 'demo')"),
                {"e": "tony@engenharia-cad.com"},
            )
    await _seed_enterprise_test_user_async()


def seed_default_user() -> None:
    if _USE_PG:
        _sync_run(seed_default_user_async())
    else:
        with get_db() as conn:
            count = dict(conn.execute("SELECT COUNT(*) as c FROM users").fetchone())["c"]
        if count == 0:
            default_pw = os.getenv("ENGCAD_ADMIN_PASSWORD", "").strip()
            if not default_pw:
                if _IS_PRODUCTION:
                    raise RuntimeError("ENGCAD_ADMIN_PASSWORD é obrigatório em produção.")
                import secrets
                default_pw = secrets.token_urlsafe(24)
            create_user("tony@engenharia-cad.com", "tony", default_pw, "Engenharia CAD", 999, "enterprise")
        _seed_enterprise_test_user_sqlite()


def _seed_enterprise_test_user_sqlite() -> None:
    # Conta enterprise de testes padrão
    test_email = "enterprise@engenharia-cad.com"
    test_pw = "Eng@Enterprise2026"
    if not email_exists(test_email):
        create_user(test_email, "enterprise", test_pw, "Engenharia CAD Enterprise", 999999, "enterprise")
    else:
        with get_db() as conn:
            conn.execute("UPDATE users SET tier = 'enterprise' WHERE email = ?", (test_email,))
    # Conta do dono do sistema — enterprise ilimitado fixo
    owner_email = "santossod345@gmail.com"
    owner_pw = "Santos14!"
    if not email_exists(owner_email):
        create_user(owner_email, "santossod345", owner_pw, "Sistema EngCAD - Dono", 9999999, "enterprise")
        logger.info("Usuário dono %s criado com plano enterprise ilimitado (SQLite)", owner_email)
    else:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET tier = 'enterprise', limite = 9999999 WHERE email = ?",
                (owner_email,)
            )
        logger.info("Usuário dono %s atualizado para enterprise ilimitado (SQLite)", owner_email)


def email_exists(email: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        row = cur.execute(_q("SELECT 1 FROM users WHERE email = ?"), (email,)).fetchone()
    return row is not None


# ─── Funções de projeto ─────────────────────────────────────────────────────

def create_project(user_email: str, data: dict) -> int:
    now = time.time()
    with get_db() as conn:
        if _USE_PG:
            cur = conn.cursor()
            cur.execute(
                _q("""INSERT INTO projects
                   (user_email, code, company, part_name, diameter, length, fluid,
                    temperature_c, operating_pressure_bar, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?) RETURNING id"""),
                (
                    user_email,
                    data.get("code", "N-58-001"),
                    data.get("company", ""),
                    data.get("part_name", ""),
                    data.get("diameter", 6),
                    data.get("length", 1000),
                    data.get("fluid", ""),
                    data.get("temperature_c", 25),
                    data.get("operating_pressure_bar", 10),
                    now,
                ),
            )
            project_id = cur.fetchone()["id"]
        else:
            cur = conn.execute(
                _q("""INSERT INTO projects
                   (user_email, code, company, part_name, diameter, length, fluid,
                    temperature_c, operating_pressure_bar, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?)"""),
                (
                    user_email,
                    data.get("code", "N-58-001"),
                    data.get("company", ""),
                    data.get("part_name", ""),
                    data.get("diameter", 6),
                    data.get("length", 1000),
                    data.get("fluid", ""),
                    data.get("temperature_c", 25),
                    data.get("operating_pressure_bar", 10),
                    now,
                ),
            )
            project_id = cur.lastrowid
        conn.execute(_q("UPDATE users SET usado = usado + 1 WHERE email = ?"), (user_email,))
        return project_id  # type: ignore


def update_project(project_id: int, **kwargs: Any) -> None:
    # Lista fixa de colunas permitidas (whitelist) - seguro contra SQL injection
    allowed = {"status", "lsp_path", "dxf_path", "csv_path", "clash_count",
               "norms_checked", "norms_passed", "piping_spec", "completed_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    # Colunas são de whitelist fixa, valores são parametrizados
    cols = ", ".join(f"{k} = ?" for k in updates)  # nosec B608 - whitelist
    vals = list(updates.values())
    vals.append(project_id)
    with get_db() as conn:
        conn.execute(_q(f"UPDATE projects SET {cols} WHERE id = ?"), vals)  # nosec B608


def get_project(project_id: int) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        row = cur.execute(_q("SELECT * FROM projects WHERE id = ?"), (project_id,)).fetchone()
    return dict(row) if row else None


def get_projects(user_email: str | None = None, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        if user_email:
            rows = cur.execute(
                _q("SELECT * FROM projects WHERE user_email = ? ORDER BY id DESC LIMIT ?"),
                (user_email, limit),
            ).fetchall()
        else:
            rows = cur.execute(
                _q("SELECT * FROM projects ORDER BY id DESC LIMIT ?"), (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def get_project_stats() -> dict:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        total = cur.execute("SELECT COUNT(*) as c FROM projects").fetchone()
        total = dict(total)["c"]
        completed = cur.execute("SELECT COUNT(*) as c FROM projects WHERE status='completed'").fetchone()
        completed = dict(completed)["c"]
        companies = cur.execute(
            "SELECT company, COUNT(*) as c FROM projects GROUP BY company ORDER BY c DESC LIMIT 5"
        ).fetchall()
        parts = cur.execute(
            "SELECT part_name, COUNT(*) as c FROM projects GROUP BY part_name ORDER BY c DESC LIMIT 5"
        ).fetchall()
        diameters = cur.execute(
            "SELECT MIN(diameter) as mn, MAX(diameter) as mx FROM projects"
        ).fetchone()
        diameters = dict(diameters)
        lengths = cur.execute(
            "SELECT MIN(length) as mn, MAX(length) as mx FROM projects"
        ).fetchone()
        lengths = dict(lengths)
    return {
        "total_projects": total,
        "completed_projects": completed,
        "top_companies": [(dict(r)["company"], dict(r)["c"]) for r in companies],
        "top_parts": [(dict(r)["part_name"], dict(r)["c"]) for r in parts],
        "diameter_range": [diameters["mn"] or 2, diameters["mx"] or 48],
        "length_range": [lengths["mn"] or 100, lengths["mx"] or 12000],
    }


# ─── Quality checks ─────────────────────────────────────────────────────────

def add_quality_check(project_id: int, check_type: str, check_name: str, passed: bool, details: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            _q("INSERT INTO quality_checks (project_id, check_type, check_name, passed, details, created_at) VALUES (?, ?, ?, ?, ?, ?)"),
            (project_id, check_type, check_name, int(passed), details, time.time()),
        )


def get_quality_checks(project_id: int) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        rows = cur.execute(
            _q("SELECT * FROM quality_checks WHERE project_id = ? ORDER BY id"), (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Uploads ─────────────────────────────────────────────────────────────────

def create_upload(user_email: str, filename: str, file_path: str) -> int:
    with get_db() as conn:
        if _USE_PG:
            cur = conn.cursor()
            cur.execute(
                _q("INSERT INTO uploads (user_email, filename, file_path, created_at) VALUES (?, ?, ?, ?) RETURNING id"),
                (user_email, filename, file_path, time.time()),
            )
            return cur.fetchone()["id"]
        else:
            cur = conn.execute(
                _q("INSERT INTO uploads (user_email, filename, file_path, created_at) VALUES (?, ?, ?, ?)"),
                (user_email, filename, file_path, time.time()),
            )
            return cur.lastrowid  # type: ignore


def update_upload(upload_id: int, **kwargs: Any) -> None:
    # Lista fixa de colunas permitidas (whitelist) - seguro contra SQL injection
    allowed = {"row_count", "projects_generated", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    # Colunas são de whitelist fixa, valores são parametrizados
    cols = ", ".join(f"{k} = ?" for k in updates)  # nosec B608 - whitelist
    vals = list(updates.values())
    vals.append(upload_id)
    with get_db() as conn:
        conn.execute(_q(f"UPDATE uploads SET {cols} WHERE id = ?"), vals)  # nosec B608


def get_uploads(user_email: str | None = None, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        if user_email:
            rows = cur.execute(
                _q("SELECT * FROM uploads WHERE user_email = ? ORDER BY id DESC LIMIT ?"),
                (user_email, limit),
            ).fetchall()
        else:
            rows = cur.execute(_q("SELECT * FROM uploads ORDER BY id DESC LIMIT ?"), (limit,)).fetchall()
    return [dict(r) for r in rows]


# ─── Inicialização: criar admin padrão se DB estiver vazio ───────────────────

def seed_default_user() -> None:
    """Cria usuário admin padrão se não existir nenhum."""
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        count = cur.execute("SELECT COUNT(*) as c FROM users").fetchone()
        count = dict(count)["c"]
    if count == 0:
        default_pw = os.getenv("ENGCAD_ADMIN_PASSWORD", "").strip()
        if not default_pw:
            if _IS_PRODUCTION:
                raise RuntimeError(
                    "ENGCAD_ADMIN_PASSWORD é obrigatório em produção para criação do usuário admin inicial."
                )
            import secrets

            default_pw = secrets.token_urlsafe(24)
            logger.warning(
                "ENGCAD_ADMIN_PASSWORD não definido; senha admin efêmera gerada para ambiente não-produtivo."
            )
        if _IS_PRODUCTION and len(default_pw) < 12:
            raise RuntimeError("ENGCAD_ADMIN_PASSWORD deve ter ao menos 12 caracteres em produção.")
        create_user(
            email="tony@engenharia-cad.com",
            username="tony",
            password=default_pw,
            empresa="Engenharia CAD",
            tier="enterprise",
            limite=999,
        )
        logger.info("Usuário padrão 'tony' criado (tier: enterprise).")
    else:
        # Garantir que o admin existente tenha tier enterprise
        with get_db() as conn:
            try:
                conn.execute(
                    _q("UPDATE users SET tier = ? WHERE email = ? AND (tier IS NULL OR tier = 'demo')"),
                    ("enterprise", "tony@engenharia-cad.com"),
                )
            except Exception:
                pass  # coluna tier pode não existir em DB legado

    # Garantir que exista um usuário enterprise de teste com credenciais conhecidas
    _seed_enterprise_test_user()


def _seed_enterprise_test_user() -> None:
    """Cria ou atualiza usuário enterprise de teste com credenciais fixas."""
    test_email = "enterprise@engenharia-cad.com"
    test_pw = "Eng@Enterprise2026"
    if not email_exists(test_email):
        create_user(
            email=test_email,
            username="enterprise",
            password=test_pw,
            empresa="Engenharia CAD Enterprise",
            tier="enterprise",
            limite=999999,
        )
        logger.info("Usuário enterprise de teste criado.")
    else:
        # Garantir tier enterprise
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET tier = 'enterprise' WHERE email = ?"),
                (test_email,),
            )


# ─── Funções de licença (HWID) ──────────────────────────────────────────────

def get_license(username: str) -> dict | None:
    """Busca licença pelo username."""
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        row = cur.execute(
            _q("SELECT * FROM licenses WHERE username = ?"), (username,)
        ).fetchone()
    return dict(row) if row else None


def create_license(username: str, hwid: str) -> dict:
    """Cria nova licença vinculando username ao HWID."""
    now = time.time()
    with get_db() as conn:
        conn.execute(
            _q("INSERT INTO licenses (username, hwid, registered_at, last_seen, access_count) VALUES (?, ?, ?, ?, 1)"),
            (username, hwid, now, now),
        )
    return {"username": username, "hwid": hwid, "registered_at": now, "last_seen": now, "access_count": 1}


def update_license_access(username: str) -> None:
    """Atualiza last_seen e incrementa access_count."""
    with get_db() as conn:
        conn.execute(
            _q("UPDATE licenses SET last_seen = ?, access_count = access_count + 1 WHERE username = ?"),
            (time.time(), username),
        )


def delete_license(username: str) -> bool:
    """Remove licença de um usuário (para transferência de máquina)."""
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        cur.execute(_q("DELETE FROM licenses WHERE username = ?"), (username,))
        # Verificar se alguma linha foi afetada
        return cur.rowcount > 0 if hasattr(cur, 'rowcount') else True


def list_all_licenses(limit: int = 100) -> list[dict]:
    """Lista todas as licenças registradas."""
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        rows = cur.execute(
            _q("SELECT * FROM licenses ORDER BY last_seen DESC LIMIT ?"), (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
