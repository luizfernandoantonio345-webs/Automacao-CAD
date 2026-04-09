#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — Rotas API de Detecção e Lançamento de AutoCAD

Endpoints REST para detectar, lançar e conectar ao AutoCAD automaticamente.
Integra-se com o sistema de licenciamento - usuário precisa estar logado.

═══════════════════════════════════════════════════════════════════════════════

Monta no router com prefixo /api/cad-detection
Exemplo: POST /api/cad-detection/detect-and-launch
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.autocad_detector import cad_detector, CADInstallation, DetectionStatus

logger = logging.getLogger("engcad.routes_detection")

router = APIRouter(prefix="/api/cad-detection", tags=["cad-detection"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class InstallationInfo(BaseModel):
    """Informações de uma instalação de CAD."""
    type: str
    version: str
    exe_path: str
    progid: Optional[str] = None
    is_64bit: bool = True


class DetectionResponse(BaseModel):
    """Resposta de operações de detecção."""
    success: bool
    status: str
    message: str
    installations: List[InstallationInfo] = []
    active_installation: Optional[InstallationInfo] = None
    process_id: Optional[int] = None
    document_name: Optional[str] = None
    details: dict = {}


class LaunchRequest(BaseModel):
    """Requisição para lançar CAD específico."""
    installation_index: int = Field(default=0, ge=0, description="Índice da instalação a usar")
    auto_connect: bool = Field(default=True, description="Conectar automaticamente via COM")
    auto_load_lsp: bool = Field(default=True, description="Carregar automação LSP")
    wait_seconds: int = Field(default=60, ge=10, le=180, description="Timeout de inicialização")


class ConfigurePathsRequest(BaseModel):
    """Requisição para configurar caminhos de automação."""
    lsp_path: Optional[str] = Field(default=None, description="Caminho do forge_vigilante.lsp")
    drop_path: Optional[str] = Field(default=None, description="Pasta para comandos LSP")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=DetectionResponse)
async def get_quick_status():
    """
    Retorna status rápido do CAD sem tentar lançar ou conectar.
    
    Útil para verificar se há CAD instalado/rodando antes de tentar conectar.
    Mostra ícone de status no frontend.
    """
    result = cad_detector.quick_status()
    return _to_response(result)


@router.get("/installations", response_model=List[InstallationInfo])
async def list_installations():
    """
    Lista todas as instalações de CAD detectadas no sistema.
    
    Retorna lista vazia se nenhum CAD estiver instalado.
    """
    installations = cad_detector.scan_installations()
    return [
        InstallationInfo(
            type=inst.cad_type.value,
            version=inst.version,
            exe_path=inst.exe_path,
            progid=inst.progid,
            is_64bit=inst.is_64bit,
        )
        for inst in installations
    ]


@router.post("/detect-and-launch", response_model=DetectionResponse)
async def detect_and_launch(request: LaunchRequest = None):
    """
    🚀 OPERAÇÃO PRINCIPAL: Detecta, lança e conecta ao CAD automaticamente.
    
    Este é o endpoint que o botão "Conectar ao AutoCAD" deve chamar.
    
    Fluxo:
    1. Escaneia instalações de CAD
    2. Verifica se já está rodando
    3. Se não, lança o CAD (aguarda inicialização)
    4. Conecta via COM
    5. Configura pastas de automação
    6. Carrega forge_vigilante.lsp
    
    Body (opcional):
    - installation_index: Qual instalação usar (0 = primeira)
    - auto_connect: Se deve conectar via COM (default: true)
    - auto_load_lsp: Se deve carregar LSP (default: true)
    - wait_seconds: Timeout de inicialização (default: 60)
    """
    if request is None:
        request = LaunchRequest()
    
    # Se especificou uma instalação específica
    installation = None
    if request.installation_index > 0:
        installations = cad_detector.scan_installations()
        if request.installation_index < len(installations):
            installation = installations[request.installation_index]
    
    result = cad_detector.detect_and_launch(
        auto_connect=request.auto_connect,
        auto_load_lsp=request.auto_load_lsp,
    )
    
    return _to_response(result)


@router.post("/launch", response_model=DetectionResponse)
async def launch_cad(request: LaunchRequest = None):
    """
    Lança o CAD sem conectar automaticamente.
    
    Útil quando precisa apenas abrir o CAD para o usuário.
    """
    if request is None:
        request = LaunchRequest()
    
    installation = None
    if request.installation_index >= 0:
        installations = cad_detector.scan_installations()
        if request.installation_index < len(installations):
            installation = installations[request.installation_index]
    
    result = cad_detector.launch_cad(
        installation=installation,
        wait_seconds=request.wait_seconds,
    )
    
    return _to_response(result)


@router.post("/connect", response_model=DetectionResponse)
async def connect_com():
    """
    Conecta ao CAD já em execução via COM.
    
    Útil quando o CAD já está aberto e só precisa conectar.
    """
    result = cad_detector.connect_com()
    return _to_response(result)


@router.post("/load-lsp", response_model=DetectionResponse)
async def load_automation_lsp():
    """
    Carrega o forge_vigilante.lsp no CAD conectado.
    
    Requer conexão COM prévia.
    """
    if not cad_detector.is_connected():
        raise HTTPException(
            status_code=400,
            detail="CAD não conectado. Use /connect primeiro."
        )
    
    result = cad_detector.load_automation_lsp()
    return _to_response(result)


@router.post("/configure-paths", response_model=DetectionResponse)
async def configure_paths(request: ConfigurePathsRequest):
    """
    Configura caminhos de automação (LSP e pasta de drop).
    """
    if request.lsp_path:
        cad_detector.lsp_path = request.lsp_path
    if request.drop_path:
        cad_detector.drop_path = request.drop_path
    
    result = cad_detector.setup_drop_folder()
    return _to_response(result)


@router.post("/test-connection", response_model=DetectionResponse)
async def test_connection():
    """
    Testa a conexão COM enviando um comando simples.
    
    Desenha um círculo de teste e verifica se foi criado.
    """
    if not cad_detector.is_connected():
        raise HTTPException(
            status_code=400,
            detail="CAD não conectado"
        )
    
    try:
        import pythoncom
        pythoncom.CoInitialize()
        
        # Desenhar círculo de teste
        cad_detector._com_doc.SendCommand('(command "_CIRCLE" "0,0" "50") ')
        
        return DetectionResponse(
            success=True,
            status=DetectionStatus.CONNECTED.value,
            message="Teste OK - Círculo desenhado em (0,0) Ø100",
            details={"test": "circle", "radius": 50},
        )
        
    except Exception as e:
        return DetectionResponse(
            success=False,
            status=DetectionStatus.ERROR.value,
            message=f"Erro no teste: {str(e)}",
        )
    finally:
        pythoncom.CoUninitialize()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _to_response(result) -> DetectionResponse:
    """Converte DetectionResult para DetectionResponse."""
    return DetectionResponse(
        success=result.success,
        status=result.status.value,
        message=result.message,
        installations=[
            InstallationInfo(
                type=inst.cad_type.value,
                version=inst.version,
                exe_path=inst.exe_path,
                progid=inst.progid,
                is_64bit=inst.is_64bit,
            )
            for inst in result.installations
        ],
        active_installation=InstallationInfo(
            type=result.active_installation.cad_type.value,
            version=result.active_installation.version,
            exe_path=result.active_installation.exe_path,
            progid=result.active_installation.progid,
            is_64bit=result.active_installation.is_64bit,
        ) if result.active_installation else None,
        process_id=result.process_id,
        document_name=result.document_name,
        details=result.details,
    )
