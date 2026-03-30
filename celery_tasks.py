#!/usr/bin/env python3
# ====================================================================
# celery_tasks.py - Tasks Celery Refatoradas do AsyncJobManager
# Convertidas de _execute_* em @app.task distribuídos
# ====================================================================

import json
import logging
import time
import sys
import tracemalloc
from pathlib import Path
from typing import Dict, Any, Optional

# Adicionar paths
PROJECT_ROOT = Path(__file__).resolve().parent
ENGINEERING_ROOT = PROJECT_ROOT / "engenharia_automacao"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from circuit_breaker import circuit_breaker, CircuitBreakerOpen
from dead_letter_queue import get_dlq
from gpu_support import gpu_task, should_use_gpu
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from celery_app import app

# Logger estruturado
logger = logging.getLogger('celery.task')

# ✓ Prometheus metrics wrapper
try:
    from prometheus_client import Counter, Histogram, Gauge
    
    TASKS_TOTAL = Counter(
        'celery_tasks_total',
        'Total tasks',
        ['task_name', 'status']
    )
    TASKS_DURATION = Histogram(
        'celery_task_duration_seconds',
        'Task duration',
        ['task_name']
    )
    QUEUE_SIZE = Gauge(
        'celery_queue_size',
        'Queue size',
        ['queue_name']
    )
except ImportError:
    logger.warning("prometheus_client não instalado - metrics desativadas")
    TASKS_TOTAL = None
    TASKS_DURATION = None
    QUEUE_SIZE = None


class LogErrorsTask(Task):
    """Base task com logging de erros."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name}({task_id}) falhou: {exc}")
        if TASKS_TOTAL:
            TASKS_TOTAL.labels(task_name=self.name, status='failed').inc()
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {self.name}({task_id}) retentando: {exc}")
    
    def on_success(self, result, task_id, args, kwargs):
        logger.info(f"Task {self.name}({task_id}) sucesso")
        if TASKS_TOTAL:
            TASKS_TOTAL.labels(task_name=self.name, status='success').inc()


# ====================================================================
# Task 1: Generate Project
# ====================================================================

@app.task(
    bind=True,
    base=LogErrorsTask,
    name='celery_tasks.generate_project_task',
    queue='cad_jobs',
    priority=5,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
)
def generate_project_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✓ Celery Task: Gera projeto CAD do payload.
    
    Args:
        payload: Dict com parâmetros do projeto
        
    Returns:
        Dict com resultado/caminho do arquivo
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        logger.info(f"Iniciando generate_project - task_id={task_id}", extra={
            'task_id': task_id,
            'job_type': 'generate_project',
            'payload_size': len(str(payload))
        })
        
        from engenharia_automacao.core.main import ProjectService
        from integration.python_api.dependencies import get_output_dir
        
        service = ProjectService()
        output_dir = get_output_dir()
        
        # Executar
        result_path = service.generate_project(
            payload,
            output_dir / f"{payload.get('code', 'AUTO')}.lsp",
            execute_in_autocad=False
        )
        
        result = {"path": str(result_path), "task_id": task_id}
        
        # Métricas
        duration = time.time() - start_time
        logger.info(f"generate_project completo: {duration:.2f}s", extra={
            'task_id': task_id,
            'job_type': 'generate_project',
            'duration': duration,
            'status': 'success'
        })
        if TASKS_DURATION:
            TASKS_DURATION.labels(task_name='generate_project_task').observe(duration)
        
        return result
        
    except SoftTimeLimitExceeded:
        logger.error("generate_project timeout (soft limit)")
        raise
    except Exception as exc:
        logger.exception(f"Erro em generate_project: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ====================================================================
# Task 2: Rebuild Stats
# ====================================================================

@app.task(
    bind=True,
    base=LogErrorsTask,
    name='celery_tasks.rebuild_stats_task',
    queue='cad_jobs',
    priority=5,
)
def rebuild_stats_task(self) -> Dict[str, Any]:
    """
    ✓ Celery Task: Reconstrói estatísticas gerais.
    
    Returns:
        Dict com stats
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        logger.info(f"Iniciando rebuild_stats - task_id={task_id}")
        
        from integration.python_api.dependencies import get_telemetry_store
        
        telemetry = get_telemetry_store()
        stats = telemetry.rebuild_stats()
        
        duration = time.time() - start_time
        logger.info(f"rebuild_stats completo: {duration:.2f}s")
        if TASKS_DURATION:
            TASKS_DURATION.labels(task_name='rebuild_stats_task').observe(duration)
        
        return stats
        
    except Exception as exc:
        logger.exception(f"Erro em rebuild_stats: {exc}")
        raise self.retry(exc=exc, countdown=300)


