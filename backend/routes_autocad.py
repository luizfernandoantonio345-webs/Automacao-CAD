#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — Rotas API do AutoCAD Driver (Nível 4)
Expõe operações COM como endpoints REST para o Frontend/AIOrchestrator.
═══════════════════════════════════════════════════════════════════════════════

Monta no router com prefixo /api/autocad
Exemplo: POST /api/autocad/draw-pipe
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.autocad_driver import acad_driver, DriverStatus

logger = logging.getLogger("engcad.routes_autocad")

router = APIRouter(prefix="/api/autocad", tags=["autocad-driver"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE REQUEST
# ═══════════════════════════════════════════════════════════════════════════════

class DrawPipeRequest(BaseModel):
    points: List[List[float]] = Field(..., min_length=2, description="Coordenadas [[x,y,z], ...]")
    diameter: float = Field(default=6.0, gt=0, le=120)
    layer: str = Field(default="PIPE-PROCESS", max_length=64)

    @field_validator("points")
    @classmethod
    def validate_points(cls, v):
        for i, pt in enumerate(v):
            if len(pt) < 2 or len(pt) > 3:
                raise ValueError(f"Ponto {i} deve ter 2 ou 3 coordenadas, recebeu {len(pt)}")
        return v


class DrawLineRequest(BaseModel):
    start: List[float] = Field(..., min_length=2, max_length=3)
    end: List[float] = Field(..., min_length=2, max_length=3)
    layer: str = Field(default="PIPE-PROCESS", max_length=64)


class InsertComponentRequest(BaseModel):
    block_name: str = Field(..., min_length=1, max_length=255)
    coordinate: List[float] = Field(..., min_length=2, max_length=3)
    rotation: float = Field(default=0.0, ge=0, lt=360)
    scale: float = Field(default=1.0, gt=0, le=100)
    layer: str = Field(default="VALVE", max_length=64)


class AddTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=512)
    position: List[float] = Field(..., min_length=2, max_length=3)
    height: float = Field(default=2.5, gt=0, le=100)
    layer: str = Field(default="ANNOTATION", max_length=64)


class SendCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=1024)


