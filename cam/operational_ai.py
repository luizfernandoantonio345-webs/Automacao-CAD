"""
═══════════════════════════════════════════════════════════════════════════════
IA OPERACIONAL - Sistema Inteligente de Automação CAM
═══════════════════════════════════════════════════════════════════════════════

Sistema de IA que atua ativamente no processo CAM:
- Sugere parâmetros automaticamente baseado em material/geometria
- Corrige erros de geometria automaticamente
- Escolhe melhor estratégia de nesting
- Sugere estratégia de corte otimizada
- Detecta problemas antes da execução
- Otimiza toolpath para máxima eficiência

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("engcad.cam.operational_ai")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class AIConfidence(Enum):
    """Nível de confiança da IA na recomendação."""
    LOW = "low"                 # < 60% - precisa revisão manual
    MEDIUM = "medium"           # 60-80% - provavelmente correto
    HIGH = "high"               # 80-95% - muito confiável
    CERTAIN = "certain"         # > 95% - baseado em regras estabelecidas


class ProblemSeverity(Enum):
    """Severidade do problema detectado."""
    INFO = "info"               # Informativo
    WARNING = "warning"         # Atenção recomendada
    ERROR = "error"             # Requer correção
    CRITICAL = "critical"       # Impede execução


class OptimizationType(Enum):
    """Tipos de otimização."""
    SPEED = "speed"             # Maximizar velocidade
    QUALITY = "quality"         # Maximizar qualidade
    CONSUMABLES = "consumables" # Economizar consumíveis
    BALANCED = "balanced"       # Equilíbrio


class CuttingStrategy(Enum):
    """Estratégias de corte."""
    INSIDE_FIRST = "inside_first"       # Furos internos primeiro
    OUTSIDE_FIRST = "outside_first"     # Contorno externo primeiro
    NEAREST_NEIGHBOR = "nearest_neighbor"  # Mais próximo primeiro
    ZIGZAG = "zigzag"                   # Padrão zigzag
    SPIRAL = "spiral"                   # Espiral de fora para dentro
    HEAT_AWARE = "heat_aware"           # Considera acúmulo de calor


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIRecommendation:
    """Recomendação da IA."""
    
    category: str                       # Categoria da recomendação
    title: str                          # Título curto
    description: str                    # Descrição detalhada
    confidence: AIConfidence            # Nível de confiança
    
    # Ação sugerida
    action_type: str = ""               # Tipo de ação
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Impacto estimado
    impact: Dict[str, Any] = field(default_factory=dict)
    
    # Referências
    affected_items: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence.value,
            "action_type": self.action_type,
            "action_params": self.action_params,
            "impact": self.impact,
            "affected_items": self.affected_items,
        }


@dataclass
class GeometryProblem:
    """Problema detectado na geometria."""
    
    severity: ProblemSeverity
    problem_type: str
    description: str
    location: Optional[Tuple[float, float]] = None
    affected_entity: str = ""
    
    # Correção automática disponível
    auto_fix_available: bool = False
    fix_description: str = ""
    fix_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "type": self.problem_type,
            "description": self.description,
            "location": self.location,
            "affected_entity": self.affected_entity,
            "auto_fix_available": self.auto_fix_available,
            "fix_description": self.fix_description,
        }


@dataclass
class CuttingParameters:
    """Parâmetros de corte recomendados."""
    
    # Material
    material: str = "mild_steel"
    thickness: float = 6.0
    
    # Plasma
    amperage: int = 45
    cutting_speed: float = 2000.0       # mm/min
    pierce_delay: float = 0.5           # segundos
    
    # Alturas
    pierce_height: float = 3.0          # mm
    cut_height: float = 1.5             # mm
    
    # Lead-in/out
    lead_in_length: float = 5.0         # mm
    lead_in_angle: float = 45.0         # graus
    lead_type: str = "arc"
    
    # THC
    arc_voltage: float = 120.0
    thc_enabled: bool = True
    
    # Kerf
    kerf_width: float = 1.5             # mm
    
    # Confiança
    confidence: AIConfidence = AIConfidence.HIGH
    source: str = "database"            # "database", "calculated", "learned"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": self.material,
            "thickness": self.thickness,
            "amperage": self.amperage,
            "cutting_speed": self.cutting_speed,
            "pierce_delay": self.pierce_delay,
            "pierce_height": self.pierce_height,
            "cut_height": self.cut_height,
            "lead_in_length": self.lead_in_length,
            "lead_in_angle": self.lead_in_angle,
            "lead_type": self.lead_type,
            "arc_voltage": self.arc_voltage,
            "thc_enabled": self.thc_enabled,
            "kerf_width": self.kerf_width,
            "confidence": self.confidence.value,
            "source": self.source,
        }


@dataclass
class NestingStrategy:
    """Estratégia de nesting recomendada."""
    
    algorithm: str = "genetic"          # Algoritmo recomendado
    priority: str = "efficiency"        # Prioridade
    rotation_enabled: bool = True       # Permitir rotação
    rotation_step: float = 90.0         # Graus
    spacing: float = 5.0                # Espaçamento entre peças
    margin: float = 10.0                # Margem da chapa
    
    # Estimativas
    estimated_efficiency: float = 0.0   # Eficiência estimada (%)
    estimated_time: float = 0.0         # Tempo de processamento (s)
    
    confidence: AIConfidence = AIConfidence.MEDIUM
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "priority": self.priority,
            "rotation_enabled": self.rotation_enabled,
            "rotation_step": self.rotation_step,
            "spacing": self.spacing,
            "margin": self.margin,
            "estimated_efficiency": self.estimated_efficiency,
            "estimated_time": self.estimated_time,
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
        }


@dataclass
class ToolpathOptimization:
    """Otimização de toolpath recomendada."""
    
    cutting_strategy: CuttingStrategy = CuttingStrategy.INSIDE_FIRST
    optimization_type: OptimizationType = OptimizationType.BALANCED
    
    # Reordenação
    reorder_enabled: bool = True
    sequence: List[int] = field(default_factory=list)
    
    # Lead-in otimizado
    optimized_lead_ins: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    # Tabs automáticos
    auto_tabs: bool = False
    tab_count: int = 0
    
    # Estimativas de melhoria
    time_saved: float = 0.0             # segundos
    rapid_reduction: float = 0.0        # mm
    pierce_reduction: int = 0
    
    confidence: AIConfidence = AIConfidence.MEDIUM
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cutting_strategy": self.cutting_strategy.value,
            "optimization_type": self.optimization_type.value,
            "reorder_enabled": self.reorder_enabled,
            "sequence": self.sequence,
            "auto_tabs": self.auto_tabs,
            "tab_count": self.tab_count,
            "improvements": {
                "time_saved_seconds": self.time_saved,
                "rapid_reduction_mm": self.rapid_reduction,
                "pierce_reduction": self.pierce_reduction,
            },
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BANCO DE DADOS DE CORTE
# ═══════════════════════════════════════════════════════════════════════════════

class CuttingDatabase:
    """
    Banco de dados de parâmetros de corte por material e espessura.
    Baseado em dados de fabricantes (Hypertherm, ESAB, etc.)
    """
    
    # Formato: {material: {espessura: (amperage, speed, kerf, pierce_delay)}}
    CUTTING_DATA = {
        "mild_steel": {
            1.0: (25, 4500, 0.8, 0.0),
            1.5: (25, 4000, 0.9, 0.1),
            2.0: (30, 3500, 1.0, 0.1),
            3.0: (30, 3000, 1.1, 0.2),
            4.0: (40, 2500, 1.3, 0.3),
            5.0: (40, 2200, 1.4, 0.3),
            6.0: (45, 2000, 1.5, 0.4),
            8.0: (55, 1500, 1.7, 0.5),
            10.0: (65, 1200, 1.9, 0.7),
            12.0: (80, 900, 2.1, 1.0),
            16.0: (100, 650, 2.4, 1.5),
            20.0: (130, 480, 2.7, 2.0),
            25.0: (170, 350, 3.0, 2.5),
            32.0: (200, 250, 3.5, 3.5),
        },
        "stainless": {
            1.0: (30, 3500, 0.9, 0.1),
            1.5: (35, 3000, 1.0, 0.2),
            2.0: (40, 2500, 1.2, 0.2),
            3.0: (45, 2000, 1.4, 0.3),
            4.0: (55, 1600, 1.6, 0.4),
            5.0: (65, 1300, 1.8, 0.5),
            6.0: (75, 1100, 2.0, 0.6),
            8.0: (90, 800, 2.3, 0.8),
            10.0: (110, 600, 2.6, 1.2),
            12.0: (130, 450, 2.9, 1.5),
        },
        "aluminum": {
            1.0: (30, 5000, 1.2, 0.1),
            1.5: (35, 4500, 1.4, 0.1),
            2.0: (40, 4000, 1.6, 0.2),
            3.0: (50, 3200, 1.8, 0.2),
            4.0: (60, 2600, 2.0, 0.3),
            5.0: (70, 2200, 2.2, 0.4),
            6.0: (80, 1800, 2.4, 0.5),
            8.0: (100, 1300, 2.7, 0.6),
            10.0: (120, 1000, 3.0, 0.8),
        },
        "copper": {
            1.0: (35, 3500, 1.3, 0.2),
            1.5: (40, 3000, 1.5, 0.3),
            2.0: (50, 2500, 1.7, 0.4),
            3.0: (60, 2000, 2.0, 0.5),
            4.0: (75, 1500, 2.3, 0.6),
            5.0: (90, 1200, 2.5, 0.8),
            6.0: (105, 900, 2.8, 1.0),
        },
        "brass": {
            1.0: (30, 4000, 1.2, 0.1),
            1.5: (35, 3500, 1.4, 0.2),
            2.0: (45, 3000, 1.6, 0.3),
            3.0: (55, 2400, 1.8, 0.4),
            4.0: (65, 1900, 2.0, 0.5),
            5.0: (80, 1500, 2.3, 0.6),
            6.0: (95, 1200, 2.5, 0.8),
        },
        "galvanized": {
            1.0: (25, 4200, 0.9, 0.1),
            1.5: (30, 3800, 1.0, 0.1),
            2.0: (35, 3200, 1.2, 0.2),
            3.0: (40, 2600, 1.4, 0.3),
        },
    }
    
    # Tensões de arco típicas por material/amperagem
    ARC_VOLTAGES = {
        "mild_steel": {45: 118, 65: 122, 80: 126, 100: 130, 130: 135, 200: 145},
        "stainless": {45: 120, 65: 124, 80: 128, 100: 132, 130: 138},
        "aluminum": {45: 115, 65: 118, 80: 122, 100: 126, 130: 130},
    }
    
    @classmethod
    def get_parameters(
        cls, 
        material: str, 
        thickness: float
    ) -> Optional[CuttingParameters]:
        """
        Obtém parâmetros de corte para material e espessura.
        Interpola se a espessura exata não existir.
        """
        if material not in cls.CUTTING_DATA:
            return None
        
        data = cls.CUTTING_DATA[material]
        thicknesses = sorted(data.keys())
        
        # Espessura exata
        if thickness in data:
            amp, speed, kerf, delay = data[thickness]
            return cls._create_params(material, thickness, amp, speed, kerf, delay)
        
        # Fora do range
        if thickness < thicknesses[0]:
            amp, speed, kerf, delay = data[thicknesses[0]]
            return cls._create_params(material, thickness, amp, speed, kerf, delay)
        if thickness > thicknesses[-1]:
            return None  # Espessura muito grande
        
        # Interpolação linear
        for i, t in enumerate(thicknesses[:-1]):
            if t < thickness < thicknesses[i + 1]:
                t1, t2 = t, thicknesses[i + 1]
                d1, d2 = data[t1], data[t2]
                
                ratio = (thickness - t1) / (t2 - t1)
                
                amp = int(d1[0] + (d2[0] - d1[0]) * ratio)
                speed = d1[1] + (d2[1] - d1[1]) * ratio
                kerf = d1[2] + (d2[2] - d1[2]) * ratio
                delay = d1[3] + (d2[3] - d1[3]) * ratio
                
                params = cls._create_params(material, thickness, amp, speed, kerf, delay)
                params.confidence = AIConfidence.MEDIUM
                params.source = "interpolated"
                return params
        
        return None
    
    @classmethod
    def _create_params(
        cls,
        material: str,
        thickness: float,
        amperage: int,
        speed: float,
        kerf: float,
        pierce_delay: float
    ) -> CuttingParameters:
        """Cria objeto CuttingParameters completo."""
        
        # Calcular alturas baseado na espessura
        pierce_height = min(10.0, max(2.0, thickness * 0.5))
        cut_height = min(5.0, max(1.0, thickness * 0.2))
        
        # Lead-in baseado na espessura e kerf
        lead_length = min(15.0, max(3.0, kerf * 3))
        
        # Tensão de arco
        arc_voltage = cls._get_arc_voltage(material, amperage)
        
        return CuttingParameters(
            material=material,
            thickness=thickness,
            amperage=amperage,
            cutting_speed=speed,
            pierce_delay=pierce_delay,
            pierce_height=pierce_height,
            cut_height=cut_height,
            lead_in_length=lead_length,
            lead_in_angle=45.0,
            lead_type="arc",
            arc_voltage=arc_voltage,
            thc_enabled=thickness >= 3.0,
            kerf_width=kerf,
            confidence=AIConfidence.HIGH,
            source="database",
        )
    
    @classmethod
    def _get_arc_voltage(cls, material: str, amperage: int) -> float:
        """Obtém tensão de arco para material e amperagem."""
        if material not in cls.ARC_VOLTAGES:
            material = "mild_steel"
        
        voltages = cls.ARC_VOLTAGES[material]
        amps = sorted(voltages.keys())
        
        if amperage <= amps[0]:
            return voltages[amps[0]]
        if amperage >= amps[-1]:
            return voltages[amps[-1]]
        
        for i, a in enumerate(amps[:-1]):
            if a <= amperage < amps[i + 1]:
                ratio = (amperage - a) / (amps[i + 1] - a)
                return voltages[a] + (voltages[amps[i + 1]] - voltages[a]) * ratio
        
        return 120.0


# ═══════════════════════════════════════════════════════════════════════════════
# IA OPERACIONAL PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class OperationalAI:
    """
    IA Operacional para automação de processos CAM.
    
    Capabilities:
    - Sugestão automática de parâmetros de corte
    - Detecção e correção de erros de geometria
    - Escolha de algoritmo de nesting
    - Otimização de toolpath
    - Análise pré-execução
    """
    
    def __init__(self):
        self.cutting_db = CuttingDatabase()
        self.recommendations: List[AIRecommendation] = []
        self.problems: List[GeometryProblem] = []
        
        # Histórico para aprendizado
        self.history: List[Dict[str, Any]] = []
    
    def suggest_cutting_parameters(
        self,
        material: str,
        thickness: float,
        geometry_info: Optional[Dict[str, Any]] = None,
        optimization: OptimizationType = OptimizationType.BALANCED
    ) -> CuttingParameters:
        """
        Sugere parâmetros de corte otimizados.
        
        Args:
            material: Tipo de material
            thickness: Espessura em mm
            geometry_info: Informações da geometria (opcional)
            optimization: Tipo de otimização desejada
            
        Returns:
            Parâmetros de corte recomendados
        """
        # Buscar parâmetros base
        params = CuttingDatabase.get_parameters(material, thickness)
        
        if not params:
            # Material não encontrado, usar estimativa
            params = self._estimate_parameters(material, thickness)
        
        # Ajustar baseado na geometria
        if geometry_info:
            params = self._adjust_for_geometry(params, geometry_info)
        
        # Ajustar baseado no tipo de otimização
        params = self._apply_optimization(params, optimization)
        
        # Gerar recomendação
        self.recommendations.append(AIRecommendation(
            category="cutting_parameters",
            title="Parâmetros de Corte Otimizados",
            description=f"Amperagem: {params.amperage}A, Velocidade: {params.cutting_speed}mm/min",
            confidence=params.confidence,
            action_type="apply_parameters",
            action_params=params.to_dict(),
            impact={
                "quality": "optimized" if optimization == OptimizationType.QUALITY else "standard",
                "speed": "maximized" if optimization == OptimizationType.SPEED else "standard",
            }
        ))
        
        return params
    
    def _estimate_parameters(self, material: str, thickness: float) -> CuttingParameters:
        """Estima parâmetros para material desconhecido."""
        # Usar aço carbono como base
        base_params = CuttingDatabase.get_parameters("mild_steel", thickness)
        
        if base_params:
            base_params.material = material
            base_params.confidence = AIConfidence.LOW
            base_params.source = "estimated"
            return base_params
        
        # Estimativa muito grosseira
        amperage = int(thickness * 8 + 20)
        speed = max(500, 4000 - thickness * 150)
        kerf = 0.8 + thickness * 0.15
        pierce_delay = min(3.0, thickness * 0.1)
        
        return CuttingParameters(
            material=material,
            thickness=thickness,
            amperage=amperage,
            cutting_speed=speed,
            pierce_delay=pierce_delay,
            kerf_width=kerf,
            confidence=AIConfidence.LOW,
            source="estimated",
        )
    
    def _adjust_for_geometry(
        self, 
        params: CuttingParameters, 
        geometry: Dict[str, Any]
    ) -> CuttingParameters:
        """Ajusta parâmetros baseado na geometria."""
        
        # Muitos furos pequenos = reduzir velocidade para qualidade
        small_holes = geometry.get("small_holes_count", 0)
        if small_holes > 10:
            params.cutting_speed *= 0.9
            params.lead_in_length = max(2.0, params.lead_in_length * 0.8)
        
        # Geometria complexa = mais conservative
        complexity = geometry.get("complexity", "normal")
        if complexity == "high":
            params.cutting_speed *= 0.85
            params.pierce_delay *= 1.2
        
        # Peças pequenas = lead-in menor
        min_feature = geometry.get("min_feature_size", 100)
        if min_feature < 20:
            params.lead_in_length = min(params.lead_in_length, min_feature * 0.3)
        
        return params
    
    def _apply_optimization(
        self, 
        params: CuttingParameters, 
        opt_type: OptimizationType
    ) -> CuttingParameters:
        """Aplica ajustes de otimização."""
        
        if opt_type == OptimizationType.SPEED:
            params.cutting_speed *= 1.15
            params.pierce_delay *= 0.8
        elif opt_type == OptimizationType.QUALITY:
            params.cutting_speed *= 0.85
            params.pierce_delay *= 1.2
            params.lead_in_length *= 1.2
        elif opt_type == OptimizationType.CONSUMABLES:
            params.amperage = max(25, int(params.amperage * 0.9))
            params.cutting_speed *= 0.95
        
        return params
    
    def analyze_geometry(
        self, 
        geometry: Dict[str, Any]
    ) -> List[GeometryProblem]:
        """
        Analisa geometria e detecta problemas.
        
        Args:
            geometry: Dicionário com informações da geometria
            
        Returns:
            Lista de problemas detectados
        """
        problems = []
        
        # Verificar entidades abertas
        open_contours = geometry.get("open_contours", [])
        for contour in open_contours:
            problems.append(GeometryProblem(
                severity=ProblemSeverity.ERROR,
                problem_type="open_contour",
                description=f"Contorno aberto detectado",
                location=contour.get("start_point"),
                affected_entity=contour.get("id", ""),
                auto_fix_available=True,
                fix_description="Fechar contorno automaticamente",
                fix_params={"action": "close_contour", "entity_id": contour.get("id")}
            ))
        
        # Verificar geometrias pequenas demais
        kerf = geometry.get("kerf_width", 1.5)
        min_features = geometry.get("min_features", [])
        for feature in min_features:
            size = feature.get("size", 0)
            if size < kerf * 2:
                problems.append(GeometryProblem(
                    severity=ProblemSeverity.WARNING,
                    problem_type="feature_too_small",
                    description=f"Detalhes menores que 2x kerf ({size:.2f}mm < {kerf*2:.2f}mm)",
                    location=feature.get("center"),
                    affected_entity=feature.get("id", ""),
                    auto_fix_available=False,
                    fix_description="Considere aumentar o detalhe ou remover",
                ))
        
        # Verificar auto-interseções
        intersections = geometry.get("self_intersections", [])
        for inter in intersections:
            problems.append(GeometryProblem(
                severity=ProblemSeverity.ERROR,
                problem_type="self_intersection",
                description="Auto-interseção detectada no contorno",
                location=inter.get("point"),
                affected_entity=inter.get("entity_id", ""),
                auto_fix_available=True,
                fix_description="Dividir contorno no ponto de interseção",
                fix_params={"action": "split_at_intersection", "point": inter.get("point")}
            ))
        
        # Verificar furos muito próximos
        close_holes = geometry.get("close_hole_pairs", [])
        for pair in close_holes:
            distance = pair.get("distance", 0)
            if distance < kerf * 1.5:
                problems.append(GeometryProblem(
                    severity=ProblemSeverity.WARNING,
                    problem_type="holes_too_close",
                    description=f"Furos muito próximos ({distance:.2f}mm, mínimo recomendado: {kerf*1.5:.2f}mm)",
                    location=pair.get("midpoint"),
                    auto_fix_available=False,
                    fix_description="Considere unir furos ou aumentar distância",
                ))
        
        # Verificar ângulos agudos
        sharp_corners = geometry.get("sharp_corners", [])
        for corner in sharp_corners:
            angle = corner.get("angle", 90)
            if angle < 30:
                problems.append(GeometryProblem(
                    severity=ProblemSeverity.WARNING,
                    problem_type="sharp_corner",
                    description=f"Canto muito agudo ({angle:.1f}°)",
                    location=corner.get("point"),
                    affected_entity=corner.get("entity_id", ""),
                    auto_fix_available=True,
                    fix_description="Adicionar raio de concordância",
                    fix_params={"action": "fillet_corner", "radius": kerf * 0.5}
                ))
        
        self.problems = problems
        return problems
    
    def suggest_nesting_strategy(
        self,
        pieces: List[Dict[str, Any]],
        sheet: Dict[str, Any],
        priority: str = "efficiency"
    ) -> NestingStrategy:
        """
        Sugere estratégia de nesting baseada nas peças e chapa.
        
        Args:
            pieces: Lista de peças para nesting
            sheet: Informações da chapa
            priority: Prioridade (efficiency, speed, quality)
            
        Returns:
            Estratégia de nesting recomendada
        """
        strategy = NestingStrategy()
        strategy.priority = priority
        
        # Analisar características das peças
        total_pieces = len(pieces)
        total_area = sum(p.get("area", 0) for p in pieces)
        sheet_area = sheet.get("width", 1000) * sheet.get("height", 500)
        
        # Determinar complexidade
        avg_vertices = sum(p.get("vertices", 4) for p in pieces) / max(total_pieces, 1)
        has_complex_shapes = avg_vertices > 8
        has_rotatable = any(p.get("allow_rotation", True) for p in pieces)
        
        # Escolher algoritmo
        if total_pieces <= 5:
            strategy.algorithm = "blf"  # Simples e rápido
            strategy.estimated_time = 0.5
            strategy.reasoning = "Poucas peças - BLF é eficiente"
        elif has_complex_shapes:
            strategy.algorithm = "nfp"  # Melhor para formas complexas
            strategy.estimated_time = total_pieces * 0.3
            strategy.reasoning = "Formas complexas - NFP para melhor encaixe"
        elif total_pieces > 50:
            strategy.algorithm = "genetic"
            strategy.estimated_time = total_pieces * 0.1
            strategy.reasoning = "Muitas peças - Genético para otimização global"
        else:
            strategy.algorithm = "hybrid"
            strategy.estimated_time = total_pieces * 0.2
            strategy.reasoning = "Caso geral - Híbrido para equilíbrio"
        
        # Configurações de rotação
        if has_rotatable:
            strategy.rotation_enabled = True
            if has_complex_shapes:
                strategy.rotation_step = 15.0  # Mais opções
            else:
                strategy.rotation_step = 90.0  # Apenas ortogonal
        
        # Espaçamento baseado na espessura
        thickness = sheet.get("thickness", 6.0)
        strategy.spacing = max(3.0, thickness * 0.5 + 2.0)
        
        # Margem
        strategy.margin = max(10.0, thickness)
        
        # Estimar eficiência
        fill_ratio = total_area / sheet_area
        strategy.estimated_efficiency = min(95, fill_ratio * 100 * 1.1)  # Otimismo moderado
        
        # Ajustar confiança
        if total_pieces > 20 and has_complex_shapes:
            strategy.confidence = AIConfidence.MEDIUM
        else:
            strategy.confidence = AIConfidence.HIGH
        
        # Gerar recomendação
        self.recommendations.append(AIRecommendation(
            category="nesting",
            title=f"Usar algoritmo {strategy.algorithm.upper()}",
            description=strategy.reasoning,
            confidence=strategy.confidence,
            action_type="configure_nesting",
            action_params=strategy.to_dict(),
            impact={
                "estimated_efficiency": f"{strategy.estimated_efficiency:.1f}%",
                "processing_time": f"{strategy.estimated_time:.1f}s",
            }
        ))
        
        return strategy
    
    def optimize_toolpath(
        self,
        contours: List[Dict[str, Any]],
        optimization_type: OptimizationType = OptimizationType.BALANCED
    ) -> ToolpathOptimization:
        """
        Otimiza sequência de corte e parâmetros de toolpath.
        
        Args:
            contours: Lista de contornos com informações
            optimization_type: Tipo de otimização
            
        Returns:
            Otimização de toolpath recomendada
        """
        opt = ToolpathOptimization()
        opt.optimization_type = optimization_type
        
        # Separar contornos internos e externos
        internal = [c for c in contours if c.get("is_internal", False)]
        external = [c for c in contours if not c.get("is_internal", False)]
        
        # Determinar estratégia de corte
        if len(internal) > len(external) * 2:
            # Muitos furos - agrupar por área
            opt.cutting_strategy = CuttingStrategy.HEAT_AWARE
            opt.reasoning = "Muitos furos - estratégia de dissipação de calor"
        elif optimization_type == OptimizationType.SPEED:
            opt.cutting_strategy = CuttingStrategy.NEAREST_NEIGHBOR
            opt.reasoning = "Minimizar movimentos rápidos"
        else:
            opt.cutting_strategy = CuttingStrategy.INSIDE_FIRST
            opt.reasoning = "Cortar furos antes do contorno externo"
        
        # Calcular sequência otimizada
        sequence = self._calculate_optimal_sequence(
            contours, 
            opt.cutting_strategy
        )
        opt.sequence = sequence
        
        # Calcular melhorias estimadas
        original_rapid = self._calculate_rapid_distance(contours, list(range(len(contours))))
        optimized_rapid = self._calculate_rapid_distance(contours, sequence)
        
        opt.rapid_reduction = original_rapid - optimized_rapid
        opt.time_saved = opt.rapid_reduction / 500 * 60  # Assumindo 500mm/s de rapid
        
        # Recomendar tabs para peças grandes
        large_pieces = [c for c in contours if c.get("area", 0) > 10000]  # > 100cm²
        if large_pieces:
            opt.auto_tabs = True
            opt.tab_count = len(large_pieces) * 4
        
        # Confiança
        if len(contours) > 50:
            opt.confidence = AIConfidence.MEDIUM
        else:
            opt.confidence = AIConfidence.HIGH
        
        # Gerar recomendação
        self.recommendations.append(AIRecommendation(
            category="toolpath",
            title=f"Estratégia: {opt.cutting_strategy.value}",
            description=opt.reasoning,
            confidence=opt.confidence,
            action_type="apply_toolpath_optimization",
            action_params=opt.to_dict(),
            impact={
                "rapid_reduction_mm": f"{opt.rapid_reduction:.1f}",
                "time_saved_seconds": f"{opt.time_saved:.1f}",
                "pierce_reduction": opt.pierce_reduction,
            }
        ))
        
        return opt
    
    def _calculate_optimal_sequence(
        self, 
        contours: List[Dict[str, Any]],
        strategy: CuttingStrategy
    ) -> List[int]:
        """Calcula sequência ótima de corte."""
        n = len(contours)
        if n == 0:
            return []
        
        # Separar internos e externos
        internal_idx = [i for i, c in enumerate(contours) if c.get("is_internal", False)]
        external_idx = [i for i, c in enumerate(contours) if not c.get("is_internal", False)]
        
        if strategy == CuttingStrategy.INSIDE_FIRST:
            # Internos primeiro, depois externos
            sequence = internal_idx + external_idx
        elif strategy == CuttingStrategy.OUTSIDE_FIRST:
            sequence = external_idx + internal_idx
        elif strategy == CuttingStrategy.NEAREST_NEIGHBOR:
            # Nearest neighbor simples
            sequence = self._nearest_neighbor_sequence(contours)
        elif strategy == CuttingStrategy.HEAT_AWARE:
            # Distribuir furos para evitar acúmulo de calor
            sequence = self._heat_aware_sequence(contours)
        else:
            sequence = list(range(n))
        
        return sequence
    
    def _nearest_neighbor_sequence(self, contours: List[Dict[str, Any]]) -> List[int]:
        """Sequência nearest neighbor."""
        if not contours:
            return []
        
        n = len(contours)
        visited = [False] * n
        sequence = [0]
        visited[0] = True
        
        for _ in range(n - 1):
            current = sequence[-1]
            current_pos = self._get_contour_center(contours[current])
            
            best_idx = -1
            best_dist = float('inf')
            
            for i in range(n):
                if not visited[i]:
                    pos = self._get_contour_center(contours[i])
                    dist = math.sqrt(
                        (pos[0] - current_pos[0])**2 + 
                        (pos[1] - current_pos[1])**2
                    )
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
            
            if best_idx >= 0:
                sequence.append(best_idx)
                visited[best_idx] = True
        
        return sequence
    
    def _heat_aware_sequence(self, contours: List[Dict[str, Any]]) -> List[int]:
        """Sequência que minimiza acúmulo de calor."""
        if not contours:
            return []
        
        # Dividir em grid
        min_x = min(c.get("center", (0, 0))[0] for c in contours)
        max_x = max(c.get("center", (0, 0))[0] for c in contours)
        min_y = min(c.get("center", (0, 0))[1] for c in contours)
        max_y = max(c.get("center", (0, 0))[1] for c in contours)
        
        # Alternar entre regiões
        n = len(contours)
        indexed = [(i, self._get_contour_center(c)) for i, c in enumerate(contours)]
        
        # Ordenar por distância alternada
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        
        # Dividir em quadrantes e alternar
        quadrants = [[], [], [], []]
        for i, (x, y) in indexed:
            q = (0 if x < mid_x else 1) + (0 if y < mid_y else 2)
            quadrants[q].append(i)
        
        # Intercalar quadrantes
        sequence = []
        while any(quadrants):
            for q in [0, 2, 1, 3]:  # Padrão diagonal
                if quadrants[q]:
                    sequence.append(quadrants[q].pop(0))
        
        return sequence
    
    def _get_contour_center(self, contour: Dict[str, Any]) -> Tuple[float, float]:
        """Obtém centro do contorno."""
        center = contour.get("center", (0, 0))
        if isinstance(center, (list, tuple)) and len(center) >= 2:
            return (center[0], center[1])
        return (0, 0)
    
    def _calculate_rapid_distance(
        self, 
        contours: List[Dict[str, Any]], 
        sequence: List[int]
    ) -> float:
        """Calcula distância total de movimentos rápidos."""
        if len(sequence) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(sequence) - 1):
            p1 = self._get_contour_center(contours[sequence[i]])
            p2 = self._get_contour_center(contours[sequence[i + 1]])
            total += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        return total
    
    def pre_execution_check(
        self,
        gcode: str,
        machine_limits: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verifica G-code antes da execução.
        
        Args:
            gcode: Código G-code
            machine_limits: Limites da máquina (opcional)
            
        Returns:
            Resultado da verificação
        """
        issues = []
        warnings = []
        info = []
        
        lines = gcode.strip().split('\n')
        
        # Análise básica
        max_x = max_y = max_z = 0.0
        min_x = min_y = min_z = 0.0
        has_plasma_on = False
        has_plasma_off = False
        pierce_count = 0
        
        import re
        
        for line_num, line in enumerate(lines):
            line = line.strip().upper()
            
            # Extrair coordenadas
            x_match = re.search(r'X(-?\d+\.?\d*)', line)
            y_match = re.search(r'Y(-?\d+\.?\d*)', line)
            z_match = re.search(r'Z(-?\d+\.?\d*)', line)
            
            if x_match:
                x = float(x_match.group(1))
                max_x = max(max_x, x)
                min_x = min(min_x, x)
            if y_match:
                y = float(y_match.group(1))
                max_y = max(max_y, y)
                min_y = min(min_y, y)
            if z_match:
                z = float(z_match.group(1))
                max_z = max(max_z, z)
                min_z = min(min_z, z)
            
            # Verificar M-codes
            if 'M03' in line or 'M3' in line:
                has_plasma_on = True
                if not has_plasma_off and pierce_count > 0:
                    # Plasma ligado sem ter desligado antes
                    pass  # Normal se for primeiro pierce
                pierce_count += 1
            
            if 'M05' in line or 'M5' in line:
                has_plasma_off = True
            
            # Verificar limites da máquina
            if machine_limits:
                if x_match and machine_limits.get("x_max"):
                    if float(x_match.group(1)) > machine_limits["x_max"]:
                        issues.append({
                            "line": line_num + 1,
                            "type": "limit_exceeded",
                            "message": f"Coordenada X excede limite da máquina"
                        })
                if y_match and machine_limits.get("y_max"):
                    if float(y_match.group(1)) > machine_limits["y_max"]:
                        issues.append({
                            "line": line_num + 1,
                            "type": "limit_exceeded",
                            "message": f"Coordenada Y excede limite da máquina"
                        })
        
        # Verificações gerais
        if not has_plasma_on:
            warnings.append({
                "type": "no_plasma_on",
                "message": "Nenhum comando de ligar plasma (M03) encontrado"
            })
        
        if has_plasma_on and not has_plasma_off:
            issues.append({
                "type": "plasma_not_off",
                "message": "Plasma é ligado mas nunca desligado (falta M05)"
            })
        
        if pierce_count == 0:
            warnings.append({
                "type": "no_pierce",
                "message": "Nenhum pierce detectado"
            })
        
        # Informações
        info.append({"type": "pierce_count", "value": pierce_count})
        info.append({"type": "work_area", "value": f"{max_x - min_x:.1f}mm x {max_y - min_y:.1f}mm"})
        info.append({"type": "line_count", "value": len(lines)})
        
        can_execute = len(issues) == 0
        
        return {
            "can_execute": can_execute,
            "issues": issues,
            "warnings": warnings,
            "info": info,
            "summary": {
                "bounds": {
                    "x": [min_x, max_x],
                    "y": [min_y, max_y],
                    "z": [min_z, max_z],
                },
                "pierce_count": pierce_count,
                "line_count": len(lines),
            }
        }
    
    def get_all_recommendations(self) -> List[Dict[str, Any]]:
        """Retorna todas as recomendações geradas."""
        return [r.to_dict() for r in self.recommendations]
    
    def get_all_problems(self) -> List[Dict[str, Any]]:
        """Retorna todos os problemas detectados."""
        return [p.to_dict() for p in self.problems]
    
    def clear(self):
        """Limpa recomendações e problemas."""
        self.recommendations = []
        self.problems = []


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════════════════════════════════

