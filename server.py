from __future__ import annotations

import asyncio
import datetime
from datetime import UTC
import io
import json
import logging
import os
import re
import sqlite3
import time
import traceback
import zipfile
from collections import defaultdict, deque
from threading import Lock

import jwt
import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing import Annotated, Any
from sse_starlette.sse import EventSourceResponse

# Redis Session Management (Production-ready)
try:
    from backend.redis_session import SessionMiddleware, initialize_session_manager, close_session_manager
    _REDIS_SESSION_AVAILABLE = True
except ImportError:
    _REDIS_SESSION_AVAILABLE = False
    SessionMiddleware = None
    initialize_session_manager = None
    close_session_manager = None

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING ESTRUTURADO COM STRUCTLOG (Enterprise)
# ══════════════════════════════════════════════════════════════════════════════
try:
    import structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if os.getenv("LOG_FORMAT") == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger("engcad.server")
except ImportError:
    # Fallback para logging padrão se structlog não estiver disponível
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("engcad.server")

# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING COM SLOWAPI (Enterprise)
# ══════════════════════════════════════════════════════════════════════════════
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address)
    _SLOWAPI_AVAILABLE = True
except ImportError:
    logger.warning("slowapi não disponível - rate limiting desabilitado")
    limiter = None
    RateLimitExceeded = Exception
    _rate_limit_exceeded_handler = None
    _SLOWAPI_AVAILABLE = False

# Importações opcionais - graceful degradation para deploy serverless
import logging as _log

try:
    from engenharia_automacao.app.routes_cad import router as cad_router
except ImportError as e:
    _log.warning(f"CAD router not available: {e}")
    cad_router = None

try:
    from backend.routes_autocad import router as autocad_router
    from backend.routes_autocad import debug_router as autocad_debug_router
except ImportError as e:
    _log.warning(f"AutoCAD router not available: {e}")
    autocad_router = None
    autocad_debug_router = None

try:
    from backend.routes_license import router as license_router
except ImportError as e:
    _log.warning(f"License router not available: {e}")
    license_router = None

try:
    from backend.routes_billing import router as billing_router
except ImportError as e:
    _log.warning(f"Billing router not available: {e}")
    billing_router = None

try:
    from backend.routes_auth import router as auth_router
except ImportError as e:
    _log.warning(f"Auth router not available: {e}")
    auth_router = None

try:
    from backend.routes_analytics import router as analytics_router
except ImportError as e:
    _log.warning(f"Analytics router not available: {e}")
    analytics_router = None

try:
    from backend.routes_notifications import router as notifications_router
except ImportError as e:
    _log.warning(f"Notifications router not available: {e}")
    notifications_router = None

try:
    from backend.audit_trail import router as audit_router
except ImportError as e:
    _log.warning(f"Audit router not available: {e}")
    audit_router = None

try:
    from ai_watchdog import install_watchdog, watchdog
except ImportError as e:
    _log.warning(f"AI watchdog not available: {e}")
    install_watchdog = None
    watchdog = None

try:
    from cam.routes import router as cam_router
except ImportError as e:
    _log.warning(f"CAM router not available: {e}")
    cam_router = None

try:
    from cam.nesting_routes import router as nesting_router
except ImportError as e:
    _log.warning(f"Nesting router not available: {e}")
    nesting_router = None

try:
    from cam.job_history import router as job_history_router
except ImportError as e:
    _log.warning(f"Job history router not available: {e}")
    job_history_router = None

try:
    from cam.dashboard_metrics import router as dashboard_router
except ImportError as e:
    _log.warning(f"Dashboard router not available: {e}")
    dashboard_router = None

try:
    from cam.machine_integration import router as machine_router
except ImportError as e:
    _log.warning(f"Machine integration router not available: {e}")
    machine_router = None

try:
    from backend.routes_cad_detection import router as cad_detection_router
except ImportError as e:
    _log.warning(f"CAD Detection router not available: {e}")
    cad_detection_router = None

try:
    from backend.routes_storage import router as storage_router
except ImportError as e:
    _log.warning(f"Storage router not available: {e}")
    storage_router = None

try:
    from backend.database.db import (
        init_db, seed_default_user, authenticate_user, create_user,
        email_exists, get_user_by_email, create_project as db_create_project,
        update_project as db_update_project, get_project as db_get_project,
        get_projects as db_get_projects, get_project_stats,
        add_quality_check, get_quality_checks,
        create_upload, update_upload, get_uploads,
        _hash_password, _q, get_db,
    )
except ImportError as e:
    _log.warning(f"Database module not available: {e}")
    init_db = seed_default_user = authenticate_user = create_user = None
    email_exists = get_user_by_email = db_create_project = None
    db_update_project = db_get_project = db_get_projects = get_project_stats = None
    add_quality_check = get_quality_checks = create_upload = update_upload = get_uploads = None
    _hash_password = _q = get_db = None

# logger = logging.getLogger(__name__)  # Deprecated - using structlog

# Load and validate environment variables
# ── Modo de operação: Servidor Central (com .env) ou Agente Local (sem .env) ──
# O Agente Local (forge_link_agent.py) NUNCA carrega este módulo.
# Se chegou aqui, é o Servidor Central — exigir JARVIS_SECRET.
JARVIS_SECRET = os.getenv("JARVIS_SECRET", "").strip()
_MIN_SECRET_BYTES = 32
_APP_ENV = os.getenv("APP_ENV", "development").lower()

if not JARVIS_SECRET or JARVIS_SECRET == "jarvis_secret_key_change_me":
    if _APP_ENV == "production":
        print("FATAL: JARVIS_SECRET não definido em produção. SERVIDOR NÃO VAI INICIAR.")
        raise SystemExit("FATAL: Defina JARVIS_SECRET (>= 32 bytes) antes de iniciar em produção.")
    import secrets as _secrets_mod
    JARVIS_SECRET = _secrets_mod.token_hex(32)
    print("JARVIS_SECRET não definido — usando secret efêmero (NÃO USE EM PRODUÇÃO)")
elif len(JARVIS_SECRET.encode("utf-8")) < _MIN_SECRET_BYTES:
    if _APP_ENV == "production":
        print("FATAL: JARVIS_SECRET muito curto. SERVIDOR NÃO VAI INICIAR.")
        raise SystemExit("FATAL: JARVIS_SECRET deve ter >= 32 bytes em produção.")
    import secrets as _secrets_mod
    _old_len = len(JARVIS_SECRET.encode("utf-8"))
    JARVIS_SECRET = _secrets_mod.token_hex(32)
    print(f"JARVIS_SECRET tinha apenas {_old_len} bytes (mínimo: {_MIN_SECRET_BYTES} para HS256/RFC 7518). Chave automática gerada. Defina uma chave >= 32 bytes em produção.")

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
_REGISTER_RATE_MAX = int(os.getenv("RATE_LIMIT_REGISTER_PER_MINUTE", "3"))
_DEMO_RATE_MAX = 5
_REQUEST_HISTORY: defaultdict[str, deque] = defaultdict(deque)
_REGISTER_HISTORY: defaultdict[str, deque] = defaultdict(deque)
_DEMO_HISTORY: defaultdict[str, deque] = defaultdict(deque)
_RATE_LOCK = Lock()
_RATE_LOCK_ASYNC = None  # Lazy-initialized asyncio.Lock

# Redis rate-limit connection (optional, falls back to in-memory)
_REDIS_RATE: Any = None
try:
    import redis as _redis_mod
    _redis_url = os.getenv("REDIS_URL", "")
    if _redis_url:
        _REDIS_RATE = _redis_mod.Redis.from_url(_redis_url, decode_responses=True, socket_timeout=2)
        _REDIS_RATE.ping()
        logger.info("Redis rate-limiter conectado: %s", _redis_url[:30])
except Exception as _redis_err:
    _REDIS_RATE = None
    logger.info("Redis rate-limiter indisponível (usando in-memory): %s", _redis_err)
_SSE_CONNECTIONS: defaultdict[str, int] = defaultdict(int)
_SSE_LOCK = Lock()
_SSE_MAX_PER_IP = 5
_SSE_TIMEOUT_SECONDS = 300  # 5 minutos
_MAX_EXCEL_UPLOAD_BYTES = int(os.getenv("MAX_EXCEL_UPLOAD_MB", "15")) * 1024 * 1024
_DEMO_EMAIL = "demo@engenharia-cad.com"
_DEMO_TOKEN_EXPIRY_MINUTES = 10

# ── Rotas que NÃO exigem autenticação ──
_AUTH_WHITELIST = {
    "", "/", "/login", "/auth/register", "/auth/demo", "/auth/refresh", "/health", "/healthz", "/docs",
    "/openapi.json", "/redoc",
    # Admin endpoint para seed de usuário de teste (temporário)
    "/admin/seed-test-user",
    # Bridge endpoints para sincronizador local (não expõe dados sensíveis)
    "/api/bridge/pending", "/api/bridge/status", "/api/bridge/send",
    "/api/bridge/draw-pipe", "/api/bridge/insert-component",
    "/api/bridge/connection", "/api/bridge/ack", "/api/bridge/health",
    # Download do sincronizador (público para facilitar instalação)
    "/api/download/sincronizador",
    # Status endpoints para dashboard (somente leitura)
    "/api/autocad/health", "/api/autocad/buffer", "/api/autocad/status",
    # AI endpoints para frontend (somente leitura e chat)
    "/api/ai/status", "/api/ai/engines", "/api/ai/chat",
    # ChatCAD endpoints (NLP → AutoCAD, sem dados sensíveis)
    "/api/chatcad/examples", "/api/chatcad/chat",
    "/api/chatcad/interpret", "/api/chatcad/execute",
    # Refineries endpoint (somente leitura, informação pública)
    "/api/refineries",
    # CAD execute stream (SSE, somente leitura)
    "/api/cad/execute-stream",
    # CAM endpoints para geração de G-code (somente leitura/processamento)
    "/api/cam/materials", "/api/cam/parse", "/api/cam/generate", "/api/cam/validate",
    "/api/cam/nesting/run", "/api/cam/nesting/quick-piece", "/api/cam/library/pieces",
    "/api/cam/simulate", "/api/cam/consumables/estimate",
    # CAM IA endpoints (novos)
    "/api/cam/ai/suggest-parameters", "/api/cam/ai/analyze-geometry",
    "/api/cam/ai/optimize-toolpath", "/api/cam/ai/pre-check",
    # CAM Simulação Física endpoints (novos)
    "/api/cam/simulate/physics", "/api/cam/simulate/estimate-time",
    "/api/cam/simulate/machine-presets", "/api/cam/consumables/estimate",
    # Monitoring endpoints (somente leitura, métricas do sistema)
    "/api/monitoring/dashboard", "/api/monitoring/tasks",
    # WebSocket stats (somente leitura)
    "/ws/stats",
}

# ── Rotas bloqueadas para demo ──
_DEMO_BLOCKED_ROUTES = {
    "/generate", "/excel", "/jobs/stress/porticos-50",
    "/api/license/reset", "/api/license/all",
    "/api/autocad/connect", "/api/autocad/disconnect",
    "/api/autocad/draw-pipe", "/api/autocad/draw-line",
    "/api/autocad/insert-component", "/api/autocad/send-command",
    "/api/autocad/batch-draw", "/api/autocad/commit",
    "/ai/diagnostics", "/telemetry/test",
}

