"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Gerador de Toolpath
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Responsável por:
- Converter geometrias em caminhos de corte (toolpaths)
- Ordenar cortes de forma inteligente (internos primeiro)
- Minimizar movimentos de deslocamento rápido
- Aplicar lead-in e lead-out
- Implementar compensação de kerf
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .geometry_parser import Geometry, Line, Arc, Circle, Polyline, Point

logger = logging.getLogger("engcad.cam.toolpath_generator")


class MoveType(Enum):
    """Tipos de movimento."""
    RAPID = "rapid"       # G00 - Movimento rápido (sem corte)
    LINEAR = "linear"     # G01 - Movimento linear (corte)
    ARC_CW = "arc_cw"     # G02 - Arco horário
    ARC_CCW = "arc_ccw"   # G03 - Arco anti-horário


class ContourType(Enum):
    """Tipo de contorno."""
    EXTERNAL = "external"  # Contorno externo
    INTERNAL = "internal"  # Contorno interno (furo)


@dataclass
class ToolpathMove:
    """Um movimento individual do toolpath."""
    move_type: MoveType
    end_point: Point
    start_point: Optional[Point] = None
    
    # Para arcos
    center: Optional[Point] = None
    radius: Optional[float] = None
    
    # Metadados
    feed_rate: Optional[float] = None  # mm/min
    is_cutting: bool = False
    
    def length(self) -> float:
        """Calcula comprimento do movimento."""
        if not self.start_point:
            return 0.0
        
        if self.move_type in (MoveType.RAPID, MoveType.LINEAR):
            return self.start_point.distance_to(self.end_point)
        else:
            # Arco - calcular comprimento do arco
            if self.radius:
                # Cálculo simplificado usando a corda como aproximação
                chord = self.start_point.distance_to(self.end_point)
                # Ângulo aproximado
                angle = 2 * math.asin(min(chord / (2 * self.radius), 1.0))
                return angle * self.radius
        
        return 0.0


@dataclass
class LeadInOut:
    """Configuração de lead-in e lead-out."""
    enabled: bool = True
    type: str = "arc"  # "arc", "line", "tangent"
    length: float = 3.0  # mm
    angle: float = 45.0  # graus (para lead-in linear)


@dataclass
class CuttingPath:
    """Um caminho de corte completo (um contorno)."""
    moves: List[ToolpathMove] = field(default_factory=list)
    contour_type: ContourType = ContourType.EXTERNAL
    
    # Geometria original
    original_geometry: Optional[Polyline] = None
    
    # Lead-in/out
    lead_in: List[ToolpathMove] = field(default_factory=list)
    lead_out: List[ToolpathMove] = field(default_factory=list)
    
    # Metadados
    total_length: float = 0.0
    estimated_time: float = 0.0  # segundos
    
    @property
    def start_point(self) -> Optional[Point]:
        """Ponto inicial do corte (após lead-in)."""
        if self.moves:
            return self.moves[0].start_point
        return None
    
    @property
    def entry_point(self) -> Optional[Point]:
        """Ponto de entrada (antes do lead-in)."""
        if self.lead_in:
            return self.lead_in[0].start_point
        return self.start_point
    
    def calculate_metrics(self, cutting_speed: float, rapid_speed: float = 10000) -> None:
        """Calcula métricas do caminho."""
        self.total_length = 0.0
        self.estimated_time = 0.0
        
        all_moves = self.lead_in + self.moves + self.lead_out
        
        for move in all_moves:
            length = move.length()
            self.total_length += length
            
            if move.move_type == MoveType.RAPID:
                self.estimated_time += length / rapid_speed * 60  # segundos
            else:
                speed = move.feed_rate or cutting_speed
                self.estimated_time += length / speed * 60  # segundos


