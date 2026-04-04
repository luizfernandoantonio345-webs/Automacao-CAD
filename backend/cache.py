# ═══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE CACHE - AUTOMAÇÃO CAD
# ═══════════════════════════════════════════════════════════════════════════════
"""
Sistema de cache com suporte a:
- LRU Cache (in-memory, padrão)
- Redis (produção)
- TTL configurável
- Decorators para fácil uso

Uso:
    from backend.cache import cache, cached

    # Decorator simples
    @cached(ttl=300)
    def get_expensive_data(id: str):
        return database.query(id)

    # Manual
    cache.set("key", value, ttl=60)
    value = cache.get("key")
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import logging
import functools
from typing import Any, Optional, Callable, TypeVar, Union
from collections import OrderedDict
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger("engcad.cache")

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheConfig:
    """Configuração do sistema de cache."""
    
    # Backend: 'memory' ou 'redis'
    backend: str = "memory"
    
    # Redis URL (se backend='redis')
    redis_url: str = ""
    
    # Tamanho máximo do cache LRU (in-memory)
    max_size: int = 1000
    
    # TTL padrão em segundos
    default_ttl: int = 300  # 5 minutos
    
    # Prefixo para chaves (útil em ambiente compartilhado)
    key_prefix: str = "engcad:"
    
    # Se deve serializar valores como JSON
    serialize: bool = True


def get_cache_config() -> CacheConfig:
    """Obtém configuração do cache baseada no ambiente."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    
    if redis_url:
        return CacheConfig(
            backend="redis",
            redis_url=redis_url,
            max_size=10000,
            default_ttl=300,
        )
    
    return CacheConfig(
        backend="memory",
        max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
        default_ttl=int(os.getenv("CACHE_TTL", "300")),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE IN-MEMORY (LRU)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheEntry:
    """Entrada no cache com TTL."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)


class LRUCache:
    """
    Cache LRU (Least Recently Used) in-memory com TTL.
    
    Thread-safe para uso em ambiente multi-thread.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            # Verificar TTL
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Mover para o final (mais recente)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Define valor no cache."""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        with self._lock:
            # Se já existe, atualizar
            if key in self._cache:
                self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
                self._cache.move_to_end(key)
                return
            
            # Se cheio, remover mais antigo
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe e não expirou."""
        return self.get(key) is not None
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "backend": "memory",
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
            }
    
    def cleanup_expired(self) -> int:
        """Remove entradas expiradas. Retorna quantidade removida."""
        now = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() 
                if now > v.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        return removed


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE REDIS
# ═══════════════════════════════════════════════════════════════════════════════

class RedisCache:
    """
    Cache usando Redis.
    
    Requer redis-py: pip install redis
    """
    
    def __init__(self, redis_url: str, default_ttl: int = 300, key_prefix: str = "engcad:"):
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client = None
        self._redis_url = redis_url
        self._hits = 0
        self._misses = 0
    
    def _get_client(self):
        """Lazy loading do cliente Redis."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self._redis_url, decode_responses=True)
                self._client.ping()
                logger.info("Redis conectado: %s", self._redis_url.split("@")[-1])
            except Exception as e:
                logger.warning("Redis indisponível (%s), usando fallback", e)
                return None
        return self._client
    
    def _make_key(self, key: str) -> str:
        """Adiciona prefixo à chave."""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do Redis."""
        client = self._get_client()
        if client is None:
            self._misses += 1
            return None
        
        try:
            full_key = self._make_key(key)
            value = client.get(full_key)
            
            if value is None:
                self._misses += 1
                return None
            
            self._hits += 1
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error("Redis GET error: %s", e)
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Define valor no Redis."""
        client = self._get_client()
        if client is None:
            return
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Serializar se não for string
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            client.setex(full_key, ttl, value)
            
        except Exception as e:
            logger.error("Redis SET error: %s", e)
    
    def delete(self, key: str) -> bool:
        """Remove valor do Redis."""
        client = self._get_client()
        if client is None:
            return False
        
        try:
            full_key = self._make_key(key)
            return client.delete(full_key) > 0
        except Exception as e:
            logger.error("Redis DELETE error: %s", e)
            return False
    
    def clear(self) -> None:
        """Limpa todas as chaves com o prefixo."""
        client = self._get_client()
        if client is None:
            return
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
            self._hits = 0
            self._misses = 0
        except Exception as e:
            logger.error("Redis CLEAR error: %s", e)
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe."""
        client = self._get_client()
        if client is None:
            return False
        
        try:
            full_key = self._make_key(key)
            return client.exists(full_key) > 0
        except Exception:
            return False
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        client = self._get_client()
        
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        stats = {
            "backend": "redis",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }
        
        if client:
            try:
                info = client.info("memory")
                stats["used_memory"] = info.get("used_memory_human", "N/A")
                stats["connected"] = True
            except Exception:
                stats["connected"] = False
        
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE UNIFICADO
# ═══════════════════════════════════════════════════════════════════════════════

