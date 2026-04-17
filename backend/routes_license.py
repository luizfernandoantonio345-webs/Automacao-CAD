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

Armazenamento: PostgreSQL/SQLite (persistente, não perde dados em cold starts)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.hwid import validate_hwid
from backend.middleware.rate_limit import rate_limit
from backend.database.db import (
    get_license, create_license, update_license_access,
    delete_license, list_all_licenses, get_user_by_email
)

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
@rate_limit(requests=10, window=60)
async def validate_license(request: Request, req: HWIDValidateRequest):
    """
    Valida se o HWID da máquina corresponde ao registrado para o usuário.

    - Usuário sem HWID registrado → registra automaticamente (primeira ativação)
    - Mesmo HWID → autorizado
    - HWID diferente → BLOQUEADO
    """
    user_entry = get_license(req.username)

    if user_entry is None:
        # Primeiro acesso — registrar máquina no banco de dados
        create_license(req.username, req.hwid)
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
        update_license_access(req.username)
        access_count = user_entry.get("access_count", 0) + 1
        logger.info("Acesso autorizado: %s (acesso #%d)", req.username, access_count)
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
    user_entry = get_license(username)

    # Buscar tier do banco de dados
    tier = "demo"
    try:
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
    deleted = delete_license(username)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    logger.info("Licença resetada: %s", username)
    return {"message": f"Licença de '{username}' resetada. Próximo login registrará nova máquina."}


@router.get("/all")
async def get_all_licenses(request: Request):
    """Lista todas as licenças registradas (admin). Requer autenticação."""
    _require_auth(request)
    licenses = list_all_licenses()

    return {
        "total": len(licenses),
        "licenses": [
            {
                "username": lic["username"],
                "hwid_prefix": lic["hwid"][:8] + "...",
                "registered_at": lic.get("registered_at"),
                "last_seen": lic.get("last_seen"),
                "access_count": lic.get("access_count", 0),
            }
            for lic in licenses
        ],
    }
