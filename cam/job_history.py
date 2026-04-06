# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         JOB HISTORY - Histórico de Jobs CNC                   ║
║                                                                               ║
║  Sistema completo de histórico de jobs para rastreabilidade e análise.        ║
║  Permite salvar, recuperar e analisar jobs executados.                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status possíveis de um job."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class JobMaterial:
    """Dados do material do job."""
    type: str  # mild_steel, stainless, aluminum, etc.
    thickness: float  # mm
    width: float = 0  # mm (dimensão da chapa)
    height: float = 0  # mm
    weight_kg: float = 0
    cost_per_kg: float = 0


@dataclass
class JobParameters:
    """Parâmetros de corte do job."""
    amperage: int = 45
    cutting_speed: float = 2000  # mm/min
    pierce_delay: float = 0.5  # seconds
    pierce_height: float = 3.0  # mm
    cut_height: float = 1.5  # mm
    kerf_width: float = 1.5  # mm
    thc_enabled: bool = True
    arc_voltage: float = 120


@dataclass
class JobStatistics:
    """Estatísticas de execução do job."""
    total_pieces: int = 0
    completed_pieces: int = 0
    failed_pieces: int = 0
    total_cutting_length_mm: float = 0
    total_rapid_length_mm: float = 0
    total_pierces: int = 0
    estimated_time_minutes: float = 0
    actual_time_minutes: float = 0
    material_used_kg: float = 0
    waste_kg: float = 0
    efficiency_percent: float = 0


@dataclass
class JobCosts:
    """Custos do job."""
    material_cost: float = 0
    consumables_cost: float = 0
    labor_cost: float = 0
    machine_cost: float = 0
    total_cost: float = 0
    cost_per_piece: float = 0


@dataclass
class ConsumablesUsed:
    """Consumíveis usados no job."""
    electrode_wear_percent: float = 0
    nozzle_wear_percent: float = 0
    shield_wear_percent: float = 0
    gas_liters: float = 0
    arc_on_time_minutes: float = 0


@dataclass
class Job:
    """Representa um job de corte CNC completo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    status: JobStatus = JobStatus.PENDING
    priority: int = 0  # 0 = normal, 1 = alta, 2 = urgente
    
    # Dados do job
    material: JobMaterial = field(default_factory=lambda: JobMaterial(type="mild_steel", thickness=6))
    parameters: JobParameters = field(default_factory=JobParameters)
    statistics: JobStatistics = field(default_factory=JobStatistics)
    costs: JobCosts = field(default_factory=JobCosts)
    consumables: ConsumablesUsed = field(default_factory=ConsumablesUsed)
    
    # Arquivos
    source_file: str = ""  # DXF/SVG original
    gcode_file: str = ""   # G-code gerado
    nesting_job_id: str = ""  # ID do nesting se aplicável
    
    # Máquina
    machine_id: str = ""
    machine_name: str = ""
    operator_id: str = ""
    operator_name: str = ""
    
    # Metadados
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    error_log: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        data = asdict(self)
        data['status'] = self.status.value
        data['material'] = asdict(self.material)
        data['parameters'] = asdict(self.parameters)
        data['statistics'] = asdict(self.statistics)
        data['costs'] = asdict(self.costs)
        data['consumables'] = asdict(self.consumables)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Cria Job a partir de dicionário."""
        job = cls()
        job.id = data.get('id', job.id)
        job.name = data.get('name', '')
        job.description = data.get('description', '')
        job.created_at = data.get('created_at', job.created_at)
        job.updated_at = data.get('updated_at', job.updated_at)
        job.started_at = data.get('started_at')
        job.completed_at = data.get('completed_at')
        job.status = JobStatus(data.get('status', 'pending'))
        job.priority = data.get('priority', 0)
        
        if 'material' in data:
            mat = data['material']
            job.material = JobMaterial(**mat)
        
        if 'parameters' in data:
            job.parameters = JobParameters(**data['parameters'])
        
        if 'statistics' in data:
            job.statistics = JobStatistics(**data['statistics'])
        
        if 'costs' in data:
            job.costs = JobCosts(**data['costs'])
        
        if 'consumables' in data:
            job.consumables = ConsumablesUsed(**data['consumables'])
        
        job.source_file = data.get('source_file', '')
        job.gcode_file = data.get('gcode_file', '')
        job.nesting_job_id = data.get('nesting_job_id', '')
        job.machine_id = data.get('machine_id', '')
        job.machine_name = data.get('machine_name', '')
        job.operator_id = data.get('operator_id', '')
        job.operator_name = data.get('operator_name', '')
        job.tags = data.get('tags', [])
        job.notes = data.get('notes', '')
        job.error_log = data.get('error_log', [])
        
        return job


