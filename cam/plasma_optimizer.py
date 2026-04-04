"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Otimizador para Corte Plasma
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Responsável por:
- Otimizações específicas para plasma
- Análise térmica simplificada
- Validação de parâmetros de corte
- Sugestões de melhorias
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .geometry_parser import Geometry, Point, Polyline
from .toolpath_generator import Toolpath, CuttingPath, ContourType

logger = logging.getLogger("engcad.cam.plasma_optimizer")


class OptimizationLevel(Enum):
    """Níveis de otimização."""
    BASIC = "basic"           # Apenas ordenação básica
    STANDARD = "standard"     # Ordenação + minimização de deslocamento
    ADVANCED = "advanced"     # Todas as otimizações


class WarningLevel(Enum):
    """Níveis de alerta."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class OptimizationWarning:
    """Alerta de otimização."""
    level: WarningLevel
    message: str
    suggestion: Optional[str] = None
    path_index: Optional[int] = None


@dataclass
class OptimizationConfig:
    """Configuração do otimizador."""
    
    # Nível de otimização
    level: OptimizationLevel = OptimizationLevel.STANDARD
    
    # Distâncias mínimas
    min_feature_size: float = 2.0  # mm - tamanho mínimo de feature
    min_internal_corner_radius: float = 1.0  # mm
    
    # Limites de velocidade
    max_speed_reduction_factor: float = 0.5  # Redução máxima em cantos
    
    # Térmica
    min_distance_between_cuts: float = 50.0  # mm - distância para resfriamento
    max_heat_input_density: float = 1000.0  # J/mm² (simplificado)
    
    # Lead-in/out
    min_lead_length: float = 2.0  # mm
    max_lead_length: float = 10.0  # mm
    
    # Validação
    validate_geometry: bool = True
    check_intersections: bool = True


@dataclass
class OptimizationResult:
    """Resultado da otimização."""
    
    # Toolpath otimizado
    toolpath: Optional[Toolpath] = None
    
    # Alertas e sugestões
    warnings: List[OptimizationWarning] = field(default_factory=list)
    
    # Métricas
    original_rapid_distance: float = 0.0
    optimized_rapid_distance: float = 0.0
    distance_saved: float = 0.0
    time_saved: float = 0.0  # segundos
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    
    @property
    def improvement_percentage(self) -> float:
        """Porcentagem de melhoria no deslocamento."""
        if self.original_rapid_distance <= 0:
            return 0.0
        return (self.distance_saved / self.original_rapid_distance) * 100


class PlasmaOptimizer:
    """Otimizador de corte plasma."""
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Inicializa o otimizador.
        
        Args:
            config: Configuração de otimização
        """
        self.config = config or OptimizationConfig()
    
    def optimize(self, toolpath: Toolpath) -> OptimizationResult:
        """
        Otimiza um toolpath existente.
        
        Args:
            toolpath: Toolpath para otimizar
            
        Returns:
            OptimizationResult: Resultado com toolpath otimizado
        """
        logger.info(f"Otimizando toolpath com {len(toolpath.paths)} caminhos")
        
        result = OptimizationResult()
        result.original_rapid_distance = toolpath.total_rapid_length
        
        try:
            # Validar geometria
            if self.config.validate_geometry:
                validation_warnings = self._validate_geometry(toolpath)
                result.warnings.extend(validation_warnings)
            
            # Aplicar otimizações baseado no nível
            if self.config.level == OptimizationLevel.BASIC:
                optimized = self._basic_optimization(toolpath)
            elif self.config.level == OptimizationLevel.STANDARD:
                optimized = self._standard_optimization(toolpath)
            else:
                optimized = self._advanced_optimization(toolpath)
            
            # Recalcular estatísticas
            optimized.calculate_statistics()
            
            result.toolpath = optimized
            result.optimized_rapid_distance = optimized.total_rapid_length
            result.distance_saved = result.original_rapid_distance - result.optimized_rapid_distance
            
            # Estimar tempo economizado (assumindo 10000 mm/min para rapids)
            result.time_saved = result.distance_saved / 10000 * 60
            
            logger.info(
                f"Otimização concluída: {result.improvement_percentage:.1f}% de melhoria, "
                f"{result.distance_saved:.1f}mm economizados"
            )
        
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Erro na otimização: {e}")
        
        return result
    
    def analyze(self, geometry: Geometry) -> List[OptimizationWarning]:
        """
        Analisa geometria antes da geração de toolpath.
        
        Args:
            geometry: Geometria para análise
            
        Returns:
            Lista de alertas e sugestões
        """
        warnings = []
        
        # Verificar tamanho mínimo de features
        for i, poly in enumerate(geometry.polylines):
            if poly.is_closed:
                area = poly.area()
                if area < self.config.min_feature_size ** 2:
                    warnings.append(OptimizationWarning(
                        level=WarningLevel.WARNING,
                        message=f"Contorno {i+1} muito pequeno (área: {area:.2f}mm²)",
                        suggestion="Considere remover ou aumentar para melhor qualidade de corte",
                        path_index=i
                    ))
        
        # Verificar círculos pequenos
        for i, circle in enumerate(geometry.circles):
            if circle.radius < self.config.min_feature_size:
                warnings.append(OptimizationWarning(
                    level=WarningLevel.WARNING,
                    message=f"Círculo {i+1} muito pequeno (raio: {circle.radius:.2f}mm)",
                    suggestion="Raio mínimo recomendado: {:.1f}mm".format(self.config.min_feature_size),
                    path_index=i
                ))
        
        # Verificar cantos internos agudos
        warnings.extend(self._check_sharp_corners(geometry))
        
        # Verificar sobreposições
        if self.config.check_intersections:
            warnings.extend(self._check_intersections(geometry))
        
        return warnings
    
    def suggest_parameters(
        self, 
        geometry: Geometry,
        material: str = "mild_steel",
        thickness: float = 6.0
    ) -> Dict:
        """
        Sugere parâmetros de corte otimizados.
        
        Args:
            geometry: Geometria para análise
            material: Tipo de material
            thickness: Espessura em mm
            
        Returns:
            Dict com parâmetros sugeridos
        """
        # Calcular bounding box
        bbox = geometry.calculate_bounding_box()
        width = bbox[1].x - bbox[0].x
        height = bbox[1].y - bbox[0].y
        
        # Calcular comprimento total estimado de corte
        total_length = 0.0
        for poly in geometry.polylines:
            total_length += poly.length
        for circle in geometry.circles:
            total_length += circle.circumference
        for arc in geometry.arcs:
            total_length += arc.arc_length
        for line in geometry.lines:
            total_length += line.length
        
        # Parâmetros base por material
        params = {
            "mild_steel": {
                "kerf_width": 1.0 + thickness * 0.08,
                "lead_in_length": max(2.0, thickness * 0.4),
                "lead_out_length": max(1.5, thickness * 0.3),
                "pierce_delay": 0.3 + thickness * 0.05,
            },
            "stainless": {
                "kerf_width": 1.2 + thickness * 0.1,
                "lead_in_length": max(2.5, thickness * 0.5),
                "lead_out_length": max(2.0, thickness * 0.35),
                "pierce_delay": 0.4 + thickness * 0.06,
            },
            "aluminum": {
                "kerf_width": 1.5 + thickness * 0.12,
                "lead_in_length": max(3.0, thickness * 0.5),
                "lead_out_length": max(2.5, thickness * 0.4),
                "pierce_delay": 0.25 + thickness * 0.04,
            },
        }
        
        base = params.get(material.lower(), params["mild_steel"])
        
        # Ajustar lead baseado no tamanho dos contornos
        has_small_features = any(
            poly.area() < 500 for poly in geometry.polylines if poly.is_closed
        )
        if has_small_features:
            base["lead_in_length"] = min(base["lead_in_length"], 2.5)
            base["lead_out_length"] = min(base["lead_out_length"], 2.0)
        
        return {
            **base,
            "estimated_cut_length": total_length,
            "sheet_size": {"width": width, "height": height},
            "num_contours": len(geometry.polylines) + len(geometry.circles),
            "lead_type": "arc" if thickness > 8 else "line",
            "thc_enabled": thickness > 3,
            "recommended_nesting": width > 500 or height > 500,
        }
    
    def _validate_geometry(self, toolpath: Toolpath) -> List[OptimizationWarning]:
        """Valida geometria do toolpath."""
        warnings = []
        
        for i, path in enumerate(toolpath.paths):
            if not path.moves:
                warnings.append(OptimizationWarning(
                    level=WarningLevel.WARNING,
                    message=f"Caminho {i+1} sem movimentos",
                    path_index=i
                ))
                continue
            
            # Verificar movimentos muito curtos
            for j, move in enumerate(path.moves):
                if move.length() < 0.1:  # < 0.1mm
                    warnings.append(OptimizationWarning(
                        level=WarningLevel.INFO,
                        message=f"Movimento muito curto no caminho {i+1}",
                        suggestion="Considere simplificar a geometria",
                        path_index=i
                    ))
                    break
        
        return warnings
    
    def _check_sharp_corners(self, geometry: Geometry) -> List[OptimizationWarning]:
        """Verifica cantos internos muito agudos."""
        warnings = []
        
        for i, poly in enumerate(geometry.polylines):
            if not poly.is_closed or len(poly.points) < 3:
                continue
            
            n = len(poly.points)
            for j in range(n):
                p_prev = poly.points[(j - 1) % n]
                p_curr = poly.points[j]
                p_next = poly.points[(j + 1) % n]
                
                # Calcular ângulo
                v1 = Point(p_curr.x - p_prev.x, p_curr.y - p_prev.y)
                v2 = Point(p_next.x - p_curr.x, p_next.y - p_curr.y)
                
                len1 = math.sqrt(v1.x**2 + v1.y**2)
                len2 = math.sqrt(v2.x**2 + v2.y**2)
                
                if len1 < 0.001 or len2 < 0.001:
                    continue
                
                cos_angle = (v1.x * v2.x + v1.y * v2.y) / (len1 * len2)
                cos_angle = max(-1, min(1, cos_angle))
                angle = math.degrees(math.acos(cos_angle))
                
                # Verificar se é canto interno muito agudo
                cross = v1.x * v2.y - v1.y * v2.x
                if cross < 0 and angle < 30:  # Canto interno < 30°
                    warnings.append(OptimizationWarning(
                        level=WarningLevel.WARNING,
                        message=f"Canto interno agudo ({angle:.0f}°) no contorno {i+1}",
                        suggestion="Adicione um raio de pelo menos {:.1f}mm".format(
                            self.config.min_internal_corner_radius
                        ),
                        path_index=i
                    ))
                    break  # Um aviso por contorno
        
        return warnings
    
    def _check_intersections(self, geometry: Geometry) -> List[OptimizationWarning]:
        """Verifica intersecções entre contornos."""
        warnings = []
        
        # Verificação simplificada usando bounding boxes
        polys = geometry.polylines
        
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                if self._bboxes_intersect(polys[i], polys[j]):
                    # Podem intersectar - verificar mais detalhadamente
                    if not polys[i].is_closed or not polys[j].is_closed:
                        continue
                    
                    # Verificar se um está dentro do outro (OK) vs sobreposição (problema)
                    if not polys[i].is_inside(polys[j]) and not polys[j].is_inside(polys[i]):
                        warnings.append(OptimizationWarning(
                            level=WarningLevel.ERROR,
                            message=f"Possível sobreposição entre contornos {i+1} e {j+1}",
                            suggestion="Verifique e corrija a geometria antes do corte"
                        ))
        
        return warnings
    
    def _bboxes_intersect(self, poly1: Polyline, poly2: Polyline) -> bool:
        """Verifica se bounding boxes se intersectam."""
        bbox1 = poly1.bounding_box
        bbox2 = poly2.bounding_box
        
        return not (
            bbox1[1].x < bbox2[0].x or  # poly1 à esquerda de poly2
            bbox1[0].x > bbox2[1].x or  # poly1 à direita de poly2
            bbox1[1].y < bbox2[0].y or  # poly1 abaixo de poly2
            bbox1[0].y > bbox2[1].y     # poly1 acima de poly2
        )
    
    def _basic_optimization(self, toolpath: Toolpath) -> Toolpath:
        """Otimização básica - apenas reordenação interna primeiro."""
        # Já foi feito no toolpath generator
        return toolpath
    
    def _standard_optimization(self, toolpath: Toolpath) -> Toolpath:
        """Otimização padrão - inclui minimização de deslocamento."""
        # Reordenar usando TSP simplificado (greedy)
        paths = list(toolpath.paths)
        
        if len(paths) <= 2:
            return toolpath
        
        # Separar internos e externos
        internals = [p for p in paths if p.contour_type == ContourType.INTERNAL]
        externals = [p for p in paths if p.contour_type == ContourType.EXTERNAL]
        
        # Otimizar cada grupo
        optimized_internals = self._greedy_tsp(internals)
        optimized_externals = self._greedy_tsp(externals)
        
        # Reconstruir toolpath
        new_toolpath = Toolpath(
            kerf_compensation=toolpath.kerf_compensation,
            cutting_speed=toolpath.cutting_speed
        )
        new_toolpath.paths = optimized_internals + optimized_externals
        
        return new_toolpath
    
    def _advanced_optimization(self, toolpath: Toolpath) -> Toolpath:
        """Otimização avançada - todas as otimizações."""
        # Aplicar otimização padrão primeiro
        optimized = self._standard_optimization(toolpath)
        
        # Adicionar considerações térmicas
        optimized = self._apply_thermal_optimization(optimized)
        
        return optimized
    
    def _greedy_tsp(self, paths: List[CuttingPath]) -> List[CuttingPath]:
        """Algoritmo guloso para TSP."""
        if not paths:
            return []
        
        result = []
        remaining = list(paths)
        current_pos = Point(0, 0)
        
        while remaining:
            # Encontrar caminho mais próximo
            min_dist = float('inf')
            min_idx = 0
            
            for i, path in enumerate(remaining):
                entry = path.entry_point or (path.original_geometry.centroid if path.original_geometry else Point(0, 0))
                if entry:
                    dist = current_pos.distance_to(entry)
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
            
            # Adicionar ao resultado
            selected = remaining.pop(min_idx)
            result.append(selected)
            
            # Atualizar posição
            if selected.moves:
                last_move = (selected.lead_out or selected.moves)[-1]
                current_pos = last_move.end_point
        
        return result
    
    def _apply_thermal_optimization(self, toolpath: Toolpath) -> Toolpath:
        """Aplica otimização térmica (reordenar para distribuir calor)."""
        # Implementação simplificada - intercalar cortes distantes
        paths = list(toolpath.paths)
        
        if len(paths) <= 2:
            return toolpath
        
        # Dividir em regiões (quadrantes simplificados)
        # e intercalar entre regiões
        
        # Por enquanto, retornar sem modificação adicional
        # (otimização térmica completa requer análise mais complexa)
        
        return toolpath