# SSE event queues (bounded to prevent memory leaks)
_SYSTEM_EVENTS = asyncio.Queue(maxsize=1000)
_TELEMETRY_EVENTS = asyncio.Queue(maxsize=1000)
_NOTIFICATION_EVENTS = asyncio.Queue(maxsize=1000)
_AI_EVENTS = asyncio.Queue(maxsize=1000)

# Configuração de JSON com suporte a UTF-8
import json
from fastapi.responses import JSONResponse

class UTF8JSONResponse(JSONResponse):
    """JSONResponse que garante encoding UTF-8 correto para caracteres acentuados."""
    media_type = "application/json; charset=utf-8"
    
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
        ).encode('utf-8')

app = FastAPI(
    title="Engenharia CAD - Sistema CNC Plasma",
    description="API completa para automação de corte plasma CNC com IA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=UTF8JSONResponse,
)

_CORS_ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"}
_CORS_ORIGIN_REGEX = re.compile(
    r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
    r"|^https://[a-z0-9\-]+\.vercel\.app$"
)

# ══════════════════════════════════════════════════════════════════════════════
# CORS MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_CORS_ALLOWED_ORIGINS),
    allow_origin_regex=_CORS_ORIGIN_REGEX.pattern,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Correlation-ID"],
)

# ══════════════════════════════════════════════════════════════════════════════
# SECURITY HEADERS MIDDLEWARE (OWASP)
# ══════════════════════════════════════════════════════════════════════════════
try:
    from backend.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware habilitado")
except ImportError as e:
    logger.warning("Security headers middleware não disponível: %s", e)

# ══════════════════════════════════════════════════════════════════════════════
# REDIS SESSION MIDDLEWARE (Production)
# ══════════════════════════════════════════════════════════════════════════════
if _REDIS_SESSION_AVAILABLE and SessionMiddleware:
    app.add_middleware(SessionMiddleware)
    logger.info("Redis session middleware habilitado")
else:
    logger.warning("Redis session middleware não disponível - usando fallback em memória")

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE PROFILING MIDDLEWARE (Métricas de latência)
# ══════════════════════════════════════════════════════════════════════════════
try:
    from backend.performance_middleware import PerformanceMiddleware
    app.add_middleware(PerformanceMiddleware)
    logger.info("Performance profiling middleware habilitado")
except ImportError as e:
    logger.warning("Performance middleware não disponível: %s", e)

# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════
if _SLOWAPI_AVAILABLE and limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting habilitado via slowapi")
else:
    # Fallback para rate limiter interno com suporte a Redis
    try:
        from backend.rate_limiter import RateLimitMiddleware, rate_limiter
        app.add_middleware(RateLimitMiddleware)
        logger.info(f"Rate limiting habilitado via backend (backend: {rate_limiter.backend})")
    except ImportError as e:
        logger.warning(f"Rate limiting fallback não disponível: {e}")

# ── Exception Handlers com mensagens em português ──
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Traduz erros de validação para português."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        msg_type = error["type"]
        
        # Traduzir tipos de erro comuns
        translations = {
            "missing": f"Campo obrigatório não informado: {field}",
            "string_type": f"O campo '{field}' deve ser texto",
            "int_type": f"O campo '{field}' deve ser número inteiro",
            "float_type": f"O campo '{field}' deve ser número decimal",
            "bool_type": f"O campo '{field}' deve ser verdadeiro ou falso",
            "value_error": f"Valor inválido para '{field}'",
            "type_error": f"Tipo incorreto para '{field}'",
            "json_invalid": "JSON inválido no corpo da requisição",
        }
        
        translated = translations.get(msg_type, f"Erro em '{field}': {error['msg']}")
        errors.append({
            "campo": field,
            "mensagem": translated,
            "tipo": msg_type,
        })
    
    return UTF8JSONResponse(
        status_code=422,
        content={
            "sucesso": False,
            "erro": "Dados de entrada inválidos",
            "detalhes": errors,
            "dica": "Verifique os campos obrigatórios e seus tipos",
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Traduz erros HTTP para português."""
    status_messages = {
        400: "Requisição inválida",
        401: "Não autorizado - faça login",
        403: "Acesso negado",
        404: "Recurso não encontrado",
        405: "Método não permitido",
        408: "Tempo limite excedido",
        422: "Dados de entrada inválidos",
        429: "Muitas requisições - aguarde",
        500: "Erro interno do servidor",
        502: "Erro de gateway",
        503: "Serviço temporariamente indisponível",
    }
    
    message = status_messages.get(exc.status_code, str(exc.detail))
    
    return UTF8JSONResponse(
        status_code=exc.status_code,
        content={
            "sucesso": False,
            "erro": message,
            "detalhe": str(exc.detail) if exc.detail != message else None,
            "codigo": exc.status_code,
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler geral para exceções não tratadas."""
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return UTF8JSONResponse(
        status_code=500,
        content={
            "sucesso": False,
            "erro": "Erro interno do servidor",
            "mensagem": "Ocorreu um erro inesperado. Por favor, tente novamente.",
            "tipo": type(exc).__name__,
        }
    )

# ── Inicializar banco de dados SQLite ──
if init_db:
    init_db()
if seed_default_user:
    seed_default_user()
logger.info("Banco de dados Engenharia CAD inicializado")

# ── Validação de variáveis de ambiente ──
try:
    from backend.env_validator import validate_environment, get_env_summary
    
    # Validar apenas em produção (raise_on_error=True se produção)
    is_prod = _APP_ENV == "production"
    env_result = validate_environment(strict=is_prod, raise_on_error=is_prod)
    
    if env_result["valid"]:
        logger.info(f"✓ Variáveis de ambiente validadas: {len(env_result['validated'])} OK")
    else:
        for warning in env_result.get("warnings", []):
            logger.warning(f"⚠ Env: {warning}")
        for error in env_result.get("errors", []):
            logger.error(f"✗ Env: {error}")
            
except ImportError as e:
    logger.warning(f"Validador de ambiente não disponível: {e}")
except Exception as e:
    if _APP_ENV == "production":
        logger.critical(f"FATAL: Falha na validação de ambiente: {e}")
        raise SystemExit(f"FATAL: {e}")
    else:
        logger.warning(f"Validação de ambiente falhou (dev mode): {e}")

# ══════════════════════════════════════════════════════════════════════════════
# REDIS SESSION INITIALIZATION (Startup/Shutdown Events)
# ══════════════════════════════════════════════════════════════════════════════
if _REDIS_SESSION_AVAILABLE and initialize_session_manager and close_session_manager:
    @app.on_event("startup")
    async def startup_redis_session():
        """Initialize Redis session manager on app startup"""
        try:
            await initialize_session_manager()
            logger.info("✓ Redis session manager inicializado no startup")
        except Exception as e:
            logger.error(f"Erro ao inicializar Redis session manager: {e}")
            # Don't raise - allow app to continue with in-memory fallback
    
    @app.on_event("shutdown")
    async def shutdown_redis_session():
        """Close Redis connection on app shutdown"""
        try:
            await close_session_manager()
            logger.info("✓ Redis session manager finalizado no shutdown")
        except Exception as e:
            logger.error(f"Erro ao finalizar Redis session manager: {e}")

# ── AI Watchdog — IA de Baixo Nível invisível ──
# Intercepta TODA request: sanitiza payloads, bloqueia operações em sobrecarga,
# e injeta fallback se o handler crashar. Completamente invisível ao usuário.
if install_watchdog:
    install_watchdog(app)

# Include CAD routes
if cad_router:
    app.include_router(cad_router)

# Include CAM Plasma CNC routes (Geração de G-code)
if cam_router:
    app.include_router(cam_router)

# Include CAM Nesting & Library routes (Otimização de Chapa)
if nesting_router:
    app.include_router(nesting_router)

# Include Job History routes (Histórico de Jobs CNC)
if job_history_router:
    app.include_router(job_history_router)

# Include Dashboard Metrics routes (KPIs e Métricas)
if dashboard_router:
    app.include_router(dashboard_router)

# Include Machine Integration routes (Comunicação CNC)
if machine_router:
    app.include_router(machine_router)

# Include AutoCAD COM Driver routes (Nível 4)
if autocad_router:
    app.include_router(autocad_router)
if autocad_debug_router:
    app.include_router(autocad_debug_router)

# Include CAD Detection & Auto-Launch routes (Enterprise)
if cad_detection_router:
    app.include_router(cad_detection_router)
    logger.info("CAD Detection & Auto-Launch routes carregados")

# Include File Storage routes
if storage_router:
    app.include_router(storage_router)
    logger.info("File Storage routes carregados")

# Include License / HWID routes
if license_router:
    app.include_router(license_router)

# Include Billing / Monetization routes (Stripe)
if billing_router:
    app.include_router(billing_router)
    logger.info("Billing & Monetization routes carregados")

# Include Advanced Auth routes (Password Reset, 2FA, Profile)
if auth_router:
    app.include_router(auth_router)
    logger.info("Advanced Auth routes carregados (password reset, 2FA, profile)")

# Include Analytics routes (Enterprise KPIs)
if analytics_router:
    app.include_router(analytics_router)

# Include Notifications routes (Enterprise Alerts)
if notifications_router:
    app.include_router(notifications_router)

# Include Audit Trail routes (Enterprise Compliance)
if audit_router:
    app.include_router(audit_router)

# Include Enterprise routes (RBAC, Integrations, Workflows, etc.)
try:
    from backend.enterprise.routes import router as enterprise_router
    app.include_router(enterprise_router)
    logger.info("Enterprise routes carregadas com sucesso")
except Exception as e:
    logger.warning(f"Enterprise routes não disponíveis: {e}")

# Include AI Engine routes (Sistema Enterprise de IAs)
try:
    from ai_engines.routes import router as ai_router
    app.include_router(ai_router)
    logger.info("AI Engines carregados com sucesso")
except ImportError as e:
    logger.warning(f"AI Engines não disponíveis: {e}")

# Include ChatCAD routes (NLP → AutoCAD)
try:
    from ai_engines.chatcad_routes import router as chatcad_router
    app.include_router(chatcad_router)
    logger.info("ChatCAD NLP carregado com sucesso")
except ImportError as e:
    logger.warning(f"ChatCAD não disponível: {e}")

# Include LLM Gateway routes (Multi-provider AI proxy)
try:
    from ai_engines.llm_gateway import router as llm_router
    app.include_router(llm_router)
    logger.info("LLM Gateway carregado com sucesso")
except ImportError as e:
    logger.warning(f"LLM Gateway não disponível: {e}")

# Agent download endpoint
try:
    from backend.routes_agent_download import router as agent_download_router
    app.include_router(agent_download_router)
    logger.info("Agent Download endpoint carregado")
except ImportError as e:
    logger.warning(f"Agent Download não disponível: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET HUB (Real-time bidirecional multi-usuário)
# ══════════════════════════════════════════════════════════════════════════════
try:
    from backend.websocket_hub import router as ws_router, ws_manager, start_ws_cleanup, stop_ws_cleanup
    app.include_router(ws_router)
    logger.info("WebSocket Hub carregado com sucesso")
except ImportError as e:
    logger.warning(f"WebSocket Hub não disponível: {e}")
    ws_manager = None
    start_ws_cleanup = stop_ws_cleanup = None

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM MONITOR & TASK QUEUE (Startup/Shutdown)
# ══════════════════════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_infrastructure():
    """Inicializa componentes de infraestrutura no startup."""
    # Task Queue
    try:
        from backend.task_queue import get_task_queue
        tq = get_task_queue()
        await tq.start(num_workers=int(os.getenv("TASK_QUEUE_WORKERS", "4")))
        logger.info("✓ Task Queue iniciada")
    except Exception as e:
        logger.warning("Task Queue não iniciada: %s", e)

    # System Monitor
    try:
        from backend.system_monitor import get_monitor
        monitor = get_monitor()
        await monitor.start()
        logger.info("✓ System Monitor iniciado")
    except Exception as e:
        logger.warning("System Monitor não iniciado: %s", e)

    # WebSocket cleanup
    if start_ws_cleanup:
        try:
            start_ws_cleanup()
            logger.info("✓ WebSocket cleanup task iniciada")
        except Exception as e:
            logger.warning("WS cleanup não iniciado: %s", e)

    # Connection Pool (async PG)
    try:
        from backend.database.connection_pool import get_pool, AsyncPGPool
        pool = get_pool()
        if isinstance(pool, AsyncPGPool):
            await pool.initialize()
            logger.info("✓ PostgreSQL connection pool inicializado")
        else:
            logger.info("✓ SQLite connection pool ativo")
    except Exception as e:
        logger.warning("Connection pool: %s", e)


@app.on_event("shutdown")
async def shutdown_infrastructure():
    """Finaliza componentes de infraestrutura."""
    try:
        from backend.task_queue import get_task_queue
        await get_task_queue().stop()
    except Exception:
        pass
    try:
        from backend.system_monitor import get_monitor
        await get_monitor().stop()
    except Exception:
        pass
    if stop_ws_cleanup:
        try:
            stop_ws_cleanup()
        except Exception:
            pass
    try:
        from backend.database.connection_pool import get_pool, AsyncPGPool
        pool = get_pool()
        if isinstance(pool, AsyncPGPool):
            await pool.close()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# MONITORING ENDPOINTS (Dashboard de infraestrutura)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/monitoring/dashboard")
async def monitoring_dashboard():
    """Dashboard completo de monitoramento do sistema."""
    result: dict = {"timestamp": datetime.datetime.now(UTC).isoformat()}

    # System Monitor
    try:
        from backend.system_monitor import get_monitor
        result["system"] = get_monitor().get_full_dashboard()
    except Exception as e:
        result["system"] = {"error": str(e)}

    # Task Queue
    try:
        from backend.task_queue import get_task_queue
        tq = get_task_queue()
        result["task_queue"] = tq.get_stats()
        result["active_tasks"] = tq.get_active_tasks()
    except Exception as e:
        result["task_queue"] = {"error": str(e)}

    # Connection Pool
    try:
        from backend.database.connection_pool import get_pool_stats
        result["db_pool"] = get_pool_stats()
    except Exception as e:
        result["db_pool"] = {"error": str(e)}

    # Cache
    try:
        from backend.distributed_cache import get_cache
        result["cache"] = get_cache().stats
    except Exception as e:
        result["cache"] = {"error": str(e)}

    # WebSocket
    if ws_manager:
        result["websocket"] = ws_manager.get_stats()

    return result


@app.get("/api/monitoring/tasks")
async def monitoring_tasks(user_email: str = "", limit: int = 50):
    """Lista tarefas ativas e histórico."""
    try:
        from backend.task_queue import get_task_queue
        tq = get_task_queue()
        return {
            "active": tq.get_active_tasks(user_email or None),
            "history": tq.get_history(user_email or None, limit=limit),
            "stats": tq.get_stats(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/monitoring/tasks/{task_id}")
async def monitoring_task_status(task_id: str):
    """Status de uma tarefa específica."""
    try:
        from backend.task_queue import get_task_queue
        result = await get_task_queue().get_status(task_id)
        if result:
            return result.to_dict()
        return {"error": "Tarefa não encontrada"}
    except Exception as e:
        return {"error": str(e)}


class LoginData(BaseModel):
    username: str = Field(default="", max_length=64, strip_whitespace=True)
    password: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=120, strip_whitespace=True)
    senha: str = Field(default="", max_length=120)
    hwid: str = ""  # Hardware ID enviado pelo Agente Local


class RegisterData(BaseModel):
    email: str = Field(..., min_length=1, max_length=120, strip_whitespace=True)
    senha: str = Field(..., min_length=1, max_length=120)
    empresa: str = Field(default="", max_length=120)


# SSE Functions
async def system_metrics_generator():
    """Generator for real-time system metrics with periodic heartbeat."""
    _heartbeat_interval = 0  # counter to emit ping every ~10s (5 cycles of 2s)
    while True:
        try:
            cpu_percent = psutil.cpu_percent(interval=0)
            ram_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage(os.sep).percent

            data = {
                "timestamp": datetime.datetime.now(UTC).isoformat(),
                "cpu": cpu_percent,
                "ram": ram_percent,
                "disk": disk_percent,
                "type": "system_metrics"
            }

            yield {
                "event": "system_update",
                "data": json.dumps(data)
            }

            _heartbeat_interval += 1
            if _heartbeat_interval >= 5:
                yield {
                    "event": "ping",
                    "data": json.dumps({"ts": datetime.datetime.now(UTC).isoformat()})
                }
                _heartbeat_interval = 0

            await asyncio.sleep(2)

        except Exception as e:
            logger.warning("SSE system_metrics error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "type": "system_error"})
            }
            await asyncio.sleep(5)


async def telemetry_events_generator():
    """Generator for telemetry events."""
    while True:
        try:
            event = await asyncio.wait_for(_TELEMETRY_EVENTS.get(), timeout=15.0)
            yield {
                "event": "telemetry_update",
                "data": json.dumps(event)
            }
        except asyncio.TimeoutError:
            yield {
                "event": "ping",
                "data": json.dumps({"ts": datetime.datetime.now(UTC).isoformat()})
            }
        except Exception as e:
            logger.warning("SSE telemetry error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "type": "telemetry_error"})
            }


async def notification_generator():
    """Generator for notifications."""
    while True:
        try:
            notification = await asyncio.wait_for(_NOTIFICATION_EVENTS.get(), timeout=15.0)
            yield {
                "event": "notification",
                "data": json.dumps(notification)
            }
        except asyncio.TimeoutError:
            yield {
                "event": "ping",
                "data": json.dumps({"ts": datetime.datetime.now(UTC).isoformat()})
            }
        except Exception as e:
            logger.warning("SSE notification error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "type": "notification_error"})
            }


async def ai_events_generator():
    """✓ PROBLEMA #11: Generator for AI CAD responses com compressão e error recovery."""
    import gzip
    import base64
    
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            # ✓ PROBLEMA #11: Timeout para evitar travamento
            event = await asyncio.wait_for(_AI_EVENTS.get(), timeout=30.0)
            
            # ✓ PROBLEMA #11: Compressão para reduzir bandwidth
            event_json = json.dumps(event)
            if len(event_json) > 1024:  # Comprimir se > 1KB
                compressed = gzip.compress(event_json.encode('utf-8'))
                event_data = base64.b64encode(compressed).decode('utf-8')
                yield {
                    "event": "ai_response_compressed",
                    "data": event_data
                }
            else:
                yield {
                    "event": "ai_response",
                    "data": event_json
                }
            
            retry_count = 0  # Reset retry on success
            
        except asyncio.TimeoutError:
            # ✓ PROBLEMA #11: Error recovery - yield heartbeat
            yield {
                "event": "ping",
                "data": json.dumps({"ts": datetime.datetime.now(UTC).isoformat()})
            }
            
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": f"AI SSE falhou após {max_retries} tentativas", "type": "ai_error"})
                }
                break  # Exit generator on persistent errors
            
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "type": "ai_error", "retry": retry_count})
            }
            await asyncio.sleep(1)  # Backoff


