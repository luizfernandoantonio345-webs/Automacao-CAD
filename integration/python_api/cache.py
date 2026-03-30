from __future__ import annotations

import json
import pickle
from typing import Any, Optional

try:
    import redis
except ImportError:
    redis = None


class CacheClient:
    """Cliente Redis para cache com fallback em memória."""

    def __init__(self, redis_url: str, default_ttl: int = 300):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self._memory_cache: dict[str, Any] = {}
        self._memory_ttl: dict[str, float] = {}

        if redis:
            try:
                self._client = redis.from_url(redis_url, decode_responses=True)
                self._client.ping()  # Test connection
            except Exception:
                self._client = None
                print("Redis não disponível, usando cache em memória")

    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        if self._client:
            try:
                data = self._client.get(key)
                return json.loads(data) if data else None
            except Exception:
                pass

        # Fallback para cache em memória
        if key in self._memory_cache:
            if self._is_expired(key):
                del self._memory_cache[key]
                del self._memory_ttl[key]
                return None
            return self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Define valor no cache."""
        ttl = ttl or self.default_ttl
        serialized = json.dumps(value, ensure_ascii=False)

        if self._client:
            try:
                self._client.setex(key, ttl, serialized)
                return
            except Exception:
                pass

        # Fallback para cache em memória
        self._memory_cache[key] = value
        self._memory_ttl[key] = self._current_time() + ttl

    def delete(self, key: str) -> None:
        """Remove chave do cache."""
        if self._client:
            try:
                self._client.delete(key)
            except Exception:
                pass

        # Fallback para cache em memória
        self._memory_cache.pop(key, None)
        self._memory_ttl.pop(key, None)

    def clear_pattern(self, pattern: str) -> None:
        """Remove todas as chaves que correspondem ao padrão."""
        if self._client:
            try:
                batch: list[str] = []
                for key in self._client.scan_iter(match=pattern):
                    batch.append(key)
                    if len(batch) >= 500:
                        self._client.delete(*batch)
                        batch.clear()
                if batch:
                    self._client.delete(*batch)
                return
            except Exception:
                pass

        # Fallback: limpar cache em memória (simplificado)
        keys_to_delete = [k for k in self._memory_cache.keys() if pattern.replace("*", "") in k]
        for key in keys_to_delete:
            del self._memory_cache[key]
            del self._memory_ttl[key]

    def _is_expired(self, key: str) -> bool:
        """Verifica se chave expirou no cache em memória."""
        return self._current_time() > self._memory_ttl.get(key, 0)

    def _current_time(self) -> float:
        """Retorna timestamp atual."""
        import time
        return time.time()

    def is_available(self) -> bool:
        """Verifica se Redis está disponível."""
        return self._client is not None


class CacheDecorator:
    """Decorador para cache de funções."""

    def __init__(self, cache_client: CacheClient, ttl: Optional[int] = None):
        self.cache_client = cache_client
        self.ttl = ttl

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Criar chave baseada no nome da função e argumentos
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Tentar obter do cache
            cached = self.cache_client.get(key)
            if cached is not None:
                return cached

            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            self.cache_client.set(key, result, self.ttl)
            return result

        return wrapper


# Instância global do cache
_cache_instance: Optional[CacheClient] = None


def get_cache_client() -> CacheClient:
    """Obtém instância global do cache."""
    return _cache_instance


def init_cache(redis_url: str, default_ttl: int = 300) -> CacheClient:
    """Inicializa cache global."""
    global _cache_instance
    _cache_instance = CacheClient(redis_url, default_ttl)
    return _cache_instance