def get_cutting_parameters(material: str, thickness: float) -> Dict[str, Any]:
    """
    Função utilitária para obter parâmetros de corte.
    
    Args:
        material: Tipo de material
        thickness: Espessura em mm
        
    Returns:
        Dicionário com parâmetros
    """
    ai = OperationalAI()
    params = ai.suggest_cutting_parameters(material, thickness)
    return params.to_dict()


def analyze_and_fix_geometry(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analisa geometria e sugere correções.
    
    Args:
        geometry: Dicionário com informações da geometria
        
    Returns:
        Problemas detectados e correções sugeridas
    """
    ai = OperationalAI()
    problems = ai.analyze_geometry(geometry)
    
    return {
        "problems_count": len(problems),
        "auto_fixable": sum(1 for p in problems if p.auto_fix_available),
        "critical_count": sum(1 for p in problems if p.severity == ProblemSeverity.CRITICAL),
        "problems": [p.to_dict() for p in problems],
    }


def suggest_all_optimizations(
    material: str,
    thickness: float,
    pieces: List[Dict[str, Any]],
    sheet: Dict[str, Any],
    contours: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Sugere todas as otimizações em uma única chamada.
    
    Returns:
        Todas as recomendações da IA
    """
    ai = OperationalAI()
    
    cutting_params = ai.suggest_cutting_parameters(material, thickness)
    nesting_strategy = ai.suggest_nesting_strategy(pieces, sheet)
    toolpath_opt = ai.optimize_toolpath(contours)
    
    return {
        "cutting_parameters": cutting_params.to_dict(),
        "nesting_strategy": nesting_strategy.to_dict(),
        "toolpath_optimization": toolpath_opt.to_dict(),
        "all_recommendations": ai.get_all_recommendations(),
    }