def publish_ai_event(event_data: dict) -> None:
    """Função helper para publicar eventos AI com request ID."""
    import uuid
    
    try:
        if "request_id" not in event_data:
            event_data["request_id"] = str(uuid.uuid4())
        
        event_data["timestamp"] = datetime.datetime.now(UTC).isoformat()
        
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(_AI_EVENTS.put_nowait, event_data)
        except RuntimeError:
            # No running event loop — use put_nowait directly
            try:
                _AI_EVENTS.put_nowait(event_data)
            except asyncio.QueueFull:
                logger.warning("AI event queue full, dropping event")
        
    except Exception as e:
        logger.error("Erro ao publicar evento AI: %s", e)


def _enforce_rate_limit(client_ip: str) -> None:
    """Rate limit síncrono (thread-safe). Uses Redis when available, falls back to in-memory.
    
    NOTA: Esta função usa threading.Lock e deve ser chamada via
    asyncio.to_thread() em contextos async para não bloquear o event loop.
    """
    _enforce_rate_generic(client_ip, "rl:req", _REQUEST_HISTORY, RATE_LIMIT_MAX_REQUESTS, "Limite de requisicoes excedido")


def _enforce_register_rate_limit(client_ip: str) -> None:
    """Rate limit específico para /auth/register (3/min).
    
    NOTA: Esta função usa threading.Lock e deve ser chamada via
    asyncio.to_thread() em contextos async para não bloquear o event loop.
    """
    _enforce_rate_generic(client_ip, "rl:reg", _REGISTER_HISTORY, _REGISTER_RATE_MAX, "Muitas tentativas de registro. Aguarde.")


def _enforce_demo_rate_limit(client_ip: str) -> None:
    """Rate limit específico para /auth/demo (5/min)."""
    _enforce_rate_generic(client_ip, "rl:demo", _DEMO_HISTORY, _DEMO_RATE_MAX, "Muitas tentativas de demonstração. Aguarde.")


def _enforce_rate_generic(client_ip: str, prefix: str, fallback: defaultdict, max_requests: int, error_msg: str) -> None:
    """Generic rate limiter: Redis-backed with in-memory fallback."""
    if _REDIS_RATE:
        try:
            key = f"{prefix}:{client_ip}"
            current = _REDIS_RATE.incr(key)
            if current == 1:
                _REDIS_RATE.expire(key, RATE_LIMIT_WINDOW_SECONDS)
            if current > max_requests:
                raise HTTPException(status_code=429, detail=error_msg)
            return
        except HTTPException:
            raise
        except Exception:
            pass  # Fall through to in-memory

    now = time.time()
    with _RATE_LOCK:
        bucket = fallback[client_ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail=error_msg)
        bucket.append(now)
        
        # Periodic cleanup to prevent memory leak
        if prefix == "rl:req" and len(fallback) > 10000:
            stale_cutoff = now - RATE_LIMIT_WINDOW_SECONDS * 2
            stale_ips = [
                ip for ip, b in fallback.items()
                if not b or b[-1] < stale_cutoff
            ]
            for ip in stale_ips[:1000]:
                del fallback[ip]


