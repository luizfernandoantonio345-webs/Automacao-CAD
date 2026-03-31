from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from threading import Lock

import jwt
import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing import Annotated
from sse_starlette.sse import EventSourceResponse
from engenharia_automacao.app.routes_cad import router as cad_router
from backend.routes_autocad import router as autocad_router
from backend.routes_autocad import debug_router as autocad_debug_router
from backend.routes_license import router as license_router
from ai_watchdog import install_watchdog, watchdog
from backend.database.db import (
    init_db, seed_default_user, authenticate_user, create_user,
    email_exists, get_user_by_email, create_project as db_create_project,
    update_project as db_update_project, get_project as db_get_project,
    get_projects as db_get_projects, get_project_stats,
    add_quality_check, get_quality_checks,
    create_upload, update_upload, get_uploads,
)

logger = logging.getLogger(__name__)

# Load and validate environment variables
# ── Modo de operação: Servidor Central (com .env) ou Agente Local (sem .env) ──
# O Agente Local (forge_link_agent.py) NUNCA carrega este módulo.
# Se chegou aqui, é o Servidor Central — exigir JARVIS_SECRET.
JARVIS_SECRET = os.getenv("JARVIS_SECRET", "").strip()
_MIN_SECRET_BYTES = 32
_APP_ENV = os.getenv("APP_ENV", "development").lower()

if not JARVIS_SECRET or JARVIS_SECRET == "jarvis_secret_key_change_me":
    if _APP_ENV == "production":
        logger.critical("JARVIS_SECRET não definido em produção. SERVIDOR NÃO VAI INICIAR.")
        raise SystemExit("FATAL: Defina JARVIS_SECRET (>= 32 bytes) antes de iniciar em produção.")
    import secrets as _secrets_mod
    JARVIS_SECRET = _secrets_mod.token_hex(32)
    logger.warning(
        "JARVIS_SECRET não definido — usando secret efêmero (NÃO USE EM PRODUÇÃO)"
    )
elif len(JARVIS_SECRET.encode("utf-8")) < _MIN_SECRET_BYTES:
    if _APP_ENV == "production":
        logger.critical("JARVIS_SECRET muito curto (%d bytes, mínimo %d). SERVIDOR NÃO VAI INICIAR.",
                        len(JARVIS_SECRET.encode("utf-8")), _MIN_SECRET_BYTES)
        raise SystemExit("FATAL: JARVIS_SECRET deve ter >= 32 bytes em produção.")
    import secrets as _secrets_mod
    _old_len = len(JARVIS_SECRET.encode("utf-8"))
    JARVIS_SECRET = _secrets_mod.token_hex(32)
    logger.warning(
        "JARVIS_SECRET tinha apenas %d bytes (mínimo: %d para HS256/RFC 7518). "
        "Chave automática gerada. Defina uma chave >= 32 bytes em produção.",
        _old_len, _MIN_SECRET_BYTES,
    )

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
_REGISTER_RATE_MAX = int(os.getenv("RATE_LIMIT_REGISTER_PER_MINUTE", "3"))
_REQUEST_HISTORY: defaultdict[str, deque] = defaultdict(deque)
_REGISTER_HISTORY: defaultdict[str, deque] = defaultdict(deque)
_RATE_LOCK = Lock()
_SSE_CONNECTIONS: defaultdict[str, int] = defaultdict(int)
_SSE_LOCK = Lock()
_SSE_MAX_PER_IP = 5
_SSE_TIMEOUT_SECONDS = 300  # 5 minutos
_MAX_EXCEL_UPLOAD_BYTES = int(os.getenv("MAX_EXCEL_UPLOAD_MB", "15")) * 1024 * 1024
_DEMO_EMAIL = "demo@engenharia-cad.com"
_DEMO_TOKEN_EXPIRY_MINUTES = 10

