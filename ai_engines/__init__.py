"""
═══════════════════════════════════════════════════════════════════════════════
  FORGECAD AI ENGINES - Sistema Enterprise de Inteligência Artificial
═══════════════════════════════════════════════════════════════════════════════

Este módulo contém 8 IAs especializadas para automação CAD industrial:

  1. DrawingAnalyzer    - Analisa e extrai informações de desenhos DWG/DXF
  2. PipeOptimizer      - Otimiza rotas de tubulação e calcula materiais
  3. ConflictDetector   - Detecta colisões e interferências entre componentes
  4. CostEstimator      - Estima custos e gera relatórios de MTO (Material Take-Off)
  5. QualityInspector   - Inspeção automática de qualidade e conformidade
  6. DocumentGenerator  - Gera documentação técnica automaticamente
  7. MaintenancePredict - Predição de manutenção baseada em padrões
  8. AssistantChatbot   - Chatbot assistente técnico com conhecimento CAD

Cada IA é independente mas pode ser orquestrada pelo AIRouter central.

═══════════════════════════════════════════════════════════════════════════════
"""

from .router import AIRouter
from .drawing_analyzer import DrawingAnalyzerAI
from .pipe_optimizer import PipeOptimizerAI
from .conflict_detector import ConflictDetectorAI
from .cost_estimator import CostEstimatorAI
from .quality_inspector import QualityInspectorAI
from .document_generator import DocumentGeneratorAI
from .maintenance_predictor import MaintenancePredictorAI
from .assistant_chatbot import AssistantChatbotAI

__all__ = [
    "AIRouter",
    "DrawingAnalyzerAI",
    "PipeOptimizerAI", 
    "ConflictDetectorAI",
    "CostEstimatorAI",
    "QualityInspectorAI",
    "DocumentGeneratorAI",
    "MaintenancePredictorAI",
    "AssistantChatbotAI",
]

__version__ = "1.0.0"