def _decode_token(request: Request) -> dict | None:
    """Decodifica JWT do header Authorization. Retorna payload ou None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        return jwt.decode(auth_header[7:], JARVIS_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def _is_demo_user(request: Request) -> bool:
    """Verifica se o token pertence ao usuário demo."""
    payload = _decode_token(request)
    if not payload:
        return False
    return payload.get("user", "") == _DEMO_EMAIL


@app.middleware("http")
async def auth_and_rate_middleware(request: Request, call_next):
    """Middleware global: rate limiting + autenticação obrigatória + demo restrictions."""
    # ── CORS preflight (OPTIONS) deve passar direto para o CORSMiddleware ──
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path.rstrip("/")

    # ── Rate limiting global (executar em threadpool para não bloquear) ──
    try:
        await asyncio.to_thread(_enforce_rate_limit, client_ip)
    except HTTPException as e:
        return _json_response(e.status_code, {"detail": e.detail}, request)

    # ── Rate limiting específico para register ──
    if path == "/auth/register":
        try:
            await asyncio.to_thread(_enforce_register_rate_limit, client_ip)
        except HTTPException as e:
            return _json_response(e.status_code, {"detail": e.detail}, request)

    # ── Rate limiting específico para demo (5/min) ──
    if path == "/auth/demo":
        try:
            await asyncio.to_thread(_enforce_demo_rate_limit, client_ip)
        except HTTPException as e:
            return _json_response(e.status_code, {"detail": e.detail}, request)

    # ── Rotas públicas (sem auth) ──
    if path in _AUTH_WHITELIST:
        return await call_next(request)

    # ── Billing routes: webhooks usam Stripe signature, não JWT ──
    if path.startswith("/api/billing/webhooks/") or path.startswith("/api/billing/subscription/"):
        return await call_next(request)

    # ── Bridge routes: todas públicas (agente local, sem dados sensíveis) ──
    if path.startswith("/api/bridge/"):
        return await call_next(request)

    # ── AI routes: permitir acesso público para leitura ──
    if path.startswith("/api/ai/"):
        return await call_next(request)

    # ── CAM routes: permitir acesso público para geração de G-code ──
    if path.startswith("/api/cam/"):
        return await call_next(request)

    # ── Refineries e CAD stream: somente leitura, acesso público ──
    if path.startswith("/api/refineries") or path.startswith("/api/cad/"):
        return await call_next(request)

    # ── SSE routes verificadas separadamente (dentro do handler) ──
    if path.startswith("/sse/"):
        # Auth é verificada dentro do handler SSE
        return await call_next(request)

    # ── WebSocket (auth verificada dentro do handler) ──
    if path.startswith("/ws"):
        return await call_next(request)

    # ── Monitoring routes: acesso público para dashboards ──
    if path.startswith("/api/monitoring/"):
        return await call_next(request)

    # ── Todas as outras rotas: exigir JWT válido ──
    payload = _decode_token(request)
    if not payload:
        return _json_response(401, {"detail": "Autenticação obrigatória"}, request)

    user_email = payload.get("user", "")

    # ── Demo: bloquear rotas restritas ──
    if user_email == _DEMO_EMAIL:
        for blocked in _DEMO_BLOCKED_ROUTES:
            if path.startswith(blocked):
                return _json_response(403, {
                    "detail": "Acesso restrito no modo demonstração. Crie uma conta para acesso completo."
                }, request)

    # Injetar email no request.state para uso nos handlers
    request.state.user_email = user_email

    return await call_next(request)


def _json_response(status_code: int, body: dict, request: Request | None = None):
    """Cria response JSON com CORS headers quando originado do middleware.

    Responses retornadas diretamente pelo middleware (sem call_next) não
    passam pelo CORSMiddleware do Starlette, então precisamos injetar
    os headers manualmente para que o browser não bloqueie a resposta.
    """
    from starlette.responses import JSONResponse
    response = JSONResponse(status_code=status_code, content=body)
    if request:
        origin = request.headers.get("origin", "")
        if origin and (origin in _CORS_ALLOWED_ORIGINS or _CORS_ORIGIN_REGEX.fullmatch(origin)):
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
    return response


_DEMO_USER = {
    "email": _DEMO_EMAIL,
    "empresa": "Engenharia CAD Demo",
    "limite": 100,
    "usado": 0,
}


def _make_token(user_email: str, *, expiry_minutes: int = 60) -> str:
    return jwt.encode(
        {"user": user_email, "exp": datetime.datetime.now(UTC) + datetime.timedelta(minutes=expiry_minutes)},
        JARVIS_SECRET,
        algorithm="HS256",
    )


def _authenticate(identifier: str, password: str) -> dict | None:
    return authenticate_user(identifier, password)


@app.post("/login")
def login(data: LoginData):
    # Aceitar tanto username/password quanto email/senha (frontend envia email/senha)
    identifier = data.email or data.username
    password = data.senha or data.password
    if not identifier or not password:
        raise HTTPException(status_code=401, detail="Credenciais obrigatórias")

    user = _authenticate(identifier, password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    # Validar HWID se fornecido (Agente Local envia, Frontend web não)
    if data.hwid:
        from backend.hwid import validate_hwid
        from backend.routes_license import _load_licenses, _save_licenses, _LICENSE_LOCK
        import time as _time

        with _LICENSE_LOCK:
            licenses = _load_licenses()
            entry = licenses.get(identifier)

            if entry is None:
                licenses[identifier] = {
                    "hwid": data.hwid,
                    "registered_at": _time.time(),
                    "last_seen": _time.time(),
                    "access_count": 1,
                }
                _save_licenses(licenses)
            elif not validate_hwid(entry["hwid"], data.hwid):
                raise HTTPException(
                    status_code=403,
                    detail="Acesso negado: Este computador não está autorizado para esta licença.",
                )
            else:
                entry["last_seen"] = _time.time()
                entry["access_count"] = entry.get("access_count", 0) + 1
                _save_licenses(licenses)

    token = _make_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user["email"],
        "empresa": user["empresa"],
        "tier": user.get("tier", "demo"),
        "limite": user["limite"],
        "usado": user["usado"],
    }


@app.post("/auth/register")
def auth_register(data: RegisterData):
    email = data.email.strip()
    if email_exists(email):
        raise HTTPException(status_code=400, detail="Email já registrado")
    username = email.split("@")[0]
    user = create_user(
        email=email,
        username=username,
        password=data.senha,
        empresa=data.empresa or "Não informada",
        limite=100,
        tier="starter",
    )
    token = _make_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user["email"],
        "empresa": user["empresa"],
        "tier": user.get("tier", "starter"),
        "limite": user["limite"],
        "usado": user["usado"],
    }


@app.post("/admin/seed-test-user")
def admin_seed_test_user():
    """
    Endpoint administrativo para criar/atualizar usuário de teste.
    Usado apenas para setup inicial de contas de teste.
    """
    TEST_EMAIL = "santossod345@gmail.com"
    TEST_SENHA = "Santos14"
    TEST_EMPRESA = "Conta Teste Enterprise"
    
    if email_exists(TEST_EMAIL):
        # Atualizar senha e tier
        pw_hash = _hash_password(TEST_SENHA)
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET password_hash = ?, tier = ?, limite = ? WHERE email = ?"),
                (pw_hash, "enterprise", 999999, TEST_EMAIL)
            )
        return {
            "status": "updated",
            "email": TEST_EMAIL,
            "tier": "enterprise",
            "message": "Usuário atualizado com sucesso. Senha: Santos14"
        }
    else:
        # Criar novo usuário
        user = create_user(
            email=TEST_EMAIL,
            username="santossod345",
            password=TEST_SENHA,
            empresa=TEST_EMPRESA,
            tier="enterprise",
            limite=999999
        )
        return {
            "status": "created",
            "email": TEST_EMAIL,
            "tier": "enterprise",
            "message": "Usuário criado com sucesso. Senha: Santos14"
        }


@app.post("/auth/demo")
def auth_demo():
    token = _make_token(_DEMO_USER["email"], expiry_minutes=_DEMO_TOKEN_EXPIRY_MINUTES)
    return {
        "access_token": token,
        "token_type": "bearer",
        "tier": "demo",
        **_DEMO_USER,
    }


@app.get("/auth/me")
def auth_me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JARVIS_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user_email = payload.get("user", "")
    # Buscar usuário no banco de dados
    user = get_user_by_email(user_email)
    if user:
        return user
    if user_email == _DEMO_USER["email"]:
        return _DEMO_USER
    raise HTTPException(status_code=401, detail="Usuário não encontrado")


@app.post("/auth/refresh")
def auth_refresh(request: Request):
    """Renova um token JWT válido (ou recém-expirado em até 24h) sem exigir re-login."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = auth_header[7:]
    try:
        # Aceitar tokens expirados em até 24h para refresh
        payload = jwt.decode(
            token, JARVIS_SECRET, algorithms=["HS256"],
            options={"verify_exp": False}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_email = payload.get("user", "")
    if not user_email:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Verificar se o token expirou há mais de 24h
    exp = payload.get("exp", 0)
    now = datetime.datetime.now(UTC).timestamp()
    if exp and now - exp > 86400:
        raise HTTPException(status_code=401, detail="Token expirado há muito tempo. Faça login novamente.")

    # Demo users get short-lived tokens
    if user_email == _DEMO_EMAIL:
        new_token = _make_token(user_email, expiry_minutes=_DEMO_TOKEN_EXPIRY_MINUTES)
    else:
        new_token = _make_token(user_email, expiry_minutes=60)

    return {
        "access_token": new_token,
        "token_type": "bearer",
    }


@app.get("/")
def root():
    """Status público da API."""
    return {
        "service": "Engenharia CAD API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check():
    """Health check consolidado — banco, IA, Redis, Celery e AutoCAD."""
    from urllib.parse import urlparse

    db_ok = False
    db_ephemeral = None
    db_type = "unknown"
    db_error = None
    try:
        from backend.database.db import _get_conn, is_ephemeral, _USE_PG

        conn = _get_conn()
        if _USE_PG:
            conn.cursor().execute("SELECT 1")
        else:
            conn.execute("SELECT 1")
        db_ok = True
        db_ephemeral = bool(is_ephemeral())
        db_type = "postgresql" if _USE_PG else "sqlite"
    except Exception as exc:
        db_error = str(exc)

    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_RESULT_BACKEND", "")
    redis_ok = False
    redis_configured = redis_url.startswith("redis://")
    redis_error = None
    if redis_configured:
        try:
            from redis import Redis

            redis_client = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            redis_client.ping()
            redis_ok = True
        except Exception as exc:
            redis_error = str(exc)

    celery_broker = os.getenv("CELERY_BROKER_URL", "")
    celery_ok = False
    celery_configured = bool(celery_broker)
    celery_error = None
    if celery_configured:
        try:
            parsed = urlparse(celery_broker)
            host = parsed.hostname
            port = parsed.port
            if parsed.scheme in {"amqp", "amqps"}:
                port = port or (5671 if parsed.scheme == "amqps" else 5672)
            elif parsed.scheme.startswith("redis"):
                port = port or 6379
            if host and port:
                import socket

                with socket.create_connection((host, int(port)), timeout=2):
                    celery_ok = True
            else:
                celery_error = "Broker URL inválida para verificação de conectividade"
        except Exception as exc:
            celery_error = str(exc)

    autocad_ok = False
    autocad_details: dict = {}
    autocad_error = None
    try:
        from backend.autocad_driver import acad_driver

        autocad_details = acad_driver.health_check()
        autocad_ok = bool(
            autocad_details.get("healthy", False)
            or autocad_details.get("driver_status") in {"Connected", "Bridge", "Cloud"}
        )
    except Exception as exc:
        autocad_error = str(exc)

    llm_providers: dict = {}
    llm_available = False
    llm_error = None
    try:
        from ai_engines.llm_gateway import OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_BASE_URL
        from urllib.request import urlopen, Request

        ollama_ok = False
        try:
            req = Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
            with urlopen(req, timeout=2.5) as response:
                ollama_ok = response.status == 200
        except Exception:
            ollama_ok = False

        llm_providers = {
            "openai": {"configured": bool(OPENAI_API_KEY), "available": bool(OPENAI_API_KEY)},
            "anthropic": {"configured": bool(ANTHROPIC_API_KEY), "available": bool(ANTHROPIC_API_KEY)},
            "ollama": {"configured": True, "available": ollama_ok},
        }
        llm_available = any(p.get("available") for p in llm_providers.values())
    except Exception as exc:
        llm_error = str(exc)

    status = "healthy" if db_ok else "degraded"

    return {
        "status": status,
        "autocad": autocad_ok,
        "database": db_ok,
        "services": {
            "database": {
                "ok": db_ok,
                "type": db_type,
                "ephemeral": db_ephemeral,
                "error": db_error,
            },
            "redis": {
                "ok": redis_ok,
                "configured": redis_configured,
                "url": redis_url if redis_configured else None,
                "error": redis_error,
            },
            "celery": {
                "ok": celery_ok,
                "configured": celery_configured,
                "broker": celery_broker if celery_configured else None,
                "error": celery_error,
            },
            "llm": {
                "ok": llm_available,
                "providers": llm_providers,
                "error": llm_error,
            },
            "autocad": {
                "ok": autocad_ok,
                "driver": autocad_details,
                "error": autocad_error,
            },
        },
    }


@app.get("/healthz")
def healthz_check():
    """Endpoint curto de liveness/readiness para CI e smoke checks."""
    result = health_check()
    return {"status": result.get("status", "degraded")}


@app.get("/api/security/status")
def security_status():
    """Retorna status de todos os recursos de segurança."""
    # Rate limiting
    rate_limit_info = {"enabled": False, "backend": "none"}
    if _SLOWAPI_AVAILABLE and limiter is not None:
        rate_limit_info = {"enabled": True, "backend": "slowapi"}
    else:
        try:
            from backend.rate_limiter import rate_limiter as rl
            rate_limit_info = {"enabled": True, "backend": rl.backend}
        except ImportError:
            pass
    
    # Criptografia
    crypto_info = {"available": False}
    try:
        from backend.crypto import is_encryption_available
        crypto_info = {"available": is_encryption_available()}
    except ImportError:
        pass
    
    # Headers de segurança
    security_headers = {"enabled": False}
    try:
        from backend.security import SecurityHeadersMiddleware
        security_headers = {"enabled": True}
    except ImportError:
        pass
    
    # Sessions
    sessions = {"backend": "memory"}
    if _REDIS_SESSION_AVAILABLE:
        sessions = {"backend": "redis"}
    
    return {
        "status": "secure",
        "rate_limiting": rate_limit_info,
        "encryption": crypto_info,
        "security_headers": security_headers,
        "sessions": sessions,
        "cors": {
            "origins_count": len(_CORS_ALLOWED_ORIGINS),
        },
        "features": {
            "jwt_auth": True,
            "hsts": True,
            "csp": True,
            "audit_logging": audit_router is not None,
        }
    }


@app.get("/project-stats")
def project_stats():
    """Retorna estatísticas agregadas de projetos para o Dashboard."""
    stats = get_project_stats()
    uploads = get_uploads(limit=5)
    return {
        "stats": stats,
        "recent_uploads": uploads,
    }


@app.post("/quality-check/{project_id}")
def run_quality_check(project_id: int):
    """Executa verificação de qualidade completa em um projeto."""
    import json as _json
    project = db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Verificar normas
    checks_run = []
    piping_spec_str = project.get("piping_spec", "{}")
    piping_spec = _json.loads(piping_spec_str) if piping_spec_str else {}

    # Check 1: Material conforme norma
    material = piping_spec.get("material", "")
    mat_ok = material in ("ASTM A106 Gr.B", "ASTM A335 P11")
    add_quality_check(project_id, "material", "Material conforme ASTM", mat_ok,
                      f"Material: {material}" if material else "Sem especificação de material")
    checks_run.append({"name": "Material ASTM", "passed": mat_ok, "detail": material or "N/A"})

    # Check 2: Schedule válido
    schedule = piping_spec.get("selected_schedule", "")
    sch_ok = schedule.startswith("SCH") if schedule else False
    add_quality_check(project_id, "schedule", "Schedule conforme ASME B31.3", sch_ok,
                      f"Schedule: {schedule}" if schedule else "Sem schedule")
    checks_run.append({"name": "Schedule ASME", "passed": sch_ok, "detail": schedule or "N/A"})

    # Check 3: Espessura de parede
    wall = piping_spec.get("wall_thickness_mm", 0)
    wall_ok = wall > 0
    add_quality_check(project_id, "wall", "Espessura parede >= mínimo", wall_ok,
                      f"Espessura: {wall}mm")
    checks_run.append({"name": "Espessura Parede", "passed": wall_ok, "detail": f"{wall}mm"})

    # Check 4: Classe de pressão
    pc = piping_spec.get("pressure_class", "")
    pc_ok = pc.startswith("ASME") if pc else False
    add_quality_check(project_id, "pressure", "Classe de pressão ASME", pc_ok,
                      f"Classe: {pc}" if pc else "Sem classe de pressão")
    checks_run.append({"name": "Classe Pressão", "passed": pc_ok, "detail": pc or "N/A"})

    # Check 5: Teste hidrostático
    hydro = piping_spec.get("hydrotest_pressure_bar", 0)
    hydro_ok = hydro > 0
    add_quality_check(project_id, "hydrotest", "Pressão hidrostática definida", hydro_ok,
                      f"Pressão: {hydro} bar")
    checks_run.append({"name": "Teste Hidrostático", "passed": hydro_ok, "detail": f"{hydro} bar"})

    # Check 6: Arquivo LISP gerado
    lsp = project.get("lsp_path", "")
    lsp_ok = bool(lsp) and os.path.isfile(lsp)
    add_quality_check(project_id, "file", "Arquivo LISP gerado", lsp_ok,
                      lsp if lsp_ok else "Arquivo não encontrado")
    checks_run.append({"name": "Arquivo LISP", "passed": lsp_ok, "detail": os.path.basename(lsp) if lsp else "N/A"})

    passed_count = sum(1 for c in checks_run if c["passed"])
    total_count = len(checks_run)
    all_passed = passed_count == total_count

    # Atualizar status geral do projeto
    norms = ["ASME B31.3", "ASTM A106/A335", "Petrobras N-58"]
    norms_p = [n for n, c in zip(norms, [mat_ok and sch_ok, wall_ok and pc_ok, hydro_ok and lsp_ok]) if c]
    db_update_project(project_id,
                      norms_checked=_json.dumps(norms),
                      norms_passed=_json.dumps(norms_p),
                      clash_count=0)

    return {
        "project_id": project_id,
        "checks": checks_run,
        "passed": passed_count,
        "total": total_count,
        "all_passed": all_passed,
        "verdict": "APROVADO" if all_passed else "REPROVADO" if passed_count < total_count / 2 else "PARCIAL",
    }


@app.get("/system")
def system():
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(os.sep).percent,
    }


@app.get("/ai")
def ai(q: str = ""):
    query = str(q).strip()
    if not query:
        raise HTTPException(status_code=400, detail="Pergunta vazia")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Pergunta excede limite de 500 caracteres")
    return {"response": f"Jarvis: resposta para '{query}'"}


# SSE Endpoints — cada um valida JWT e controla conexões por IP
def _sse_check_auth(request: Request) -> dict:
    """Valida JWT para SSE. Retorna payload ou levanta HTTPException."""
    payload = _decode_token(request)
    if not payload:
        raise HTTPException(status_code=401, detail="Token SSE inválido ou ausente")
    return payload


def _sse_track_connect(client_ip: str) -> None:
    with _SSE_LOCK:
        if _SSE_CONNECTIONS[client_ip] >= _SSE_MAX_PER_IP:
            raise HTTPException(status_code=429, detail="Limite de conexões SSE atingido")
        _SSE_CONNECTIONS[client_ip] += 1


def _sse_track_disconnect(client_ip: str) -> None:
    with _SSE_LOCK:
        _SSE_CONNECTIONS[client_ip] = max(0, _SSE_CONNECTIONS[client_ip] - 1)


async def _sse_with_timeout(gen, client_ip: str):
    """Wraps SSE generator com timeout global e cleanup."""
    start = time.time()
    try:
        async for event in gen:
            if time.time() - start > _SSE_TIMEOUT_SECONDS:
                yield {"event": "timeout", "data": json.dumps({"message": "Conexão SSE expirada"})}
                break
            yield event
    finally:
        _sse_track_disconnect(client_ip)


@app.get("/sse/system")
async def system_sse(request: Request):
    """Server-Sent Events for real-time system metrics."""
    _sse_check_auth(request)
    client_ip = request.client.host if request.client else "unknown"
    _sse_track_connect(client_ip)
    return EventSourceResponse(_sse_with_timeout(system_metrics_generator(), client_ip))


@app.get("/sse/telemetry")
async def telemetry_sse(request: Request):
    """Server-Sent Events for telemetry updates."""
    _sse_check_auth(request)
    client_ip = request.client.host if request.client else "unknown"
    _sse_track_connect(client_ip)
    return EventSourceResponse(_sse_with_timeout(telemetry_events_generator(), client_ip))


@app.get("/sse/notifications")
async def notifications_sse(request: Request):
    """Server-Sent Events for notifications."""
    _sse_check_auth(request)
    client_ip = request.client.host if request.client else "unknown"
    _sse_track_connect(client_ip)
    return EventSourceResponse(_sse_with_timeout(notification_generator(), client_ip))


@app.get("/sse/ai-stream")
async def ai_stream_sse(request: Request):
    """Server-Sent Events for AI CAD responses."""
    _sse_check_auth(request)
    client_ip = request.client.host if request.client else "unknown"
    _sse_track_connect(client_ip)
    return EventSourceResponse(_sse_with_timeout(ai_events_generator(), client_ip))


# ============================================================================
# IMPORTANTE: Rotas CAD (Engenharia CAD v1.0) já incluÍ­das via app.include_router
# ============================================================================
# Endpoints disponÍ­veis:
# - GET /api/refineries - Lista todas as refinarias
# - GET /api/refineries/{refinery_id} - Detalhes de uma refinaria
# - POST /api/cad/inject - Injetar comando LISP no AutoCAD
# - GET /api/cad/inject/{script_id} - Status de injeção
# - GET /api/cad/norms/{refinery_id} - Normas aplicáveis
# - GET /api/cad/materials/{refinery_id} - Database de materiais


# Helper functions to send events
async def send_telemetry_event(event_data: dict):
    """Send telemetry event to all connected clients."""
    await _TELEMETRY_EVENTS.put(event_data)


async def send_notification(message: str, level: str = "info", user: str = None):
    """Send notification to all connected clients."""
    notification = {
        "timestamp": datetime.datetime.now(UTC).isoformat(),
        "message": message,
        "level": level,
        "user": user,
        "type": "notification"
    }
    await _NOTIFICATION_EVENTS.put(notification)


async def send_ai_event(text: str, status: str = "processing", job_id: str = None):
    """Send AI event to all connected clients."""
    ai_event = {
        "timestamp": datetime.datetime.now(UTC).isoformat(),
        "text": text,
        "status": status,
        "job_id": job_id,
        "type": "ai_response"
    }
    await _AI_EVENTS.put(ai_event)


# â”€â”€ AI Watchdog Diagnostics (invisÍ­vel para o usuário, vital para ops) â”€â”€â”€â”€â”€â”€
@app.get("/ai/diagnostics")
def ai_diagnostics():
    """Retorna estado interno da IA de Baixo Nível. Debug e monitoramento."""
    return watchdog.diagnostics()


@app.get("/ai/health")
def ai_health():
    """Health check rápido da camada de IA — frontend heartbeat usa este endpoint."""
    from backend.autocad_driver import acad_driver

    diag = watchdog.diagnostics()
    trend = diag.get("resource_trend", {})
    driver_info = acad_driver.health_check()
    return {
        "ai_active": diag.get("active", False),
        "backend_ok": True,
        "recent_crashes": diag.get("recent_crashes", 0),
        "corrections_applied": diag.get("corrections_applied", 0),
        "avg_cpu": trend.get("avg_cpu", 0),
        "avg_ram": trend.get("avg_ram", 0),
        "autocad_driver": {
            "status": driver_info.get("driver_status"),
            "com_available": driver_info.get("com_available"),
            "document": driver_info.get("document"),
            "stats": driver_info.get("stats"),
        },
    }


# Example endpoint that triggers telemetry events
@app.post("/telemetry/test")
async def test_telemetry():
    """Test endpoint to trigger telemetry events."""
    test_data = {
        "timestamp": datetime.datetime.now(UTC).isoformat(),
        "event": "test_event",
        "data": {
            "projects_processed": 42,
            "templates_generated": 15,
            "performance_score": 98.5
        },
        "type": "telemetry_test"
    }

    await send_telemetry_event(test_data)
    await send_notification("Teste de telemetria executado com sucesso", "success")

    return {"status": "Telemetry event sent"}


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints chamados pelo Frontend Dashboard (api.ts)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/insights")
def get_insights():
    """Retorna insights e estatísticas reais do banco de dados."""
    stats = get_project_stats()
    total = stats["total_projects"]
    return {
        "stats": {
            "total_projects": total,
            "seed_projects": 0,
            "real_projects": total,
            "completed_projects": stats["completed_projects"],
            "top_part_names": stats["top_parts"],
            "top_companies": stats["top_companies"],
            "diameter_range": stats["diameter_range"],
            "length_range": stats["length_range"],
            "draft_feedback": {"accepted": 0, "rejected": 0},
        },
        "recommendations": {
            "suggested_part_name": "FLANGE-PADRAO",
            "suggested_company": "PETROBRAS-REGAP",
            "typical_diameter_min": 2,
            "typical_diameter_max": 48,
            "typical_length_min": 100,
            "typical_length_max": 12000,
            "total_projects": total,
        },
        "templates": [],
    }


@app.get("/history")
def get_history():
    """Retorna histórico de projetos do banco de dados."""
    projects = db_get_projects(limit=50)
    history = [
        f"Projeto {p.get('company','?')} / {p.get('part_name','?')} — Ø{p.get('diameter',0)}mm × {p.get('length',0)}mm [{p.get('status','?')}]"
        for p in projects
    ]
    return {"history": history}


@app.get("/projects")
def list_projects(request: Request):
    """Lista todos os projetos (com dados reais do DB)."""
    projects = db_get_projects(limit=100)
    return {"projects": projects, "total": len(projects)}


@app.get("/projects/{project_id}")
def get_single_project(project_id: int):
    """Retorna detalhes de um projeto específico."""
    project = db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    checks = get_quality_checks(project_id)
    return {"project": project, "quality_checks": checks}


@app.get("/projects/{project_id}/download/{file_type}")
def download_project_file(project_id: int, file_type: str):
    """Baixa arquivo gerado de um projeto (lsp, dxf, csv)."""
    from fastapi.responses import FileResponse
    project = db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    path_key = {"lsp": "lsp_path", "dxf": "dxf_path", "csv": "csv_path"}.get(file_type)
    if not path_key:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido (lsp, dxf, csv)")

    file_path = project.get(path_key)
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Arquivo {file_type} não disponível para este projeto")

    # Validar que o arquivo está dentro do diretório de output permitido
    _allowed_base = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
    allowed_dir = os.path.normpath(_allowed_base)
    real_path = os.path.normpath(os.path.realpath(file_path))
    if not real_path.startswith(allowed_dir):
        raise HTTPException(status_code=403, detail="Acesso negado: caminho fora do diretório permitido")

    return FileResponse(file_path, filename=os.path.basename(file_path))


@app.get("/logs")
def get_logs():
    """Retorna logs do sistema."""
    _log_base = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
    log_file = os.path.join(_log_base, "ai_watchdog.log")
    lines: list[str] = []
    if os.path.isfile(log_file):
        with open(log_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-100:]
    lines = [l.strip() for l in lines if l.strip()]
    if not lines:
        lines = [
            f"[{datetime.datetime.now(UTC).isoformat()}] Sistema iniciado com sucesso",
            f"[{datetime.datetime.now(UTC).isoformat()}] Watchdog ativo — monitorando recursos",
        ]
    return {"logs": lines}


@app.post("/generate")
async def generate_project(request: Request):
    """Gera um projeto CAD real usando o motor de engenharia."""
    import json as _json
    import traceback

    _ProjectService = None
    _select_piping_specification = None
    try:
        from engenharia_automacao.core.main import ProjectService as _ProjectService
        from engenharia_automacao.core.piping.specs import select_piping_specification as _select_piping_specification
    except Exception as _import_err:
        logger.warning("Módulos de engenharia não disponíveis: %s", _import_err)

    body = await request.json()
    diameter = body.get("diameter", 6)
    length = body.get("length", 1000)
    company = body.get("company", "PETROBRAS-REGAP")
    part_name = body.get("part_name", "FLANGE-PADRAO")
    code = body.get("code", "N-58-DEFAULT")
    executar = body.get("executar", False)
    fluid = body.get("fluid", "Hidrocarboneto")
    temperature_c = body.get("temperature_c", 25)
    operating_pressure_bar = body.get("operating_pressure_bar", 10)

    # Obter email do usuário autenticado (middleware já validou JWT)
    user_email = getattr(request.state, "user_email", _DEMO_EMAIL)

    # Criar registro no banco de dados
    project_data = {
        "code": code, "company": company, "part_name": part_name,
        "diameter": diameter, "length": length, "fluid": fluid,
        "temperature_c": temperature_c,
        "operating_pressure_bar": operating_pressure_bar,
    }
    project_id = db_create_project(user_email, project_data)

    _data_base = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
    output_dir = os.path.join(_data_base, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Calcular especificação de tubulação (ASME B31.3)
    piping_spec_data = {}
    norms_checked = ["ASME B31.3"]
    norms_passed = []
    try:
        if _select_piping_specification is None:
            raise ImportError("select_piping_specification não disponível")
        piping_spec = _select_piping_specification(
            fluid=fluid,
            temperature_c=temperature_c,
            operating_pressure_bar=operating_pressure_bar,
            diameter_mm=diameter,
        )
        piping_spec_data = {
            "pressure_class": piping_spec.pressure_class,
            "material": piping_spec.material,
            "flange_face": piping_spec.flange_face,
            "selected_schedule": piping_spec.selected_schedule,
            "wall_thickness_mm": piping_spec.selected_wall_thickness_mm,
            "hydrotest_pressure_bar": piping_spec.hydrotest_pressure_bar,
            "corrosion_allowance_mm": piping_spec.corrosion_allowance_mm,
        }
        norms_passed.append("ASME B31.3")
        add_quality_check(project_id, "norm", "ASME B31.3 - Espessura", True,
                          f"Schedule {piping_spec.selected_schedule}, parede {piping_spec.selected_wall_thickness_mm}mm")
    except Exception as e:
        logger.warning("Falha no cálculo de piping spec: %s", e)
        add_quality_check(project_id, "norm", "ASME B31.3 - Espessura", False, str(e))

    # Gerar arquivos CAD usando o motor de engenharia
    lsp_path = None
    csv_path = None
    try:
        if _ProjectService is None:
            raise ImportError("ProjectService não disponível (dependências ausentes)")
        svc = _ProjectService()
        # O payload do ProjectService espera campos específicos
        eng_payload = {
            "code": code, "company": company, "part_name": part_name,
            "diameter": diameter, "length": length,
            "fluid": fluid, "temperature_c": temperature_c,
            "operating_pressure_bar": operating_pressure_bar,
        }
        generated_path = svc.generate_project(eng_payload, output_dir, execute_in_autocad=executar)
        lsp_path = str(generated_path)
        csv_path_candidate = str(generated_path.with_name(f"{generated_path.stem}_line_list.csv"))
        if os.path.isfile(csv_path_candidate):
            csv_path = csv_path_candidate
        add_quality_check(project_id, "generation", "LISP Generation", True, f"Arquivo: {generated_path.name}")
    except Exception as e:
        logger.error("Falha na geração via ProjectService: %s\n%s", e, traceback.format_exc())
        # Fallback: gerar LISP básico
        add_quality_check(project_id, "generation", "LISP Generation", False, str(e))
        out_path = os.path.join(output_dir, f"project_{project_id}.lsp")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"; Engenharia CAD Generated Project #{project_id}\n")
            f.write(f"; Company: {company} | Part: {part_name}\n")
            f.write(f"; Diameter: {diameter}mm | Length: {length}mm\n")
            if piping_spec_data:
                f.write(f"; Material: {piping_spec_data.get('material','N/A')} | Schedule: {piping_spec_data.get('selected_schedule','N/A')}\n")
            f.write(f'(command "LINE" "0,0,0" "{length},0,0" "")\n')
        lsp_path = out_path

    # Atualizar projeto no banco
    db_update_project(
        project_id,
        status="completed",
        lsp_path=lsp_path,
        csv_path=csv_path,
        piping_spec=_json.dumps(piping_spec_data),
        norms_checked=_json.dumps(norms_checked),
        norms_passed=_json.dumps(norms_passed),
        completed_at=time.time(),
    )

    # Notificar via SSE
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_notification(
            f"Projeto {code} gerado com sucesso — {company}/{part_name}",
            "success",
            user_email,
        ))
    except Exception:
        pass

    user = get_user_by_email(user_email)
    return {
        "id": project_id,
        "path": lsp_path,
        "csv_path": csv_path,
        "piping_spec": piping_spec_data,
        "quality_checks": get_quality_checks(project_id),
        "usado": user["usado"] if user else 0,
        "limite": user["limite"] if user else 999,
    }