class BridgeConfigRequest(BaseModel):
    """Configura o caminho da pasta de rede (ponte) para o Vigilante AutoCAD."""
    path: str = Field(..., min_length=1, max_length=512, description="Caminho da pasta de rede (ex: Z:/AutoCAD_Drop/)")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        import os
        v = v.strip()

        # 1. Bloquear null bytes (binary injection)
        if "\x00" in v:
            raise ValueError("Caminho inválido — null bytes detectados")

        # 2. Normalizar e resolver para caminho absoluto
        normalized = os.path.normpath(os.path.abspath(v))

        # 3. Bloquear path traversal: presença de .. ANTES ou DEPOIS da normalização
        if ".." in v or ".." in normalized:
            raise ValueError("Caminho inválido — tentativa de path traversal detectada")

        # 4. Whitelist de diretórios permitidos (raízes seguras)
        #    Aceita: qualquer drive letter (D:\, Z:\, etc.), UNC paths (\\server\share),
        #    e paths relativos que resolvem para dentro do workspace
        _BLOCKED_DIRS = (
            os.path.normpath(os.environ.get("SYSTEMROOT", "C:\\Windows")),
            os.path.normpath(os.environ.get("PROGRAMFILES", "C:\\Program Files")),
            os.path.normpath(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")),
            os.path.normpath("C:\\Windows"),
            os.path.normpath("C:\\Program Files"),
            "/etc", "/usr", "/bin", "/sbin", "/var", "/proc", "/sys",
        )
        normalized_lower = normalized.lower()
        for blocked in _BLOCKED_DIRS:
            if normalized_lower.startswith(blocked.lower()):
                raise ValueError(
                    f"Caminho inválido — diretório de sistema protegido: {blocked}"
                )

        # 5. Bloquear caminhos que apontam para arquivos sensíveis
        _BLOCKED_FILES = ("passwd", "shadow", "hosts", ".env", "web.config")
        basename = os.path.basename(normalized).lower()
        if basename in _BLOCKED_FILES:
            raise ValueError(f"Caminho inválido — alvo protegido: {basename}")

        return normalized


class SetModeRequest(BaseModel):
    """Alterna entre modo COM direto e modo Ponte (rede)."""
    use_bridge: bool = Field(..., description="True = Modo Ponte, False = Modo COM direto")


class BatchDrawRequest(BaseModel):
    """Desenha múltiplas tubulações de uma vez — usado pelo AIOrchestrator."""
    pipes: List[DrawPipeRequest]
    components: Optional[List[InsertComponentRequest]] = None
    finalize: bool = Field(default=True, description="Executar Gran Finale ao final")


# ═══════════════════════════════════════════════════════════════════════════════
# CONEXÃO E DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/connect")
async def connect():
    """Conecta ao AutoCAD ativo ou inicia nova instância."""
    result = acad_driver.connect()
    return result.to_dict()


@router.post("/disconnect")
async def disconnect():
    """Desconecta do AutoCAD (não fecha o programa)."""
    result = acad_driver.disconnect()
    return result.to_dict()


@router.get("/status")
async def get_status():
    """Status atual do driver + estatísticas."""
    return acad_driver.stats


@router.get("/health")
async def driver_health():
    """Health check detalhado — usado pelo ai_watchdog."""
    return acad_driver.health_check()


# ═══════════════════════════════════════════════════════════════════════════════
# OPERAÇÕES DE DESENHO
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/draw-pipe")
async def draw_pipe(req: DrawPipeRequest):
    """Desenha tubulação 3D/2D no AutoCAD."""
    result = acad_driver.draw_pipe(
        points=req.points,
        diameter=req.diameter,
        layer=req.layer,
    )
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/draw-line")
async def draw_line(req: DrawLineRequest):
    """Desenha uma linha simples."""
    result = acad_driver.draw_line(
        start=req.start,
        end=req.end,
        layer=req.layer,
    )
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/insert-component")
async def insert_component(req: InsertComponentRequest):
    """Insere bloco (válvula, flange, etc.) da biblioteca REGAP."""
    result = acad_driver.insert_component(
        block_name=req.block_name,
        coordinate=req.coordinate,
        rotation=req.rotation,
        scale=req.scale,
        layer=req.layer,
    )
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/add-text")
async def add_text(req: AddTextRequest):
    """Adiciona anotação de texto."""
    result = acad_driver.add_text(
        text=req.text,
        position=req.position,
        height=req.height,
        layer=req.layer,
    )
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/send-command")
async def send_command(req: SendCommandRequest):
    """Envia comando de texto direto ao AutoCAD."""
    result = acad_driver.send_command(req.command)
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# LAYERS E FINALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/create-layers")
async def create_layers():
    """Cria sistema completo de layers N-58 Petrobras."""
    result = acad_driver.create_layer_system()
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/finalize")
async def finalize_view():
    """Gran Finale: ZoomExtents + Regen — mostra o projeto completo."""
    result = acad_driver.finalize_view()
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.post("/save")
async def save_document():
    """Salva o documento ativo."""
    result = acad_driver.save_document()
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PONTE DE REDE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/config/bridge")
async def configure_bridge(req: BridgeConfigRequest):
    """Define o caminho da pasta de rede onde o Vigilante espera os .lsp."""
    result = acad_driver.set_bridge_path(req.path)
    return result.to_dict()


@router.post("/config/mode")
async def set_driver_mode(req: SetModeRequest):
    """Alterna entre modo COM direto e modo Ponte."""
    result = acad_driver.set_mode(req.use_bridge)
    return result.to_dict()


@router.post("/commit")
async def commit_bridge():
    """
    Grava o buffer de comandos AutoLISP como arquivo .lsp na pasta de rede.
    O script vigilante no PC remoto detecta e executa automaticamente.
    """
    if not acad_driver.use_bridge:
        raise HTTPException(
            status_code=400,
            detail="Commit só é válido em Modo Ponte. Use POST /api/autocad/config/mode para ativar.",
        )
    result = acad_driver.commit()
    if not result.success:
        raise HTTPException(status_code=503, detail=result.to_dict())
    return result.to_dict()


@router.get("/buffer")
async def get_buffer_status():
    """Retorna status do buffer AutoLISP atual (tamanho, modo, caminho)."""
    return {
        "mode": "bridge" if acad_driver.use_bridge else "com",
        "bridge_path": acad_driver.bridge_path,
        "buffer_size": len(acad_driver.command_buffer),
        "bridge_accessible": bool(acad_driver.bridge_path) and os.path.isdir(acad_driver.bridge_path),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH — OPERAÇÃO COMPLETA DA IA
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/batch-draw")
async def batch_draw(req: BatchDrawRequest):
    """
    Executa desenho completo em lote: múltiplas tubulações + componentes.
    Usado pelo AIOrchestrator para desenhar um projeto inteiro de uma vez.

    Retorna o resumo de todas as operações.
    """
    # 1. Garantir layers N-58
    layers_result = acad_driver.create_layer_system()

    results = {
        "layers": layers_result.to_dict(),
        "pipes": [],
        "components": [],
        "finalize": None,
        "summary": {"total": 0, "success": 0, "failed": 0},
    }

    # 2. Desenhar tubulações
    for pipe_req in req.pipes:
        r = acad_driver.draw_pipe(
            points=pipe_req.points,
            diameter=pipe_req.diameter,
            layer=pipe_req.layer,
        )
        results["pipes"].append(r.to_dict())
        results["summary"]["total"] += 1
        if r.success:
            results["summary"]["success"] += 1
        else:
            results["summary"]["failed"] += 1

    # 3. Inserir componentes
    if req.components:
        for comp_req in req.components:
            r = acad_driver.insert_component(
                block_name=comp_req.block_name,
                coordinate=comp_req.coordinate,
                rotation=comp_req.rotation,
                scale=comp_req.scale,
                layer=comp_req.layer,
            )
            results["components"].append(r.to_dict())
            results["summary"]["total"] += 1
            if r.success:
                results["summary"]["success"] += 1
            else:
                results["summary"]["failed"] += 1

    # 4. Gran Finale
    if req.finalize:
        fin = acad_driver.finalize_view()
        results["finalize"] = fin.to_dict()

    # 5. Auto-commit em modo PONTE — grava .lsp na pasta de rede automaticamente
    if acad_driver.use_bridge and acad_driver.command_buffer:
        commit_result = acad_driver.commit()
        results["commit"] = commit_result.to_dict()

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE DE FOGO — Validação Ponta a Ponta
# ═══════════════════════════════════════════════════════════════════════════════

debug_router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@debug_router.post("/draw-sample")
async def draw_sample():
    """
    Teste de Fogo: desenha um quadrado 1000x1000 e insere uma válvula no centro.
    Valida a conexão COM ponta a ponta em uma única chamada.
    """
    # Garantir conexão
    conn = acad_driver.connect()
    if not conn.success and acad_driver.status not in ("Connected", "Simulation"):
        raise HTTPException(status_code=503, detail=conn.to_dict())

    # 1. Layers
    layers_result = acad_driver.create_layer_system()

    results = {
        "layers": layers_result.to_dict(),
        "pipes": [],
        "components": [],
        "finalize": None,
        "summary": {"total": 0, "success": 0, "failed": 0},
    }

    # 2. Quadrado 1000x1000 (4 lados)
    square_points = [
        [0.0, 0.0, 0.0],
        [1000.0, 0.0, 0.0],
        [1000.0, 1000.0, 0.0],
        [0.0, 1000.0, 0.0],
        [0.0, 0.0, 0.0],
    ]
    r = acad_driver.draw_pipe(points=square_points, diameter=4.0, layer="PIPE-PROCESS")
    results["pipes"].append(r.to_dict())
    results["summary"]["total"] += 1
    if r.success:
        results["summary"]["success"] += 1
    else:
        results["summary"]["failed"] += 1

    # 3. Diagonal decorativa
    r2 = acad_driver.draw_line(start=[0.0, 0.0, 0.0], end=[1000.0, 1000.0, 0.0], layer="PIPE-UTILITY")
    results["pipes"].append(r2.to_dict())
    results["summary"]["total"] += 1
    if r2.success:
        results["summary"]["success"] += 1
    else:
        results["summary"]["failed"] += 1

    # 4. Válvula no centro
    r3 = acad_driver.insert_component(
        block_name="VALVE-GATE",
        coordinate=[500.0, 500.0, 0.0],
        rotation=45.0,
        scale=1.0,
        layer="VALVE",
    )
    results["components"].append(r3.to_dict())
    results["summary"]["total"] += 1
    if r3.success:
        results["summary"]["success"] += 1
    else:
        results["summary"]["failed"] += 1

    # 5. Texto de identificação
    r4 = acad_driver.add_text(
        text="Engenharia CAD — Teste E2E",
        position=[200.0, -100.0, 0.0],
        height=40.0,
        layer="ANNOTATION",
    )
    results["components"].append(r4.to_dict())
    results["summary"]["total"] += 1
    if r4.success:
        results["summary"]["success"] += 1
    else:
        results["summary"]["failed"] += 1

    # 6. Gran Finale
    fin = acad_driver.finalize_view()
    results["finalize"] = fin.to_dict()

    return results
