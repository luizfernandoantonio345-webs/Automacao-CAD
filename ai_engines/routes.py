"""
═══════════════════════════════════════════════════════════════════════════════
  AI ENGINE API ROUTES - Endpoints de API para sistema de IAs
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Importar IAs
from ai_engines import (
    AIRouter as AIEngineRouter,
    DrawingAnalyzerAI,
    PipeOptimizerAI,
    ConflictDetectorAI,
    CostEstimatorAI,
    QualityInspectorAI,
    DocumentGeneratorAI,
    MaintenancePredictorAI,
    AssistantChatbotAI,
)
from ai_engines.base import ai_registry
from ai_engines.router import TaskType, TaskPriority, ai_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Engines"])


# ════════════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Request para o chatbot."""
    message: str = Field(..., description="Mensagem do usuário")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexto adicional")


class AnalysisRequest(BaseModel):
    """Request genérico para análises."""
    data: Dict[str, Any] = Field(..., description="Dados para análise")
    options: Dict[str, Any] = Field(default_factory=dict, description="Opções de análise")


class PipelineRequest(BaseModel):
    """Request para pipeline completo."""
    project_data: Dict[str, Any] = Field(..., description="Dados do projeto")
    include_ais: List[str] = Field(default=[], description="IAs específicas a usar")
    parallel: bool = Field(default=True, description="Executar em paralelo")


# ════════════════════════════════════════════════════════════════════════════
# STATUS & INFO ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_ai_status():
    """Retorna status de todas as IAs disponíveis."""
    return {
        "status": "ok",
        "router": ai_router.get_router_status(),
        "engines": ai_registry.get_all_status(),
    }


@router.get("/engines")
async def list_engines():
    """Lista todas as IAs disponíveis e suas capacidades."""
    engines = []
    for name in ai_registry.list_all():
        ai = ai_registry.get(name)
        if ai:
            engines.append({
                "name": ai.name,
                "version": ai.version,
                "status": ai.status.value,
                "capabilities": ai.get_capabilities(),
            })
    return {"engines": engines}


@router.get("/engines/{engine_name}")
async def get_engine_details(engine_name: str):
    """Retorna detalhes de uma IA específica."""
    ai = ai_registry.get(engine_name)
    if not ai:
        raise HTTPException(status_code=404, detail=f"IA '{engine_name}' não encontrada")
    return ai.get_status()


# ════════════════════════════════════════════════════════════════════════════
# CHATBOT ENDPOINTS (com Guardrails)
# ════════════════════════════════════════════════════════════════════════════