class JobHistoryManager:
    """
    Gerenciador de histórico de jobs.
    
    Armazena jobs em arquivo JSON para persistência.
    Em produção, pode ser substituído por banco de dados.
    """
    
    def __init__(self, storage_path: str = "data/job_history"):
        self.storage_path = storage_path
        self.jobs: Dict[str, Job] = {}
        self._ensure_storage()
        self._load_jobs()
    
    def _ensure_storage(self):
        """Garante que o diretório de armazenamento existe."""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
        except OSError:
            # Read-only filesystem (serverless)
            pass
    
    def _get_jobs_file(self) -> str:
        """Retorna caminho do arquivo de jobs."""
        return os.path.join(self.storage_path, "jobs.json")
    
    def _load_jobs(self):
        """Carrega jobs do disco."""
        try:
            jobs_file = self._get_jobs_file()
            if os.path.exists(jobs_file):
                with open(jobs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_data in data.get('jobs', []):
                        job = Job.from_dict(job_data)
                        self.jobs[job.id] = job
                logger.info(f"Carregados {len(self.jobs)} jobs do histórico")
        except Exception as e:
            logger.warning(f"Erro ao carregar histórico de jobs: {e}")
    
    def _save_jobs(self):
        """Salva jobs no disco."""
        try:
            jobs_file = self._get_jobs_file()
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "jobs": [job.to_dict() for job in self.jobs.values()]
            }
            with open(jobs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar histórico de jobs: {e}")
    
    def create_job(self, 
                   name: str,
                   material_type: str = "mild_steel",
                   thickness: float = 6,
                   **kwargs) -> Job:
        """
        Cria um novo job.
        
        Args:
            name: Nome do job
            material_type: Tipo de material
            thickness: Espessura em mm
            **kwargs: Outros campos do job
            
        Returns:
            Job criado
        """
        job = Job()
        job.name = name
        job.material = JobMaterial(type=material_type, thickness=thickness)
        
        # Aplicar kwargs
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        self.jobs[job.id] = job
        self._save_jobs()
        
        logger.info(f"Job criado: {job.id} - {job.name}")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Retorna um job pelo ID."""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **updates) -> Optional[Job]:
        """
        Atualiza um job existente.
        
        Args:
            job_id: ID do job
            **updates: Campos a atualizar
            
        Returns:
            Job atualizado ou None
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        job.updated_at = datetime.now().isoformat()
        self._save_jobs()
        
        return job
    
    def start_job(self, job_id: str, operator_id: str = "", operator_name: str = "") -> Optional[Job]:
        """Inicia execução de um job."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.now().isoformat()
        job.operator_id = operator_id
        job.operator_name = operator_name
        job.updated_at = datetime.now().isoformat()
        
        self._save_jobs()
        logger.info(f"Job iniciado: {job_id}")
        return job
    
    def complete_job(self, job_id: str, statistics: Dict[str, Any] = None) -> Optional[Job]:
        """Marca job como concluído."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now().isoformat()
        job.updated_at = datetime.now().isoformat()
        
        if statistics:
            for key, value in statistics.items():
                if hasattr(job.statistics, key):
                    setattr(job.statistics, key, value)
        
        # Calcular tempo real
        if job.started_at:
            started = datetime.fromisoformat(job.started_at)
            completed = datetime.fromisoformat(job.completed_at)
            job.statistics.actual_time_minutes = (completed - started).total_seconds() / 60
        
        self._save_jobs()
        logger.info(f"Job concluído: {job_id}")
        return job
    
    def fail_job(self, job_id: str, error: str) -> Optional[Job]:
        """Marca job como falho."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatus.FAILED
        job.error_log.append(f"[{datetime.now().isoformat()}] {error}")
        job.updated_at = datetime.now().isoformat()
        
        self._save_jobs()
        logger.error(f"Job falhou: {job_id} - {error}")
        return job
    
    def cancel_job(self, job_id: str, reason: str = "") -> Optional[Job]:
        """Cancela um job."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatus.CANCELLED
        if reason:
            job.notes = f"{job.notes}\nCancelado: {reason}".strip()
        job.updated_at = datetime.now().isoformat()
        
        self._save_jobs()
        logger.info(f"Job cancelado: {job_id}")
        return job
    
    def list_jobs(self, 
                  status: Optional[JobStatus] = None,
                  material: Optional[str] = None,
                  from_date: Optional[str] = None,
                  to_date: Optional[str] = None,
                  limit: int = 100,
                  offset: int = 0) -> List[Job]:
        """
        Lista jobs com filtros opcionais.
        
        Args:
            status: Filtrar por status
            material: Filtrar por material
            from_date: Data inicial (ISO format)
            to_date: Data final (ISO format)
            limit: Máximo de resultados
            offset: Pular N primeiros resultados
            
        Returns:
            Lista de jobs filtrados
        """
        jobs = list(self.jobs.values())
        
        # Aplicar filtros
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if material:
            jobs = [j for j in jobs if j.material.type == material]
        
        if from_date:
            jobs = [j for j in jobs if j.created_at >= from_date]
        
        if to_date:
            jobs = [j for j in jobs if j.created_at <= to_date]
        
        # Ordenar por data de criação (mais recente primeiro)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        # Aplicar paginação
        return jobs[offset:offset + limit]
    
    def get_statistics(self, 
                       from_date: Optional[str] = None,
                       to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna estatísticas agregadas dos jobs.
        
        Args:
            from_date: Data inicial
            to_date: Data final
            
        Returns:
            Dicionário com estatísticas
        """
        jobs = self.list_jobs(from_date=from_date, to_date=to_date, limit=10000)
        
        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.status == JobStatus.COMPLETED])
        failed_jobs = len([j for j in jobs if j.status == JobStatus.FAILED])
        pending_jobs = len([j for j in jobs if j.status == JobStatus.PENDING])
        in_progress = len([j for j in jobs if j.status == JobStatus.IN_PROGRESS])
        
        total_pieces = sum(j.statistics.total_pieces for j in jobs)
        completed_pieces = sum(j.statistics.completed_pieces for j in jobs)
        total_cutting_length = sum(j.statistics.total_cutting_length_mm for j in jobs)
        total_time = sum(j.statistics.actual_time_minutes for j in jobs)
        total_cost = sum(j.costs.total_cost for j in jobs)
        
        # Materiais usados
        materials = {}
        for job in jobs:
            mat = job.material.type
            if mat not in materials:
                materials[mat] = {"count": 0, "weight_kg": 0}
            materials[mat]["count"] += 1
            materials[mat]["weight_kg"] += job.statistics.material_used_kg
        
        return {
            "period": {
                "from": from_date,
                "to": to_date
            },
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "pending": pending_jobs,
                "in_progress": in_progress,
                "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            },
            "production": {
                "total_pieces": total_pieces,
                "completed_pieces": completed_pieces,
                "total_cutting_length_m": total_cutting_length / 1000,
                "total_time_hours": total_time / 60,
                "average_time_per_job_min": total_time / completed_jobs if completed_jobs > 0 else 0
            },
            "costs": {
                "total_cost": total_cost,
                "average_cost_per_job": total_cost / completed_jobs if completed_jobs > 0 else 0
            },
            "materials": materials
        }
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """
        Retorna resumo diário de produção.
        
        Args:
            date: Data no formato YYYY-MM-DD (default: hoje)
            
        Returns:
            Resumo do dia
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        
        jobs = self.list_jobs(from_date=start, to_date=end, limit=10000)
        
        completed = [j for j in jobs if j.status == JobStatus.COMPLETED]
        
        return {
            "date": date,
            "jobs_started": len(jobs),
            "jobs_completed": len(completed),
            "total_pieces": sum(j.statistics.completed_pieces for j in completed),
            "total_cutting_length_m": sum(j.statistics.total_cutting_length_mm for j in completed) / 1000,
            "total_time_hours": sum(j.statistics.actual_time_minutes for j in completed) / 60,
            "total_cost": sum(j.costs.total_cost for j in completed),
            "materials_used": list(set(j.material.type for j in jobs)),
            "operators": list(set(j.operator_name for j in jobs if j.operator_name))
        }
    
    def delete_job(self, job_id: str) -> bool:
        """Remove um job do histórico."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            logger.info(f"Job deletado: {job_id}")
            return True
        return False
    
    def search_jobs(self, query: str, limit: int = 50) -> List[Job]:
        """
        Busca jobs por texto em nome, descrição ou tags.
        
        Args:
            query: Texto de busca
            limit: Máximo de resultados
            
        Returns:
            Jobs encontrados
        """
        query_lower = query.lower()
        results = []
        
        for job in self.jobs.values():
            if (query_lower in job.name.lower() or
                query_lower in job.description.lower() or
                any(query_lower in tag.lower() for tag in job.tags)):
                results.append(job)
        
        results.sort(key=lambda j: j.created_at, reverse=True)
        return results[:limit]


# Instância global do gerenciador
_job_manager: Optional[JobHistoryManager] = None


def get_job_manager() -> JobHistoryManager:
    """Retorna instância do gerenciador de jobs."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobHistoryManager()
    return _job_manager


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS FastAPI
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class CreateJobRequest(BaseModel):
    """Request para criar um job."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    material_type: str = Field(default="mild_steel")
    thickness: float = Field(default=6, gt=0, le=100)
    priority: int = Field(default=0, ge=0, le=2)
    tags: List[str] = Field(default_factory=list)
    
    # Parâmetros de corte opcionais
    amperage: Optional[int] = None
    cutting_speed: Optional[float] = None


class UpdateJobRequest(BaseModel):
    """Request para atualizar um job."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class JobStatisticsUpdate(BaseModel):
    """Atualização de estatísticas do job."""
    total_pieces: Optional[int] = None
    completed_pieces: Optional[int] = None
    failed_pieces: Optional[int] = None
    total_cutting_length_mm: Optional[float] = None
    total_pierces: Optional[int] = None


@router.get("/")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    material: Optional[str] = Query(None, description="Filtrar por material"),
    from_date: Optional[str] = Query(None, description="Data inicial (ISO)"),
    to_date: Optional[str] = Query(None, description="Data final (ISO)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Lista jobs com filtros opcionais."""
    manager = get_job_manager()
    
    status_enum = JobStatus(status) if status else None
    jobs = manager.list_jobs(
        status=status_enum,
        material=material,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "count": len(jobs),
        "jobs": [job.to_dict() for job in jobs]
    }


@router.post("/")
async def create_job(request: CreateJobRequest):
    """Cria um novo job."""
    manager = get_job_manager()
    
    job = manager.create_job(
        name=request.name,
        material_type=request.material_type,
        thickness=request.thickness,
        description=request.description,
        priority=request.priority,
        tags=request.tags
    )
    
    # Aplicar parâmetros de corte se fornecidos
    if request.amperage:
        job.parameters.amperage = request.amperage
    if request.cutting_speed:
        job.parameters.cutting_speed = request.cutting_speed
    
    manager._save_jobs()
    
    return {
        "success": True,
        "job": job.to_dict()
    }


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Retorna detalhes de um job."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "job": job.to_dict()
    }


@router.patch("/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest):
    """Atualiza um job existente."""
    manager = get_job_manager()
    
    updates = request.model_dump(exclude_none=True)
    job = manager.update_job(job_id, **updates)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "job": job.to_dict()
    }


@router.post("/{job_id}/start")
async def start_job(
    job_id: str,
    operator_id: str = Query(default=""),
    operator_name: str = Query(default="")
):
    """Inicia execução de um job."""
    manager = get_job_manager()
    job = manager.start_job(job_id, operator_id, operator_name)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": "Job iniciado",
        "job": job.to_dict()
    }


@router.post("/{job_id}/complete")
async def complete_job(job_id: str, statistics: Optional[JobStatisticsUpdate] = None):
    """Marca job como concluído."""
    manager = get_job_manager()
    
    stats = statistics.model_dump(exclude_none=True) if statistics else None
    job = manager.complete_job(job_id, stats)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": "Job concluído",
        "job": job.to_dict()
    }


