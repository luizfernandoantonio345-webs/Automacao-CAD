#!/usr/bin/env python3
"""
Health Check para Sistema Engenharia Automação + AI CAD

Verifica disponibilidade de:
- Ollama (LLM backend)
- Redis (cache + jobs)
- Database (PostgreSQL/SQLite)
- Arquivo de log

✓ PROBLEMA #5, #11: Health check completo do sistema
"""
import sys
import logging
from pathlib import Path
import time
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("health_check")


def check_ollama(ollama_url: str = "http://localhost:11434", timeout: int = 5) -> Dict[str, bool]:
    """Verificar conectividade com Ollama."""
    logger.info(f"Verificando Ollama em {ollama_url}...")
    try:
        from urllib.request import urlopen, Request
        from urllib.error import URLError
        
        # Tentar conectar com retry
        for attempt in range(2):
            try:
                req = Request(f"{ollama_url}/api/tags", method="GET")
                with urlopen(req, timeout=timeout) as response:
                    if response.status == 200:
                        logger.info("✓ Ollama OK")
                        return {"ollama": True}
            except URLError as e:
                if attempt < 1:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}, retentando...")
                    time.sleep(1)
                else:
                    logger.error(f"❌ Ollama indisponível: {e}")
                    return {"ollama": False}
    except Exception as e:
        logger.error(f"❌ Erro ao verificar Ollama: {e}")
        return {"ollama": False}
    
    return {"ollama": False}


def check_redis(redis_url: str = "redis://localhost:6379/0") -> Dict[str, bool]:
    """Verificar conectividade com Redis."""
    logger.info(f"Verificando Redis em {redis_url}...")
    try:
        from redis import Redis
        r = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
        r.ping()
        logger.info("✓ Redis OK")
        return {"redis": True}
    except Exception as e:
        logger.warning(f"⚠️ Redis indisponível (não-crítico): {e}")
        return {"redis": False}


def check_database(database_url: str = None) -> Dict[str, bool]:
    """Verificar conectividade com banco de dados."""
    logger.info(f"Verificando Database...")
    try:
        from sqlalchemy import create_engine, text
        
        if not database_url:
            database_url = f"sqlite:///{Path.cwd() / 'data' / 'engenharia_automacao.db'}"
        
        engine = create_engine(database_url, echo=False, connect_args={"timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"✓ Database OK ({database_url[:30]}...)")
        return {"database": True}
    except Exception as e:
        logger.error(f"❌ Database erro: {e}")
        return {"database": False}


def check_log_file(log_file: Path) -> Dict[str, bool]:
    """Verificar se diretório de logs é escrevível."""
    logger.info(f"Verificando log file ({log_file})...")
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        test_msg = f"Test write at {time.time()}"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(test_msg + "\n")
        logger.info("✓ Log file OK")
        return {"log_file": True}
    except Exception as e:
        logger.error(f"❌ Log file erro: {e}")
        return {"log_file": False}


def main():
    """Executar todas verificações."""
    from integration.python_api.config import load_config
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"❌ Erro ao carregar config: {e}")
        return False
    
    results = {}
    
    # Críticos
    results.update(check_ollama(config.ollama_url))
    results.update(check_database(config.database_url))
    
    # Não-críticos
    results.update(check_redis(config.jobs_redis_url))
    results.update(check_log_file(config.log_file))
    
    # Sumário
    logger.info("\n" + "="*50)
    logger.info("HEALTH CHECK SUMMARY:")
    for service, status in results.items():
        status_str = "✓" if status else "❌"
        logger.info(f"  {status_str} {service.upper()}")
    
    all_critical_ok = results.get("ollama", False) and results.get("database", False)
    
    if all_critical_ok:
        logger.info("="*50 + "\n✓ Sistema pronto para iniciar\n")
        return True
    else:
        logger.error("="*50 + "\n❌ Problemas críticos encontrados\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