@dataclass
class Toolpath:
    """Toolpath completo para um desenho."""
    paths: List[CuttingPath] = field(default_factory=list)
    
    # Estatísticas
    total_cutting_length: float = 0.0
    total_rapid_length: float = 0.0
    total_time: float = 0.0
    
    # Configurações usadas
    kerf_compensation: float = 0.0
    cutting_speed: float = 0.0
    
    def calculate_statistics(self) -> None:
        """Calcula estatísticas do toolpath."""
        self.total_cutting_length = 0.0
        self.total_rapid_length = 0.0
        self.total_time = 0.0
        
        for path in self.paths:
            for move in (path.lead_in + path.moves + path.lead_out):
                length = move.length()
                if move.move_type == MoveType.RAPID:
                    self.total_rapid_length += length
                else:
                    self.total_cutting_length += length
            
            self.total_time += path.estimated_time


class ToolpathGenerator:
    """Gerador de toolpaths para corte plasma."""
    
    def __init__(
        self,
        kerf_width: float = 1.5,      # mm - largura do corte
        lead_in_length: float = 3.0,  # mm
        lead_out_length: float = 2.0, # mm
        lead_type: str = "arc",       # "arc" ou "line"
        safe_height: float = 10.0,    # mm - altura segura para movimentos rápidos
    ):
        """
        Inicializa o gerador de toolpath.
        
        Args:
            kerf_width: Largura do corte do plasma (para compensação)
            lead_in_length: Comprimento do lead-in
            lead_out_length: Comprimento do lead-out
            lead_type: Tipo de lead-in/out ("arc" ou "line")
            safe_height: Altura segura para movimentos rápidos
        """
        self.kerf_width = kerf_width
        self.lead_in_length = lead_in_length
        self.lead_out_length = lead_out_length
        self.lead_type = lead_type
        self.safe_height = safe_height
    
    def generate(
        self,
        geometry: Geometry,
        cutting_speed: float = 2000,  # mm/min
        apply_kerf: bool = True,
        optimize_order: bool = True
    ) -> Toolpath:
        """
        Gera toolpath a partir da geometria.
        
        Args:
            geometry: Objeto Geometry com as entidades
            cutting_speed: Velocidade de corte em mm/min
            apply_kerf: Se deve aplicar compensação de kerf
            optimize_order: Se deve otimizar a ordem de corte
            
        Returns:
            Toolpath: Toolpath completo
        """
        logger.info(f"Gerando toolpath para {geometry.total_entities} entidades")
        
        toolpath = Toolpath(
            kerf_compensation=self.kerf_width if apply_kerf else 0,
            cutting_speed=cutting_speed
        )
        
        # Converter todas as geometrias em polilinhas
        contours = self._extract_contours(geometry)
        
        # Classificar contornos (interno/externo)
        classified = self._classify_contours(contours)
        
        # Ordenar para otimização
        if optimize_order:
            ordered = self._optimize_order(classified)
        else:
            ordered = classified
        
        # Gerar caminhos de corte
        current_pos = Point(0, 0)
        
        for contour, contour_type in ordered:
            path = self._generate_cutting_path(
                contour, 
                contour_type, 
                current_pos,
                cutting_speed,
                apply_kerf
            )
            path.calculate_metrics(cutting_speed)
            toolpath.paths.append(path)
            
            # Atualizar posição atual
            if path.moves:
                last_move = (path.lead_out or path.moves)[-1]
                current_pos = last_move.end_point
        
        toolpath.calculate_statistics()
        
        logger.info(
            f"Toolpath gerado: {len(toolpath.paths)} caminhos, "
            f"{toolpath.total_cutting_length:.1f}mm de corte, "
            f"{toolpath.total_rapid_length:.1f}mm de deslocamento rápido"
        )
        
        return toolpath
    
    def _extract_contours(self, geometry: Geometry) -> List[Polyline]:
        """Extrai e converte todas as geometrias em polilinhas."""
        contours: List[Polyline] = []
        
        # Copiar polilinhas existentes
        for poly in geometry.polylines:
            if len(poly.points) >= 2:
                contours.append(poly)
        
        # Converter círculos em polilinhas
        for circle in geometry.circles:
            poly = self._circle_to_polyline(circle)
            contours.append(poly)
        
        # Converter arcos em polilinhas
        for arc in geometry.arcs:
            poly = self._arc_to_polyline(arc)
            contours.append(poly)
        
        # Tentar conectar linhas em polilinhas
        connected = self._connect_lines(geometry.lines)
        contours.extend(connected)
        
        return contours
    
    def _circle_to_polyline(self, circle: Circle, segments: int = 72) -> Polyline:
        """Converte círculo em polilinha."""
        points = []
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = circle.center.x + circle.radius * math.cos(angle)
            y = circle.center.y + circle.radius * math.sin(angle)
            points.append(Point(x, y))
        
        return Polyline(points=points, closed=True, layer=circle.layer)
    
    def _arc_to_polyline(self, arc: Arc, segments_per_degree: float = 0.5) -> Polyline:
        """Converte arco em polilinha."""
        angle_span = abs(arc.end_angle - arc.start_angle)
        if angle_span > 180:
            angle_span = 360 - angle_span
        
        num_segments = max(3, int(angle_span * segments_per_degree))
        
        points = []
        for i in range(num_segments + 1):
            if arc.clockwise:
                angle = arc.start_angle - (angle_span * i / num_segments)
            else:
                angle = arc.start_angle + (angle_span * i / num_segments)
            
            rad = math.radians(angle)
            x = arc.center.x + arc.radius * math.cos(rad)
            y = arc.center.y + arc.radius * math.sin(rad)
            points.append(Point(x, y))
        
        return Polyline(points=points, closed=False, layer=arc.layer)
    
    def _connect_lines(self, lines: List[Line], tolerance: float = 0.01) -> List[Polyline]:
        """Tenta conectar linhas soltas em polilinhas."""
        if not lines:
            return []
        
        polylines = []
        used = set()
        
        for i, line in enumerate(lines):
            if i in used:
                continue
            
            # Iniciar nova polilinha
            points = [line.start, line.end]
            used.add(i)
            
            # Tentar estender
            changed = True
            while changed:
                changed = False
                for j, other in enumerate(lines):
                    if j in used:
                        continue
                    
                    # Verificar se conecta no início
                    if points[0].distance_to(other.end) < tolerance:
                        points.insert(0, other.start)
                        used.add(j)
                        changed = True
                    elif points[0].distance_to(other.start) < tolerance:
                        points.insert(0, other.end)
                        used.add(j)
                        changed = True
                    # Verificar se conecta no final
                    elif points[-1].distance_to(other.start) < tolerance:
                        points.append(other.end)
                        used.add(j)
                        changed = True
                    elif points[-1].distance_to(other.end) < tolerance:
                        points.append(other.start)
                        used.add(j)
                        changed = True
            
            # Verificar se fechou
            is_closed = points[0].distance_to(points[-1]) < tolerance
            
            polylines.append(Polyline(
                points=points,
                closed=is_closed,
                layer=lines[i].layer
            ))
        
        return polylines
    
    def _classify_contours(
        self, 
        contours: List[Polyline]
    ) -> List[Tuple[Polyline, ContourType]]:
        """Classifica contornos como internos ou externos."""
        result = []
        
        # Para cada contorno, verificar se está dentro de outro
        for i, contour in enumerate(contours):
            if not contour.is_closed:
                # Contornos abertos são tratados como externos
                result.append((contour, ContourType.EXTERNAL))
                continue
            
            is_internal = False
            for j, other in enumerate(contours):
                if i == j or not other.is_closed:
                    continue
                
                # Verificar se contour está dentro de other
                if contour.is_inside(other):
                    is_internal = True
                    break
            
            contour_type = ContourType.INTERNAL if is_internal else ContourType.EXTERNAL
            result.append((contour, contour_type))
        
        return result
    
    def _optimize_order(
        self, 
        classified: List[Tuple[Polyline, ContourType]]
    ) -> List[Tuple[Polyline, ContourType]]:
        """
        Otimiza a ordem de corte.
        
        Regras:
        1. Cortes internos primeiro (para evitar distorção)
        2. Dentro de cada grupo, usar nearest-neighbor para minimizar deslocamentos
        """
        # Separar internos e externos
        internals = [(c, t) for c, t in classified if t == ContourType.INTERNAL]
        externals = [(c, t) for c, t in classified if t == ContourType.EXTERNAL]
        
        # Ordenar cada grupo por nearest-neighbor
        ordered_internals = self._nearest_neighbor_sort(internals)
        ordered_externals = self._nearest_neighbor_sort(externals)
        
        # Internos primeiro, depois externos
        return ordered_internals + ordered_externals
    
    def _nearest_neighbor_sort(
        self, 
        items: List[Tuple[Polyline, ContourType]]
    ) -> List[Tuple[Polyline, ContourType]]:
        """Ordena usando algoritmo nearest-neighbor."""
        if not items:
            return []
        
        result = []
        remaining = list(items)
        current_pos = Point(0, 0)
        
        while remaining:
            # Encontrar o mais próximo
            min_dist = float('inf')
            min_idx = 0
            
            for i, (contour, _) in enumerate(remaining):
                if contour.points:
                    dist = current_pos.distance_to(contour.centroid)
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
            
            # Adicionar ao resultado
            item = remaining.pop(min_idx)
            result.append(item)
            
            # Atualizar posição
            if item[0].points:
                current_pos = item[0].centroid
        
        return result
    
    def _generate_cutting_path(
        self,
        contour: Polyline,
        contour_type: ContourType,
        current_pos: Point,
        cutting_speed: float,
        apply_kerf: bool
    ) -> CuttingPath:
        """Gera um caminho de corte para um contorno."""
        path = CuttingPath(
            contour_type=contour_type,
            original_geometry=contour
        )
        
        if not contour.points or len(contour.points) < 2:
            return path
        
        # Aplicar compensação de kerf se necessário
        if apply_kerf and contour.is_closed:
            offset_contour = self._apply_kerf_compensation(contour, contour_type)
        else:
            offset_contour = contour
        
        # Encontrar melhor ponto de entrada (para minimizar distorção)
        entry_idx = self._find_entry_point(offset_contour)
        
        # Reordenar pontos a partir do ponto de entrada
        points = self._reorder_from_index(offset_contour.points, entry_idx)
        
        # Gerar lead-in
        if offset_contour.is_closed and self.lead_in_length > 0:
            lead_in_moves = self._generate_lead_in(points[0], points[1], current_pos)
            path.lead_in = lead_in_moves
        
        # Gerar movimentos de corte
        for i in range(len(points) - 1):
            move = ToolpathMove(
                move_type=MoveType.LINEAR,
                start_point=points[i],
                end_point=points[i + 1],
                feed_rate=cutting_speed,
                is_cutting=True
            )
            path.moves.append(move)
        
        # Fechar contorno se necessário
        if offset_contour.is_closed and points:
            move = ToolpathMove(
                move_type=MoveType.LINEAR,
                start_point=points[-1],
                end_point=points[0],
                feed_rate=cutting_speed,
                is_cutting=True
            )
            path.moves.append(move)
        
        # Gerar lead-out
        if offset_contour.is_closed and self.lead_out_length > 0 and path.moves:
            last_move = path.moves[-1]
            lead_out_moves = self._generate_lead_out(last_move.end_point, points[0])
            path.lead_out = lead_out_moves
        
        return path
    
    def _apply_kerf_compensation(
        self, 
        contour: Polyline, 
        contour_type: ContourType
    ) -> Polyline:
        """
        Aplica compensação de kerf (offset do caminho).
        
        Para contornos externos: offset para fora (kerf/2)
        Para contornos internos: offset para dentro (kerf/2)
        """
        if not contour.is_closed or len(contour.points) < 3:
            return contour
        
        offset = self.kerf_width / 2
        
        # Para internos, invertemos o offset
        if contour_type == ContourType.INTERNAL:
            offset = -offset
        
        # Calcular normais e aplicar offset
        new_points = []
        n = len(contour.points)
        
        for i in range(n):
            p_prev = contour.points[(i - 1) % n]
            p_curr = contour.points[i]
            p_next = contour.points[(i + 1) % n]
            
            # Vetores das arestas
            v1 = Point(p_curr.x - p_prev.x, p_curr.y - p_prev.y)
            v2 = Point(p_next.x - p_curr.x, p_next.y - p_curr.y)
            
            # Normalizar
            len1 = math.sqrt(v1.x**2 + v1.y**2)
            len2 = math.sqrt(v2.x**2 + v2.y**2)
            
            if len1 < 0.001 or len2 < 0.001:
                new_points.append(p_curr)
                continue
            
            v1 = Point(v1.x / len1, v1.y / len1)
            v2 = Point(v2.x / len2, v2.y / len2)
            
            # Normais (perpendiculares à esquerda)
            n1 = Point(-v1.y, v1.x)
            n2 = Point(-v2.y, v2.x)
            
            # Média das normais (bissetriz)
            bisector = Point((n1.x + n2.x) / 2, (n1.y + n2.y) / 2)
            len_bis = math.sqrt(bisector.x**2 + bisector.y**2)
            
            if len_bis < 0.001:
                bisector = n1
                len_bis = 1.0
            
            bisector = Point(bisector.x / len_bis, bisector.y / len_bis)
            
            # Calcular fator de escala para manter offset correto
            dot = n1.x * bisector.x + n1.y * bisector.y
            if abs(dot) < 0.001:
                scale_factor = 1.0
            else:
                scale_factor = 1.0 / dot
            
            # Limitar para evitar pontos muito distantes em ângulos agudos
            scale_factor = min(scale_factor, 3.0)
            
            # Aplicar offset
            new_x = p_curr.x + bisector.x * offset * scale_factor
            new_y = p_curr.y + bisector.y * offset * scale_factor
            new_points.append(Point(new_x, new_y))
        
        return Polyline(
            points=new_points,
            closed=contour.closed,
            layer=contour.layer
        )
    
    def _find_entry_point(self, contour: Polyline) -> int:
        """
        Encontra o melhor ponto de entrada para o corte.
        
        Preferências:
        1. Cantos (mudança de direção)
        2. Longe de detalhes importantes
        3. Pontos mais distantes do centro
        """
        if not contour.points or len(contour.points) < 3:
            return 0
        
        n = len(contour.points)
        centroid = contour.centroid
        
        # Calcular "score" para cada ponto
        best_idx = 0
        best_score = -float('inf')
        
        for i in range(n):
            p_prev = contour.points[(i - 1) % n]
            p_curr = contour.points[i]
            p_next = contour.points[(i + 1) % n]
            
            # Calcular ângulo de mudança de direção
            v1 = Point(p_curr.x - p_prev.x, p_curr.y - p_prev.y)
            v2 = Point(p_next.x - p_curr.x, p_next.y - p_curr.y)
            
            len1 = math.sqrt(v1.x**2 + v1.y**2)
            len2 = math.sqrt(v2.x**2 + v2.y**2)
            
            if len1 < 0.001 or len2 < 0.001:
                continue
            
            # Produto escalar normalizado (cosseno do ângulo)
            cos_angle = (v1.x * v2.x + v1.y * v2.y) / (len1 * len2)
            cos_angle = max(-1, min(1, cos_angle))  # Clamp
            
            # Ângulo (maior = canto mais agudo)
            angle = abs(math.acos(cos_angle))
            
            # Distância do centro
            dist_center = p_curr.distance_to(centroid)
            
            # Score: preferir cantos e pontos distantes do centro
            score = angle * 100 + dist_center
            
            if score > best_score:
                best_score = score
                best_idx = i
        
        return best_idx
    
    def _reorder_from_index(self, points: List[Point], start_idx: int) -> List[Point]:
        """Reordena lista de pontos para começar em um índice específico."""
        if not points or start_idx == 0:
            return list(points)
        
        n = len(points)
        return [points[(start_idx + i) % n] for i in range(n)]
    
    def _generate_lead_in(
        self, 
        entry_point: Point, 
        next_point: Point,
        current_pos: Point
    ) -> List[ToolpathMove]:
        """Gera movimento de lead-in."""
        moves = []
        
        # Calcular direção do corte
        dx = next_point.x - entry_point.x
        dy = next_point.y - entry_point.y
        length = math.sqrt(dx**2 + dy**2)
        
        if length < 0.001:
            return moves
        
        # Normalizar
        dx /= length
        dy /= length
        
        if self.lead_type == "arc":
            # Lead-in em arco (90 graus)
            # Perpendicular à direção do corte
            perp_x = -dy
            perp_y = dx
            
            # Ponto de início do arco
            arc_start = Point(
                entry_point.x + perp_x * self.lead_in_length,
                entry_point.y + perp_y * self.lead_in_length
            )
            
            # Movimento rápido para posição de início
            moves.append(ToolpathMove(
                move_type=MoveType.RAPID,
                start_point=current_pos,
                end_point=arc_start,
                is_cutting=False
            ))
            
            # Arco até o ponto de entrada
            moves.append(ToolpathMove(
                move_type=MoveType.ARC_CW,
                start_point=arc_start,
                end_point=entry_point,
                center=entry_point,
                radius=self.lead_in_length,
                is_cutting=True
            ))
        
        else:  # "line"
            # Lead-in linear a 45 graus
            angle = math.atan2(dy, dx) + math.radians(135)
            
            line_start = Point(
                entry_point.x + self.lead_in_length * math.cos(angle),
                entry_point.y + self.lead_in_length * math.sin(angle)
            )
            
            # Movimento rápido para posição de início
            moves.append(ToolpathMove(
                move_type=MoveType.RAPID,
                start_point=current_pos,
                end_point=line_start,
                is_cutting=False
            ))
            
            # Linha até o ponto de entrada
            moves.append(ToolpathMove(
                move_type=MoveType.LINEAR,
                start_point=line_start,
                end_point=entry_point,
                is_cutting=True
            ))
        
        return moves
    
    def _generate_lead_out(
        self, 
        exit_point: Point, 
        first_point: Point
    ) -> List[ToolpathMove]:
        """Gera movimento de lead-out."""
        moves = []
        
        # Calcular direção oposta ao início do corte
        dx = exit_point.x - first_point.x
        dy = exit_point.y - first_point.y
        length = math.sqrt(dx**2 + dy**2)
        
        if length < 0.001:
            return moves
        
        # Normalizar
        dx /= length
        dy /= length
        
        if self.lead_type == "arc":
            # Lead-out em arco
            perp_x = dy
            perp_y = -dx
            
            arc_end = Point(
                exit_point.x + perp_x * self.lead_out_length,
                exit_point.y + perp_y * self.lead_out_length
            )
            
            moves.append(ToolpathMove(
                move_type=MoveType.ARC_CW,
                start_point=exit_point,
                end_point=arc_end,
                center=exit_point,
                radius=self.lead_out_length,
                is_cutting=True
            ))
        
        else:  # "line"
            # Lead-out linear
            line_end = Point(
                exit_point.x + dx * self.lead_out_length,
                exit_point.y + dy * self.lead_out_length
            )
            
            moves.append(ToolpathMove(
                move_type=MoveType.LINEAR,
                start_point=exit_point,
                end_point=line_end,
                is_cutting=True
            ))
        
        return moves