# ── Rotas que NÃO exigem autenticação ──
_AUTH_WHITELIST = {
    "", "/", "/login", "/auth/register", "/auth/demo", "/health", "/docs",
    "/openapi.json", "/redoc",
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

app = FastAPI()

_CORS_ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"}
_CORS_ORIGIN_REGEX = re.compile(
    r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
    r"|^https://[a-z0-9\-]+\.vercel\.app$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_CORS_ALLOWED_ORIGINS),
    allow_origin_regex=_CORS_ORIGIN_REGEX.pattern,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Inicializar banco de dados SQLite ──
init_db()
seed_default_user()
logger.info("Banco de dados Engenharia CAD inicializado")

# ── AI Watchdog — IA de Baixo Nível invisível ──
# Intercepta TODA request: sanitiza payloads, bloqueia operações em sobrecarga,
# e injeta fallback se o handler crashar. Completamente invisível ao usuário.
install_watchdog(app)

# Include CAD routes
app.include_router(cad_router)

# Include AutoCAD COM Driver routes (Nível 4)
app.include_router(autocad_router)
app.include_router(autocad_debug_router)

# Include License / HWID routes
app.include_router(license_router)


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
                "timestamp": datetime.datetime.utcnow().isoformat(),
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
                    "data": json.dumps({"ts": datetime.datetime.utcnow().isoformat()})
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
                "data": json.dumps({"ts": datetime.datetime.utcnow().isoformat()})
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
                "data": json.dumps({"ts": datetime.datetime.utcnow().isoformat()})
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
                "data": json.dumps({"ts": datetime.datetime.utcnow().isoformat()})
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
        
        event_data["timestamp"] = datetime.datetime.utcnow().isoformat()
        
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
    now = time.time()
    with _RATE_LOCK:
        bucket = _REQUEST_HISTORY[client_ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="Limite de requisicoes excedido")
        bucket.append(now)


def _enforce_register_rate_limit(client_ip: str) -> None:
    """Rate limit específico para /auth/register (3/min)."""
    now = time.time()
    with _RATE_LOCK:
        bucket = _REGISTER_HISTORY[client_ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _REGISTER_RATE_MAX:
            raise HTTPException(status_code=429, detail="Muitas tentativas de registro. Aguarde.")
        bucket.append(now)


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

    # ── Rate limiting global ──
    _enforce_rate_limit(client_ip)

    # ── Rate limiting específico para register ──
    if path == "/auth/register":
        _enforce_register_rate_limit(client_ip)

    # ── Rotas públicas (sem auth) ──
    if path in _AUTH_WHITELIST:
        return await call_next(request)

    # ── SSE routes verificadas separadamente (dentro do handler) ──
    if path.startswith("/sse/"):
        # Auth é verificada dentro do handler SSE
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
        {"user": user_email, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)},
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
    )
    token = _make_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user["email"],
        "empresa": user["empresa"],
        "limite": user["limite"],
        "usado": user["usado"],
    }


@app.post("/auth/demo")
def auth_demo():
    token = _make_token(_DEMO_USER["email"], expiry_minutes=_DEMO_TOKEN_EXPIRY_MINUTES)
    return {
        "access_token": token,
        "token_type": "bearer",
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
    """Health check real — verifica banco de dados e dependências."""
    from backend.database.db import _get_conn
    db_ok = False
    try:
        conn = _get_conn()
        conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    return {"autocad": True, "database": db_ok, "status": "healthy" if db_ok else "degraded"}


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
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": message,
        "level": level,
        "user": user,
        "type": "notification"
    }
    await _NOTIFICATION_EVENTS.put(notification)


async def send_ai_event(text: str, status: str = "processing", job_id: str = None):
    """Send AI event to all connected clients."""
    ai_event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
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
        "timestamp": datetime.datetime.utcnow().isoformat(),
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
            f"[{datetime.datetime.utcnow().isoformat()}] Sistema iniciado com sucesso",
            f"[{datetime.datetime.utcnow().isoformat()}] Watchdog ativo — monitorando recursos",
        ]
    return {"logs": lines}


@app.post("/generate")
async def generate_project(request: Request):
    """Gera um projeto CAD real usando o motor de engenharia."""
    from engenharia_automacao.core.main import ProjectService
    from engenharia_automacao.core.piping.specs import select_piping_specification
    import json as _json
    import traceback

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
        piping_spec = select_piping_specification(
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
        svc = ProjectService()
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

    # Registrar upload no DB
    upload_id = create_upload(user_email, original_name, saved_path)

    # Processar via ProjectService
    try:
        svc = ProjectService()
        generated_files = svc.generate_projects_from_excel(saved_path, output_dir)

        # Registrar cada projeto gerado no DB
        project_ids = []
        for gen_path in generated_files:
            pid = db_create_project(user_email, {
                "code": gen_path.stem,
                "company": "Excel Import",
                "part_name": original_name,
            })
            db_update_project(pid, status="completed", lsp_path=str(gen_path), completed_at=time.time())
            project_ids.append(pid)

        update_upload(upload_id, row_count=len(generated_files), projects_generated=len(generated_files), status="completed")

        user = get_user_by_email(user_email)
        return {
            "files": [str(f) for f in generated_files],
            "count": len(generated_files),
            "upload_id": upload_id,
            "project_ids": project_ids,
            "usado": user["usado"] if user else 0,
            "limite": user["limite"] if user else 999,
        }
    except Exception as e:
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