# ====================================================================
# Task 3: Excel Batch
# ====================================================================

@app.task(
    bind=True,
    base=LogErrorsTask,
    name='celery_tasks.excel_batch_task',
    queue='bulk_jobs',
    priority=3,
    autoretry_for=(Exception,),
    max_retries=2,
)
def excel_batch_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✓ Celery Task: Processa batch Excel.
    
    Args:
        payload: Dict com "excel_path"
        
    Returns:
        Dict com files gerados
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        logger.info(f"Iniciando excel_batch - task_id={task_id}")
        
        from engenharia_automacao.core.main import ProjectService
        from integration.python_api.dependencies import get_output_dir
        
        service = ProjectService()
        output_dir = get_output_dir()
        
        excel_path = Path(payload["excel_path"])
        generated = service.generate_projects_from_excel(excel_path, output_dir)
        
        result = {"files": [str(p) for p in generated], "count": len(generated), "task_id": task_id}
        
        duration = time.time() - start_time
        logger.info(f"excel_batch completo: {len(generated)} files em {duration:.2f}s")
        if TASKS_DURATION:
            TASKS_DURATION.labels(task_name='excel_batch_task').observe(duration)
        
        return result
        
    except Exception as exc:
        logger.exception(f"Erro em excel_batch: {exc}")
        raise self.retry(exc=exc, countdown=300)


# ====================================================================
# Task 4: AI CAD (High Priority)
# ====================================================================

@app.task(
    bind=True,
    base=LogErrorsTask,
    name='celery_tasks.ai_cad_task',
    queue='ai_cad',
    priority=10,  # Máxima prioridade
    time_limit=3600,  # 1h ao máximo
    soft_time_limit=3300,  # 55 min soft limit
    autoretry_for=(Exception,),
    max_retries=2,
)
@circuit_breaker("ai_cad", failure_threshold=3, recovery_timeout=300)
@gpu_task(device_id=0)
def ai_cad_task(self, payload: Dict[str, Any], device=None) -> Dict[str, Any]:
    """
    ✓ Celery Task: Gera LSP via IA (Ollama/LLM).
    
    Features: Validação rigorosa, retry com backoff, métricas.
    
    Args:
        payload: Dict com desc, diameter, length, details, code
        
    Returns:
        Dict com lsp_path, tokens, success
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        logger.info(f"Iniciando ai_cad - task_id={task_id}, desc={payload.get('desc', '')[:50]}")
        
        # ✓ Importar & validar Ollama
        try:
            from langchain_ollama import OllamaLLM
        except ImportError as exc:
            logger.error("langchain-ollama/ollama não instalados")
            raise ImportError("Instale: pip install -r requirements-celery.txt") from exc
        
        from integration.python_api.dependencies import get_output_dir, get_telemetry_store
        import re
        import math
        from integration.python_api.config import load_config
        CONFIG = load_config()
        
        # ✓ Validações
        desc = str(payload.get("desc", "")).strip()
        if not desc:
            raise ValueError("Campo 'desc' é obrigatório")
        if len(desc) > 500:
            raise ValueError("Campo 'desc' não pode exceder 500 caracteres")
        
        try:
            diameter = float(payload.get("diameter", 0))
            length = float(payload.get("length", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Diâmetro e comprimento devem ser números válidos: {e}") from e
        
        if not (0 < diameter <= 1_000_000) or not math.isfinite(diameter):
            raise ValueError(f"Diâmetro deve estar entre 0 e 1M: {diameter}")
        if not (0 < length <= 10_000_000) or not math.isfinite(length):
            raise ValueError(f"Comprimento deve estar entre 0 e 10M: {length}")
        
        details = str(payload.get("details", "")).strip()[:200]
        code = str(payload.get("code", "auto_ai"))
        code = re.sub(r"[^A-Za-z0-9_-]", "_", code).strip("_")[:50]
        if not code:
            code = "auto_ai"
        
        payload_clean = {
            "desc": desc,
            "diameter": diameter,
            "length": length,
            "details": details,
            "code": code,
        }
        
        # ✓ Verificar se deve usar GPU
        use_gpu = should_use_gpu("ai_cad", payload)
        if use_gpu and device:
            logger.info(f"Usando GPU para AI CAD: {device}")
        else:
            logger.info("Usando CPU para AI CAD")
        
        # ✓ LLM com retry
        llm = None
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries and not llm:
            try:
                logger.info(f"Conectando ao Ollama (tentativa {retry_count + 1}/{max_retries})")
                llm = OllamaLLM(
                    model=CONFIG.llm_model,
                    base_url=CONFIG.ollama_url,
                    max_tokens=CONFIG.max_tokens,
                    timeout=30,
                )
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Ollama não conectou após {max_retries} tentativas: {e}")
                    raise RuntimeError(f"Ollama indisponível em {CONFIG.ollama_url}") from e
                time.sleep(1 * retry_count)
        
        # ✓ Invocar LLM
        prompt = f"""Gere código LSP AutoCAD para: {desc}
