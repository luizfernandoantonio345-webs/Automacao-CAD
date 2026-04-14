"""
═══════════════════════════════════════════════════════════════════════════════
  CONNECTION POOL MANAGER — Pool de Conexões Async para PostgreSQL/SQLite
  Suporta múltiplos usuários simultâneos sem bloqueio
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("engcad.db.pool")

# ── Engine detection ─────────────────────────────────────────────────────────
_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
_USE_PG = _DATABASE_URL.startswith("postgresql://") or _DATABASE_URL.startswith("postgres://")
_IS_VERCEL = bool(os.getenv("VERCEL"))


@dataclass
class PoolStats:
    """Estatísticas do pool de conexões."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_queries: int = 0
    avg_query_time_ms: float = 0.0
    peak_connections: int = 0
    total_errors: int = 0
    pool_exhausted_count: int = 0
    _query_times: list = field(default_factory=list, repr=False)

    def record_query(self, duration_ms: float) -> None:
        self.total_queries += 1
        self._query_times.append(duration_ms)
        if len(self._query_times) > 1000:
            self._query_times = self._query_times[-500:]
        self.avg_query_time_ms = sum(self._query_times) / len(self._query_times)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "total_queries": self.total_queries,
            "avg_query_time_ms": round(self.avg_query_time_ms, 2),
            "peak_connections": self.peak_connections,
            "total_errors": self.total_errors,
            "pool_exhausted_count": self.pool_exhausted_count,
        }


class AsyncPGPool:
    """Pool assíncrono para PostgreSQL usando asyncpg."""

    def __init__(
        self,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        max_idle_time: float = 300.0,
        command_timeout: float = 30.0,
    ):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.command_timeout = command_timeout
        self._pool = None
        self._stats = PoolStats()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Inicializa o pool de conexões."""
        if self._pool is not None:
            return
        async with self._lock:
            if self._pool is not None:
                return
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    max_inactive_connection_lifetime=self.max_idle_time,
                    command_timeout=self.command_timeout,
                )
                self._stats.total_connections = self.min_size
                self._stats.idle_connections = self.min_size
                logger.info(
                    "PostgreSQL pool inicializado: min=%d max=%d",
                    self.min_size, self.max_size,
                )
            except Exception as e:
                logger.error("Falha ao criar pool PostgreSQL: %s", e)
                raise

    async def close(self) -> None:
        """Fecha o pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool fechado")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator:
        """Adquire uma conexão do pool."""
        if not self._pool:
            await self.initialize()
        start = time.monotonic()
        try:
            async with self._pool.acquire() as conn:
                self._stats.active_connections += 1
                if self._stats.active_connections > self._stats.peak_connections:
                    self._stats.peak_connections = self._stats.active_connections
                try:
                    yield conn
                finally:
                    self._stats.active_connections -= 1
                    elapsed = (time.monotonic() - start) * 1000
                    self._stats.record_query(elapsed)
        except Exception as e:
            self._stats.total_errors += 1
            logger.error("Erro ao adquirir conexão: %s", e)
            raise

    async def execute(self, query: str, *args) -> str:
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    @property
    def stats(self) -> PoolStats:
        if self._pool:
            self._stats.total_connections = self._pool.get_size()
            self._stats.idle_connections = self._pool.get_idle_size()
        return self._stats


class SQLitePool:
    """Pool thread-safe para SQLite com WAL mode e connection reuse."""

    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: list[sqlite3.Connection] = []
        self._in_use: set[int] = set()
        self._lock = threading.Lock()
        self._stats = PoolStats()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
        conn.execute("PRAGMA synchronous=NORMAL")
        self._stats.total_connections += 1
        return conn

    @contextmanager
    def acquire(self):
        """Adquire uma conexão do pool."""
        conn = None
        with self._lock:
            for c in self._pool:
                if id(c) not in self._in_use:
                    conn = c
                    self._in_use.add(id(c))
                    break
            if conn is None:
                if len(self._pool) < self.max_connections:
                    conn = self._create_connection()
                    self._pool.append(conn)
                    self._in_use.add(id(conn))
                else:
                    self._stats.pool_exhausted_count += 1
                    raise RuntimeError(
                        f"Pool de conexões SQLite esgotado (max={self.max_connections})"
                    )
            self._stats.active_connections = len(self._in_use)
            if self._stats.active_connections > self._stats.peak_connections:
                self._stats.peak_connections = self._stats.active_connections

        start = time.monotonic()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            self._stats.record_query(elapsed)
            with self._lock:
                self._in_use.discard(id(conn))
                self._stats.active_connections = len(self._in_use)

    @asynccontextmanager
    async def acquire_async(self):
        """Wrapper async para uso em contextos assíncronos."""
        loop = asyncio.get_event_loop()
        conn = await loop.run_in_executor(None, self._acquire_sync)
        start = time.monotonic()
        try:
            yield conn
            await loop.run_in_executor(None, conn.commit)
        except Exception:
            await loop.run_in_executor(None, conn.rollback)
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            self._stats.record_query(elapsed)
            with self._lock:
                self._in_use.discard(id(conn))
                self._stats.active_connections = len(self._in_use)

    def _acquire_sync(self) -> sqlite3.Connection:
        with self._lock:
            for c in self._pool:
                if id(c) not in self._in_use:
                    self._in_use.add(id(c))
                    return c
            if len(self._pool) < self.max_connections:
                conn = self._create_connection()
                self._pool.append(conn)
                self._in_use.add(id(conn))
                return conn
            self._stats.pool_exhausted_count += 1
            raise RuntimeError("Pool SQLite esgotado")

    def close_all(self) -> None:
        with self._lock:
            for conn in self._pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool.clear()
            self._in_use.clear()
            self._stats.active_connections = 0

    @property
    def stats(self) -> PoolStats:
        return self._stats


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL — Instância única do pool
# ═══════════════════════════════════════════════════════════════════════════════

_pool_instance: Optional[AsyncPGPool | SQLitePool] = None
_pool_lock = threading.Lock()


def get_pool() -> AsyncPGPool | SQLitePool:
    """Retorna a instância singleton do pool de conexões."""
    global _pool_instance
    if _pool_instance is not None:
        return _pool_instance
    with _pool_lock:
        if _pool_instance is not None:
            return _pool_instance
        if _USE_PG:
            pg_min = int(os.getenv("DB_POOL_MIN", "5"))
            pg_max = int(os.getenv("DB_POOL_MAX", "20"))
            _pool_instance = AsyncPGPool(
                dsn=_DATABASE_URL,
                min_size=pg_min,
                max_size=pg_max,
            )
        else:
            if _IS_VERCEL:
                db_path = "/tmp/engcad.db"
            else:
                db_path = str(
                    Path(os.getenv("ENGCAD_DB_PATH", ""))
                    or Path(__file__).resolve().parents[2] / "data" / "engcad.db"
                )
            sqlite_max = int(os.getenv("DB_POOL_MAX", "10"))
            _pool_instance = SQLitePool(db_path=db_path, max_connections=sqlite_max)
        return _pool_instance


def get_pool_stats() -> Dict[str, Any]:
    """Retorna estatísticas do pool para health checks."""
    pool = get_pool()
    return pool.stats.to_dict()
