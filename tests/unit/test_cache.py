# ═══════════════════════════════════════════════════════════════════════════════
# TESTES - BACKEND CACHE
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes unitários para o sistema de cache LRU/Redis.
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cache_module():
    """Importa módulo de cache dinamicamente."""
    from backend import cache
    return cache


@pytest.fixture
def lru_cache(cache_module):
    """Cria instância de LRUCache para testes."""
    # LRUCache takes max_size and default_ttl directly, not CacheConfig
    return cache_module.LRUCache(max_size=5, default_ttl=1)


@pytest.fixture
def unified_cache(cache_module):
    """Cria instância de Cache unificado."""
    config = cache_module.CacheConfig(max_size=10, default_ttl=2)
    return cache_module.Cache(config)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES LRU CACHE
# ═══════════════════════════════════════════════════════════════════════════════

class TestLRUCache:
    """Testes para LRUCache."""
    
    def test_set_and_get(self, lru_cache):
        """Testa operações básicas de set/get."""
        lru_cache.set("key1", "value1")
        assert lru_cache.get("key1") == "value1"
    
    def test_get_missing_key(self, lru_cache):
        """Testa get de chave inexistente."""
        # LRUCache.get() only takes key, no default parameter
        assert lru_cache.get("nonexistent") is None
    
    def test_delete(self, lru_cache):
        """Testa remoção de chave."""
        lru_cache.set("key1", "value1")
        assert lru_cache.get("key1") == "value1"
        
        lru_cache.delete("key1")
        assert lru_cache.get("key1") is None
    
    def test_clear(self, lru_cache):
        """Testa limpeza completa do cache."""
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        
        lru_cache.clear()
        
        assert lru_cache.get("key1") is None
        assert lru_cache.get("key2") is None
    
    def test_max_size_eviction(self, lru_cache):
        """Testa evicção quando limite é atingido."""
        # Cache tem max_size=5
        for i in range(7):
            lru_cache.set(f"key{i}", f"value{i}")
        
        # Primeiras chaves devem ter sido removidas
        assert lru_cache.get("key0") is None
        assert lru_cache.get("key1") is None
        
        # Últimas chaves devem existir
        assert lru_cache.get("key6") == "value6"
    
    def test_ttl_expiration(self, lru_cache):
        """Testa expiração por TTL."""
        lru_cache.set("expire_me", "value")
        assert lru_cache.get("expire_me") == "value"
        
        # Esperar TTL expirar (1 segundo + margem)
        time.sleep(1.2)
        
        assert lru_cache.get("expire_me") is None
    
    def test_custom_ttl(self, lru_cache):
        """Testa TTL customizado por chave."""
        # TTL muito curto
        lru_cache.set("short", "value", ttl=0.5)
        
        # TTL mais longo
        lru_cache.set("long", "value", ttl=5)
        
        time.sleep(0.7)
        
        assert lru_cache.get("short") is None
        assert lru_cache.get("long") == "value"
    
    def test_stats(self, lru_cache):
        """Testa estatísticas do cache."""
        lru_cache.set("key1", "value1")
        lru_cache.get("key1")  # hit
        lru_cache.get("key1")  # hit
        lru_cache.get("nonexistent")  # miss
        
        # LRUCache doesn't have stats() method, use internal attributes
        assert lru_cache._hits == 2
        assert lru_cache._misses == 1
        assert len(lru_cache._cache) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES CACHE UNIFICADO
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnifiedCache:
    """Testes para Cache unificado."""
    
    def test_set_get(self, unified_cache):
        """Testa operações básicas."""
        unified_cache.set("key", {"data": "value"})
        result = unified_cache.get("key")
        
        assert result == {"data": "value"}
    
    def test_get_or_set(self, unified_cache):
        """Testa get_or_set com factory."""
        # Primeira chamada - executa factory
        result1 = unified_cache.get_or_set("computed", lambda: "expensive_result")
        assert result1 == "expensive_result"
        
        # Segunda chamada - usa cache
        call_count = [0]
        def factory():
            call_count[0] += 1
            return "new_result"
        
        result2 = unified_cache.get_or_set("computed", factory)
        assert result2 == "expensive_result"  # Ainda o valor antigo
        assert call_count[0] == 0  # Factory não foi chamada


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestCachedDecorator:
    """Testes para @cached decorator."""
    
    def test_cached_function(self, cache_module):
        """Testa cache de função."""
        call_count = [0]
        
        @cache_module.cached(ttl=5)
        def expensive_function(x, y):
            call_count[0] += 1
            return x + y
        
        # Primeira chamada
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count[0] == 1
        
        # Segunda chamada com mesmos args - deve usar cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count[0] == 1  # Não incrementou
        
        # Terceira chamada com args diferentes
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count[0] == 2  # Incrementou


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES THREAD SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Testes de concorrência."""
    
    def test_concurrent_access(self, lru_cache):
        """Testa acesso concorrente ao cache."""
        import threading
        
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    lru_cache.set(f"key{i}", f"value{i}")
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for i in range(100):
                    lru_cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Erros de concorrência: {errors}"
