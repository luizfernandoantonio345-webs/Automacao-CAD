#!/usr/bin/env python3
"""
backend/routes_agent_download.py
---------------------------------
FastAPI endpoint: GET /api/agent/download
Serve o script SINCRONIZADOR.ps1 para download, com hash SHA-256 e metadados.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger("engcad.agent_download")

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Caminho canônico do script do agente — relativo à raiz do projeto
_AGENT_SCRIPT = Path(__file__).resolve().parent.parent / "AutoCAD_Cliente" / "SINCRONIZADOR.ps1"


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


@router.get("/download", summary="Baixar script do agente CAD")
def download_agent(meta: bool = Query(False, description="Se true, retorna metadados JSON em vez do arquivo")):
    """
    Serve o SINCRONIZADOR.ps1 para instalação automática nos clientes.

    - `meta=false` (padrão): retorna o arquivo `.ps1` para download.
    - `meta=true`: retorna JSON com `filename`, `sha256`, `size_bytes` e `version`.
    """
    script_path = _AGENT_SCRIPT
    if not script_path.exists():
        logger.error("Agent script not found at %s", script_path)
        raise HTTPException(status_code=404, detail="Arquivo do agente não encontrado no servidor.")

    sha256 = _sha256_of(script_path)
    size = script_path.stat().st_size

    if meta:
        return JSONResponse({
            "filename": script_path.name,
            "sha256": sha256,
            "size_bytes": size,
            "version": os.environ.get("AGENT_VERSION", "latest"),
        })

    return FileResponse(
        path=str(script_path),
        media_type="application/octet-stream",
        filename="SINCRONIZADOR.ps1",
        headers={
            "X-SHA256": sha256,
            "X-File-Size": str(size),
            "Cache-Control": "no-store",
        },
    )