Parâmetros: Ø{diameter}mm x {length}mm, {details}
Retorne APENAS o código LSP válido, sem explicações."""
        
        try:
            logger.info(f"Invocando Ollama para: {desc[:50]}")
            response = llm.invoke(prompt)
            
            if not response:
                raise ValueError("Ollama retornou resposta vazia")
            
            response = response.strip()
            if len(response) < 10:
                logger.warning(f"Resposta curta: {response[:50]}")
        
        except Exception as e:
            logger.error(f"Erro ao invocar Ollama: {e}")
            raise RuntimeError(f"Falha ao gerar LSP via Ollama: {str(e)}") from e
        
        # ✓ Limitar tamanho
        if len(response) > 10_000:
            logger.warning(f"Resposta truncada de {len(response)} para 10k chars")
            response = response[:10_000]
        
        # ✓ Salvar arquivo
        try:
            output_dir = get_output_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            lsp_name = f"{code}_ai.lsp"
            lsp_path = output_dir / lsp_name
            
            if not str(lsp_path).startswith(str(output_dir)):
                raise ValueError("Caminho LSP inválido - possível path traversal")
            
            lsp_path.write_text(response, encoding="utf-8")
            logger.info(f"LSP salvo: {lsp_path} ({len(response)} bytes)")
        
        except Exception as e:
            logger.error(f"Erro ao salvar LSP: {e}")
            raise RuntimeError(f"Falha ao salvar arquivo: {str(e)}") from e
        
        # ✓ Telemetria (non-blocking)
        try:
            telemetry = get_telemetry_store()
            telemetry.record_event(
                payload={
                    "code": code,
                    "company": str(payload.get('company', 'ai'))[:100],
                    "part_name": desc[:100],
                    "diameter": diameter,
                    "length": length,
                },
                source='ai_cad',
                result_path=str(lsp_path)
            )
        except Exception as e:
            logger.warning(f"Falha ao registrar telemetria: {e}")
        
        # ✓ Resultado
        tokens = len(response.split())
        tokens = max(tokens, 50)
        
        result = {
            "lsp_path": str(lsp_path),
            "tokens": tokens,
            "ai_response": response[:1000],
            "success": True,
            "task_id": task_id,
            "ai_model_version": CONFIG.llm_model,
        }
        
        duration = time.time() - start_time
        logger.info(f"ai_cad completo: {tokens} tokens em {duration:.2f}s")
        if TASKS_DURATION:
            TASKS_DURATION.labels(task_name='ai_cad_task').observe(duration)
        
        return result
        
    except SoftTimeLimitExceeded:
        logger.error(f"ai_cad timeout (soft limit) - task_id={task_id}")
        # ✓ FASE 3: Adicionar à DLQ
        dlq = get_dlq()
        dlq.add_failed_job("ai_cad", payload, "SoftTimeLimitExceeded", task_id, self.request.retries)
        raise
    except Exception as exc:
        logger.exception(f"Erro em ai_cad: {exc}")
        # ✓ FASE 3: Adicionar à DLQ
        dlq = get_dlq()
        dlq.add_failed_job("ai_cad", payload, str(exc), task_id, self.request.retries)
        
        remaining_retries = self.max_retries - self.request.retries
        if remaining_retries > 0:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            logger.error(f"Max retries atingido para ai_cad - task_id={task_id}")
            raise


# ====================================================================
# Periodic Tasks (Celery Beat)
# ====================================================================

@app.task(bind=True, name='celery_tasks.health_check_task')
def health_check_task(self):
    """✓ Health check periódico dos workers."""
    try:
        active = app.control.inspect().active()
        logger.info(f"Health check OK - {len(active or {})} workers ativos")
        return {"status": "ok", "workers": len(active or {})}
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        raise


@app.task(bind=True, name='celery_tasks.cleanup_old_jobs_task')
def cleanup_old_jobs_task(self):
    """✓ Limpa jobs antigos do Redis a cada 1h."""
    try:
        from integration.python_api.async_jobs import AsyncJobManager
        from integration.python_api.config import load_config

        config = load_config()
        manager = AsyncJobManager(config.jobs_redis_url)
        cleaned = manager.cleanup_old_jobs(max_age_seconds=86400)  # 24h
        logger.info(f"Limpou {cleaned} jobs antigos")
        return {"cleaned": cleaned}
    except Exception as e:
        logger.error(f"Cleanup falhou: {e}")
        raise


@app.task(
    bind=True,
    base=LogErrorsTask,
    name='celery_tasks.cad_plugin_dispatch_task',
    queue='cad_jobs',
    priority=8,
    autoretry_for=(Exception,),
    max_retries=2,
)
def cad_plugin_dispatch_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Monta comando para plugin C# AutoCAD com XData completo por pórtico."""
    task_id = self.request.id
    started_at = time.perf_counter()
    tracemalloc.start()

    try:
        header = payload.get('header') or {}
        entidade = payload.get('entidade') or {}
        xdata = entidade.get('xdata') or {}

        if entidade.get('tipo') != 'PORTICO_COMPLETO':
            raise ValueError('Entidade inválida para cad_plugin_dispatch_task')

        if not xdata.get('norma'):
            raise ValueError('XData obrigatório: norma')
        if xdata.get('peso_estimado_kg') in (None, ''):
            raise ValueError('XData obrigatório: peso_estimado_kg')

        comando_cad = {
            'event': 'comando_cad',
            'plugin': payload.get('plugin') or {
                'nome': 'AutoCAD.CSharp.Plugin',
                'comando': 'executar_desenho_portico',
            },
            'header': {
                'projeto': header.get('projeto'),
                'versao': header.get('versao'),
                'timestamp': header.get('timestamp'),
                'precisao': header.get('precisao', 'mm'),
                'gerar_cotas_auto': bool(header.get('gerar_cotas_auto', True)),
            },
            'entidade': entidade,
            'xdata': {
                'trace_id': xdata.get('trace_id'),
                'norma': xdata.get('norma'),
                'normalizacao': xdata.get('normalizacao', 'NBR/Petrobras'),
                'peso_estimado_kg': xdata.get('peso_estimado_kg'),
                'perfil': xdata.get('perfil'),
                'origem': xdata.get('origem', 'stress_test_50_porticos'),
                'task_id': task_id,
            },
        }

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        tracemalloc.stop()

        logger.info(
            'cad_plugin_dispatch task_id=%s portico=%s elapsed_ms=%.2f mem_current_mb=%.3f mem_peak_mb=%.3f',
            task_id,
            entidade.get('id'),
            elapsed_ms,
            current_mem / 1024 / 1024,
            peak_mem / 1024 / 1024,
        )

        if TASKS_DURATION:
            TASKS_DURATION.labels(task_name='cad_plugin_dispatch_task').observe(elapsed_ms / 1000.0)

        return {
            'status': 'ready_for_autocad',
            'task_id': task_id,
            'portico_id': entidade.get('id'),
            'queue': 'cad_jobs',
            'health': {
                'response_time_ms': elapsed_ms,
                'memory_current_mb': round(current_mem / 1024 / 1024, 3),
                'memory_peak_mb': round(peak_mem / 1024 / 1024, 3),
            },
            'cad_command': comando_cad,
        }
    except Exception as exc:
        try:
            tracemalloc.stop()
        except Exception:
            pass
        logger.exception('Erro em cad_plugin_dispatch_task: %s', exc)
        raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))