from ai_engines.ai_guardrails import apply_guardrails

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Envia mensagem para o chatbot assistente.
    
    Aplica guardrails para garantir que respostas sejam apenas
    sobre tópicos de engenharia, CAD e automação industrial.
    """
    # Aplicar guardrails
    guardrail_result = apply_guardrails(request.message)
    
    if not guardrail_result["allowed"]:
        # Mensagem fora do escopo - retornar redirecionamento
        return {
            "success": True,
            "response": guardrail_result["redirect"],
            "data": {
                "AssistantChatbot": {
                    "response": guardrail_result["redirect"],
                    "filtered": True,
                    "category": guardrail_result["category"],
                }
            },
            "guardrails": {
                "blocked": True,
                "category": guardrail_result["category"],
                "confidence": guardrail_result["confidence"],
            }
        }
    
    # Mensagem permitida - processar normalmente
    result = await ai_router.chat(request.message, request.context)
    return result


# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/analyze/drawing")
async def analyze_drawing(request: AnalysisRequest):
    """Analisa um desenho CAD."""
    result = await ai_router.analyze_drawing(request.data)
    return result


@router.post("/analyze/pipes")
async def analyze_pipes(request: AnalysisRequest):
    """Otimiza ou analisa rotas de tubulação."""
    result = await ai_router.optimize_pipes(request.data)
    return result


@router.post("/analyze/conflicts")
async def detect_conflicts(request: AnalysisRequest):
    """Detecta conflitos entre componentes."""
    result = await ai_router.detect_conflicts(request.data)
    return result


@router.post("/analyze/quality")
async def inspect_quality(request: AnalysisRequest):
    """Executa inspeção de qualidade."""
    result = await ai_router.inspect_quality(request.data)
    return result


# ════════════════════════════════════════════════════════════════════════════
# ESTIMATION ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/estimate/costs")
async def estimate_costs(request: AnalysisRequest):
    """Estima custos de projeto."""
    result = await ai_router.estimate_costs(request.data)
    return result


@router.post("/estimate/maintenance")
async def predict_maintenance(request: AnalysisRequest):
    """Prediz necessidades de manutenção."""
    result = await ai_router.predict_maintenance(request.data)
    return result


# ════════════════════════════════════════════════════════════════════════════
# DOCUMENT GENERATION ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/generate/document")
async def generate_document(request: AnalysisRequest):
    """Gera documentação técnica."""
    result = await ai_router.generate_document(request.data)
    return result


@router.post("/generate/report")
async def generate_report(request: AnalysisRequest):
    """Gera relatório técnico."""
    request.data["document_type"] = "technical_report"
    result = await ai_router.generate_document(request.data)
    return result


@router.post("/generate/bom")
async def generate_bom(request: AnalysisRequest):
    """Gera lista de materiais."""
    request.data["document_type"] = "material_list"
    result = await ai_router.generate_document(request.data)
    return result


# ════════════════════════════════════════════════════════════════════════════
# PIPELINE ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/pipeline/full")
async def run_full_pipeline(request: PipelineRequest):
    """Executa pipeline completo de análise."""
    result = await ai_router.run_full_pipeline(request.project_data)
    return result


@router.post("/pipeline/custom")
async def run_custom_pipeline(request: PipelineRequest):
    """Executa pipeline customizado com IAs específicas."""
    if not request.include_ais:
        raise HTTPException(
            status_code=400,
            detail="Lista de IAs (include_ais) é obrigatória"
        )
    
    result = await ai_router.route(
        task_type=TaskType.FULL_PIPELINE,
        input_data=request.project_data,
        specific_ais=request.include_ais,
        parallel=request.parallel,
    )
    return result


# ════════════════════════════════════════════════════════════════════════════
# DIRECT ENGINE ACCESS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/engine/{engine_name}/execute")
async def execute_engine(engine_name: str, request: AnalysisRequest):
    """Executa uma IA específica diretamente."""
    ai = ai_registry.get(engine_name)
    if not ai:
        raise HTTPException(status_code=404, detail=f"IA '{engine_name}' não encontrada")
    
    result = await ai.execute(request.data)
    return result.to_dict()


@router.post("/engine/{engine_name}/clear-cache")
async def clear_engine_cache(engine_name: str):
    """Limpa o cache de uma IA."""
    ai = ai_registry.get(engine_name)
    if not ai:
        raise HTTPException(status_code=404, detail=f"IA '{engine_name}' não encontrada")
    
    ai.clear_cache()
    return {"status": "ok", "message": f"Cache de '{engine_name}' limpo"}


# ════════════════════════════════════════════════════════════════════════════
# QUICK ACTIONS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/quick/health-check")
async def quick_health_check():
    """Verificação rápida de saúde de todas as IAs."""
    results = {}
    for name in ai_registry.list_all():
        ai = ai_registry.get(name)
        if ai:
            results[name] = {
                "status": ai.status.value,
                "requests": ai.metrics.total_requests,
                "success_rate": (
                    ai.metrics.successful_requests / ai.metrics.total_requests * 100
                    if ai.metrics.total_requests > 0 else 100
                ),
            }
    return {"health": results}


@router.post("/quick/analyze-project")
async def quick_analyze_project(request: AnalysisRequest):
    """Análise rápida de projeto usando múltiplas IAs."""
    # Executar análise com IAs selecionadas em paralelo
    result = await ai_router.route(
        task_type=TaskType.FULL_PIPELINE,
        input_data=request.data,
        specific_ais=["DrawingAnalyzer", "QualityInspector", "CostEstimator"],
        parallel=True,
    )
    return result
