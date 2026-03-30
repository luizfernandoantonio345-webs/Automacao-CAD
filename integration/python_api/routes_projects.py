from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, constr
from sse_starlette.sse import EventSourceResponse

from engenharia_automacao.app.auth import AuthService
from engenharia_automacao.core.main import ProjectService

from integration.python_api.config import AppConfig
from integration.python_api.dependencies import (
    get_app_config,
    get_autopilot_service,
    get_auth_service,
    get_cache_client,
    get_current_user,
    get_job_manager,
    get_log_file,
    get_output_dir,
    get_project_service,
    get_telemetry_store,
)
from integration.python_api.schemas import AutopilotRequest, GenerateRequest
from integration.python_api.telemetry import ProjectTelemetryStore
from integration.python_api.autopilot import AutopilotService


router = APIRouter()


class DraftFeedbackRequest(BaseModel):
    prompt: constr(min_length=1, max_length=500)
    feedback: constr(min_length=1, max_length=20)
    company: constr(min_length=1, max_length=120)
    part_name: constr(min_length=1, max_length=120)
    code: constr(min_length=1, max_length=120)


@router.post("/generate")
def generate_project(
    payload: GenerateRequest,
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    project_service: ProjectService = Depends(get_project_service),
    output_dir: Path = Depends(get_output_dir),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
):
    if not auth_service.verificar_limite(user):
        raise HTTPException(status_code=403, detail="Limite de uso excedido")
    result_path = project_service.generate_project(
        payload.model_dump(),
        output_dir / f"{payload.code}.lsp",
        execute_in_autocad=False,
    )
    if payload.executar:
        from integration.python_api.runtime import execute_autocad_with_retry

        execute_autocad_with_retry(result_path)
    auth_service.incrementar_uso(user, quantidade=1)
    telemetry.record_event(payload.model_dump(), source="api.generate", result_path=str(result_path))
    telemetry.rebuild_stats()
    return {"path": str(result_path), "usado": user["usado"], "limite": user["limite"]}


@router.get("/autopilot/materials")
def autopilot_materials(
    _: dict = Depends(get_current_user),
    autopilot_service: AutopilotService = Depends(get_autopilot_service),
):
    return {"materials": autopilot_service.list_materials()}


@router.post("/autopilot/execute")
def autopilot_execute(
    payload: AutopilotRequest,
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    autopilot_service: AutopilotService = Depends(get_autopilot_service),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
):
    if not auth_service.verificar_limite(user):
        raise HTTPException(status_code=403, detail="Limite de uso excedido")

    result = autopilot_service.execute(payload.model_dump())
    auth_service.incrementar_uso(user, quantidade=1)
    telemetry.record_event(
        {
            "code": payload.code,
            "company": payload.company,
            "part_name": "Project Autopilot",
            "diameter": payload.shed_width_m,
            "length": payload.shed_length_m,
        },
        source="api.autopilot",
        result_path=result["cad_payload_path"],
    )
    telemetry.rebuild_stats()
    result["usado"] = user["usado"]
    result["limite"] = user["limite"]
    return result


