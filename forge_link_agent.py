#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — ForgeLink Agent (Proxy de Desenho Local)
Agente leve que roda no PC do cliente com AutoCAD.
NÃO carrega .env / NÃO contém chaves de IA / NÃO acessa LLMs.

Arquitetura Zero Trust:
    Servidor Central (IA + chaves) ──JSON──► ForgeLink Agent ──COM──► AutoCAD
═══════════════════════════════════════════════════════════════════════════════

SEGURANÇA:
    - Este agente é um "Proxy de Desenho". Recebe coordenadas prontas, desenha.
    - Se o cliente descompilar o .exe, verá ZERO chaves secretas.
    - A autenticação é feita via token temporário emitido pelo Servidor Central.
    - Sem .env, sem dotenv, sem variáveis de ambiente sensíveis.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
import time
from typing import Optional

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Importa o driver COM — única dependência pesada
from backend.autocad_driver import acad_driver, DriverStatus
from backend.routes_autocad import router as autocad_router
from backend.routes_autocad import debug_router as autocad_debug_router
from backend.hwid import generate_hwid

# ─── Logging (arquivo local, sem telemetria externa) ────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FORGELINK] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("forgelink")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO ZERO TRUST — Nenhuma chave sensível aqui
# ═══════════════════════════════════════════════════════════════════════════════

# Porta do agente local (não conflita com o Servidor Central na 8000)
AGENT_PORT = int(os.getenv("FORGELINK_PORT", "8100"))

# URL do Servidor Central (configurável, mas NÃO é um secret)
CENTRAL_SERVER_URL = os.getenv(
    "FORGELINK_CENTRAL_URL", "http://localhost:8000"
)

# HWID desta máquina (gerado uma vez na inicialização)
MACHINE_HWID = generate_hwid()

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE TOKEN — Aceita tokens assinados pelo Servidor Central
# ═══════════════════════════════════════════════════════════════════════════════

# O agente NÃO conhece a chave de assinatura. Ele valida o token
# chamando o Servidor Central via /ai/health (handshake de confiança).
# Em produção, pode-se usar JWT com chave pública (RS256) sem expor a privada.

_authorized_sessions: dict[str, float] = {}
SESSION_TTL_S = 3600  # 1 hora


def _is_session_valid(token: str) -> bool:
    """Verifica se o token já foi validado e não expirou."""
    ts = _authorized_sessions.get(token)
    if ts and (time.time() - ts) < SESSION_TTL_S:
        return True
    _authorized_sessions.pop(token, None)
    return False


def _register_session(token: str) -> None:
    """Registra um token validado pelo Servidor Central."""
    # Limpa sessões expiradas para evitar crescimento
    now = time.time()
    expired = [k for k, v in _authorized_sessions.items() if now - v > SESSION_TTL_S]
    for k in expired:
        del _authorized_sessions[k]
    _authorized_sessions[token] = now


# ═══════════════════════════════════════════════════════════════════════════════
# APLICAÇÃO FASTAPI — Agente Leve
# ═══════════════════════════════════════════════════════════════════════════════

agent_app = FastAPI(
    title="ForgeLink Agent",
    description="Proxy de Desenho Local — AutoCAD COM Driver",
    version="1.0.0",
)

agent_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Aceita do Servidor Central em qualquer IP da LAN
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-ForgeLink-Token"],
)


# ─── Middleware de Autenticação Leve ─────────────────────────────────────────

@agent_app.middleware("http")
async def verify_forgelink_token(request: Request, call_next):
    """
    Valida que a requisição vem do Servidor Central.
    Rotas de health são públicas para monitoramento.
    """
    path = request.url.path
    # Health/status são públicos (monitoramento)
    if path in ("/health", "/", "/handshake", "/api/autocad/health", "/api/autocad/status"):
        return await call_next(request)

    token = request.headers.get("X-ForgeLink-Token", "")
    if not token:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Token ForgeLink ausente")

    if not _is_session_valid(token):
        # Valida contra Servidor Central (primeiro uso)
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{CENTRAL_SERVER_URL}/ai/health",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    _register_session(token)
                else:
                    raise HTTPException(status_code=403, detail="Token rejeitado pelo Servidor Central")
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Servidor Central indisponível para validação",
            )

    return await call_next(request)


# ─── Rotas do Agente ─────────────────────────────────────────────────────────

# Monta todas as rotas do AutoCAD Driver
agent_app.include_router(autocad_router)
agent_app.include_router(autocad_debug_router)


@agent_app.get("/health")
def agent_health():
    """Health check do agente — público, sem autenticação."""
    from agent.cad_manager import build_default_manager
    manager = build_default_manager()
    status = manager.status()
    driver_info = acad_driver.health_check()
    return {
        "agent": "ForgeLink",
        "version": "1.0.0",
        "status": "online",
        "port": AGENT_PORT,
        "cad_manager": status,
        "autocad_driver": driver_info,
        "hwid_prefix": MACHINE_HWID[:8] + "...",
        "system": {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
        },
    }


@agent_app.get("/")
def agent_root():
    """Página raiz — identifica o agente."""
    return {
        "name": "ForgeLink Agent — Proxy de Desenho",
        "description": "Agente local para execução direta no AutoCAD via COM",
        "security": "Zero Trust — sem chaves de IA armazenadas",
        "hwid_prefix": MACHINE_HWID[:8] + "...",
        "docs": f"http://localhost:{AGENT_PORT}/docs",
    }


class HandshakeRequest(BaseModel):
    """Dados para handshake com o Servidor Central."""
    username: str
    password: str


@agent_app.post("/handshake")
async def agent_handshake(data: HandshakeRequest):
    """
    Faz login no Servidor Central enviando credenciais + HWID desta máquina.
    Retorna o token JWT para uso nas requisições subsequentes.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CENTRAL_SERVER_URL}/login",
                json={
                    "username": data.username,
                    "password": data.password,
                    "hwid": MACHINE_HWID,
                },
            )
            if resp.status_code == 200:
                payload = resp.json()
                token = payload.get("token", "")
                if token:
                    _register_session(token)
                return {
                    "status": "authorized",
                    "token": token,
                    "hwid_registered": payload.get("hwid_registered", False),
                    "hwid_prefix": MACHINE_HWID[:8] + "...",
                }
            else:
                detail = resp.json().get("detail", "Falha no login")
                raise HTTPException(status_code=resp.status_code, detail=detail)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Servidor Central indisponível",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Inicia o ForgeLink Agent."""
    print("=" * 70)
    print("  Engenharia CAD — ForgeLink Agent v1.0")
    print("  Proxy de Desenho Local (Zero Trust)")
    print(f"  Porta: {AGENT_PORT}")
    print(f"  Servidor Central: {CENTRAL_SERVER_URL}")
    print(f"  HWID: {MACHINE_HWID[:8]}...{MACHINE_HWID[-8:]}")
    print("=" * 70)
    print()
    print("  SEGURANÇA: Nenhuma chave de IA armazenada neste agente.")
    print("  O agente recebe coordenadas prontas e desenha no AutoCAD.")
    print()

    # Tentar conectar ao AutoCAD na inicialização
    result = acad_driver.connect()
    if result.success:
        print(f"  AutoCAD: {result.message}")
    else:
        print(f"  AutoCAD: {result.message} (modo simulação ativo)")

    print()
    print(f"  Acesse: http://localhost:{AGENT_PORT}/docs")
    print("=" * 70)

    uvicorn.run(
        agent_app,
        host="0.0.0.0",
        port=AGENT_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