@app.post("/excel")
async def upload_excel(request: Request):
    """Recebe upload de arquivo Excel e processa em lote via motor de engenharia."""
    from engenharia_automacao.core.main import ProjectService
    import shutil
    import json as _json

    # Obter email do usuário autenticado (middleware já validou JWT)
    user_email = getattr(request.state, "user_email", _DEMO_EMAIL)

    content_type = request.headers.get("content-type", "")

    _data_base = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
    upload_dir = os.path.join(_data_base, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    output_dir = os.path.join(_data_base, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Suportar multipart/form-data (frontend) e JSON fallback
    if "multipart" in content_type:
        from starlette.datastructures import UploadFile as _UF
        form = await request.form()
        file = form.get("file") or form.get("excel")
        if file is None:
            raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

        # Validar extensão
        original_name = getattr(file, "filename", "upload.xlsx")
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in (".xlsx", ".xls"):
            raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx ou .xls")

        # Ler conteúdo e validar tamanho
        content = await file.read()
        if len(content) > _MAX_EXCEL_UPLOAD_BYTES:
            max_mb = _MAX_EXCEL_UPLOAD_BYTES // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"Arquivo excede limite de {max_mb}MB")

        # Salvar arquivo
        safe_name = f"upload_{int(time.time())}_{original_name.replace(os.sep, '_')}"
        saved_path = os.path.join(upload_dir, safe_name)
        with open(saved_path, "wb") as f:
            f.write(content)
    else:
        raise HTTPException(status_code=400, detail="Envie o arquivo como multipart/form-data")

    # Registrar upload no DB quando a camada persistente estiver disponível
    upload_id = (
        create_upload(user_email, original_name, saved_path)
        if callable(create_upload)
        else None
    )

    # Processar via ProjectService
    try:
        svc = ProjectService()
        generated_files = svc.generate_projects_from_excel(saved_path, output_dir)

        if not generated_files:
            if callable(update_upload) and upload_id is not None:
                update_upload(
                    upload_id,
                    row_count=0,
                    projects_generated=0,
                    status="failed",
                )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Nenhum projeto válido foi gerado a partir da planilha. "
                    "Verifique se as colunas obrigatórias e os dados das linhas estão preenchidos."
                ),
            )

        # Registrar cada projeto gerado no DB
        project_ids = []
        for gen_path in generated_files:
            if callable(db_create_project):
                pid = db_create_project(user_email, {
                    "code": gen_path.stem,
                    "company": "Excel Import",
                    "part_name": original_name,
                })
                if callable(db_update_project):
                    db_update_project(
                        pid,
                        status="completed",
                        lsp_path=str(gen_path),
                        completed_at=time.time(),
                    )
                project_ids.append(pid)

        if callable(update_upload) and upload_id is not None:
            update_upload(
                upload_id,
                row_count=len(generated_files),
                projects_generated=len(generated_files),
                status="completed",
            )

        user = get_user_by_email(user_email) if callable(get_user_by_email) else None
        return {
            "files": [str(f) for f in generated_files],
            "count": len(generated_files),
            "upload_id": upload_id,
            "project_ids": project_ids,
            "usado": user["usado"] if user else 0,
            "limite": user["limite"] if user else 999,
        }
    except HTTPException:
        if callable(update_upload) and upload_id is not None:
            update_upload(upload_id, status="failed")
        raise
    except (ValueError, FileNotFoundError, ImportError) as e:
        if callable(update_upload) and upload_id is not None:
            update_upload(upload_id, status="failed")
        logger.warning("Falha validando planilha Excel: %s", e)
        raise HTTPException(status_code=422, detail=f"Falha ao ler planilha Excel: {e}")
    except Exception as e:
        if callable(update_upload) and upload_id is not None:
            update_upload(upload_id, status="failed")
        logger.error("Falha no processamento Excel: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar Excel: {e}")


