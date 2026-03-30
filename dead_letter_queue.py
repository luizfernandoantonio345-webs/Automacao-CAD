#!/usr/bin/env python3
# ====================================================================
# dead_letter_queue.py - FASE 3: Dead Letter Queue
# Análise e reprocessamento de jobs falhados
# ====================================================================

import json
import os
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class DeadLetterQueue:
    """✓ FASE 3: DLQ para análise de jobs falhados."""
    
    def __init__(self, redis_url: str = None):
        try:
            import redis
            effective_url = redis_url or os.getenv("DLQ_REDIS_URL", "redis://localhost:6379/2")
            self.redis = redis.from_url(effective_url, decode_responses=True)
        except ImportError:
            self.redis = None
            logger.warning("Redis não disponível para DLQ")
    
    def add_failed_job(self, 
                      job_type: str, 
                      payload: Dict[str, Any], 
                      error: str, 
                      task_id: str = None,
                      retry_count: int = 0) -> str:
        """Adicionar job falhado à DLQ."""
        if not self.redis:
            return None
            
        dlq_id = f"dlq_{int(time.time())}_{task_id or 'unknown'}"
        
        dlq_entry = {
            "id": dlq_id,
            "job_type": job_type,
            "payload": payload,
            "error": error,
            "task_id": task_id,
            "retry_count": retry_count,
            "failed_at": datetime.utcnow().isoformat(),
            "status": "pending_analysis"
        }
        
        # Adicionar à lista DLQ
        self.redis.lpush("dlq:jobs", json.dumps(dlq_entry))
        
        # Index por tipo
        self.redis.sadd(f"dlq:types:{job_type}", dlq_id)
        
        # Index por erro
        error_type = error.split(":")[0] if ":" in error else "unknown"
        self.redis.sadd(f"dlq:errors:{error_type}", dlq_id)
        
        # TTL de 30 dias
        self.redis.expire("dlq:jobs", 30 * 24 * 3600)
        
        logger.warning(f"Job adicionado à DLQ: {dlq_id} - {error}")
        return dlq_id
    
    def get_failed_jobs(self, limit: int = 100) -> List[Dict]:
        """Obter jobs falhados para análise."""
        if not self.redis:
            return []
            
        jobs = self.redis.lrange("dlq:jobs", 0, limit - 1)
        return [json.loads(job) for job in jobs]
    
    def get_jobs_by_type(self, job_type: str) -> List[str]:
        """Obter jobs falhados por tipo."""
        if not self.redis:
            return []
            
        return self.redis.smembers(f"dlq:types:{job_type}")
    
    def get_jobs_by_error(self, error_type: str) -> List[str]:
        """Obter jobs falhados por tipo de erro."""
        if not self.redis:
            return []
            
        return self.redis.smembers(f"dlq:errors:{error_type}")
    
    def requeue_job(self, dlq_id: str) -> bool:
        """Tentar reprocessar job da DLQ."""
        if not self.redis:
            return False
            
        # Buscar job na DLQ
        jobs = self.get_failed_jobs(1000)
        job_data = None
        
        for job in jobs:
            if job["id"] == dlq_id:
                job_data = job
                break
        
        if not job_data:
            return False
        
        # Re-adicionar à fila original
        from integration.python_api.async_jobs import AsyncJobManager
        manager = AsyncJobManager()
        
        try:
            manager.submit_job(job_data["job_type"], job_data["payload"])
            
            # Remover da DLQ
            self.redis.lrem("dlq:jobs", 0, json.dumps(job_data))
            
            # Atualizar status
            job_data["status"] = "requeued"
            job_data["requeued_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Job requeued da DLQ: {dlq_id}")
            return True
            
        except Exception as e:
            logger.error(f"Falha ao requeue job {dlq_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas da DLQ."""
        if not self.redis:
            return {"error": "Redis não disponível"}

        total_jobs = self.redis.llen("dlq:jobs")

        # Contar por tipo
        types = {}
        for key in self.redis.scan_iter(match="dlq:types:*"):
            type_name = key.split(":")[-1]
            types[type_name] = self.redis.scard(key)

        # Contar por erro
        errors = {}
        for key in self.redis.scan_iter(match="dlq:errors:*"):
            error_name = key.split(":")[-1]
            errors[error_name] = self.redis.scard(key)

        return {
            "total_failed_jobs": total_jobs,
            "by_type": types,
            "by_error": errors,
            "timestamp": datetime.utcnow().isoformat()
        }

# ✓ Instância global
_dlq = None

def get_dlq() -> DeadLetterQueue:
    """Obter instância global da DLQ."""
    global _dlq
    if _dlq is None:
        _dlq = DeadLetterQueue()
    return _dlq