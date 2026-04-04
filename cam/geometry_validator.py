"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Validação Avançada de Geometria
Engenharia CAD - Validação para Corte CNC Plasma
═══════════════════════════════════════════════════════════════════════════════

Validações implementadas:
- Detecção de auto-interseções
- Verificação de contornos abertos
- Raios mínimos para kerf
- Distância mínima entre contornos
- Geometrias muito pequenas
- Ângulos agudos problemáticos
- Verificação de tolerâncias
- Análise de qualidade do corte esperado

Integração com:
- Frontend (validação em tempo real)
- G-code generator (pré-validação)
- Nesting engine (peças válidas apenas)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set

logger = logging.getLogger("engcad.cam.validator")


class ValidationSeverity(Enum):
    """Níveis de severidade das validações."""
    ERROR = "error"       # Impede geração de G-code
    WARNING = "warning"   # Pode gerar, mas com problemas
    INFO = "info"         # Informativo apenas
    SUGGESTION = "suggestion"  # Sugestão de melhoria


class ValidationCategory(Enum):
    """Categorias de validação."""
    GEOMETRY = "geometry"         # Problemas geométricos
    CUTTING = "cutting"           # Problemas de corte
    QUALITY = "quality"           # Problemas de qualidade
    PERFORMANCE = "performance"   # Problemas de performance
    SAFETY = "safety"             # Problemas de segurança


@dataclass
class ValidationIssue:
    """Representa um problema encontrado na validação."""
    code: str                      # Código único do problema
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    suggestion: Optional[str] = None
    entity_index: Optional[int] = None
    entity_type: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    value: Optional[float] = None
    min_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "entityIndex": self.entity_index,
            "entityType": self.entity_type,
            "location": {"x": self.location[0], "y": self.location[1]} if self.location else None,
            "value": self.value,
            "minValue": self.min_value
        }


@dataclass
class ValidationConfig:
    """Configuração de validação."""
    
    # Tolerâncias geométricas
    point_tolerance: float = 0.01      # mm - tolerância para pontos coincidentes
    angle_tolerance: float = 0.001     # rad - tolerância angular
    
    # Limites para plasma
    min_feature_size: float = 3.0      # mm - tamanho mínimo de feature
    min_hole_diameter: float = 3.0     # mm - diâmetro mínimo de furo
    min_corner_radius: float = 1.5     # mm - raio mínimo em cantos
    min_distance_between_cuts: float = 5.0  # mm - distância mínima entre cortes
    min_edge_distance: float = 10.0    # mm - distância mínima da borda
    
    # Ângulos
    min_internal_angle: float = 30.0   # graus - ângulo interno mínimo
    max_acute_angle: float = 15.0      # graus - limiar para canto agudo
    
    # Kerf
    kerf_width: float = 1.5            # mm - largura do kerf
    
    # Qualidade
    check_self_intersection: bool = True
    check_open_contours: bool = True
    check_small_features: bool = True
    check_sharp_corners: bool = True
    check_spacing: bool = True
    check_edge_distance: bool = True


@dataclass
class ValidationResult:
    """Resultado da validação."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "statistics": self.statistics
        }


class Point2D:
    """Ponto 2D para cálculos."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_to(self, other: "Point2D") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __eq__(self, other):
        if not isinstance(other, Point2D):
            return False
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001
    
    def __hash__(self):
        return hash((round(self.x, 3), round(self.y, 3)))


class Segment:
    """Segmento de linha para cálculos."""
    def __init__(self, start: Point2D, end: Point2D):
        self.start = start
        self.end = end
    
    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)
    
    @property
    def midpoint(self) -> Point2D:
        return Point2D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2
        )
    
    def intersects(self, other: "Segment", tolerance: float = 0.001) -> Optional[Point2D]:
        """Verifica se dois segmentos se intersectam."""
        x1, y1 = self.start.x, self.start.y
        x2, y2 = self.end.x, self.end.y
        x3, y3 = other.start.x, other.start.y
        x4, y4 = other.end.x, other.end.y
        
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        
        if abs(denom) < tolerance:
            return None  # Paralelas
        
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        
        # Ignorar interseções nos endpoints
        if tolerance < ua < 1 - tolerance and tolerance < ub < 1 - tolerance:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return Point2D(x, y)
        
        return None


