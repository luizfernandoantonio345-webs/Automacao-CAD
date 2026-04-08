#!/usr/bin/env python3
"""
Engenharia CAD — Rotas de Licenciamento por Máquina (HWID)
Endpoints do Servidor Central para registro e validação de hardware.

Fluxo:
    1. Agente Local gera HWID → envia no login
    2. Servidor Central verifica:
       - Usuário novo? Registra o HWID
       - Mesmo HWID? Autorizado
       - HWID diferente? BLOQUEADO (máquina não autorizada)
    3. Servidor retorna token de sessão se aprovado
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.hwid import validate_hwid

logger = logging.getLogger("engcad.license")

router = APIRouter(prefix="/api/license", tags=["license"])


def _require_auth(request: Request) -> str:
    """Extrai e valida JWT do header Authorization. Retorna email do usuário."""
    import jwt as _jwt
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = auth_header[7:]
    secret = os.getenv("JARVIS_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Configuração de segurança ausente")
    try:
        payload = _jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("user", "")
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except _jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ═══════════════════════════════════════════════════════════════════════════════
# STORE DE LICENÇAS — Arquivo JSON simples (produção usaria banco de dados)
# ═══════════════════════════════════════════════════════════════════════════════

_LICENSE_FILE = Path("/tmp/licenses.json") if os.getenv("VERCEL") else Path(__file__).parent.parent / "data" / "licenses.json"
_LICENSE_LOCK = threading.Lock()


def _load_licenses() -> dict:
    """Carrega o registro de licenças do disco."""
    if not _LICENSE_FILE.exists():
        return {}
    try:
        return json.loads(_LICENSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_licenses(data: dict) -> None:
    """Persiste o registro de licenças no disco."""
    _LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LICENSE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class HWIDRegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    hwid: str = Field(..., min_length=64, max_length=64, description="SHA-256 hex do hardware")


class HWIDValidateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    hwid: str = Field(..., min_length=64, max_length=64)


class LicenseStatusResponse(BaseModel):
    authorized: bool
    username: str
    machine_registered: bool
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/validate", response_model=LicenseStatusResponse)
async def validate_license(req: HWIDValidateRequest):
    """
    Valida se o HWID da máquina corresponde ao registrado para o usuário.

    - Usuário sem HWID registrado → registra automaticamente (primeira ativação)
    - Mesmo HWID → autorizado
    - HWID diferente → BLOQUEADO
    """
    with _LICENSE_LOCK:
        licenses = _load_licenses()
        user_entry = licenses.get(req.username)

        if user_entry is None:
            # Primeiro acesso — registrar máquina
            licenses[req.username] = {
                "hwid": req.hwid,
                "registered_at": time.time(),
                "last_seen": time.time(),
                "access_count": 1,
            }
            _save_licenses(licenses)
            logger.info("Nova licença registrada: %s (HWID: %s...)", req.username, req.hwid[:8])
            return LicenseStatusResponse(
                authorized=True,
                username=req.username,
                machine_registered=True,
                message="Licença ativada com sucesso nesta máquina.",
            )

        # Usuário existe — comparar HWID
        stored_hwid = user_entry.get("hwid", "")

        if validate_hwid(stored_hwid, req.hwid):
            # Mesmo hardware — autorizado
            user_entry["last_seen"] = time.time()
            user_entry["access_count"] = user_entry.get("access_count", 0) + 1
            _save_licenses(licenses)
            logger.info("Acesso autorizado: %s (acesso #%d)", req.username, user_entry["access_count"])
            return LicenseStatusResponse(
                authorized=True,
                username=req.username,
                machine_registered=True,
                message="Acesso autorizado.",
            )

        # HWID diferente — BLOQUEADO
        logger.warning(
            "ACESSO NEGADO: %s tentou acessar de máquina diferente (esperado: %s..., recebido: %s...)",
            req.username, stored_hwid[:8], req.hwid[:8],
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: Este computador não está autorizado para esta licença. "
                   "Contate o administrador para transferir a licença.",
        )


@router.get("/status/{username}")
async def license_status(username: str, request: Request):
    """Retorna informações da licença de um usuário (admin)."""
    _require_auth(request)
    with _LICENSE_LOCK:
        licenses = _load_licenses()
        user_entry = licenses.get(username)

    # Buscar tier do banco de dados
    tier = "demo"
    try:
        from backend.database.db import get_user_by_email
        user = get_user_by_email(username)
        if user:
            tier = user.get("tier", "demo")
    except Exception:
        pass

    if not user_entry:
        return {
            "username": username,
            "tier": tier,
            "hwid_prefix": None,
            "registered_at": None,
            "last_seen": None,
            "access_count": 0,
        }

    return {
        "username": username,
        "tier": tier,
        "hwid_prefix": user_entry["hwid"][:8] + "...",
        "registered_at": user_entry.get("registered_at"),
        "last_seen": user_entry.get("last_seen"),
        "access_count": user_entry.get("access_count", 0),
    }


@router.post("/reset/{username}")
async def reset_license(username: str, request: Request):
    """
    Remove o HWID registrado de um usuário (para transferência de máquina).
    Requer autenticação.
    """
    _require_auth(request)
    with _LICENSE_LOCK:
        licenses = _load_licenses()
        if username not in licenses:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        del licenses[username]
        _save_licenses(licenses)

    logger.info("Licença resetada: %s", username)
    return {"message": f"Licença de '{username}' resetada. Próximo login registrará nova máquina."}


@router.get("/all")
async def list_all_licenses(request: Request):
    """Lista todas as licenças registradas (admin). Requer autenticação."""
    _require_auth(request)
    with _LICENSE_LOCK:
        licenses = _load_licenses()

    return {
        "total": len(licenses),
        "licenses": [
            {
                "username": k,
                "hwid_prefix": v["hwid"][:8] + "...",
                "registered_at": v.get("registered_at"),
                "last_seen": v.get("last_seen"),
                "access_count": v.get("access_count", 0),
            }
            for k, v in licenses.items()
        ],
    }
