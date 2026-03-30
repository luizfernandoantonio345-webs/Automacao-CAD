from __future__ import annotations

import hashlib
import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_ROOT = PROJECT_ROOT / "engenharia_automacao"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from engenharia_automacao.app.auth import LicenseError
from engenharia_automacao.core.validations.validator import ValidationError

from integration.python_api.config import AppConfig
from integration.python_api.dependencies import (
    CONFIG,
    get_api_logger,
    get_app_config,
    get_auth_service,
    get_current_user,
    get_log_file,
    get_output_dir,
    get_project_service,
    get_telemetry_store,
    issue_token,
)
from integration.python_api.routes_auth import router as auth_router
from integration.python_api.routes_factory import router as factory_router
from integration.python_api.routes_mecanica import router as mecanica_router
from integration.python_api.routes_projects import router as project_router
from integration.python_api.routes_jobs import router as jobs_router
from integration.python_api.schemas import DemoLoginResponse, GenerateRequest, LoginRequest, RegisterRequest
from engenharia_automacao.app.routes_cad import router as cad_router


AUTH_SECRET = CONFIG.auth_secret
TOKEN_TTL_SECONDS = CONFIG.token_ttl_seconds
RATE_LIMIT_WINDOW_SECONDS = CONFIG.rate_limit_window_seconds
RATE_LIMIT_MAX_REQUESTS = CONFIG.rate_limit_max_requests
MAX_EXCEL_UPLOAD_BYTES = CONFIG.max_excel_upload_bytes
MAX_AUTOCAD_RETRIES = CONFIG.max_autocad_retries
DATA_DIR = CONFIG.data_dir
OUTPUT_DIR = CONFIG.output_dir
LOG_FILE = CONFIG.log_file

app = FastAPI(title="Engenharia Automacao API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(jobs_router)
app.include_router(mecanica_router)
app.include_router(factory_router)
app.include_router(cad_router)

_rate_limit_lock = threading.Lock()
_request_history: dict[str, deque[float]] = defaultdict(deque)


def _enforce_rate_limit(client_ip: str, config: AppConfig = CONFIG) -> None:
    now = time.time()
    with _rate_limit_lock:
        bucket = _request_history[client_ip]
        while bucket and now - bucket[0] > config.rate_limit_window_seconds:
            bucket.popleft()
        if len(bucket) >= config.rate_limit_max_requests:
            raise HTTPException(status_code=429, detail="Limite de requisicoes excedido")
        bucket.append(now)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or hashlib.md5(
        f"{time.time()}-{id(request)}".encode("utf-8")
    ).hexdigest()[:12]
    request.state.request_id = request_id
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)
    start = time.time()
    try:
        response = await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:
        get_api_logger().error("request_id=%s endpoint=%s erro_nao_tratado=%s", request_id, request.url.path, exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Erro interno", "request_id": request_id})
    elapsed_ms = int((time.time() - start) * 1000)
    get_api_logger().info(
        "request_id=%s method=%s path=%s status=%s elapsed_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, exc: ValidationError):
    get_api_logger().warning("request_id=%s erro_validacao=%s", getattr(request.state, "request_id", "n/a"), exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(LicenseError)
async def handle_license_error(request: Request, exc: LicenseError):
    get_api_logger().warning("request_id=%s erro_licenca=%s", getattr(request.state, "request_id", "n/a"), exc)
    return JSONResponse(status_code=403, content={"detail": str(exc)})


__all__ = [
    "AUTH_SECRET",
    "CONFIG",
    "DATA_DIR",
    "DemoLoginResponse",
    "GenerateRequest",
    "LOG_FILE",
    "LoginRequest",
    "MAX_AUTOCAD_RETRIES",
    "MAX_EXCEL_UPLOAD_BYTES",
    "OUTPUT_DIR",
    "RATE_LIMIT_MAX_REQUESTS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "RegisterRequest",
    "TOKEN_TTL_SECONDS",
    "app",
    "get_app_config",
    "get_auth_service",
    "get_current_user",
    "get_log_file",
    "get_output_dir",
    "get_project_service",
    "get_telemetry_store",
    "issue_token",
]
