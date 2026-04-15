"""
Engenharia CAD — Camada de persistência (SQLite ou PostgreSQL).

SQLite é o padrão para desenvolvimento local.
Se DATABASE_URL apontar para PostgreSQL, usa psycopg2 automaticamente.

IMPORTANTE: Em produção Vercel sem DATABASE_URL, o sistema usa SQLite em memória
temporária. Dados serão perdidos entre deploys. Configure DATABASE_URL para 
PostgreSQL em produção.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger("engcad.db")

# ── Engine selection ─────────────────────────────────────────────────────────
_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
_USE_PG = _DATABASE_URL.startswith("postgresql://") or _DATABASE_URL.startswith("postgres://")
_IS_VERCEL = bool(os.getenv("VERCEL"))
_IS_PRODUCTION = os.getenv("VERCEL_ENV") == "production" or os.getenv("APP_ENV") == "production"
_ALLOW_EPHEMERAL = os.getenv("ALLOW_EPHEMERAL_DB", "").strip().lower() in ("true", "1", "yes")
_EPHEMERAL_MODE = False

if _IS_PRODUCTION and not _USE_PG and not _ALLOW_EPHEMERAL:
    raise RuntimeError(
        "DATABASE_URL é obrigatório em produção e deve apontar para PostgreSQL. "
        "SQLite local/efêmero não é permitido nesse ambiente. "
        "Para demo/MVP, defina ALLOW_EPHEMERAL_DB=true (dados serão perdidos entre deploys)."
    )

if _USE_PG:
    import psycopg2
    import psycopg2.extras
    logger.info("Usando PostgreSQL: %s", _DATABASE_URL.split("@")[-1] if "@" in _DATABASE_URL else "(url)")
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

_LOCAL = threading.local()

# ── Pool de conexões integrado ───────────────────────────────────────────────
try:
    from backend.database.connection_pool import get_pool, SQLitePool
    _POOL_AVAILABLE = True
except ImportError:
    _POOL_AVAILABLE = False


def is_ephemeral() -> bool:
    """Retorna True se o banco é temporário (perderá dados entre deploys)."""
    return _EPHEMERAL_MODE and not _USE_PG


def _get_conn():
    """Uma conexão por thread (SQLite thread-safety / PG pool).
    
    Usa connection pool quando disponível para melhor suporte multi-usuário.
    Falls back para thread-local quando o pool não está disponível.
    """
    # Fallback: usa thread-local (compatibilidade)
    conn = getattr(_LOCAL, "conn", None)
    if conn is not None:
        if _USE_PG:
            try:
                conn.cursor().execute("SELECT 1")
            except Exception:
                conn = None
                _LOCAL.conn = None
        else:
            return conn
    if conn is None:
        if _USE_PG:
            conn = psycopg2.connect(_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            conn.autocommit = False
        else:
            conn = sqlite3.connect(str(_DB_PATH), timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
        _LOCAL.conn = conn
    return conn


def _q(sql: str) -> str:
    """Traduz placeholders: SQLite usa ?, PostgreSQL usa %s."""
    if _USE_PG:
        return sql.replace("?", "%s")
    return sql


class _PgCursorAdapter:
    """Compat layer: faz psycopg2 cursor se comportar como sqlite cursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql: str, params: tuple | list | None = None):
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        # Compatibilidade com padrões do código: cur.execute(...).fetchone()
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class _PgConnAdapter:
    """Compat layer para uso de conn.execute(...) e conn.cursor()."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _PgCursorAdapter(self._conn.cursor())

    def execute(self, sql: str, params: tuple | list | None = None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


@contextmanager
def get_db():
    """Context manager para transações.
    
    Usa pool de conexões quando disponível (multi-user safe),
    fallback para thread-local quando não.
    """
    if _POOL_AVAILABLE and not _USE_PG:
        pool = get_pool()
        if isinstance(pool, SQLitePool):
            with pool.acquire() as conn:
                yield conn
            return
    conn = _get_conn()
    if _USE_PG:
        conn = _PgConnAdapter(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _row_to_dict(row) -> dict | None:
    """Converte row (sqlite3.Row ou RealDictRow) para dict."""
    if row is None:
        return None
    if _USE_PG:
        return dict(row)
    return dict(row)


def _rows_to_list(rows) -> list[dict]:
    """Converte lista de rows para lista de dicts."""
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


def init_db() -> None:
    """Cria tabelas se não existirem."""
    with get_db() as conn:
        if _USE_PG:
            cur = conn.cursor()
            for ddl in _PG_TABLES:
                cur.execute(ddl)
            for alter in _PG_COMPAT_ALTERS:
                cur.execute(alter)
        else:
            conn.executescript(_SQLITE_SCHEMA)
    engine_name = "PostgreSQL" if _USE_PG else "SQLite"
    logger.info("Engenharia CAD DB inicializado (%s)", engine_name)


# ─── Funções de usuário ─────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash seguro com salt (SHA-256 + salt). Em produção usar bcrypt."""
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    import hmac
    parts = stored_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt = bytes.fromhex(parts[0])
    expected = bytes.fromhex(parts[1])
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(h, expected)


def create_user(email: str, username: str, password: str, empresa: str = "", limite: int = 100, tier: str = "demo") -> dict:
    pw_hash = _hash_password(password)
    now = time.time()
    with get_db() as conn:
        conn.execute(
            _q("INSERT INTO users (email, username, password_hash, empresa, tier, limite, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"),
            (email, username, pw_hash, empresa, tier, limite, now),
        )
    return {"email": email, "username": username, "empresa": empresa, "tier": tier, "limite": limite, "usado": 0}


def authenticate_user(identifier: str, password: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        row = cur.execute(
            _q("SELECT * FROM users WHERE email = ? OR username = ?"),
            (identifier, identifier),
        ).fetchone()
    if not row:
        return None
    row_d = dict(row)
    if not _verify_password(password, row_d["password_hash"]):
        return None
    # Atualizar last_login
    with get_db() as conn:
        conn.execute(_q("UPDATE users SET last_login = ? WHERE id = ?"), (time.time(), row_d["id"]))
    return {
        "email": row_d["email"],
        "empresa": row_d["empresa"],
        "tier": row_d.get("tier", "demo"),
        "limite": row_d["limite"],
        "usado": row_d["usado"],
    }


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor() if _USE_PG else conn
        row = cur.execute(_q("SELECT * FROM users WHERE email = ?"), (email,)).fetchone()
    if not row:
        return None
    row_d = dict(row)
    return {"email": row_d["email"], "empresa": row_d["empresa"], "tier": row_d.get("tier", "demo"), "limite": row_d["limite"], "usado": row_d["usado"]}


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
