"""
═══════════════════════════════════════════════════════════════════════════════
  BASE AI ENGINE - Classe base para todas as IAs do sistema
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)


class AIStatus(Enum):
    """Estados possíveis de uma IA."""
    ONLINE = "online"
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    WARMING_UP = "warming_up"


class AIConfidence(Enum):
    """Níveis de confiança da análise."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class AIResult:
    """Resultado padronizado de qualquer análise de IA."""
    success: bool
    ai_name: str
    operation: str
    data: Dict[str, Any]
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "ai_name": self.ai_name,
            "operation": self.operation,
            "data": self.data,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp,
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class AIMetrics:
    """Métricas de performance de uma IA."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    avg_confidence: float = 0.0
    last_request_time: Optional[str] = None
    
    def update(self, result: AIResult):
        self.total_requests += 1
        self.total_processing_time_ms += result.processing_time_ms
        self.avg_processing_time_ms = self.total_processing_time_ms / self.total_requests
        
        if result.success:
            self.successful_requests += 1
            # Atualizar média de confiança
            n = self.successful_requests
            self.avg_confidence = ((self.avg_confidence * (n-1)) + result.confidence) / n
        else:
            self.failed_requests += 1
        
        self.last_request_time = result.timestamp


class BaseAI(ABC):
    """
    Classe base abstrata para todas as IAs do sistema.
    
    Implementa:
    - Logging padronizado
    - Métricas de performance
    - Tratamento de erros
    - Cache de resultados
    - Rate limiting
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.status = AIStatus.ONLINE
        self.metrics = AIMetrics()
        self._cache: Dict[str, AIResult] = {}
        self._cache_ttl_seconds = 300  # 5 minutos
        self._rate_limit_requests_per_minute = 60
        self._request_times: List[float] = []
        
        # Configurações específicas podem ser sobrescritas
        self.confidence_threshold = 0.6
        self.max_retries = 3
        self.timeout_seconds = 30
        
        logger.info(f"[{self.name}] AI Engine v{self.version} inicializada")
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """Método principal de processamento - deve ser implementado por cada IA."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Retorna lista de capacidades da IA."""
        pass
    
    def _check_rate_limit(self) -> bool:
        """Verifica se está dentro do rate limit."""
        now = time.time()
        # Remove requests antigos (mais de 1 minuto)
        self._request_times = [t for t in self._request_times if now - t < 60]
        
        if len(self._request_times) >= self._rate_limit_requests_per_minute:
            return False
        
        self._request_times.append(now)
        return True
    
    def _get_cache_key(self, input_data: Dict[str, Any]) -> str:
        """Gera chave de cache baseada no input."""
        return f"{self.name}:{hash(json.dumps(input_data, sort_keys=True))}"
    
    def _check_cache(self, cache_key: str) -> Optional[AIResult]:
        """Verifica se existe resultado em cache válido."""
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached_time = datetime.fromisoformat(cached.timestamp)
            if (datetime.now(UTC) - cached_time).seconds < self._cache_ttl_seconds:
                cached.metadata["from_cache"] = True
                return cached
            else:
                del self._cache[cache_key]
        return None
    
    async def execute(self, input_data: Dict[str, Any], use_cache: bool = True) -> AIResult:
        """
        Executa a IA com tratamento de erros, cache e métricas.
        Este é o método que deve ser chamado externamente.
        """
        start_time = time.time()
        
        # Verificar rate limit
        if not self._check_rate_limit():
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="execute",
                data={},
                errors=["Rate limit exceeded. Aguarde alguns segundos."],
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Verificar cache
        if use_cache:
            cache_key = self._get_cache_key(input_data)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                logger.debug(f"[{self.name}] Cache hit")
                return cached_result
        
        # Processar
        self.status = AIStatus.PROCESSING
        
        try:
            result = await asyncio.wait_for(
                self.process(input_data),
                timeout=self.timeout_seconds
            )
            
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Salvar em cache se sucesso
            if use_cache and result.success:
                self._cache[cache_key] = result
            
            self.status = AIStatus.ONLINE if result.success else AIStatus.ERROR
            
        except asyncio.TimeoutError:
            result = AIResult(
                success=False,
                ai_name=self.name,
                operation="execute",
                data={},
                errors=[f"Timeout após {self.timeout_seconds} segundos"],
                processing_time_ms=(time.time() - start_time) * 1000
            )
            self.status = AIStatus.ERROR
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro no processamento")
            result = AIResult(
                success=False,
                ai_name=self.name,
                operation="execute",
                data={},
                errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )
            self.status = AIStatus.ERROR
        
        # Atualizar métricas
        self.metrics.update(result)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual da IA."""
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "capabilities": self.get_capabilities(),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": (
                    self.metrics.successful_requests / self.metrics.total_requests * 100
                    if self.metrics.total_requests > 0 else 0
                ),
                "avg_processing_time_ms": round(self.metrics.avg_processing_time_ms, 2),
                "avg_confidence": round(self.metrics.avg_confidence, 3),
                "last_request": self.metrics.last_request_time,
            },
            "config": {
                "confidence_threshold": self.confidence_threshold,
                "timeout_seconds": self.timeout_seconds,
                "cache_ttl_seconds": self._cache_ttl_seconds,
            }
        }
    
    def clear_cache(self):
        """Limpa o cache da IA."""
        self._cache.clear()
        logger.info(f"[{self.name}] Cache limpo")


# Type hints para IAs especializadas
T = TypeVar('T', bound=BaseAI)


class AIRegistry:
    """Registro central de todas as IAs disponíveis."""
    
    _instance: Optional['AIRegistry'] = None
    _ais: Dict[str, BaseAI] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ais = {}
        return cls._instance
    
    def register(self, ai: BaseAI):
        """Registra uma nova IA."""
        self._ais[ai.name] = ai
        logger.info(f"[AIRegistry] IA '{ai.name}' registrada")
    
    def get(self, name: str) -> Optional[BaseAI]:
        """Obtém uma IA pelo nome."""
        return self._ais.get(name)
    
    def list_all(self) -> List[str]:
        """Lista todas as IAs registradas."""
        return list(self._ais.keys())
    
    def get_all_status(self) -> Dict[str, Any]:
        """Retorna status de todas as IAs."""
        return {name: ai.get_status() for name, ai in self._ais.items()}


# Instância global do registry
ai_registry = AIRegistry()
