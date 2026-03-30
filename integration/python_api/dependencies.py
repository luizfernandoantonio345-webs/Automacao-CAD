from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import sys
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

from fastapi import Depends, Header, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_ROOT = PROJECT_ROOT / "engenharia_automacao"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from engenharia_automacao.app.auth import AuthService
from engenharia_automacao.core.main import ProjectService

from integration.python_api.config import AppConfig, load_config
from integration.python_api.cache import init_cache
from integration.python_api.async_jobs import get_job_manager, init_job_manager
from integration.python_api.autopilot import AutopilotService
from integration.python_api.json_repositories import (
    JSONDraftFeedbackRepository,
    JSONProjectEventRepository,
    JSONProjectStatsRepository,
    JSONUserRepository,
)
from integration.python_api.repository_config import create_repositories
from integration.python_api.telemetry import ProjectTelemetryStore


CONFIG = load_config()

# Initialize cache
_cache_client = init_cache(CONFIG.redis_url, CONFIG.cache_ttl_seconds)

# Initialize job manager
_job_manager = init_job_manager(CONFIG.jobs_redis_url)

# Create repositories based on configuration
_USER_REPO, _EVENT_REPO, _FEEDBACK_REPO, _STATS_REPO = create_repositories(CONFIG)

_APP_SERVICE = ProjectService()
_AUTH_SERVICE = AuthService(user_repository=_USER_REPO)
_AUTH_SERVICE.migrate_plaintext_passwords()
_AUTOPILOT_SERVICE = AutopilotService(CONFIG.database_url, CONFIG.output_dir)


def _is_default_runtime_config(config: AppConfig) -> bool:
    return config.data_dir == CONFIG.data_dir and config.database_url == CONFIG.database_url


def _build_local_json_repositories(config: AppConfig):
    telemetry_dir = config.data_dir / "telemetry"
    users_file = config.data_dir / "users.json"
    events_file = telemetry_dir / "project_events.jsonl"
    feedback_file = telemetry_dir / "draft_feedback.jsonl"
    stats_file = telemetry_dir / "project_stats.json"

    return (
        JSONUserRepository(users_file),
        JSONProjectEventRepository(events_file),
        JSONDraftFeedbackRepository(feedback_file),
        JSONProjectStatsRepository(stats_file),
    )


def _get_repository_bundle(config: AppConfig):
    if _is_default_runtime_config(config):
        return _USER_REPO, _EVENT_REPO, _FEEDBACK_REPO, _STATS_REPO
    return _build_local_json_repositories(config)


def build_logger(log_file: Path) -> logging.Logger:
    logger_name = f"engenharia_automacao.api.{hash(str(log_file.resolve()))}"
    api_logger = logging.getLogger(logger_name)
    if not api_logger.handlers:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s"))
        api_logger.addHandler(handler)
        api_logger.setLevel(logging.INFO)
        api_logger.propagate = False
    return api_logger


def get_app_config() -> AppConfig:
    return CONFIG


def get_auth_service(config: AppConfig = Depends(get_app_config)) -> AuthService:
    if _is_default_runtime_config(config):
        return _AUTH_SERVICE
    user_repo, _, _, _ = _get_repository_bundle(config)
    return AuthService(user_repository=user_repo)


def get_project_service() -> ProjectService:
    return _APP_SERVICE


def get_autopilot_service(config: AppConfig = Depends(get_app_config)) -> AutopilotService:
    if _is_default_runtime_config(config):
        return _AUTOPILOT_SERVICE
    return AutopilotService(config.database_url, config.output_dir)


def get_api_logger(config: AppConfig | None = None) -> logging.Logger:
    resolved_config = config or CONFIG
    return build_logger(resolved_config.log_file)


def get_output_dir(config: AppConfig = Depends(get_app_config)) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    return config.output_dir


def get_log_file(config: AppConfig = Depends(get_app_config)) -> Path:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    return config.log_file


def get_telemetry_store(config: AppConfig = Depends(get_app_config)) -> ProjectTelemetryStore:
    _, event_repo, feedback_repo, stats_repo = _get_repository_bundle(config)
    telemetry_dir = config.data_dir / "telemetry"
    return ProjectTelemetryStore(
        telemetry_dir,
        event_repository=event_repo,
        feedback_repository=feedback_repo,
        stats_repository=stats_repo,
        cache_client=_cache_client,
    )


def issue_token(email: str, config: AppConfig = CONFIG) -> str:
    expires = int(time.time()) + config.token_ttl_seconds
    payload = f"{email}|{expires}"
    signature = hmac.new(config.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}|{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def decode_token(token: str, config: AppConfig = CONFIG) -> dict:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        email, expires_str, signature = decoded.split("|", 2)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token invalido") from exc

    expected_payload = f"{email}|{expires_str}"
    expected_signature = hmac.new(
        config.auth_secret.encode("utf-8"),
        expected_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Token invalido")
    if int(expires_str) < int(time.time()):
        raise HTTPException(status_code=401, detail="Sessao expirada")
    return {"email": email}


def extract_token(auth_header: str | None) -> str:
    if not auth_header:
        raise HTTPException(status_code=401, detail="Token ausente")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token invalido")
    token = auth_header[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token ausente")
    return token


def get_cache_client():
    return _cache_client


def get_job_manager():
    return _job_manager


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
    config: AppConfig = Depends(get_app_config),
) -> dict:
    token = extract_token(authorization)
    payload = decode_token(token, config)
    if payload["email"] == "public@system.com":
        return {
            "email": "public@system.com",
            "empresa": "Usuario Publico",
            "limite": 100,
            "usado": 0,
        }
    user = auth_service.find_user_by_email(payload["email"])
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user
