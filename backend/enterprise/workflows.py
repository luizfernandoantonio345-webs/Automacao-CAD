"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE WORKFLOW ENGINE
  Automação de Processos e Fluxos de Aprovação
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import asyncio

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status do workflow."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Tipos de passos do workflow."""
    MANUAL = "manual"           # Requer ação humana
    AUTOMATIC = "automatic"     # Executado automaticamente
    APPROVAL = "approval"       # Requer aprovação
    NOTIFICATION = "notification"
    CONDITION = "condition"     # Branch condicional
    PARALLEL = "parallel"       # Execução paralela
    WAIT = "wait"              # Aguardar evento/tempo
    AI_TASK = "ai_task"        # Tarefa de IA
    INTEGRATION = "integration" # Integração externa


class ApprovalDecision(str, Enum):
    """Decisões de aprovação."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"


@dataclass
class WorkflowStep:
    """Passo de um workflow."""
    id: str
    name: str
    type: StepType
    config: Dict[str, Any]
    next_steps: List[str]  # IDs dos próximos passos
    condition: Optional[str] = None  # Expressão condicional
    timeout_minutes: Optional[int] = None
    assignees: List[str] = field(default_factory=list)  # Para aprovações
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "config": self.config,
            "next_steps": self.next_steps,
            "condition": self.condition,
            "timeout_minutes": self.timeout_minutes,
            "assignees": self.assignees,
        }


@dataclass
class WorkflowDefinition:
    """Definição de um workflow."""
    id: str
    name: str
    description: str
    version: int
    trigger: str  # Evento que dispara o workflow
    steps: Dict[str, WorkflowStep]
    start_step: str
    created_at: str
    updated_at: str
    created_by: str
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "trigger": self.trigger,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "start_step": self.start_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "is_active": self.is_active,
        }


@dataclass
class StepExecution:
    """Execução de um passo."""
    step_id: str
    started_at: str
    finished_at: Optional[str]
    status: str
    result: Optional[Dict[str, Any]]
    executed_by: Optional[str]
    approval_decision: Optional[ApprovalDecision]
    comments: Optional[str]


@dataclass
class WorkflowInstance:
    """Instância de execução de um workflow."""
    id: str
    workflow_id: str
    workflow_version: int
    status: WorkflowStatus
    current_step: str
    context: Dict[str, Any]  # Dados do workflow
    step_executions: List[StepExecution]
    started_at: str
    finished_at: Optional[str]
    started_by: str
    error: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status.value,
            "current_step": self.current_step,
            "context": self.context,
            "step_executions": [
                {
                    "step_id": se.step_id,
                    "started_at": se.started_at,
                    "finished_at": se.finished_at,
                    "status": se.status,
                    "result": se.result,
                    "executed_by": se.executed_by,
                    "approval_decision": se.approval_decision.value if se.approval_decision else None,
                    "comments": se.comments,
                }
                for se in self.step_executions
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "started_by": self.started_by,
            "error": self.error,
        }


class WorkflowEngine:
    """Motor de execução de workflows."""
    
    _instance: Optional['WorkflowEngine'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self.step_handlers: Dict[StepType, Callable] = {}
        self._setup_handlers()
        self._seed_demo_workflows()
        logger.info("WorkflowEngine initialized")
    
    def _setup_handlers(self):
        """Configura handlers para tipos de passos."""
        self.step_handlers[StepType.AUTOMATIC] = self._execute_automatic
        self.step_handlers[StepType.AI_TASK] = self._execute_ai_task
        self.step_handlers[StepType.NOTIFICATION] = self._execute_notification
        self.step_handlers[StepType.INTEGRATION] = self._execute_integration
    
    def _seed_demo_workflows(self):
        """Adiciona workflows de demonstração."""
        # Workflow de aprovação de projeto
        project_approval = WorkflowDefinition(
            id="wf_project_approval",
            name="Aprovação de Projeto",
            description="Fluxo de aprovação para novos projetos de engenharia",
            version=1,
            trigger="project.created",
            steps={
                "start": WorkflowStep(
                    id="start",
                    name="Início",
                    type=StepType.AUTOMATIC,
                    config={"action": "initialize"},
                    next_steps=["quality_check"],
                ),
                "quality_check": WorkflowStep(
                    id="quality_check",
                    name="Verificação de Qualidade",
                    type=StepType.AI_TASK,
                    config={"ai": "QualityInspectorAI", "action": "full_inspection"},
                    next_steps=["review_results"],
                ),
                "review_results": WorkflowStep(
                    id="review_results",
                    name="Revisão dos Resultados",
                    type=StepType.CONDITION,
                    config={},
                    next_steps=["manager_approval", "auto_approve"],
                    condition="quality_score >= 90",
                ),
                "auto_approve": WorkflowStep(
                    id="auto_approve",
                    name="Aprovação Automática",
                    type=StepType.AUTOMATIC,
                    config={"action": "approve"},
                    next_steps=["notify_team"],
                ),
                "manager_approval": WorkflowStep(
                    id="manager_approval",
                    name="Aprovação do Gerente",
                    type=StepType.APPROVAL,
                    config={"required_approvers": 1},
                    next_steps=["notify_team"],
                    timeout_minutes=1440,  # 24 horas
                    assignees=["manager@empresa.com"],
                ),
                "notify_team": WorkflowStep(
                    id="notify_team",
                    name="Notificar Equipe",
                    type=StepType.NOTIFICATION,
                    config={
                        "template": "project_approved",
                        "channels": ["email", "teams"],
                    },
                    next_steps=["end"],
                ),
                "end": WorkflowStep(
                    id="end",
                    name="Fim",
                    type=StepType.AUTOMATIC,
                    config={"action": "complete"},
                    next_steps=[],
                ),
            },
            start_step="start",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            created_by="system",
        )
        
        # Workflow de análise de desenho
        drawing_analysis = WorkflowDefinition(
            id="wf_drawing_analysis",
            name="Análise Completa de Desenho",
            description="Pipeline de análise automática de desenhos CAD",
            version=1,
            trigger="drawing.uploaded",
            steps={
                "start": WorkflowStep(
                    id="start",
                    name="Início",
                    type=StepType.AUTOMATIC,
                    config={"action": "initialize"},
                    next_steps=["parallel_analysis"],
                ),
                "parallel_analysis": WorkflowStep(
                    id="parallel_analysis",
                    name="Análises Paralelas",
                    type=StepType.PARALLEL,
                    config={
                        "parallel_steps": [
                            "analyze_drawing",
                            "detect_conflicts",
                            "estimate_costs",
                        ]
                    },
                    next_steps=["generate_report"],
                ),
                "analyze_drawing": WorkflowStep(
                    id="analyze_drawing",
                    name="Analisar Desenho",
                    type=StepType.AI_TASK,
                    config={"ai": "DrawingAnalyzerAI"},
                    next_steps=[],
                ),
                "detect_conflicts": WorkflowStep(
                    id="detect_conflicts",
                    name="Detectar Conflitos",
                    type=StepType.AI_TASK,
                    config={"ai": "ConflictDetectorAI"},
                    next_steps=[],
                ),
                "estimate_costs": WorkflowStep(
                    id="estimate_costs",
                    name="Estimar Custos",
                    type=StepType.AI_TASK,
                    config={"ai": "CostEstimatorAI"},
                    next_steps=[],
                ),
                "generate_report": WorkflowStep(
                    id="generate_report",
                    name="Gerar Relatório",
                    type=StepType.AI_TASK,
                    config={"ai": "DocumentGeneratorAI", "template": "analysis_report"},
                    next_steps=["sync_sap"],
                ),
                "sync_sap": WorkflowStep(
                    id="sync_sap",
                    name="Sincronizar com SAP",
                    type=StepType.INTEGRATION,
                    config={"integration": "int_sap_001", "action": "sync_mto"},
                    next_steps=["end"],
                ),
                "end": WorkflowStep(
                    id="end",
                    name="Fim",
                    type=StepType.AUTOMATIC,
                    config={"action": "complete"},
                    next_steps=[],
                ),
            },
            start_step="start",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            created_by="system",
        )
        
        self.definitions[project_approval.id] = project_approval
        self.definitions[drawing_analysis.id] = drawing_analysis
    
    async def _execute_automatic(self, step: WorkflowStep, context: Dict) -> Dict:
        """Executa passo automático."""
        action = step.config.get("action", "noop")
        logger.info(f"Executing automatic step: {step.name} ({action})")
        return {"action": action, "success": True}
    
    async def _execute_ai_task(self, step: WorkflowStep, context: Dict) -> Dict:
        """Executa tarefa de IA."""
        ai_name = step.config.get("ai", "Unknown")
        logger.info(f"Executing AI task: {ai_name}")
        # Em produção: chama o router de IA
        return {"ai": ai_name, "success": True, "result": {}}
    
    async def _execute_notification(self, step: WorkflowStep, context: Dict) -> Dict:
        """Envia notificação."""
        template = step.config.get("template", "default")
        channels = step.config.get("channels", ["email"])
        logger.info(f"Sending notification: {template} via {channels}")
        return {"template": template, "channels": channels, "sent": True}
    
    async def _execute_integration(self, step: WorkflowStep, context: Dict) -> Dict:
        """Executa integração externa."""
        integration = step.config.get("integration")
        action = step.config.get("action")
        logger.info(f"Executing integration: {integration} - {action}")
        return {"integration": integration, "action": action, "success": True}
    
    def get_all_definitions(self) -> List[WorkflowDefinition]:
        """Retorna todas as definições de workflow."""
        return list(self.definitions.values())
    
    def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Obtém uma definição de workflow."""
        return self.definitions.get(workflow_id)
    
    def create_definition(
        self,
        name: str,
        description: str,
        trigger: str,
        steps: Dict[str, WorkflowStep],
        start_step: str,
        created_by: str,
    ) -> WorkflowDefinition:
        """Cria uma nova definição de workflow."""
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        
        definition = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            version=1,
            trigger=trigger,
            steps=steps,
            start_step=start_step,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )
        
        self.definitions[workflow_id] = definition
        logger.info(f"Created workflow definition: {name}")
        return definition
    
    async def start_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any],
        started_by: str,
    ) -> WorkflowInstance:
        """Inicia uma nova instância de workflow."""
        definition = self.definitions.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if not definition.is_active:
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        instance_id = f"wfi_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        
        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow_id,
            workflow_version=definition.version,
            status=WorkflowStatus.ACTIVE,
            current_step=definition.start_step,
            context=context,
            step_executions=[],
            started_at=now,
            finished_at=None,
            started_by=started_by,
            error=None,
        )
        
        self.instances[instance_id] = instance
        logger.info(f"Started workflow instance: {instance_id} for {workflow_id}")
        
        # Executar primeiro passo
        await self.execute_current_step(instance_id)
        
        return instance
    
    async def execute_current_step(self, instance_id: str) -> Optional[StepExecution]:
        """Executa o passo atual de uma instância."""
        instance = self.instances.get(instance_id)
        if not instance:
            return None
        
        definition = self.definitions.get(instance.workflow_id)
        if not definition:
            return None
        
        step = definition.steps.get(instance.current_step)
        if not step:
            return None
        
        # Criar execução
        execution = StepExecution(
            step_id=step.id,
            started_at=datetime.now(UTC).isoformat(),
            finished_at=None,
            status="running",
            result=None,
            executed_by=None,
            approval_decision=None,
            comments=None,
        )
        
        # Executar handler se disponível
        handler = self.step_handlers.get(step.type)
        if handler:
            try:
                result = await handler(step, instance.context)
                execution.result = result
                execution.status = "completed"
            except Exception as e:
                execution.status = "failed"
                execution.result = {"error": str(e)}
                instance.error = str(e)
        elif step.type in [StepType.MANUAL, StepType.APPROVAL]:
            execution.status = "waiting"
        else:
            execution.status = "completed"
        
        execution.finished_at = datetime.now(UTC).isoformat()
        instance.step_executions.append(execution)
        
        # Avançar para próximo passo se aplicável
        if execution.status == "completed" and step.next_steps:
            instance.current_step = step.next_steps[0]
            
            # Se for o último passo, completar workflow
            next_step = definition.steps.get(instance.current_step)
            if next_step and not next_step.next_steps:
                instance.status = WorkflowStatus.COMPLETED
                instance.finished_at = datetime.now(UTC).isoformat()
            else:
                # Continuar execução
                await self.execute_current_step(instance_id)
        
        return execution
    
    async def submit_approval(
        self,
        instance_id: str,
        decision: ApprovalDecision,
        approved_by: str,
        comments: Optional[str] = None,
    ) -> bool:
        """Submete decisão de aprovação."""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        definition = self.definitions.get(instance.workflow_id)
        step = definition.steps.get(instance.current_step)
        
        if not step or step.type != StepType.APPROVAL:
            return False
        
        # Encontrar execução atual
        for execution in instance.step_executions:
            if execution.step_id == step.id and execution.status == "waiting":
                execution.approval_decision = decision
                execution.executed_by = approved_by
                execution.comments = comments
                execution.status = "completed"
                execution.finished_at = datetime.now(UTC).isoformat()
                
                if decision == ApprovalDecision.REJECTED:
                    instance.status = WorkflowStatus.FAILED
                elif decision == ApprovalDecision.APPROVED:
                    # Avançar para próximo passo
                    if step.next_steps:
                        instance.current_step = step.next_steps[0]
                        await self.execute_current_step(instance_id)
                
                return True
        
        return False
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Obtém uma instância de workflow."""
        return self.instances.get(instance_id)
    
    def get_pending_approvals(self, user_email: str) -> List[Dict[str, Any]]:
        """Retorna aprovações pendentes para um usuário."""
        pending = []
        
        for instance in self.instances.values():
            if instance.status != WorkflowStatus.ACTIVE:
                continue
            
            definition = self.definitions.get(instance.workflow_id)
            if not definition:
                continue
            
            step = definition.steps.get(instance.current_step)
            if not step or step.type != StepType.APPROVAL:
                continue
            
            if user_email in step.assignees or not step.assignees:
                pending.append({
                    "instance_id": instance.id,
                    "workflow_name": definition.name,
                    "step_name": step.name,
                    "context": instance.context,
                    "started_at": instance.started_at,
                    "started_by": instance.started_by,
                })
        
        return pending
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do engine."""
        by_status = {}
        for instance in self.instances.values():
            status = instance.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        active_count = sum(1 for i in self.instances.values() if i.status == WorkflowStatus.ACTIVE)
        completed_count = sum(1 for i in self.instances.values() if i.status == WorkflowStatus.COMPLETED)
        
        return {
            "total_definitions": len(self.definitions),
            "total_instances": len(self.instances),
            "active_instances": active_count,
            "completed_instances": completed_count,
            "by_status": by_status,
        }


# Singleton instance
workflow_engine = WorkflowEngine()
