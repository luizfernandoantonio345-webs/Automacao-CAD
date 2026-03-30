#!/usr/bin/env python3
# ====================================================================
# celery_app.py - Inicializa Celery App (singleton)
# Import: from celery_app import app
# ====================================================================

import os
import sys
import time
import tracemalloc
from uuid import uuid4
from pathlib import Path
import logging
from typing import Any

try:
    from celery import Celery
except ImportError:
    Celery = None

# Adicionar paths
PROJECT_ROOT = Path(__file__).resolve().parent
ENGINEERING_ROOT = PROJECT_ROOT / "engenharia_automacao"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

# ✓ Logger
logger = logging.getLogger(__name__)

class _LocalAsyncResult:
    def __init__(self, result: dict[str, Any]):
        self.id = result.get('task_id', str(uuid4()))
        self._result = result

    def get(self) -> dict[str, Any]:
        return self._result


class _LocalCeleryApp:
    def task(self, bind: bool = False, **_: Any):
        def decorator(func):
            return func
        return decorator

    def config_from_object(self, *_: Any, **__: Any) -> None:
        return None

    def autodiscover_tasks(self, *_: Any, **__: Any) -> None:
        return None

    def send_task(self, *_: Any, **__: Any):
        raise RuntimeError('Celery indisponível neste ambiente')

    def start(self) -> None:
        raise RuntimeError('Celery indisponível neste ambiente')


# ✓ Criar Celery app
app = Celery('cad_automacao') if Celery else _LocalCeleryApp()

# ✓ Carregar config
app.config_from_object('celery_config')

# ✓ Auto-discover tasks em celery_tasks.py
app.autodiscover_tasks(['celery_tasks'])

# ✓ Signal handlers
@app.task(bind=True)
def debug_task(self):
    """Task de debug para teste."""
    print(f'Request: {self.request!r}')
    return {'status': 'ok'}


def _run_local_cad_plugin_dispatch(payload: dict[str, Any]) -> _LocalAsyncResult:
    header = payload.get('header') or {}
    entidade = payload.get('entidade') or {}
    xdata = entidade.get('xdata') or {}

    if entidade.get('tipo') != 'PORTICO_COMPLETO':
        raise ValueError('Entidade inválida para execução local')
    if not xdata.get('norma'):
        raise ValueError('XData obrigatório: norma')
    if xdata.get('peso_estimado_kg') in (None, ''):
        raise ValueError('XData obrigatório: peso_estimado_kg')

    task_id = str(uuid4())
    started_at = time.perf_counter()
    tracemalloc.start()

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
    tracemalloc.stop()
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

    return _LocalAsyncResult(
        {
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
    )


def run_task_with_broker_fallback(task_name: str, *args: Any, **send_kwargs: Any):
    """Envia task ao broker; se falhar, executa localmente em eager mode."""
    try:
        return app.send_task(task_name, args=list(args), **send_kwargs), False
    except Exception as exc:
        logger.warning("Broker indisponível para %s. Executando localmente: %s", task_name, exc)
        if task_name == 'celery_tasks.cad_plugin_dispatch_task':
            return _run_local_cad_plugin_dispatch(args[0]), True
        raise


if __name__ == '__main__':
    app.start()
