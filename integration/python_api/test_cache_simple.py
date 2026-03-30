#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_cache_simple():
    try:
        from cache import CacheClient
        cache = CacheClient('redis://localhost:6379/0', 300)
        print("✅ Cache client criado")
        print(f"Redis disponível: {cache.is_available()}")

        # Teste básico
        cache.set("test:key", {"message": "OK"})
        result = cache.get("test:key")
        if result == {"message": "OK"}:
            print("✅ Cache funcionando!")
            return True
        else:
            print("❌ Cache não funcionou")
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cache_simple()
    sys.exit(0 if success else 1)