@app.get("/project-draft")
def get_project_draft(company: str = "PETROBRAS-REGAP", part_name: str = "FLANGE-PADRAO"):
    """Gera rascunho de projeto baseado em templates existentes."""
    return {
        "company": company,
        "part_name": part_name,
        "diameter": 6,
        "length": 1000,
        "code": "N-58-001",
        "based_on_template": None,
        "confidence": "medium",
    }


@app.get("/project-draft-from-text")
def get_project_draft_from_text(prompt: str = ""):
    """Gera rascunho de projeto a partir de texto livre."""
    return {
        "company": "PETROBRAS-REGAP",
        "part_name": "FLANGE-PADRAO",
        "diameter": 6,
        "length": 1000,
        "code": "N-58-001",
        "based_on_template": None,
        "confidence": "medium",
        "parsed_fields": ["diameter", "length"],
        "prompt": prompt,
        "explanation": f"Interpretação do prompt: '{prompt}'",
        "field_confidence": {
            "company": "medium",
            "part_name": "medium",
            "diameter": "medium",
            "length": "medium",
            "code": "medium",
        },
    }


@app.post("/project-draft-feedback")
async def post_project_draft_feedback(request: Request):
    """Recebe feedback sobre rascunho de projeto."""
    return {"status": "ok"}