class GeometryValidator:
    """
    Validador de geometria para corte CNC plasma.
    
    Executa múltiplas verificações para garantir que a geometria
    pode ser cortada com qualidade e segurança.
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        geometry: Dict[str, Any],
        sheet_width: Optional[float] = None,
        sheet_height: Optional[float] = None
    ) -> ValidationResult:
        """
        Valida geometria completa.
        
        Args:
            geometry: Geometria no formato {lines, arcs, circles, polylines}
            sheet_width: Largura da chapa (para validar posição)
            sheet_height: Altura da chapa
            
        Returns:
            ValidationResult com issues encontradas
        """
        self.issues = []
        statistics = {
            "totalEntities": 0,
            "lines": 0,
            "arcs": 0,
            "circles": 0,
            "polylines": 0,
            "totalLength": 0.0,
        }
        
        # Extrair entidades
        lines = geometry.get("lines", [])
        arcs = geometry.get("arcs", [])
        circles = geometry.get("circles", [])
        polylines = geometry.get("polylines", [])
        
        statistics["lines"] = len(lines)
        statistics["arcs"] = len(arcs)
        statistics["circles"] = len(circles)
        statistics["polylines"] = len(polylines)
        statistics["totalEntities"] = sum([
            len(lines), len(arcs), len(circles), len(polylines)
        ])
        
        # Validar cada tipo de entidade
        self._validate_lines(lines)
        self._validate_arcs(arcs)
        self._validate_circles(circles)
        self._validate_polylines(polylines)
        
        # Validações globais
        if self.config.check_self_intersection:
            self._check_self_intersections(geometry)
        
        if self.config.check_spacing:
            self._check_spacing(geometry)
        
        if sheet_width and sheet_height:
            if self.config.check_edge_distance:
                self._check_edge_distance(geometry, sheet_width, sheet_height)
        
        # Calcular comprimento total
        statistics["totalLength"] = self._calculate_total_length(geometry)
        
        # Determinar se é válido (sem erros)
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in self.issues)
        
        return ValidationResult(
            valid=not has_errors,
            issues=self.issues,
            statistics=statistics
        )
    
    def _validate_lines(self, lines: List[Dict[str, Any]]):
        """Valida linhas."""
        for i, line in enumerate(lines):
            start = line.get("start", {})
            end = line.get("end", {})
            
            p_start = Point2D(start.get("x", 0), start.get("y", 0))
            p_end = Point2D(end.get("x", 0), end.get("y", 0))
            
            length = p_start.distance_to(p_end)
            
            # Linha degenerada (muito curta)
            if length < self.config.point_tolerance:
                self.issues.append(ValidationIssue(
                    code="LINE_DEGENERATE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GEOMETRY,
                    message=f"Linha {i+1} degenerada (comprimento ≈ 0)",
                    suggestion="Remova esta linha ou corrija os pontos",
                    entity_index=i,
                    entity_type="line",
                    value=length
                ))
            
            # Linha muito curta para corte
            elif length < self.config.min_feature_size:
                self.issues.append(ValidationIssue(
                    code="LINE_TOO_SHORT",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.CUTTING,
                    message=f"Linha {i+1} muito curta ({length:.2f}mm < {self.config.min_feature_size}mm)",
                    suggestion="Considere remover ou aumentar esta linha",
                    entity_index=i,
                    entity_type="line",
                    value=length,
                    min_value=self.config.min_feature_size
                ))
    
    def _validate_arcs(self, arcs: List[Dict[str, Any]]):
        """Valida arcos."""
        for i, arc in enumerate(arcs):
            center = arc.get("center", {})
            radius = arc.get("radius", 0)
            
            # Raio muito pequeno
            if radius < self.config.min_corner_radius:
                self.issues.append(ValidationIssue(
                    code="ARC_RADIUS_TOO_SMALL",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.CUTTING,
                    message=f"Arco {i+1} com raio muito pequeno ({radius:.2f}mm < {self.config.min_corner_radius}mm)",
                    suggestion=f"Aumente o raio para pelo menos {self.config.min_corner_radius}mm",
                    entity_index=i,
                    entity_type="arc",
                    location=(center.get("x", 0), center.get("y", 0)),
                    value=radius,
                    min_value=self.config.min_corner_radius
                ))
            
            # Raio menor que kerf (impossível cortar)
            if radius < self.config.kerf_width:
                self.issues.append(ValidationIssue(
                    code="ARC_SMALLER_THAN_KERF",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GEOMETRY,
                    message=f"Arco {i+1} menor que a largura do kerf ({radius:.2f}mm < {self.config.kerf_width}mm)",
                    suggestion="Este arco não pode ser cortado com plasma",
                    entity_index=i,
                    entity_type="arc",
                    location=(center.get("x", 0), center.get("y", 0)),
                    value=radius,
                    min_value=self.config.kerf_width
                ))
    
    def _validate_circles(self, circles: List[Dict[str, Any]]):
        """Valida círculos."""
        for i, circle in enumerate(circles):
            center = circle.get("center", {})
            radius = circle.get("radius", 0)
            diameter = radius * 2
            
            # Furo muito pequeno
            if diameter < self.config.min_hole_diameter:
                self.issues.append(ValidationIssue(
                    code="HOLE_TOO_SMALL",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.CUTTING,
                    message=f"Círculo {i+1} muito pequeno (Ø{diameter:.2f}mm < Ø{self.config.min_hole_diameter}mm)",
                    suggestion=f"Aumente o diâmetro para pelo menos {self.config.min_hole_diameter}mm",
                    entity_index=i,
                    entity_type="circle",
                    location=(center.get("x", 0), center.get("y", 0)),
                    value=diameter,
                    min_value=self.config.min_hole_diameter
                ))
            
            # Impossível cortar (menor que kerf)
            if diameter < self.config.kerf_width * 2:
                self.issues.append(ValidationIssue(
                    code="HOLE_SMALLER_THAN_KERF",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GEOMETRY,
                    message=f"Círculo {i+1} menor que o kerf (Ø{diameter:.2f}mm < Ø{self.config.kerf_width * 2}mm)",
                    suggestion="Este furo não pode ser cortado com plasma. Use puncionadeira ou mandrilamento.",
                    entity_index=i,
                    entity_type="circle",
                    location=(center.get("x", 0), center.get("y", 0)),
                    value=diameter,
                    min_value=self.config.kerf_width * 2
                ))
    
    def _validate_polylines(self, polylines: List[Dict[str, Any]]):
        """Valida polilinhas."""
        for i, poly in enumerate(polylines):
            points = poly.get("points", [])
            is_closed = poly.get("closed", False)
            
            if len(points) < 2:
                self.issues.append(ValidationIssue(
                    code="POLYLINE_INSUFFICIENT_POINTS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GEOMETRY,
                    message=f"Polilinha {i+1} com pontos insuficientes ({len(points)})",
                    entity_index=i,
                    entity_type="polyline"
                ))
                continue
            
            # Verificar contorno aberto
            if self.config.check_open_contours and not is_closed:
                first = Point2D(points[0].get("x", 0), points[0].get("y", 0))
                last = Point2D(points[-1].get("x", 0), points[-1].get("y", 0))
                
                gap = first.distance_to(last)
                if gap > self.config.point_tolerance:
                    self.issues.append(ValidationIssue(
                        code="CONTOUR_NOT_CLOSED",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.GEOMETRY,
                        message=f"Contorno {i+1} não está fechado (gap: {gap:.2f}mm)",
                        suggestion="Feche o contorno conectando o último ponto ao primeiro",
                        entity_index=i,
                        entity_type="polyline",
                        value=gap
                    ))
            
            # Verificar ângulos agudos
            if self.config.check_sharp_corners and len(points) >= 3:
                self._check_sharp_corners_in_polyline(i, points, is_closed)
            
            # Verificar segmentos pequenos
            if self.config.check_small_features:
                self._check_small_segments(i, points)
    
    def _check_sharp_corners_in_polyline(
        self, 
        poly_index: int, 
        points: List[Dict[str, Any]], 
        is_closed: bool
    ):
        """Verifica ângulos agudos em polilinha."""
        n = len(points)
        
        for i in range(n):
            # Pular primeiro/último se não fechado
            if not is_closed and (i == 0 or i == n - 1):
                continue
            
            # Índices dos pontos vizinhos
            prev_idx = (i - 1) % n
            next_idx = (i + 1) % n
            
            # Pontos
            p_prev = Point2D(points[prev_idx].get("x", 0), points[prev_idx].get("y", 0))
            p_curr = Point2D(points[i].get("x", 0), points[i].get("y", 0))
            p_next = Point2D(points[next_idx].get("x", 0), points[next_idx].get("y", 0))
            
            # Vetores
            v1 = (p_prev.x - p_curr.x, p_prev.y - p_curr.y)
            v2 = (p_next.x - p_curr.x, p_next.y - p_curr.y)
            
            # Comprimentos
            len1 = math.sqrt(v1[0]**2 + v1[1]**2)
            len2 = math.sqrt(v2[0]**2 + v2[1]**2)
            
            if len1 < 0.001 or len2 < 0.001:
                continue
            
            # Ângulo entre vetores
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            cos_angle = max(-1, min(1, dot / (len1 * len2)))
            angle = math.degrees(math.acos(cos_angle))
            
            # Ângulo interno
            internal_angle = 180 - angle
            
            if internal_angle < self.config.max_acute_angle:
                self.issues.append(ValidationIssue(
                    code="SHARP_CORNER",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.QUALITY,
                    message=f"Canto agudo no contorno {poly_index+1}, ponto {i+1} ({internal_angle:.1f}°)",
                    suggestion=f"Adicione raio de {self.config.min_corner_radius}mm ou aumente o ângulo",
                    entity_index=poly_index,
                    entity_type="polyline",
                    location=(p_curr.x, p_curr.y),
                    value=internal_angle,
                    min_value=self.config.min_internal_angle
                ))
    
    def _check_small_segments(self, poly_index: int, points: List[Dict[str, Any]]):
        """Verifica segmentos muito curtos."""
        for i in range(len(points) - 1):
            p1 = Point2D(points[i].get("x", 0), points[i].get("y", 0))
            p2 = Point2D(points[i+1].get("x", 0), points[i+1].get("y", 0))
            
            length = p1.distance_to(p2)
            
            if length < self.config.min_feature_size:
                self.issues.append(ValidationIssue(
                    code="SEGMENT_TOO_SHORT",
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.QUALITY,
                    message=f"Segmento curto no contorno {poly_index+1} ({length:.2f}mm)",
                    suggestion="Considere simplificar a geometria",
                    entity_index=poly_index,
                    entity_type="polyline",
                    location=((p1.x + p2.x)/2, (p1.y + p2.y)/2),
                    value=length,
                    min_value=self.config.min_feature_size
                ))
    
    def _check_self_intersections(self, geometry: Dict[str, Any]):
        """Verifica auto-interseções entre contornos."""
        # Coletar todos os segmentos
        segments: List[Tuple[Segment, int, str]] = []
        
        for i, line in enumerate(geometry.get("lines", [])):
            start = line.get("start", {})
            end = line.get("end", {})
            seg = Segment(
                Point2D(start.get("x", 0), start.get("y", 0)),
                Point2D(end.get("x", 0), end.get("y", 0))
            )
            segments.append((seg, i, "line"))
        
        for i, poly in enumerate(geometry.get("polylines", [])):
            points = poly.get("points", [])
            for j in range(len(points) - 1):
                p1 = points[j]
                p2 = points[j + 1]
                seg = Segment(
                    Point2D(p1.get("x", 0), p1.get("y", 0)),
                    Point2D(p2.get("x", 0), p2.get("y", 0))
                )
                segments.append((seg, i, f"polyline[{j}]"))
        
        # Verificar interseções
        intersections_found: Set[Tuple[int, int]] = set()
        
        for i in range(len(segments)):
            for j in range(i + 2, len(segments)):  # +2 para evitar segmentos adjacentes
                seg1, idx1, type1 = segments[i]
                seg2, idx2, type2 = segments[j]
                
                intersection = seg1.intersects(seg2)
                if intersection:
                    key = (min(idx1, idx2), max(idx1, idx2))
                    if key not in intersections_found:
                        intersections_found.add(key)
                        
                        self.issues.append(ValidationIssue(
                            code="SELF_INTERSECTION",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.GEOMETRY,
                            message=f"Auto-interseção detectada entre entidades {type1} e {type2}",
                            suggestion="Corrija a geometria removendo a interseção",
                            location=(intersection.x, intersection.y)
                        ))
    
    def _check_spacing(self, geometry: Dict[str, Any]):
        """Verifica espaçamento entre cortes."""
        # Coletar centros de furos
        circles = geometry.get("circles", [])
        
        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                c1 = circles[i]
                c2 = circles[j]
                
                center1 = Point2D(c1["center"]["x"], c1["center"]["y"])
                center2 = Point2D(c2["center"]["x"], c2["center"]["y"])
                
                distance = center1.distance_to(center2)
                min_dist = c1["radius"] + c2["radius"] + self.config.min_distance_between_cuts
                
                if distance < min_dist:
                    actual_gap = distance - c1["radius"] - c2["radius"]
                    self.issues.append(ValidationIssue(
                        code="CIRCLES_TOO_CLOSE",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.CUTTING,
                        message=f"Círculos {i+1} e {j+1} muito próximos (gap: {actual_gap:.2f}mm)",
                        suggestion=f"Aumente a distância para pelo menos {self.config.min_distance_between_cuts}mm",
                        location=((center1.x + center2.x)/2, (center1.y + center2.y)/2),
                        value=actual_gap,
                        min_value=self.config.min_distance_between_cuts
                    ))
    
    def _check_edge_distance(
        self, 
        geometry: Dict[str, Any], 
        sheet_width: float, 
        sheet_height: float
    ):
        """Verifica distância das bordas da chapa."""
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        # Calcular bounding box
        for circle in geometry.get("circles", []):
            cx = circle["center"]["x"]
            cy = circle["center"]["y"]
            r = circle["radius"]
            min_x = min(min_x, cx - r)
            min_y = min(min_y, cy - r)
            max_x = max(max_x, cx + r)
            max_y = max(max_y, cy + r)
        
        for poly in geometry.get("polylines", []):
            for p in poly.get("points", []):
                min_x = min(min_x, p.get("x", 0))
                min_y = min(min_y, p.get("y", 0))
                max_x = max(max_x, p.get("x", 0))
                max_y = max(max_y, p.get("y", 0))
        
        for line in geometry.get("lines", []):
            for key in ["start", "end"]:
                p = line.get(key, {})
                min_x = min(min_x, p.get("x", 0))
                min_y = min(min_y, p.get("y", 0))
                max_x = max(max_x, p.get("x", 0))
                max_y = max(max_y, p.get("y", 0))
        
        # Verificar margens
        min_edge = self.config.min_edge_distance
        
        if min_x < min_edge:
            self.issues.append(ValidationIssue(
                code="TOO_CLOSE_TO_LEFT_EDGE",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SAFETY,
                message=f"Geometria muito próxima da borda esquerda ({min_x:.2f}mm < {min_edge}mm)",
                suggestion=f"Mova a geometria pelo menos {min_edge}mm da borda",
                value=min_x,
                min_value=min_edge
            ))
        
        if min_y < min_edge:
            self.issues.append(ValidationIssue(
                code="TOO_CLOSE_TO_BOTTOM_EDGE",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SAFETY,
                message=f"Geometria muito próxima da borda inferior ({min_y:.2f}mm < {min_edge}mm)",
                suggestion=f"Mova a geometria pelo menos {min_edge}mm da borda",
                value=min_y,
                min_value=min_edge
            ))
        
        if max_x > sheet_width - min_edge:
            self.issues.append(ValidationIssue(
                code="TOO_CLOSE_TO_RIGHT_EDGE",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SAFETY,
                message=f"Geometria muito próxima da borda direita ({sheet_width - max_x:.2f}mm < {min_edge}mm)",
                suggestion=f"Mova a geometria pelo menos {min_edge}mm da borda",
                value=sheet_width - max_x,
                min_value=min_edge
            ))
        
        if max_y > sheet_height - min_edge:
            self.issues.append(ValidationIssue(
                code="TOO_CLOSE_TO_TOP_EDGE",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SAFETY,
                message=f"Geometria muito próxima da borda superior ({sheet_height - max_y:.2f}mm < {min_edge}mm)",
                suggestion=f"Mova a geometria pelo menos {min_edge}mm da borda",
                value=sheet_height - max_y,
                min_value=min_edge
            ))
    
    def _calculate_total_length(self, geometry: Dict[str, Any]) -> float:
        """Calcula comprimento total de corte."""
        total = 0.0
        
        for line in geometry.get("lines", []):
            start = line.get("start", {})
            end = line.get("end", {})
            p1 = Point2D(start.get("x", 0), start.get("y", 0))
            p2 = Point2D(end.get("x", 0), end.get("y", 0))
            total += p1.distance_to(p2)
        
        for arc in geometry.get("arcs", []):
            radius = arc.get("radius", 0)
            start_angle = arc.get("start_angle", 0)
            end_angle = arc.get("end_angle", 0)
            arc_length = abs(end_angle - start_angle) * math.pi / 180 * radius
            total += arc_length
        
        for circle in geometry.get("circles", []):
            radius = circle.get("radius", 0)
            total += 2 * math.pi * radius
        
        for poly in geometry.get("polylines", []):
            points = poly.get("points", [])
            for i in range(len(points) - 1):
                p1 = Point2D(points[i].get("x", 0), points[i].get("y", 0))
                p2 = Point2D(points[i+1].get("x", 0), points[i+1].get("y", 0))
                total += p1.distance_to(p2)
            
            # Fechar polilinha se necessário
            if poly.get("closed", False) and len(points) >= 2:
                p1 = Point2D(points[-1].get("x", 0), points[-1].get("y", 0))
                p2 = Point2D(points[0].get("x", 0), points[0].get("y", 0))
                total += p1.distance_to(p2)
        
        return total


def validate_for_plasma_cutting(
    geometry: Dict[str, Any],
    kerf_width: float = 1.5,
    thickness: float = 6.0,
    sheet_width: Optional[float] = None,
    sheet_height: Optional[float] = None
) -> ValidationResult:
    """
    Função utilitária para validação rápida.
    
    Args:
        geometry: Geometria para validar
        kerf_width: Largura do kerf em mm
        thickness: Espessura do material em mm
        sheet_width: Largura da chapa
        sheet_height: Altura da chapa
        
    Returns:
        ValidationResult
    """
    # Ajustar configuração baseado na espessura
    config = ValidationConfig(
        kerf_width=kerf_width,
        min_hole_diameter=max(3.0, thickness * 0.8),  # 80% da espessura
        min_feature_size=max(2.0, kerf_width * 2),
        min_corner_radius=max(1.0, kerf_width),
        min_distance_between_cuts=max(5.0, thickness * 0.5),
    )
    
    validator = GeometryValidator(config)
    return validator.validate(geometry, sheet_width, sheet_height)
