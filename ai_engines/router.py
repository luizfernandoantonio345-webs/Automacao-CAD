"""
═══════════════════════════════════════════════════════════════════════════════
  AI ROUTER - Roteador central que orquestra todas as IAs
═══════════════════════════════════════════════════════════════════════════════

O AIRouter é responsável por:
  - Receber requisições e determinar qual(is) IA(s) devem processar
  - Orquestrar pipelines de múltiplas IAs
  - Agregar resultados de várias IAs
  - Gerenciar prioridades e filas
  - Fornecer uma interface unificada para o sistema

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import AIResult, BaseAI, AIStatus, ai_registry

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Prioridade de tarefas."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskType(Enum):
    """Tipos de tarefas que o router pode processar."""
    DRAWING_ANALYSIS = "drawing_analysis"
    PIPE_OPTIMIZATION = "pipe_optimization"
    CONFLICT_DETECTION = "conflict_detection"
    COST_ESTIMATION = "cost_estimation"
    QUALITY_INSPECTION = "quality_inspection"
    DOCUMENT_GENERATION = "document_generation"
    MAINTENANCE_PREDICTION = "maintenance_prediction"
    CHAT_ASSISTANCE = "chat_assistance"
    FULL_PIPELINE = "full_pipeline"  # Executa todas as IAs relevantes


@dataclass
class AITask:
    """Representa uma tarefa para ser processada."""
    id: str
    task_type: TaskType
    input_data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    requested_ais: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "pending"
    results: Dict[str, AIResult] = field(default_factory=dict)


class AIRouter:
    """
    Roteador central de IAs.
    
    Funcionalidades:
    - Roteamento inteligente baseado no tipo de tarefa
    - Execução paralela de múltiplas IAs
    - Agregação de resultados
    - Pipelines de processamento
    - Fila de tarefas com prioridades
    """
    
    # Mapeamento de tipos de tarefa para IAs
    TASK_TO_AI_MAP: Dict[TaskType, List[str]] = {
        TaskType.DRAWING_ANALYSIS: ["DrawingAnalyzer"],
        TaskType.PIPE_OPTIMIZATION: ["PipeOptimizer", "ConflictDetector"],
        TaskType.CONFLICT_DETECTION: ["ConflictDetector"],
        TaskType.COST_ESTIMATION: ["CostEstimator"],
        TaskType.QUALITY_INSPECTION: ["QualityInspector"],
        TaskType.DOCUMENT_GENERATION: ["DocumentGenerator"],
        TaskType.MAINTENANCE_PREDICTION: ["MaintenancePredictor"],
        TaskType.CHAT_ASSISTANCE: ["AssistantChatbot"],
        TaskType.FULL_PIPELINE: [
            "DrawingAnalyzer", "PipeOptimizer", "ConflictDetector",
            "CostEstimator", "QualityInspector"
        ],
    }
    
    def __init__(self):
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, AITask] = {}
        self.completed_tasks: Dict[str, AITask] = {}
        self._task_counter = 0
        self._is_running = False
        
        logger.info("[AIRouter] Inicializado")
    
    def _generate_task_id(self) -> str:
        """Gera um ID único para tarefa."""
        self._task_counter += 1
        return f"task_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{self._task_counter:04d}"
    
    def get_available_ais(self) -> List[Dict[str, Any]]:
        """Retorna lista de todas as IAs disponíveis com seus status."""
        return [
            {
                "name": name,
                "status": ai_registry.get(name).get_status() if ai_registry.get(name) else "not_loaded"
            }
            for name in ai_registry.list_all()
        ]
    
    def get_ai_for_task(self, task_type: TaskType) -> List[str]:
        """Retorna lista de IAs recomendadas para um tipo de tarefa."""
        return self.TASK_TO_AI_MAP.get(task_type, [])
    
    async def route(
        self,
        task_type: TaskType,
        input_data: Dict[str, Any],
        specific_ais: Optional[List[str]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Roteia uma tarefa para a(s) IA(s) apropriada(s).
        
        Args:
            task_type: Tipo da tarefa
            input_data: Dados de entrada
            specific_ais: Lista específica de IAs (opcional)
            priority: Prioridade da tarefa
            parallel: Se True, executa IAs em paralelo
            
        Returns:
            Resultado agregado de todas as IAs
        """
        task_id = self._generate_task_id()
        
        # Determinar quais IAs usar
        ai_names = specific_ais or self.TASK_TO_AI_MAP.get(task_type, [])
        
        if not ai_names:
            return {
                "success": False,
                "task_id": task_id,
                "error": f"Nenhuma IA configurada para task_type: {task_type.value}",
            }
        
        # Criar task
        task = AITask(
            id=task_id,
            task_type=task_type,
            input_data=input_data,
            priority=priority,
            requested_ais=ai_names,
        )
        
        self.active_tasks[task_id] = task
        task.status = "processing"
        
        logger.info(f"[AIRouter] Task {task_id} iniciada com IAs: {ai_names}")
        
        try:
            if parallel and len(ai_names) > 1:
                results = await self._execute_parallel(ai_names, input_data)
            else:
                results = await self._execute_sequential(ai_names, input_data)
            
            task.results = results
            task.status = "completed"
            
            # Agregar resultados
            aggregated = self._aggregate_results(results)
            aggregated["task_id"] = task_id
            aggregated["task_type"] = task_type.value
            aggregated["ais_used"] = ai_names
            
            # Mover para completed
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
            return aggregated
            
        except Exception as e:
            logger.exception(f"[AIRouter] Erro na task {task_id}")
            task.status = "error"
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
            }
    
    async def _execute_parallel(
        self,
        ai_names: List[str],
        input_data: Dict[str, Any]
    ) -> Dict[str, AIResult]:
        """Executa múltiplas IAs em paralelo."""
        tasks = []
        valid_ais = []
        
        for name in ai_names:
            ai = ai_registry.get(name)
            if ai:
                tasks.append(ai.execute(input_data))
                valid_ais.append(name)
            else:
                logger.warning(f"[AIRouter] IA '{name}' não encontrada")
        
        if not tasks:
            return {}
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            name: (
                result if isinstance(result, AIResult)
                else AIResult(
                    success=False,
                    ai_name=name,
                    operation="execute",
                    data={},
                    errors=[str(result)]
                )
            )
            for name, result in zip(valid_ais, results)
        }
    
    async def _execute_sequential(
        self,
        ai_names: List[str],
        input_data: Dict[str, Any]
    ) -> Dict[str, AIResult]:
        """Executa IAs sequencialmente, passando output para próxima."""
        results = {}
        current_data = input_data.copy()
        
        for name in ai_names:
            ai = ai_registry.get(name)
            if not ai:
                logger.warning(f"[AIRouter] IA '{name}' não encontrada")
                continue
            
            try:
                result = await ai.execute(current_data)
                results[name] = result
                
                # Passar dados para próxima IA
                if result.success:
                    current_data.update(result.data)
                    current_data[f"{name}_result"] = result.data
                    
            except Exception as e:
                results[name] = AIResult(
                    success=False,
                    ai_name=name,
                    operation="execute",
                    data={},
                    errors=[str(e)]
                )
        
        return results
    
    def _aggregate_results(self, results: Dict[str, AIResult]) -> Dict[str, Any]:
        """Agrega resultados de múltiplas IAs."""
        if not results:
            return {
                "success": False,
                "error": "Nenhum resultado disponível"
            }
        
        all_successful = all(r.success for r in results.values())
        partial_success = any(r.success for r in results.values())
        
        # Calcular confiança média
        confidences = [r.confidence for r in results.values() if r.success]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Coletar todos os warnings e errors
        all_warnings = []
        all_errors = []
        combined_data = {}
        
        for name, result in results.items():
            all_warnings.extend([f"[{name}] {w}" for w in result.warnings])
            all_errors.extend([f"[{name}] {e}" for e in result.errors])
            combined_data[name] = result.data
        
        # Tempo total de processamento
        total_time = sum(r.processing_time_ms for r in results.values())
        
        return {
            "success": all_successful,
            "partial_success": partial_success and not all_successful,
            "confidence": round(avg_confidence, 3),
            "data": combined_data,
            "processing_time_ms": round(total_time, 2),
            "warnings": all_warnings,
            "errors": all_errors,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    
    async def run_full_pipeline(
        self,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executa o pipeline completo de análise para um projeto.
        
        Pipeline:
        1. DrawingAnalyzer - Extrai informações do desenho
        2. PipeOptimizer - Otimiza rotas (paralelo com ConflictDetector)
        3. ConflictDetector - Detecta conflitos
        4. CostEstimator - Calcula custos
        5. QualityInspector - Verifica qualidade
        """
        return await self.route(
            task_type=TaskType.FULL_PIPELINE,
            input_data=project_data,
            parallel=False  # Sequencial para pipeline completo
        )
    
    def get_router_status(self) -> Dict[str, Any]:
        """Retorna status do router."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "total_tasks_processed": self._task_counter,
            "available_ais": ai_registry.list_all(),
            "task_types": [t.value for t in TaskType],
        }
    
    # Métodos de conveniência para cada tipo de tarefa
    
    async def analyze_drawing(self, drawing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa um desenho CAD."""
        return await self.route(TaskType.DRAWING_ANALYSIS, drawing_data)
    
    async def optimize_pipes(self, pipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Otimiza rotas de tubulação."""
        return await self.route(TaskType.PIPE_OPTIMIZATION, pipe_data)
    
    async def detect_conflicts(self, components_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detecta conflitos entre componentes."""
        return await self.route(TaskType.CONFLICT_DETECTION, components_data)
    
    async def estimate_costs(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estima custos do projeto."""
        return await self.route(TaskType.COST_ESTIMATION, project_data)
    
    async def inspect_quality(self, inspection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Inspeciona qualidade."""
        return await self.route(TaskType.QUALITY_INSPECTION, inspection_data)
    
    async def generate_document(self, doc_request: Dict[str, Any]) -> Dict[str, Any]:
        """Gera documentação."""
        return await self.route(TaskType.DOCUMENT_GENERATION, doc_request)
    
    async def predict_maintenance(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prediz manutenção necessária."""
        return await self.route(TaskType.MAINTENANCE_PREDICTION, asset_data)
    
    async def chat(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa mensagem do chatbot."""
        return await self.route(
            TaskType.CHAT_ASSISTANCE,
            {"message": message, "context": context or {}}
        )


# Instância global do router
ai_router = AIRouter()