@router.post("/{job_id}/fail")
async def fail_job(job_id: str, error: str = Query(..., description="Mensagem de erro")):
    """Marca job como falho."""
    manager = get_job_manager()
    job = manager.fail_job(job_id, error)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": "Job marcado como falho",
        "job": job.to_dict()
    }


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, reason: str = Query(default="", description="Motivo")):
    """Cancela um job."""
    manager = get_job_manager()
    job = manager.cancel_job(job_id, reason)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": "Job cancelado",
        "job": job.to_dict()
    }


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Remove um job do histórico."""
    manager = get_job_manager()
    
    if not manager.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": "Job removido"
    }


@router.get("/stats/summary")
async def get_statistics(
    from_date: Optional[str] = Query(None, description="Data inicial (ISO)"),
    to_date: Optional[str] = Query(None, description="Data final (ISO)")
):
    """Retorna estatísticas agregadas dos jobs."""
    manager = get_job_manager()
    stats = manager.get_statistics(from_date, to_date)
    
    return {
        "success": True,
        "statistics": stats
    }


@router.get("/stats/daily")
async def get_daily_summary(date: Optional[str] = Query(None, description="Data (YYYY-MM-DD)")):
    """Retorna resumo diário de produção."""
    manager = get_job_manager()
    summary = manager.get_daily_summary(date)
    
    return {
        "success": True,
        "summary": summary
    }


@router.get("/search")
async def search_jobs(
    q: str = Query(..., min_length=1, description="Texto de busca"),
    limit: int = Query(50, ge=1, le=200)
):
    """Busca jobs por texto."""
    manager = get_job_manager()
    jobs = manager.search_jobs(q, limit)
    
    return {
        "success": True,
        "count": len(jobs),
        "jobs": [job.to_dict() for job in jobs]
    }
