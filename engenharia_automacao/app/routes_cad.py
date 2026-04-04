from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Import the RefineryService
from engenharia_automacao.services.refinery_service import RefineryService

router = APIRouter(prefix="/api", tags=["cad"])

# Initialize RefineryService
refinery_service = RefineryService()


class CadInjectRequest(BaseModel):
    refinery_id: str
    pressure_class: str
    norms: List[str]
    drawing_type: str = "3D Piping Layout"
    additional_params: Optional[dict] = None


class CadInjectResponse(BaseModel):
    script_id: str
    refinery_id: str
    timestamp: str
    status: str
    lisp_script: Optional[str] = None


# Routes

@router.get("/refineries")
async def get_all_refineries():
    """
    Retorna todas as refinarias e suas configurações.
    Formato padronizado: {data: [...], status: "success"}
    """
    try:
        refineries = refinery_service.get_all_refineries()
        # Padronizar: converter dict {id: config} para array com id embutido
        data = [
            {"id": rid, **rconfig}
            for rid, rconfig in refineries.items()
        ]
        return {"data": data, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar refinarias: {str(e)}")


@router.get("/refineries/{refinery_id}", response_model=dict)
async def get_refinery(refinery_id: str):
    """
    Retorna configuração de uma refinaria específica
    """
    refinery = refinery_service.get_refinery(refinery_id)
    if not refinery:
        raise HTTPException(status_code=404, detail=f"Refinaria {refinery_id} não encontrada")
    return refinery


@router.post("/cad/inject", response_model=CadInjectResponse)
async def cad_inject(request: CadInjectRequest, background_tasks: BackgroundTasks):
    """
    Endpoint para injetar comandos LISP no AutoCAD

    Recebe parâmetros de projeto e retorna:
    - script_id: ID único do script gerado
    - status: Status da injeção
    - lisp_script: Script LISP gerado (simulado por enquanto)
    """
    
    # Validar refinaria
    if not refinery_service.validate_refinery(request.refinery_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Refinaria {request.refinery_id} não existe"
        )
    
    # Gerar ID único para o script
    script_id = f"AUTO-{uuid.uuid4().hex[:8]}".upper()
    timestamp = datetime.now(UTC).isoformat()
    
    # Simular geração de LISP script (será aprimorado depois)
    lisp_script = generate_lisp_script(
        refinery_id=request.refinery_id,
        drawing_type=request.drawing_type,
        pressure_class=request.pressure_class,
        norms=request.norms
    )
    
    # Adicionar task em background para processar após responder
    background_tasks.add_task(
        process_cad_injection,
        script_id=script_id,
        refinery_id=request.refinery_id,
        lisp_script=lisp_script
    )
    
    return CadInjectResponse(
        script_id=script_id,
        refinery_id=request.refinery_id,
        timestamp=timestamp,
        status="PENDING",
        lisp_script=lisp_script
    )


@router.get("/cad/inject/{script_id}")
async def get_injection_status(script_id: str):
    """
    Retorna status de uma injeção CAD específica
    """
    # TODO: Implementar consulta em banco de dados
    return {
        "script_id": script_id,
        "status": "COMPLETED",
        "timestamp": datetime.now(UTC).isoformat(),
        "progress": 100
    }


@router.get("/cad/norms/{refinery_id}", response_model=List[str])
async def get_refinery_norms(refinery_id: str):
    """
    Retorna lista de normas aplicáveis a uma refinaria
    """
    norms = refinery_service.get_refinery_norms(refinery_id)
    if not norms:
        raise HTTPException(status_code=404, detail=f"Normas não encontradas para {refinery_id}")
    return norms


@router.get("/cad/materials/{refinery_id}")
async def get_material_database(refinery_id: str):
    """
    Retorna informações do banco de dados de materiais
    """
    material_db = refinery_service.get_material_database(refinery_id)
    if not material_db:
        raise HTTPException(
            status_code=404, 
            detail=f"Database de materiais não encontrado para {refinery_id}"
        )
    return {
        "refinery_id": refinery_id,
        "material_database": material_db
    }


# Helper Functions

def generate_lisp_script(
    refinery_id: str,
    drawing_type: str,
    pressure_class: str,
    norms: list
) -> str:
    """
    Gera um script LISP simulado baseado nos parâmetros de projeto
    (Será aprimorado com lógica real de geração)
    """
    
    script = f"""
    ;; AutoCAD LISP Script - Engenharia CAD v1.0
    ;; Generated for: {refinery_id}
    ;; Drawing Type: {drawing_type}
    ;; Pressure Class: {pressure_class}
    ;; Applicable Norms: {', '.join(norms)}
    
    (defun C:INJECT_PIPING()
      (setvar "CMDECHO" 0)
      (setvar "BLIPMODE" 0)
      
      ;; Initialize project parameters
      (setq refinery "{refinery_id}")
      (setq pressure_class "{pressure_class}")
      (setq drawing_type "{drawing_type}")
      
      ;; Draw base piping layout
      (command "LAYER" "NEW" "PIPES" "")
      (command "LAYER" "NEW" "EQUIPMENT" "")
      (command "LAYER" "NEW" "ANNOTATIONS" "")
      
      ;; Set colors according to norms
      (command "LAYER" "SET" "PIPES" "")
      (command "COLOR" "2")  ;; Yellow for piping
      
      ;; Generate basic geometry (placeholder)
      ;; Real implementation will use sophisticated geometry algorithms
      (alert (strcat "Projeto iniciado para " refinery))
      
      (setvar "CMDECHO" 1)
      (princ "\\nPiping injection complete.")
    )
    
    (C:INJECT_PIPING)
    """
    
    return script.strip()


async def process_cad_injection(script_id: str, refinery_id: str, lisp_script: str):
    """Processa injeção CAD em background (logging + futura persistência)."""
    print(f"[CAD Injection] Processing script {script_id} for {refinery_id}")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT SSE: Execução real via ProjectService + streaming de logs
# ─────────────────────────────────────────────────────────────────────────────

class _SSEHandler(logging.Handler):
    """Captura registros de log do execution engine e alimenta uma asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._queue = queue
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        level = record.levelname  # INFO / ERROR / WARNING
        payload = json.dumps({"level": level, "message": message})
        # Coloca na fila de forma thread-safe
        self._loop.call_soon_threadsafe(
            self._queue.put_nowait, ("log", payload)
        )


@router.get("/cad/execute-stream")
async def execute_stream(
    refinery_id: str = Query("REGAP"),
    diameter: float = Query(50.0),
    length: float = Query(1000.0),
    company: str = Query("Petrobras"),
    part_name: str = Query("Pipe Main Header"),
    code: str = Query("AUTO-001"),
):
    """
    Executa o ProjectService.generate_project() em uma thread separada e
    transmite cada log via Server-Sent Events para o CadConsole do frontend.

    Eventos emitidos:
        log   — { level: "INFO"|"ERROR"|"WARN", message: str, progress?: number, label?: str }
        cmd   — linha de comando LISP individual
        done  — { script_path: str }
        error_event — { message: str }
    """
    if not refinery_service.validate_refinery(refinery_id):
        raise HTTPException(status_code=400, detail=f"Refinaria {refinery_id} inválida")

    refinery_cfg = refinery_service.get_refinery(refinery_id)

    event_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    async def generator() -> AsyncGenerator:
        loop = asyncio.get_running_loop()

        def queue_event(event_type: str, data: str) -> None:
            loop.call_soon_threadsafe(event_queue.put_nowait, (event_type, data))

        # Configura handler de logging que escreve na fila SSE
        sse_handler = _SSEHandler(event_queue, loop)
        sse_handler.setFormatter(logging.Formatter("%(message)s"))

        # Captura loggers do execution engine
        target_loggers = [
            "engenharia_automacao.core.main",
            "engenharia_automacao.cad.autocad_executor",
            "engenharia_automacao.core.engine.generator",
        ]
        root_logger = logging.getLogger()
        root_logger.addHandler(sse_handler)
        for name in target_loggers:
            lg = logging.getLogger(name)
            lg.addHandler(sse_handler)
            lg.setLevel(logging.DEBUG)

        # Emit: iniciando
        yield {
            "event": "log",
            "data": json.dumps({
                "level": "INFO",
                "message": f"Iniciando engine para {refinery_id}...",
                "progress": 5,
                "label": "Inicializando",
            }),
        }

        output_dir = Path("data/output")
        payload = {
            "diameter": diameter,
            "length": length,
            "company": company,
            "part_name": part_name,
            "code": code,
            "pressure_class": refinery_cfg.get("default_pressure_class", "ASME 150") if refinery_cfg else "ASME 150",
        }

        error_message: Optional[str] = None
        script_path: Optional[str] = None

        def run_engine() -> None:
            nonlocal error_message, script_path
            try:
                from engenharia_automacao.core.main import ProjectService  # lazy import
                service = ProjectService()
                # Emite alguns marcos de progresso via queue
                queue_event(
                    "log",
                    json.dumps({
                        "level": "INFO",
                        "message": "Validando parâmetros do projeto...",
                        "progress": 20,
                        "label": "Validando",
                    }),
                )
                queue_event(
                    "cmd",
                    f'"LAYER" "NEW" "PIPES_{code}" ""',
                )
                path = service.generate_project(payload, output_dir, execute_in_autocad=False)
                script_path = str(path)
                queue_event(
                    "log",
                    json.dumps({
                        "level": "INFO",
                        "message": f"Geometria gerada. Escrevendo LISP em {path.name}...",
                        "progress": 75,
                        "label": "Gerando LISP",
                    }),
                )
                queue_event(
                    "cmd",
                    '"DrawGeneratedPipe"',
                )
            except Exception as exc:
                error_message = str(exc)

        # Executa engine sem bloquear o event loop
        future = loop.run_in_executor(None, run_engine)

        # Drena a fila enquanto a thread trabalha
        try:
            while not future.done() or not event_queue.empty():
                try:
                    event_type, data = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                    yield {"event": event_type, "data": data}
                except asyncio.TimeoutError:
                    continue

            # Aguarda conclusão da thread
            await future

            # Emite eventos finais
            if error_message:
                yield {
                    "event": "error_event",
                    "data": json.dumps({"message": error_message}),
                }
            else:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "level": "INFO",
                        "message": "Execução concluída com sucesso.",
                        "progress": 100,
                        "label": "Completo",
                    }),
                }
                yield {
                    "event": "done",
                    "data": json.dumps({"script_path": script_path}),
                }
        finally:
            root_logger.removeHandler(sse_handler)
            for name in target_loggers:
                logging.getLogger(name).removeHandler(sse_handler)

    return EventSourceResponse(generator())