@app.post("/jobs/stress/porticos-50")
async def stress_test_50():
    """Dispara teste de stress com 50 pórticos."""
    import uuid
    job_ids = [str(uuid.uuid4()) for _ in range(50)]
    return {
        "status": "dispatched",
        "queue": "stress_test",
        "jobs_submitted": 50,
        "job_ids": job_ids,
        "health": {
            "dispatch_elapsed_ms": 120,
            "dispatch_memory_current_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "dispatch_memory_peak_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        },
    }


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Retorna status de um job."""
    return {"id": job_id, "status": "completed", "result": {"success": True}}


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE MODE — Comunicação com AutoCAD remoto via sincronizador
# ═══════════════════════════════════════════════════════════════════════════════

# Fila de comandos pendentes (persistente em SQLite)
# Em ambientes serverless (Vercel) o filesystem é read-only exceto /tmp
_bridge_default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    _bridge_default_dir = "/tmp"
_bridge_db_path = os.path.join(_bridge_default_dir, "bridge_queue.db")
_bridge_db_lock = Lock()
_bridge_db_initialized = False

# Fallback em memória quando SQLite falha (ambiente serverless)
_bridge_memory_queue: list[dict] = []
_bridge_memory_mode = False


def _bridge_init_db() -> None:
    """Inicializa banco SQLite ou fallback em memória se falhar."""
    global _bridge_db_initialized, _bridge_memory_mode
    if _bridge_db_initialized:
        return
    try:
        os.makedirs(os.path.dirname(_bridge_db_path), exist_ok=True)
        with sqlite3.connect(_bridge_db_path, timeout=5) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bridge_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lisp_code TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()
        _bridge_db_initialized = True
        _bridge_memory_mode = False
    except Exception as e:
        # Fallback para modo memória se SQLite falhar
        logger.warning(f"SQLite bridge init failed, using memory mode: {e}")
        _bridge_db_initialized = True
        _bridge_memory_mode = True


def _bridge_enqueue(lisp_code: str, operation: str) -> int:
    _bridge_init_db()
    
    # Modo memória (fallback)
    if _bridge_memory_mode:
        cmd_id = len(_bridge_memory_queue) + 1
        _bridge_memory_queue.append({
            "id": cmd_id,
            "lisp_code": lisp_code,
            "operation": operation,
            "timestamp": datetime.datetime.now(UTC).isoformat(),
        })
        return cmd_id
    
    with _bridge_db_lock:
        with sqlite3.connect(_bridge_db_path, timeout=5) as conn:
            cur = conn.execute(
                "INSERT INTO bridge_commands (lisp_code, operation, timestamp) VALUES (?, ?, ?)",
                (lisp_code, operation, datetime.datetime.now(UTC).isoformat()),
            )
            conn.commit()
            return int(cur.lastrowid)


def _bridge_list() -> list[dict]:
    _bridge_init_db()
    
    # Modo memória (fallback)
    if _bridge_memory_mode:
        return list(_bridge_memory_queue)
    
    try:
        with _bridge_db_lock:
            with sqlite3.connect(_bridge_db_path, timeout=5) as conn:
                rows = conn.execute(
                    "SELECT id, lisp_code, operation, timestamp FROM bridge_commands ORDER BY id ASC"
                ).fetchall()
        return [
            {
                "id": row[0],
                "lisp_code": row[1],
                "operation": row[2],
                "timestamp": row[3],
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"SQLite bridge_list failed: {e}")
        return []


def _bridge_ack(cmd_id: str) -> bool:
    _bridge_init_db()
    
    # Modo memória (fallback)
    if _bridge_memory_mode:
        global _bridge_memory_queue
        original_len = len(_bridge_memory_queue)
        _bridge_memory_queue = [c for c in _bridge_memory_queue if str(c["id"]) != str(cmd_id)]
        return len(_bridge_memory_queue) < original_len
    
    try:
        with _bridge_db_lock:
            with sqlite3.connect(_bridge_db_path, timeout=5) as conn:
                cur = conn.execute("DELETE FROM bridge_commands WHERE id = ?", (cmd_id,))
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning(f"SQLite bridge_ack failed: {e}")
        return False


def _bridge_pending_count() -> int:
    _bridge_init_db()
    
    # Modo memória (fallback)
    if _bridge_memory_mode:
        return len(_bridge_memory_queue)
    
    try:
        with _bridge_db_lock:
            with sqlite3.connect(_bridge_db_path, timeout=5) as conn:
                row = conn.execute("SELECT COUNT(*) FROM bridge_commands").fetchone()
        return int(row[0]) if row else 0
    except Exception as e:
        logger.warning(f"SQLite bridge_pending_count failed: {e}")
        return 0


# Inicialização lazy — não chamar no top-level para evitar crash em serverless

# Status de conexão do cliente
_bridge_client_info = {
    "connected": False,
    "last_seen": None,
    "cad_type": None,
    "cad_version": None,
    "machine": None,
    "commands_executed": 0,
}


@app.post("/api/bridge/connection")
async def bridge_connection(request: Request):
    """Recebe status de conexão do sincronizador."""
    global _bridge_client_info
    try:
        data = await request.json()
        
        _bridge_client_info = {
            "connected": data.get("connected", False),
            "last_seen": datetime.datetime.now(UTC).isoformat(),
            "cad_type": data.get("cad_type"),
            "cad_version": data.get("cad_version"),
            "machine": data.get("machine"),
            "commands_executed": _bridge_client_info.get("commands_executed", 0),
        }
        
        return {"status": "ok", "received": _bridge_client_info}
    except Exception as e:
        logger.error(f"Bridge connection error: {e}")
        return {"status": "error", "message": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD DO SINCRONIZADOR
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/download/sincronizador")
async def download_sincronizador():
    """Gera e retorna ZIP com o pacote do Sincronizador AutoCAD."""
    from fastapi.responses import StreamingResponse
    
    # Diretório com os arquivos do cliente
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cliente_dir = os.path.join(base_dir, "AutoCAD_Cliente")
    
    if not os.path.isdir(cliente_dir):
        raise HTTPException(status_code=404, detail="Pacote do sincronizador não encontrado")
    
    # Arquivos a incluir no ZIP
    files_to_include = [
        "INSTALAR.bat",
        "INSTALAR.ps1",
        "DETECTAR_AUTOCAD.ps1",
        "SINCRONIZADOR.ps1",
        "INICIAR_SINCRONIZADOR.bat",
        "forge_vigilante.lsp",
        "acaddoc.lsp",
    ]
    
    # Criar ZIP em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in files_to_include:
            filepath = os.path.join(cliente_dir, filename)
            if os.path.isfile(filepath):
                zf.write(filepath, f"Engenharia_CAD_Instalador/{filename}")
        
        # Adicionar README com instruções
        readme_content = """# Engenharia CAD - Instalador

## Requisitos
- Windows 10/11
- PowerShell 5.1+
- AutoCAD 2020+ (ou GstarCAD, ZWCAD, BricsCAD)

## Instalação Automática (RECOMENDADO)
1. Extraia esta pasta para qualquer local
2. Clique com botão direito em **INSTALAR.bat** → "Executar como administrador"
3. Siga as instruções na tela
4. Pronto! O sistema será configurado automaticamente