class Cache:
    """
    Interface unificada de cache.
    
    Automaticamente escolhe entre LRU (memory) e Redis baseado na configuração.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or get_cache_config()
        
        if self.config.backend == "redis" and self.config.redis_url:
            self._backend = RedisCache(
                redis_url=self.config.redis_url,
                default_ttl=self.config.default_ttl,
                key_prefix=self.config.key_prefix,
            )
            logger.info("Cache: usando Redis")
        else:
            self._backend = LRUCache(
                max_size=self.config.max_size,
                default_ttl=self.config.default_ttl,
            )
            logger.info("Cache: usando LRU in-memory (max=%d)", self.config.max_size)
    
    def get(self, key: str) -> Optional[Any]:
        return self._backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        return self._backend.delete(key)
    
    def clear(self) -> None:
        self._backend.clear()
    
    def exists(self, key: str) -> bool:
        return self._backend.exists(key)
    
    def get_stats(self) -> dict:
        return self._backend.get_stats()
    
    def get_or_set(self, key: str, factory: Callable[[], T], ttl: Optional[int] = None) -> T:
        """
        Obtém do cache ou executa factory e armazena.
        
        Uso:
            value = cache.get_or_set("key", lambda: expensive_computation(), ttl=60)
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = factory()
        self.set(key, value, ttl)
        return value


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def make_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Cria chave de cache baseada na função e argumentos."""
    # Nome da função
    func_name = f"{func.__module__}.{func.__qualname__}"
    
    # Serializar argumentos
    key_parts = [func_name]
    
    for arg in args:
        if hasattr(arg, "__dict__"):
            # Objeto complexo - usar repr ou id
            key_parts.append(str(id(arg)))
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # Hash para evitar chaves muito longas
    key_str = ":".join(key_parts)
    if len(key_str) > 200:
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
        key_str = f"{func_name}:{key_hash}"
    
    return key_str


def cached(
    ttl: int = 300,
    key: Optional[str] = None,
    cache_instance: Optional[Cache] = None,
):
    """
    Decorator para cache de funções.
    
    Args:
        ttl: Tempo de vida em segundos
        key: Chave fixa (opcional, senão gera automaticamente)
        cache_instance: Instância de cache (usa global se não fornecido)
    
    Uso:
        @cached(ttl=60)
        def get_user(user_id: int):
            return database.get_user(user_id)
        
        @cached(ttl=300, key="all_users")
        def get_all_users():
            return database.get_all_users()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Usar cache global se não fornecido
            _cache = cache_instance or cache
            
            # Gerar ou usar chave fixa
            cache_key = key or make_cache_key(func, args, kwargs)
            
            # Tentar obter do cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Executar função
            result = func(*args, **kwargs)
            
            # Armazenar no cache
            _cache.set(cache_key, result, ttl)
            
            return result
        
        # Adicionar método para invalidar cache
        def invalidate(*args, **kwargs):
            _cache = cache_instance or cache
            cache_key = key or make_cache_key(func, args, kwargs)
            _cache.delete(cache_key)
        
        wrapper.invalidate = invalidate
        wrapper.cache_key = lambda *a, **kw: key or make_cache_key(func, a, kw)
        
        return wrapper
    
    return decorator


def cached_property(ttl: int = 300):
    """
    Decorator para cache de properties.
    
    Uso:
        class MyClass:
            @cached_property(ttl=60)
            def expensive_property(self):
                return compute_expensive()
    """
    def decorator(func: Callable[[Any], T]) -> property:
        cache_attr = f"_cached_{func.__name__}"
        expires_attr = f"_expires_{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(self) -> T:
            now = time.time()
            
            # Verificar cache
            if hasattr(self, cache_attr) and hasattr(self, expires_attr):
                if now < getattr(self, expires_attr):
                    return getattr(self, cache_attr)
            
            # Calcular e cachear
            value = func(self)
            setattr(self, cache_attr, value)
            setattr(self, expires_attr, now + ttl)
            
            return value
        
        return property(wrapper)
    
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

# Cache global (singleton)
cache = Cache()


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS DE API PARA CACHE
# ═══════════════════════════════════════════════════════════════════════════════

def register_cache_routes(app):
    """Registra rotas de administração do cache."""
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/api/cache", tags=["cache"])
    
    @router.get("/stats")
    async def get_cache_stats():
        """Retorna estatísticas do cache."""
        return cache.get_stats()
    
    @router.post("/clear")
    async def clear_cache():
        """Limpa todo o cache."""
        cache.clear()
        return {"success": True, "message": "Cache limpo"}
    
    @router.delete("/{key}")
    async def delete_cache_key(key: str):
        """Remove uma chave específica do cache."""
        deleted = cache.delete(key)
        return {"success": deleted, "key": key}
    
    app.include_router(router)


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLOS DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Teste básico
    cache.set("test_key", {"data": "value"}, ttl=60)
    print("Set:", cache.get("test_key"))
    print("Stats:", cache.get_stats())
    
    # Teste com decorator
    @cached(ttl=10)
    def expensive_function(x: int) -> int:
        print(f"Computing {x}...")
        return x * 2
    
    print("Primeira chamada:", expensive_function(5))
    print("Segunda chamada (cached):", expensive_function(5))
    print("Stats após decorator:", cache.get_stats())
