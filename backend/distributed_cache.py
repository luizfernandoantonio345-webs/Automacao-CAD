"""
═══════════════════════════════════════════════════════════════════════════════
  DISTRIBUTED CACHE — Cache em camadas com Redis + In-Memory
  L1: In-memory (processo) → ultra-rápido
  L2: Redis (compartilhado) → multi-instância
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("engcad.cache")


@dataclass
class CacheEntry:
    """Entrada de cache com TTL."""
    key: str
    value: Any
    created_at: float
    ttl: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class L1Cache:
    """Cache em memória do processo (ultra-rápido, por instância)."""

    def __init__(self, max_size: int = 5000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}

    def get(self, key: str) -> Tuple[bool, Any]:
        """Retorna (hit, value)."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return False, None
            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return False, None
            entry.hits += 1
            self._stats["hits"] += 1
            self._cache.move_to_end(key)
            return True, entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Define um valor no cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
            self._cache[key] = CacheEntry(
                key=key, value=value,
                created_at=time.time(),
                ttl=ttl or self.default_ttl,
            )
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup(self) -> int:
        """Remove entradas expiradas."""
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired:
                del self._cache[k]
            return len(expired)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self._stats,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate_percent": round(hit_rate, 1),
        }


class L2RedisCache:
    """Cache Redis compartilhado entre instâncias."""

    def __init__(self, prefix: str = "engcad:", default_ttl: int = 600):
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._redis = None
        self._available = False
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
        self._connect()

    def _connect(self) -> None:
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return
        try:
            import redis
            self._redis = redis.Redis.from_url(
                redis_url, decode_responses=True,
                socket_timeout=2, socket_connect_timeout=2,
            )
            self._redis.ping()
            self._available = True
            logger.info("L2 Redis cache conectado")
        except Exception as e:
            self._redis = None
            self._available = False
            logger.info("L2 Redis cache indisponível: %s", e)

    def get(self, key: str) -> Tuple[bool, Any]:
        if not self._available:
            return False, None
        try:
            val = self._redis.get(f"{self.prefix}{key}")
            if val is None:
                self._stats["misses"] += 1
                return False, None
            self._stats["hits"] += 1
            return True, json.loads(val)
        except Exception:
            self._stats["errors"] += 1
            return False, None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self._available:
            return False
        try:
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            self._redis.setex(
                f"{self.prefix}{key}",
                ttl or self.default_ttl,
                serialized,
            )
            self._stats["sets"] += 1
            return True
        except Exception:
            self._stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        if not self._available:
            return False
        try:
            return bool(self._redis.delete(f"{self.prefix}{key}"))
        except Exception:
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalida todas as chaves que match o pattern."""
        if not self._available:
            return 0
        try:
            keys = self._redis.keys(f"{self.prefix}{pattern}")
            if keys:
                return self._redis.delete(*keys)
            return 0
        except Exception:
            return 0

    @property
    def available(self) -> bool:
        return self._available

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self._stats,
            "available": self._available,
            "hit_rate_percent": round(hit_rate, 1),
        }


class DistributedCache:
    """Cache hierárquico: L1 (memória) → L2 (Redis)."""

    def __init__(
        self,
        l1_max_size: int = 5000,
        l1_ttl: float = 300.0,
        l2_ttl: int = 600,
    ):
        self.l1 = L1Cache(max_size=l1_max_size, default_ttl=l1_ttl)
        self.l2 = L2RedisCache(default_ttl=l2_ttl)

    def get(self, key: str) -> Tuple[bool, Any]:
        """Busca L1 primeiro, depois L2."""
        hit, val = self.l1.get(key)
        if hit:
            return True, val
        hit, val = self.l2.get(key)
        if hit:
            self.l1.set(key, val)
            return True, val
        return False, None

    def set(self, key: str, value: Any, l1_ttl: Optional[float] = None, l2_ttl: Optional[int] = None) -> None:
        """Escreve em ambas as camadas."""
        self.l1.set(key, value, ttl=l1_ttl)
        self.l2.set(key, value, ttl=l2_ttl)

    def delete(self, key: str) -> None:
        self.l1.delete(key)
        self.l2.delete(key)

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalida por padrão (apenas L2 suporta glob)."""
        self.l2.invalidate_pattern(pattern)

    def clear_l1(self) -> None:
        self.l1.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "l1": self.l1.stats,
            "l2": self.l2.stats,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR PARA CACHE AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════════════════════

def cached(
    ttl: float = 300.0,
    key_prefix: str = "",
    cache_instance: Optional[DistributedCache] = None,
):
    """Decorator que cacheia resultado de funções."""
    def decorator(func: Callable):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = cache_instance or get_cache()
            key = _build_key(key_prefix or func.__name__, args, kwargs)
            hit, val = cache.get(key)
            if hit:
                return val
            result = await func(*args, **kwargs)
            cache.set(key, result, l1_ttl=ttl)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = cache_instance or get_cache()
            key = _build_key(key_prefix or func.__name__, args, kwargs)
            hit, val = cache.get(key)
            if hit:
                return val
            result = func(*args, **kwargs)
            cache.set(key, result, l1_ttl=ttl)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def _build_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """Constrói chave de cache a partir dos argumentos."""
    parts = [prefix]
    for a in args:
        parts.append(str(a))
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")
    raw = "|".join(parts)
    if len(raw) > 200:
        # SHA-256 para chaves longas (evita conflitos, não é uso de segurança)
        return prefix + ":" + hashlib.sha256(raw.encode()).hexdigest()[:32]
    return raw


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_cache: Optional[DistributedCache] = None


def get_cache() -> DistributedCache:
    """Retorna instância singleton do cache distribuído."""
    global _cache
    if _cache is None:
        l1_size = int(os.getenv("CACHE_L1_SIZE", "5000"))
        l1_ttl = float(os.getenv("CACHE_L1_TTL", "300"))
        l2_ttl = int(os.getenv("CACHE_L2_TTL", "600"))
        _cache = DistributedCache(l1_max_size=l1_size, l1_ttl=l1_ttl, l2_ttl=l2_ttl)
    return _cache