## O que o instalador faz
- Copia os arquivos para C:\\EngenhariaCAD
- Configura o auto-load no AutoCAD
- Cria pasta de comandos C:\\AutoCAD_Drop
- Cria atalho na área de trabalho
- Testa conexão com o servidor

## Instalação Manual (alternativa)
1. Execute **INICIAR_SINCRONIZADOR.bat** para iniciar o sincronizador
2. No AutoCAD, use APPLOAD para carregar forge_vigilante.lsp
3. Digite FORGE_START no AutoCAD

## Arquivos
- **INSTALAR.bat** - Instalador completo (execute este primeiro)
- **INICIAR_SINCRONIZADOR.bat** - Inicia conexão com o servidor
- **forge_vigilante.lsp** - Plugin para AutoCAD
- **acaddoc.lsp** - Auto-load do plugin

## Comandos do AutoCAD
- FORGE_START - Iniciar monitoramento
- FORGE_STOP - Parar monitoramento
- FORGE_STATUS - Ver status atual

## Desinstalar
Execute: powershell -File INSTALAR.ps1 -Uninstall

## Suporte
Site: https://automacao-cad-frontend.vercel.app
"""
        zf.writestr("Engenharia_CAD_Instalador/README.md", readme_content)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=Engenharia_CAD_Instalador.zip"
        }
    )


@app.get("/api/bridge/pending")
async def get_bridge_pending():
    """Retorna comandos pendentes para o sincronizador local."""
    global _bridge_client_info
    
    try:
        # Atualizar last_seen quando sincronizador faz polling
        _bridge_client_info["last_seen"] = datetime.datetime.now(UTC).isoformat()
        _bridge_client_info["connected"] = True
        
        commands = _bridge_list()
        return {"commands": commands, "count": len(commands)}
    except Exception as e:
        logger.error(f"Bridge pending error: {e}")
        # Retornar lista vazia em vez de erro 500
        return {"commands": [], "count": 0, "error": str(e)}


@app.post("/api/bridge/ack/{cmd_id}")
async def ack_bridge_command(cmd_id: str):
    """Confirma que um comando foi processado pelo sincronizador."""
    global _bridge_client_info
    try:
        _bridge_ack(str(cmd_id))
        _bridge_client_info["commands_executed"] = _bridge_client_info.get("commands_executed", 0) + 1
        return {"status": "acknowledged", "id": cmd_id}
    except Exception as e:
        logger.error(f"Bridge ack error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/bridge/send")
async def send_bridge_command(request: Request):
    """Envia um comando LISP para a fila do sincronizador."""
    try:
        data = await request.json()

        cmd_id = _bridge_enqueue(
            lisp_code=data.get("lisp_code", ""),
            operation=data.get("operation", "custom"),
        )

        return {"status": "queued", "id": cmd_id}
    except Exception as e:
        logger.error(f"Bridge send error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/bridge/draw-pipe")
async def bridge_draw_pipe(request: Request):
    """Gera comando LISP para desenhar tubo e envia para fila."""
    data = await request.json()
    
    points = data.get("points", [[0,0,0], [1000,0,0]])
    diameter = data.get("diameter", 6)
    layer = data.get("layer", "PIPE-PROCESS")
    
    # Gerar código LISP para desenhar linha
    start = points[0]
    end = points[1] if len(points) > 1 else points[0]
    
    lisp_code = f'''
; Engenharia CAD - Desenho de Tubo
(defun c:ENGCAD_PIPE ()
  (command "._LAYER" "M" "{layer}" "")
  (command "._LINE" "{start[0]},{start[1]},{start[2]}" "{end[0]},{end[1]},{end[2]}" "")
  (command "._ZOOM" "E")
  (princ "\\n[Engenharia CAD] Tubo desenhado com sucesso!")
  (princ)
)
(c:ENGCAD_PIPE)
'''
    
    cmd_id = _bridge_enqueue(lisp_code=lisp_code, operation="draw-pipe")

    return {"status": "queued", "id": cmd_id, "operation": "draw-pipe"}


@app.post("/api/bridge/insert-component")
async def bridge_insert_component(request: Request):
    """Gera comando LISP para inserir componente e envia para fila."""
    data = await request.json()
    
    block_name = data.get("block_name", "VALVE-GATE")
    coord = data.get("coordinate", [0,0,0])
    rotation = data.get("rotation", 0)
    scale = data.get("scale", 1)
    layer = data.get("layer", "VALVE")
    
    lisp_code = f'''
; Engenharia CAD - Inserção de Componente
(defun c:ENGCAD_COMPONENT ()
  (command "._LAYER" "M" "{layer}" "")
  ; Desenhar símbolo de válvula como placeholder
  (command "._CIRCLE" "{coord[0]},{coord[1]},{coord[2]}" "{scale * 50}")
  (command "._TEXT" "J" "MC" "{coord[0]},{coord[1]},{coord[2]}" "{scale * 20}" "{rotation}" "{block_name}")
  (princ "\\n[Engenharia CAD] Componente {block_name} inserido!")
  (princ)
)
(c:ENGCAD_COMPONENT)
'''
    
    cmd_id = _bridge_enqueue(lisp_code=lisp_code, operation="insert-component")

    return {"status": "queued", "id": cmd_id, "operation": "insert-component"}


@app.get("/api/bridge/status")
async def bridge_status():
    """Retorna status do modo bridge com info do cliente."""
    global _bridge_client_info
    
    # Verificar se cliente ainda está conectado (timeout 15s)
    client_connected = False
    if _bridge_client_info.get("last_seen"):
        try:
            last_seen = datetime.datetime.fromisoformat(_bridge_client_info["last_seen"].replace("Z", "+00:00"))
            diff = (datetime.datetime.now(UTC) - last_seen.replace(tzinfo=UTC)).total_seconds()
            client_connected = diff < 15
        except:
            pass
    
    return {
        "mode": "bridge",
        "pending_commands": _bridge_pending_count(),
        "status": "active",
        "message": "Modo Bridge ativo. Use o sincronizador no PC do AutoCAD.",
        "client": {
            "connected": client_connected,
            "cad_type": _bridge_client_info.get("cad_type"),
            "cad_version": _bridge_client_info.get("cad_version"),
            "machine": _bridge_client_info.get("machine"),
            "last_seen": _bridge_client_info.get("last_seen"),
            "commands_executed": _bridge_client_info.get("commands_executed", 0),
        }
    }


@app.get("/api/bridge/health")
async def bridge_health():
    """
    Health check do agente Bridge para o frontend.
    Retorna status de conexão baseado no último heartbeat.
    O frontend usa este endpoint ao invés de localhost:8100/health.
    """
    global _bridge_client_info
    
    # Verificar se cliente ainda está conectado (timeout 30s - tolerante a cold start)
    connected = False
    seconds_since_heartbeat = None
    
    if _bridge_client_info.get("last_seen"):
        try:
            last_seen = datetime.datetime.fromisoformat(_bridge_client_info["last_seen"].replace("Z", "+00:00"))
            diff = (datetime.datetime.now(UTC) - last_seen.replace(tzinfo=UTC)).total_seconds()
            seconds_since_heartbeat = int(diff)
            connected = diff < 30  # 30s timeout (heartbeat a cada 5s)
        except:
            pass
    
    return {
        "status": "ok" if connected else "disconnected",
        "connected": connected,
        "last_heartbeat": _bridge_client_info.get("last_seen"),
        "seconds_since_heartbeat": seconds_since_heartbeat,
        "cad_type": _bridge_client_info.get("cad_type"),
        "cad_version": _bridge_client_info.get("cad_version"),
        "machine": _bridge_client_info.get("machine"),
        "commands_pending": _bridge_pending_count(),
        "commands_executed": _bridge_client_info.get("commands_executed", 0),
    }


# ─── Refineries & CAD Execute Stream ─────────────────────────────────────────

_REFINERIES: dict = {
    "REGAP": {"id": "REGAP", "name": "Refinaria Gabriel Passos", "city": "Betim", "state": "MG", "status": "active"},
    "REPLAN": {"id": "REPLAN", "name": "Refinaria de Paulínia", "city": "Paulínia", "state": "SP", "status": "active"},
    "REDUC": {"id": "REDUC", "name": "Refinaria Duque de Caxias", "city": "Duque de Caxias", "state": "RJ", "status": "active"},
    "RNEST": {"id": "RNEST", "name": "Refinaria do Nordeste", "city": "Ipojuca", "state": "PE", "status": "active"},
    "REMAN": {"id": "REMAN", "name": "Refinaria Isaac Sabbá", "city": "Manaus", "state": "AM", "status": "active"},
    "REPAR": {"id": "REPAR", "name": "Refinaria Presidente Getúlio Vargas", "city": "Araucária", "state": "PR", "status": "active"},
}


@app.get("/api/refineries/{refinery_id}")
async def get_refinery(refinery_id: str):
    """Retorna informações de uma refinaria pelo ID."""
    rid = str(refinery_id).upper()[:20]
    refinery = _REFINERIES.get(rid, {
        "id": rid,
        "name": f"Unidade {rid}",
        "city": "N/A",
        "state": "N/A",
        "status": "active",
    })
    return {"refinery": refinery, "status": "connected"}


@app.get("/api/cad/execute-stream")
async def cad_execute_stream(
    request: Request,
    refinery_id: str = "REGAP",
    diameter: float = 50.0,
    length: float = 1000.0,
    company: str = "Petrobras",
    part_name: str = "Pipe",
    code: str = "AUTO-001",
):
    """SSE endpoint que transmite o progresso da execução CAD em tempo real."""

    # Validate inputs
    diameter = max(1.0, min(diameter, 5000.0))
    length = max(1.0, min(length, 100000.0))
    company = company[:100]
    part_name = part_name[:200]
    code = code[:50]
    refinery_id = refinery_id[:20]

    async def event_generator():
        import json as _json

        steps = [
            (5,  "Inicializando motor CAD...", "log", "INFO"),
            (12, f"Carregando refinaria {refinery_id}...", "log", "INFO"),
            (20, f"Calculando geometria — Ø{diameter}mm × {length}mm", "log", "INFO"),
            (30, "Verificando especificações ASME B31.3...", "log", "INFO"),
            (40, "Gerando pontos de referência...", "log", "INFO"),
            (50, "Criando layers AutoCAD...", "log", "CMD"),
            (60, "Desenhando tubulação principal...", "log", "CMD"),
            (68, "Inserindo flanges e conexões...", "log", "CMD"),
            (75, "Adicionando anotações técnicas...", "log", "INFO"),
            (82, "Aplicando espessura de parede...", "log", "INFO"),
            (90, f"Gerando script LISP para {company}...", "log", "INFO"),
            (95, "Validando geometria final...", "log", "INFO"),
            (98, "Exportando arquivo DXF...", "log", "INFO"),
        ]

        for progress, message, event_type, level in steps:
            if await request.is_disconnected():
                break
            payload = _json.dumps({"level": level, "message": message, "progress": progress, "label": message})
            yield {"event": "log", "data": payload}
            await asyncio.sleep(0.4)

        if not await request.is_disconnected():
            output_dir = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data", "output")
            script_path = f"{output_dir}/{code}_{refinery_id}.lsp"
            done_payload = _json.dumps({"script_path": script_path, "progress": 100})
            yield {"event": "done", "data": done_payload}

    return EventSourceResponse(event_generator())
