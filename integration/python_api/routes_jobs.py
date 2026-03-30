from __future__ import annotations

from typing import Dict, Any
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import logging
import json
import threading
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from integration.python_api.dependencies import get_job_manager, get_auth_service, get_app_config, get_output_dir
from integration.python_api.config import AppConfig
from integration.python_api.async_jobs import AsyncJobManager
from engenharia_automacao.app.auth import AuthService

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("routes_jobs")

# ✓ PROBLEMA #6: Rate limiting simples com memória (para múltiplas instâncias, usar Redis)
_ai_job_rate_limit: dict[str, deque[float]] = defaultdict(deque)
_ai_global_rate_limit: deque[float] = deque()
_ai_rate_lock = threading.Lock()
AI_JOBS_PER_MINUTE = 10
AI_JOBS_GLOBAL_LIMIT = 100
AI_RATE_WINDOW_SECONDS = 60


PROFILE_MASS_KG_M = {
    "W200x15": 15.0,
    "W250x25": 25.0,
    "W310x32.7": 32.7,
    "W310x32": 32.0,
    "W360x44": 44.0,
    "W410x60": 60.0,
}


def gerar_teste_stress_50_porticos() -> Dict[str, Any]:
    configuracao = {
        "vao": 25,
        "altura": 8,
        "espacamento": 6,
        "qtdPorticos": 50,
        "perfil": "W310x32.7",
        "gerarCotas": True,
    }

    entidades_porticos = []

    for i in range(configuracao["qtdPorticos"]):
        posicao_z = i * configuracao["espacamento"] * 1000
        vao_mm = configuracao["vao"] * 1000
        altura_mm = configuracao["altura"] * 1000
        peso_kg_m = PROFILE_MASS_KG_M.get(configuracao["perfil"], 32.7)
        comprimento_aprox_m = (2 * configuracao["altura"]) + configuracao["vao"]
        peso_estimado_kg = round(peso_kg_m * comprimento_aprox_m, 2)
        trace_id = f"TRACE-P-{i + 1:03d}-{uuid4().hex[:8]}"

        entidades_porticos.append(
            {
                "tipo": "PORTICO_COMPLETO",
                "id": f"P-{i + 1}",
                "coordenadas": {"x": 0, "y": 0, "z": posicao_z},
                "dimensoes": {"vao": vao_mm, "altura": altura_mm},
                "detalhes": {
                    "perfil": configuracao["perfil"],
                    "inclinacao_telhado": "10%",
                    "gerar_cotas_auto": True,
                    "precisao": "mm",
                },
                "xdata": {
                    "trace_id": trace_id,
                    "normalizacao": "NBR/Petrobras",
                    "norma": "NBR-8800 + Petrobras",
                    "peso_estimado_kg": peso_estimado_kg,
                    "perfil": configuracao["perfil"],
                    "origem": "stress_test_50_porticos",
                },
            }
        )

    return {
        "header": {
            "projeto": "TESTE_STRESS_PETROBRAS_50",
            "versao": "1.0.0_ENTERPRISE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "norma": "NBR/Petrobras",
            "precisao": "mm",
            "gerar_cotas_auto": True,
        },
        "entidades": entidades_porticos,
    }


def calcular_peso_total_aco(entidades: list[Dict[str, Any]]) -> float:
    return round(sum(float(item.get("xdata", {}).get("peso_estimado_kg", 0) or 0) for item in entidades), 2)


