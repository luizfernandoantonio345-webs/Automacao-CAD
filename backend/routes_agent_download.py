#!/usr/bin/env python3
"""
backend/routes_agent_download.py
---------------------------------
Endpoints para download e instalação do agente AutoCAD:
  GET /api/agent/download    - Baixa SINCRONIZADOR.ps1
  GET /api/agent/install     - Retorna script de instalação rápida
  GET /api/agent/installer   - Baixa INSTALAR_SILENCIOSO.bat
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

logger = logging.getLogger("engcad.agent_download")

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Caminhos dos arquivos do agente
_BASE_DIR = Path(__file__).resolve().parent.parent / "AutoCAD_Cliente"
_AGENT_SCRIPT = _BASE_DIR / "SINCRONIZADOR.ps1"
_INSTALLER_BAT = _BASE_DIR / "INSTALAR_SILENCIOSO.bat"
_INSTALLER_INTERACTIVE = _BASE_DIR / "INSTALAR_AGENTE.bat"


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


@router.get("/installer", summary="Baixar instalador BAT")
def download_installer(
    mode: str = Query("silent", description="Modo: 'silent' ou 'interactive'")
):
    """
    Serve o instalador BAT para download.
    
    - `mode=silent`: INSTALAR_SILENCIOSO.bat (automático)
    - `mode=interactive`: INSTALAR_AGENTE.bat (com prompts)
    """
    if mode == "interactive":
        installer_path = _INSTALLER_INTERACTIVE
        filename = "INSTALAR_AGENTE.bat"
    else:
        installer_path = _INSTALLER_BAT
        filename = "INSTALAR_SILENCIOSO.bat"
    
    if not installer_path.exists():
        raise HTTPException(status_code=404, detail=f"Instalador não encontrado: {filename}")
    
    return FileResponse(
        path=str(installer_path),
        media_type="application/x-batch",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/install", summary="Comando de instalação rápida")
def get_install_command(
    start: bool = Query(True, description="Iniciar agente após instalação"),
    desktop: bool = Query(True, description="Criar atalho na área de trabalho"),
):
    """
    Retorna um comando PowerShell one-liner para instalação rápida.
    Cole no CMD ou PowerShell para instalar automaticamente.
    """
    backend_url = os.environ.get("BACKEND_URL", "https://automacao-cad-backend.vercel.app")
    github_raw = "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"
    
    # Comando PowerShell compacto
    ps_command = f'''[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$d="$env:USERPROFILE\\EngCAD-Agente"
md $d -Force|Out-Null
$wc=New-Object Net.WebClient
$wc.Encoding=[Text.Encoding]::UTF8
try{{$c=$wc.DownloadString('{backend_url}/api/agent/download')}}catch{{$c=$wc.DownloadString('{github_raw}/SINCRONIZADOR.ps1')}}
[IO.File]::WriteAllText("$d\\SINCRONIZADOR.ps1",$c,[Text.Encoding]::UTF8)
Write-Host "Instalado em: $d" -ForegroundColor Green'''
    
    if desktop:
        ps_command += '''
$bat="@echo off`nstart `"`" powershell -NoProfile -ExecutionPolicy Bypass -File `"$d\\SINCRONIZADOR.ps1`""
[IO.File]::WriteAllText("$env:USERPROFILE\\Desktop\\EngCAD Agente.bat",$bat)
Write-Host "Atalho criado na area de trabalho" -ForegroundColor Cyan'''
    
    if start:
        ps_command += '''
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$d\\SINCRONIZADOR.ps1"'''
    
    # Versão one-liner para CMD
    one_liner = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{ps_command.replace(chr(10), "; ")}"'
    
    return JSONResponse({
        "cmd_oneliner": one_liner,
        "powershell": ps_command,
        "usage": {
            "cmd": "Cole o valor de 'cmd_oneliner' no Prompt de Comando (CMD)",
            "powershell": "Cole o valor de 'powershell' no PowerShell",
        },
        "options": {
            "start": start,
            "desktop": desktop,
        }
    })
