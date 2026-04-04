#!/usr/bin/env python3
# ====================================================================
# celery_config.py - Configuração Celery Robusta para Fase 1
# Features: Retries, timeouts, rate limiting, monitoring
# ====================================================================

import os
from pathlib import Path
from kombu import Exchange, Queue
from datetime import timedelta

# ✓ Broker & Backend
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672/")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# ✓ Timeouts & Execution
CELERY_TASK_TIME_LIMIT = 3600  # 1 hora max (hard timeout)
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 min (soft timeout - gera exceção)
task_acks_late = True  # Reconhecer após execução (não antes)
task_reject_on_worker_lost = True  # Rejeitar se worker morre

# ✓ Retries & Routing
CELERY_TASK_AUTORETRY_FOR = (Exception,)  # Auto-retry em exceções
task_max_retries = 3
task_default_retry_delay = 60  # 1 min entre retries
task_default_queue = 'default'
task_default_exchange = 'tasks'
task_default_routing_key = 'task.default'

# ✓ Queues: Separar por tipo de job (prioridade)
CELERY_QUEUES = (
    # High priority: AI CAD (lentos, mas críticos)
    Queue(
        'ai_cad',
        Exchange('ai_cad', type='direct'),
        routing_key='ai_cad'
    ),
    # Normal: Generate project, rebuild stats
    Queue(
        'cad_jobs',
        Exchange('cad_jobs', type='direct'),
        routing_key='cad_jobs'
    ),
    # Low priority: Excel batch (bulk)
    Queue(
        'bulk_jobs',
        Exchange('bulk_jobs', type='direct'),
        routing_key='bulk_jobs'
    ),
    # Default
    Queue(
        'default',
        Exchange('tasks', type='direct'),
        routing_key='task.default'
    ),
)

# ✓ Rotas: Mapear tasks para queues
CELERY_TASK_ROUTES = {
    'celery_tasks.ai_cad_task': {'queue': 'ai_cad', 'routing_key': 'ai_cad'},
    'celery_tasks.generate_project_task': {'queue': 'cad_jobs', 'routing_key': 'cad_jobs'},
    'celery_tasks.cad_plugin_dispatch_task': {'queue': 'cad_jobs', 'routing_key': 'cad_jobs'},
    'celery_tasks.rebuild_stats_task': {'queue': 'cad_jobs', 'routing_key': 'cad_jobs'},
    'celery_tasks.excel_batch_task': {'queue': 'bulk_jobs', 'routing_key': 'bulk_jobs'},
}

# ✓ Serialização
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# ✓ Konkurrency & Prefetch
worker_prefetch_multiplier = 4  # Cada worker prefetch 4 tasks
worker_max_tasks_per_child = 100  # Recycle worker após 100 tasks (memory leak prevention)
worker_disable_rate_limits = False
task_acks_late = True

# ✓ Resultados
result_expires = 86400  # 24h (limpar resultados antigos)
result_extended = True

# ✓ Monitoring
worker_enable_remote_control = True
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# ✓ FASE 2: Logging Estruturado JSON
import logging
import json
from datetime import datetime, UTC

class JSONFormatter(logging.Formatter):
    """✓ FASE 2: Formatter JSON para logs estruturados."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }
        
        # Adicionar campos extras se existirem
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'job_type'):
            log_entry['job_type'] = record.job_type
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
            
        # Adicionar exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
    ]
)

# Logger específico para Celery
celery_logger = logging.getLogger('celery')
celery_logger.setLevel(logging.INFO)

# Handler JSON para arquivo estruturado
_log_dir = Path(os.getenv('LOG_DIR', './logs'))
try:
    _log_dir.mkdir(parents=True, exist_ok=True)
    _celery_log_handler = logging.FileHandler(_log_dir / 'celery.log', mode='a')
    logging.getLogger().addHandler(_celery_log_handler)
    json_handler = logging.FileHandler(_log_dir / 'celery_structured.log', mode='a')
    json_handler.setFormatter(JSONFormatter())
    celery_logger.addHandler(json_handler)
except OSError:
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(JSONFormatter())
    celery_logger.addHandler(json_handler)

# Logger para tasks
task_logger = logging.getLogger('celery.task')
task_logger.setLevel(logging.INFO)
task_logger.addHandler(json_handler)

# ✓ Scheduled Tasks (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    # Health check a cada 30s
    'health-check': {
        'task': 'celery_tasks.health_check_task',
        'schedule': timedelta(seconds=30),
        'options': {'queue': 'default', 'priority': 10}
    },
    # Cleanup jobs antigos a cada 1h
    'cleanup-old-jobs': {
        'task': 'celery_tasks.cleanup_old_jobs_task',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'default', 'priority': 5}
    },
}