def persistir_stress_test_result(
    output_dir: Path,
    envelope: Dict[str, Any],
    dispatch_results: list[Dict[str, Any]],
    execution_mode: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "stress_test_result.json"
    result_payload = {
        "header": envelope["header"],
        "summary": {
            "execution_mode": execution_mode,
            "qtd_porticos": len(envelope["entidades"]),
            "peso_total_aco_kg": calcular_peso_total_aco(envelope["entidades"]),
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        },
        "entidades": envelope["entidades"],
        "dispatch_results": dispatch_results,
    }
    result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return result_path


def _prune_expired(bucket: deque[float], cutoff: float) -> None:
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()


def _check_ai_rate_limit(user_email: str = "anonymous") -> None:
    """✓ PROBLEMA #6: Rate limiting por usuário + global."""
    now = time.time()
    cutoff = now - AI_RATE_WINDOW_SECONDS

    with _ai_rate_lock:
        _prune_expired(_ai_global_rate_limit, cutoff)
        if len(_ai_global_rate_limit) >= AI_JOBS_GLOBAL_LIMIT:
            logger.warning(f"Global AI rate limit hit: {len(_ai_global_rate_limit)} jobs/min")
            raise HTTPException(
                status_code=429,
                detail=f"Sistema sobrecarregado - máximo {AI_JOBS_GLOBAL_LIMIT} jobs/min globalmente"
            )

        user_jobs = _ai_job_rate_limit[user_email]
        _prune_expired(user_jobs, cutoff)
        if len(user_jobs) >= AI_JOBS_PER_MINUTE:
            logger.warning(f"Per-user AI rate limit hit for {user_email}: {len(user_jobs)} jobs/min")
            raise HTTPException(
                status_code=429,
                detail=f"Limite de {AI_JOBS_PER_MINUTE} jobs/min por usuário atingido"
            )

        user_jobs.append(now)
        _ai_global_rate_limit.append(now)


def _validate_ai_chat_payload(payload: Dict[str, Any]) -> None:
    """✓ PROBLEMA #6, #1: Validar input size e conteúdo."""
    # Limitar tamanho total do payload
    payload_size = len(json.dumps(payload).encode('utf-8'))
    if payload_size > 5000:  # 5KB max
        raise ValueError(f"Payload muito grande ({payload_size} bytes, máximo 5KB)")
    
    # desc é obrigatório
    desc = str(payload.get("desc", "")).strip()
    if not desc or len(desc) > 500:
        raise ValueError("Campo 'desc' obrigatório (máximo 500 caracteres)")
    
    # Optional fields validation
    try:
        diameter = float(str(payload.get("diameter", "0")))
        length = float(str(payload.get("length", "0")))
    except (ValueError, TypeError):
        raise ValueError("Diâmetro e comprimento devem ser números válidos")
    
    details = str(payload.get("details", "")).strip()
    if len(details) > 200:
        raise ValueError("Campo 'details' não pode exceder 200 caracteres")
    
    code = str(payload.get("code", "")).strip()
    if len(code) > 50:
        raise ValueError("Campo 'code' não pode exceder 50 caracteres")


@router.post("/generate-project")
async def submit_generate_project_job(
    payload: Dict[str, Any],
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """Submete um job para gerar projeto."""
    try:
        job_id = job_manager.submit_job("generate_project", payload)
        return {"job_id": job_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao submeter job: {str(e)}")


@router.post("/rebuild-stats")
async def submit_rebuild_stats_job(
    payload: Dict[str, Any] = None,
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """Submete um job para rebuild das estatísticas."""
    try:
        payload = payload or {}
        job_id = job_manager.submit_job("rebuild_stats", payload)
        return {"job_id": job_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao submeter job: {str(e)}")


@router.post("/excel-batch")
async def submit_excel_batch_job(
    payload: Dict[str, Any],
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """Submete um job para processar batch Excel."""
    try:
        if "excel_path" not in payload:
            raise HTTPException(status_code=400, detail="excel_path é obrigatório")
        job_id = job_manager.submit_job("excel_batch", payload)
        return {"job_id": job_id, "status": "submitted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao submeter job: {str(e)}")


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Obtém status de um job."""
    try:
        status = job_manager.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter status: {str(e)}")


@router.post("/ai/chat")
async def submit_ai_chat_job(
    payload: Dict[str, Any],
    request: Request,
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """Submete job AI CAD com validação rigorosa e rate limiting."""
    try:
        # ✓ PROBLEMA #6: Validar input tamanho
        _validate_ai_chat_payload(payload)
        
        # ✓ PROBLEMA #6: Rate limiting por usuário  
        user_email = request.headers.get("X-User-Email", "anonymous")
        _check_ai_rate_limit(user_email)
        
        logger.info(f"Submitting AI job for {user_email}: {payload.get('desc', '')[:30]}...")
        job_id = job_manager.submit_job("ai_cad", payload)
        return {"job_id": job_id, "status": "submitted"}
        
    except ValueError as e:
        logger.warning(f"Validation error in AI job submission: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao submeter job AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao submeter job AI: {str(e)}")


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    job_manager: AsyncJobManager = Depends(get_job_manager),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """Cancela um job (se possível)."""
    try:
        # Por enquanto, apenas marcar como cancelado se ainda não foi processado
        status = job_manager.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job não encontrado")

        if status["status"] == "pending":
            job_manager.update_job_status(job_id, "cancelled")
            return {"message": "Job cancelado"}
        else:
            raise HTTPException(status_code=400, detail="Job não pode ser cancelado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar job: {str(e)}")


@router.post("/stress/porticos-50")
async def submit_stress_50_porticos(
    config: AppConfig = Depends(get_app_config),
    output_dir: Path = Depends(get_output_dir),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Dispara 50 pórticos para fila cad_jobs com XData de rastreabilidade."""
    try:
        from celery_app import run_task_with_broker_fallback

        tracemalloc.start()
        start = time.perf_counter()
        envelope = gerar_teste_stress_50_porticos()
        task_ids: list[str] = []
        dispatch_results: list[Dict[str, Any]] = []
        used_fallback = False

        def _dispatch_entidade(entidade: Dict[str, Any]) -> Dict[str, Any]:
            payload_task = {
                "header": envelope["header"],
                "entidade": entidade,
                "plugin": {
                    "nome": "AutoCAD.CSharp.Plugin",
                    "comando": "executar_desenho_portico",
                },
                "health_monitoring": {
                    "enabled": True,
                    "collect_response_time_ms": True,
                    "collect_memory_mb": True,
                },
            }

            result, eager_mode = run_task_with_broker_fallback(
                "celery_tasks.cad_plugin_dispatch_task",
                queue="cad_jobs",
                routing_key="cad_jobs",
                priority=8,
                *[payload_task],
            )
            if eager_mode:
                eager_result = result.get()
                return {
                    "task_id": str(eager_result.get("task_id", entidade["id"])),
                    "fallback": True,
                    "result": eager_result,
                }

            return {
                "task_id": str(result.id),
                "fallback": False,
                "result": {
                    "status": "submitted",
                    "task_id": str(result.id),
                    "portico_id": entidade["id"],
                    "queue": "cad_jobs",
                },
            }

        max_workers = min(32, max(4, config.jobs_max_workers * 4), len(envelope["entidades"]))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            parallel_results = list(executor.map(_dispatch_entidade, envelope["entidades"]))

        for item in parallel_results:
            task_ids.append(item["task_id"])
            dispatch_results.append(item["result"])
            used_fallback = used_fallback or bool(item["fallback"]) or config.simulation_mode

        result_path = persistir_stress_test_result(
            output_dir,
            envelope,
            dispatch_results,
            execution_mode="eager" if used_fallback else "broker",
        )

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "Stress 50 pórticos submetido: jobs=%d elapsed_ms=%.2f mem_current_mb=%.2f mem_peak_mb=%.2f",
            len(task_ids),
            elapsed_ms,
            current_mem / 1024 / 1024,
            peak_mem / 1024 / 1024,
        )

        return {
            "status": "submitted",
            "queue": "cad_jobs",
            "jobs_submitted": len(task_ids),
            "job_ids": task_ids,
            "execution_mode": "eager" if used_fallback else "broker",
            "health": {
                "dispatch_elapsed_ms": elapsed_ms,
                "dispatch_memory_current_mb": round(current_mem / 1024 / 1024, 3),
                "dispatch_memory_peak_mb": round(peak_mem / 1024 / 1024, 3),
                "parallel_workers": max_workers,
                "target_response_ms_50_structures": 2000,
            },
            "cad_envelope": {
                "projeto": envelope["header"]["projeto"],
                "norma": envelope["header"]["norma"],
                "precisao": envelope["header"]["precisao"],
                "gerar_cotas_auto": envelope["header"]["gerar_cotas_auto"],
                "peso_total_aco_kg": calcular_peso_total_aco(envelope["entidades"]),
            },
            "result_file": str(result_path),
            "message": "Servidor pronto para envio do pacote ao plugin C# AutoCAD.",
        }
    except Exception as e:
        logger.error("Falha ao disparar stress 50 pórticos: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao disparar stress test: {str(e)}")