@router.post("/excel")
def generate_excel(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    project_service: ProjectService = Depends(get_project_service),
    config: AppConfig = Depends(get_app_config),
    output_dir: Path = Depends(get_output_dir),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
):
    if not auth_service.verificar_limite(user):
        raise HTTPException(status_code=403, detail="Limite de uso excedido")

    filename = (file.filename or "").lower()
    if not filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Arquivo invalido. Use .xls ou .xlsx")

    if hasattr(file, "size") and file.size > config.max_excel_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede tamanho maximo de {config.max_excel_upload_bytes // (1024*1024)}MB",
        )

    excel_path = config.data_dir / f"upload_{uuid4().hex}.xlsx"
    written = 0
    try:
        with excel_path.open("wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > config.max_excel_upload_bytes:
                    excel_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Arquivo excede tamanho maximo de {config.max_excel_upload_bytes // (1024*1024)}MB",
                    )
                f.write(chunk)

        generated = project_service.generate_projects_from_excel(excel_path, output_dir)
        if generated:
            auth_service.incrementar_uso(user, quantidade=len(generated))
            for path in generated:
                telemetry.record_event(
                    {
                        "code": Path(path).stem,
                        "company": user.get("empresa", ""),
                        "part_name": "excel_batch",
                        "diameter": 0,
                        "length": 0,
                    },
                    source="api.excel",
                    result_path=str(path),
                )
            telemetry.rebuild_stats()
        return {"files": [str(p) for p in generated], "count": len(generated), "usado": user["usado"], "limite": user["limite"]}
    finally:
        excel_path.unlink(missing_ok=True)


@router.get("/history")
def history(_: dict = Depends(get_current_user), output_dir: Path = Depends(get_output_dir)):
    history_files = sorted(output_dir.glob("*.lsp"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"history": [str(p) for p in history_files[:200]]}


@router.get("/logs")
def logs(_: dict = Depends(get_current_user), log_file: Path = Depends(get_log_file)):
    if not log_file.exists():
        return {"logs": []}
    lines = log_file.read_text(encoding="utf-8").splitlines()
    return {"logs": lines[-300:]}


@router.get("/insights")
def insights(_: dict = Depends(get_current_user), telemetry: ProjectTelemetryStore = Depends(get_telemetry_store)):
    return {
        "stats": telemetry.get_stats(),
        "recommendations": telemetry.get_recommendations(),
        "templates": telemetry.get_templates(),
    }


@router.get("/project-draft")
def project_draft(
    _: dict = Depends(get_current_user),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
    company: str | None = Query(default=None, max_length=120),
    part_name: str | None = Query(default=None, max_length=120),
):
    return telemetry.build_project_draft(company=company, part_name=part_name)


@router.get("/project-draft-from-text")
def project_draft_from_text(
    _: dict = Depends(get_current_user),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
    prompt: str = Query(..., min_length=3, max_length=500),
):
    return telemetry.build_project_draft_from_text(prompt)


@router.post("/project-draft-feedback")
def project_draft_feedback(
    payload: DraftFeedbackRequest,
    _: dict = Depends(get_current_user),
    telemetry: ProjectTelemetryStore = Depends(get_telemetry_store),
):
    telemetry.record_draft_feedback(
        prompt=payload.prompt,
        draft={
            "company": payload.company,
            "part_name": payload.part_name,
            "code": payload.code,
        },
        feedback=payload.feedback,
    )
    return {"status": "ok"}


@router.get("/health")
def health(config: AppConfig = Depends(get_app_config)):
    if config.simulation_mode:
        return {"autocad": True, "simulation_mode": True, "status": "ok"}

    autocad_open = False
    try:
        import win32com.client

        try:
            win32com.client.GetActiveObject("AutoCAD.Application")
            autocad_open = True
        except Exception:
            autocad_open = False
    except Exception:
        autocad_open = False
    return {"autocad": autocad_open, "simulation_mode": False, "status": "ok"}


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
def readiness(
    config: AppConfig = Depends(get_app_config),
    cache_client=Depends(get_cache_client),
    job_manager=Depends(get_job_manager),
):
    db_ok = True
    if config.database_url.startswith("sqlite:///"):
        db_path = Path(config.database_url.replace("sqlite:///", "", 1))
        db_ok = db_path.exists()

    cache_ok = bool(getattr(cache_client, "is_available", lambda: False)())
    jobs_ok = bool(getattr(job_manager, "redis", None) is not None)

    components = {
        "api": True,
        "database": db_ok,
        "cache": cache_ok,
        "jobs": jobs_ok,
    }

    if config.simulation_mode:
        payload = {
            "status": "ready",
            "mode": "simulation",
            "components": {
                **components,
                "cache": True,
                "jobs": True,
            },
            "bypassed": ["cache", "jobs", "ollama"],
        }
        return payload

    ready = all(components.values())
    payload = {"status": "ready" if ready else "degraded", "components": components}
    if ready:
        return payload
    return JSONResponse(status_code=503, content=payload)


@router.get("/events")
async def events_stream(_: dict = Depends(get_current_user), log_file: Path = Depends(get_log_file)):
    """SSE endpoint para streaming de eventos em tempo real."""

    async def event_generator():
        """Generator para eventos SSE."""
        last_size = 0
        last_stats = None

        while True:
            try:
                # Verificar se o arquivo de log mudou
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    if current_size > last_size:
                        # Ler novas linhas
                        with open(log_file, "r", encoding="utf-8") as f:
                            f.seek(last_size)
                            new_lines = f.read().splitlines()
                            if new_lines:
                                yield {
                                    "event": "logs",
                                    "data": "\n".join(new_lines[-10:])  # Últimas 10 linhas
                                }
                        last_size = current_size

                # Verificar mudanças nas estatísticas (menos frequente)
                from integration.python_api.dependencies import get_telemetry_store
                telemetry = get_telemetry_store()
                current_stats = telemetry.get_stats()

                # Comparar apenas campos principais para evitar spam
                stats_changed = (
                    last_stats is None or
                    current_stats.get("total_projects") != last_stats.get("total_projects") or
                    current_stats.get("real_projects") != last_stats.get("real_projects")
                )

                if stats_changed:
                    yield {
                        "event": "stats",
                        "data": {
                            "total_projects": current_stats.get("total_projects", 0),
                            "real_projects": current_stats.get("real_projects", 0),
                            "top_company": current_stats.get("top_companies", [[]])[0][0] if current_stats.get("top_companies") else "",
                            "top_part": current_stats.get("top_part_names", [[]])[0][0] if current_stats.get("top_part_names") else "",
                        }
                    }
                    last_stats = current_stats

                # Verificar status do AutoCAD
                autocad_open = False
                try:
                    import win32com.client
                    win32com.client.GetActiveObject("AutoCAD.Application")
                    autocad_open = True
                except:
                    autocad_open = False

                yield {
                    "event": "health",
                    "data": {"autocad": autocad_open}
                }

            except Exception as e:
                yield {
                    "event": "error",
                    "data": f"Erro no stream: {str(e)}"
                }

            # Aguardar antes da próxima verificação
            import asyncio
            await asyncio.sleep(2)  # Atualização a cada 2 segundos

    return EventSourceResponse(event_generator())
