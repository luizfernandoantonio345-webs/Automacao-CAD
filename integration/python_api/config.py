from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    output_dir: Path
    log_file: Path
    api_host: str
    api_port: int
    auth_secret: str
    token_ttl_seconds: int
    rate_limit_window_seconds: int
    rate_limit_max_requests: int
    max_excel_upload_bytes: int
    max_autocad_retries: int
    database_url: str
    redis_url: str
    cache_ttl_seconds: int
    jobs_redis_url: str
    jobs_max_workers: int
    jobs_queue_timeout: int
    ollama_url: str
    llm_model: str
    max_tokens: int
    allow_demo_login: bool
    simulation_mode: bool


def load_config() -> AppConfig:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir = data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = data_dir / "engenharia_automacao.log"

    auth_secret = os.getenv("ENG_AUTH_SECRET")
    if not auth_secret or auth_secret == "eng-local-secret-change-me":
        raise ValueError("ENG_AUTH_SECRET must be set to a secure value in .env file")

    database_url = os.getenv("DATABASE_URL", f"sqlite:///{data_dir / 'engenharia_automacao.db'}")
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    simulation_mode = os.getenv("SIMULATION_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
    if not simulation_mode and app_env != "production":
        simulation_mode = True

    # ✓ PROBLEMA #5: Validar Ollama disponível
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    _validate_ollama_health(ollama_url, simulation_mode)

    return AppConfig(
        data_dir=data_dir,
        output_dir=output_dir,
        log_file=log_file,
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("API_PORT", "8000")),
        auth_secret=auth_secret,
        token_ttl_seconds=60 * 60,
        rate_limit_window_seconds=60,
        rate_limit_max_requests=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120")),
        max_excel_upload_bytes=int(os.getenv("MAX_EXCEL_UPLOAD_MB", "15")) * 1024 * 1024,
        max_autocad_retries=2,
        database_url=database_url,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
        jobs_redis_url=os.getenv("JOBS_REDIS_URL", "redis://localhost:6379/1"),
        jobs_max_workers=int(os.getenv("JOBS_MAX_WORKERS", "4")),
        jobs_queue_timeout=int(os.getenv("JOBS_QUEUE_TIMEOUT", "30")),
        ollama_url=ollama_url,
        llm_model=os.getenv("LLM_MODEL", "llama3.2:1b"),
        max_tokens=int(os.getenv("MAX_TOKENS", "2048")),
        allow_demo_login=os.getenv("ALLOW_DEMO_LOGIN", "true").strip().lower() in {"1", "true", "yes", "on"},
        simulation_mode=simulation_mode,
    )


def _validate_ollama_health(ollama_url: str, simulation_mode: bool) -> None:
    """✓ PROBLEMA #5: Validar que Ollama está acessível com retry."""
    import time
    import logging
    from urllib.request import urlopen
    from urllib.error import URLError
    
    logger = logging.getLogger("config")
    max_retries = 2

    if simulation_mode:
        logger.info("Modo simulação ativo - health check do Ollama ignorado")
        return
    
    for attempt in range(max_retries):
        try:
            health_url = f"{ollama_url}/api/tags"
            urlopen(health_url, timeout=5)
            logger.info(f"✓ Ollama health check OK: {ollama_url}")
            return
        except URLError as e:
            logger.warning(f"Ollama health check falhou (tentativa {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    
    logger.warning(f"⚠️ Aviso: Ollama em {ollama_url} pode estar indisponível. "
                   "AI CAD não funcionará até que Ollama esteja online.")
    # NÃO levantar erro aqui para não quebrar inicialização se Ollama for iniciado depois
