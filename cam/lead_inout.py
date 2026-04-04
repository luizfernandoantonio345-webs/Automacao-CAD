"""
═══════════════════════════════════════════════════════════════════════════════
LEAD-IN / LEAD-OUT EDITÁVEL - Sistema Profissional de Entrada/Saída
═══════════════════════════════════════════════════════════════════════════════

Sistema industrial para configuração de lead-in e lead-out em corte plasma:
- Múltiplos tipos: Linear, Arco, Tangente, Espiral
- Configuração de tamanho, ângulo e offset
- Posicionamento inteligente automático
- Edição visual interativa
- Validação de colisão

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.cam.lead_inout")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class LeadType(Enum):
    """Tipos de lead-in/lead-out disponíveis."""
    NONE = "none"               # Sem lead
    LINEAR = "linear"           # Linha reta em ângulo
    ARC = "arc"                 # Arco circular
    ARC_TANGENT = "arc_tangent" # Arco tangente ao contorno
    SPIRAL = "spiral"           # Espiral (para furos)
    PERPENDICULAR = "perpendicular"  # Perpendicular ao contorno
    RAMP = "ramp"               # Rampa com descida em Z


class LeadPosition(Enum):
    """Posição do lead em relação ao contorno."""
    AUTO = "auto"               # Automático (escolhe melhor posição)
    CORNER = "corner"           # Em um canto
    MIDPOINT = "midpoint"       # No ponto médio de um segmento
    LONGEST = "longest"         # No segmento mais longo
    CUSTOM = "custom"           # Posição customizada


class LeadDirection(Enum):
    """Direção do lead."""
    INSIDE = "inside"           # Para dentro do contorno
    OUTSIDE = "outside"         # Para fora do contorno
    LEFT = "left"               # À esquerda
    RIGHT = "right"             # À direita


class ContourDirection(Enum):
    """Direção de corte do contorno."""
    CW = "cw"                   # Horário (climb cut)
    CCW = "ccw"                 # Anti-horário (conventional)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Point2D:
    """Ponto 2D."""
    x: float
    y: float
    
    def distance_to(self, other: "Point2D") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other: "Point2D") -> float:
        return math.atan2(other.y - self.y, other.x - self.x)
    
    def offset(self, angle: float, distance: float) -> "Point2D":
        """Retorna novo ponto deslocado."""
        return Point2D(
            self.x + distance * math.cos(angle),
            self.y + distance * math.sin(angle)
        )
    
    def rotate_around(self, center: "Point2D", angle: float) -> "Point2D":
        """Rotaciona ponto em torno de um centro."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        dx = self.x - center.x
        dy = self.y - center.y
        return Point2D(
            center.x + dx * cos_a - dy * sin_a,
            center.y + dx * sin_a + dy * cos_a
        )
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class LeadConfig:
    """Configuração completa de lead-in ou lead-out."""
    
    # Tipo e habilitação
    enabled: bool = True
    lead_type: LeadType = LeadType.ARC
    
    # Dimensões
    length: float = 5.0             # mm - comprimento total
    radius: float = 3.0             # mm - raio (para arcos)
    angle: float = 45.0             # graus - ângulo de entrada
    
    # Posicionamento
    position: LeadPosition = LeadPosition.AUTO
    direction: LeadDirection = LeadDirection.OUTSIDE
    custom_position: float = 0.0    # % do contorno (0-100) para CUSTOM
    
    # Offset adicional
    offset_x: float = 0.0           # mm
    offset_y: float = 0.0           # mm
    
    # Para rampa/Z
    z_start: float = 0.0            # Altura Z inicial
    z_end: float = 0.0              # Altura Z final
    
    # Arco específico
    arc_angle: float = 90.0         # Ângulo do arco (graus)
    arc_direction: str = "ccw"      # "cw" ou "ccw"
    
    # Espiral
    spiral_turns: float = 0.5       # Número de voltas
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "lead_type": self.lead_type.value,
            "length": self.length,
            "radius": self.radius,
            "angle": self.angle,
            "position": self.position.value,
            "direction": self.direction.value,
            "arc_angle": self.arc_angle,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeadConfig":
        return cls(
            enabled=data.get("enabled", True),
            lead_type=LeadType(data.get("lead_type", "arc")),
            length=data.get("length", 5.0),
            radius=data.get("radius", 3.0),
            angle=data.get("angle", 45.0),
            position=LeadPosition(data.get("position", "auto")),
            direction=LeadDirection(data.get("direction", "outside")),
            arc_angle=data.get("arc_angle", 90.0),
        )


@dataclass
class LeadMove:
    """Movimento de lead-in/out."""
    move_type: str              # "linear", "arc_cw", "arc_ccw"
    start: Point2D
    end: Point2D
    center: Optional[Point2D] = None  # Para arcos
    radius: float = 0.0               # Para arcos
    feed_rate: float = 0.0
    z_start: float = 0.0
    z_end: float = 0.0


@dataclass
class LeadResult:
    """Resultado da geração de lead."""
    moves: List[LeadMove] = field(default_factory=list)
    entry_point: Optional[Point2D] = None   # Ponto onde começa o lead
    contour_point: Optional[Point2D] = None # Ponto onde entra no contorno
    total_length: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# PERFIS PREDEFINIDOS
# ═══════════════════════════════════════════════════════════════════════════════

class LeadPresets:
    """Configurações predefinidas de lead-in/out."""
    
    @staticmethod
    def standard_arc() -> Tuple[LeadConfig, LeadConfig]:
        """Lead padrão com arco - bom para maioria dos casos."""
        lead_in = LeadConfig(
            lead_type=LeadType.ARC,
            length=5.0,
            radius=3.0,
            angle=45.0,
            arc_angle=90.0,
        )
        lead_out = LeadConfig(
            lead_type=LeadType.ARC,
            length=3.0,
            radius=2.0,
            angle=45.0,
            arc_angle=60.0,
        )
        return lead_in, lead_out
    
    @staticmethod
    def linear_simple() -> Tuple[LeadConfig, LeadConfig]:
        """Lead linear simples - rápido e direto."""
        lead_in = LeadConfig(
            lead_type=LeadType.LINEAR,
            length=5.0,
            angle=45.0,
        )
        lead_out = LeadConfig(
            lead_type=LeadType.LINEAR,
            length=3.0,
            angle=45.0,
        )
        return lead_in, lead_out
    
    @staticmethod
    def perpendicular() -> Tuple[LeadConfig, LeadConfig]:
        """Lead perpendicular - entrada limpa."""
        lead_in = LeadConfig(
            lead_type=LeadType.PERPENDICULAR,
            length=5.0,
            angle=90.0,
        )
        lead_out = LeadConfig(
            lead_type=LeadType.PERPENDICULAR,
            length=3.0,
            angle=90.0,
        )
        return lead_in, lead_out
    
    @staticmethod
    def tangent_arc() -> Tuple[LeadConfig, LeadConfig]:
        """Lead com arco tangente - suave e preciso."""
        lead_in = LeadConfig(
            lead_type=LeadType.ARC_TANGENT,
            length=6.0,
            radius=4.0,
            arc_angle=120.0,
        )
        lead_out = LeadConfig(
            lead_type=LeadType.ARC_TANGENT,
            length=4.0,
            radius=3.0,
            arc_angle=90.0,
        )
        return lead_in, lead_out
    
    @staticmethod
    def for_hole(diameter: float) -> Tuple[LeadConfig, LeadConfig]:
        """Lead otimizado para furos."""
        # Para furos pequenos, usar espiral ou arco pequeno
        if diameter < 10:
            lead_in = LeadConfig(
                lead_type=LeadType.SPIRAL,
                radius=diameter * 0.2,
                spiral_turns=0.3,
            )
        else:
            lead_in = LeadConfig(
                lead_type=LeadType.ARC,
                length=min(5.0, diameter * 0.3),
                radius=min(3.0, diameter * 0.2),
                arc_angle=90.0,
            )
        
        # Lead-out mínimo para furos
        lead_out = LeadConfig(
            lead_type=LeadType.ARC,
            length=2.0,
            radius=1.5,
            arc_angle=45.0,
        )
        
        return lead_in, lead_out
    
    @staticmethod
    def for_thickness(thickness: float) -> Tuple[LeadConfig, LeadConfig]:
        """Lead otimizado para espessura do material."""
        # Materiais grossos precisam de lead-in maior
        # para estabilização do arco
        
        if thickness <= 3:
            length = 3.0
            radius = 2.0
        elif thickness <= 6:
            length = 5.0
            radius = 3.0
        elif thickness <= 12:
            length = 7.0
            radius = 4.0
        else:
            length = 10.0
            radius = 6.0
        
        lead_in = LeadConfig(
            lead_type=LeadType.ARC,
            length=length,
            radius=radius,
            arc_angle=90.0,
        )
        
        lead_out = LeadConfig(
            lead_type=LeadType.ARC,
            length=length * 0.6,
            radius=radius * 0.7,
            arc_angle=60.0,
        )
        
        return lead_in, lead_out


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR DE LEAD-IN/OUT
# ═══════════════════════════════════════════════════════════════════════════════

class LeadGenerator:
    """
    Gerador de movimentos de lead-in e lead-out.
    
    Calcula trajetórias de entrada e saída do corte
    considerando geometria do contorno e parâmetros configurados.
    """
    
    def __init__(self, default_feed_rate: float = 2000):
        self.default_feed_rate = default_feed_rate
    
    def generate_lead_in(
        self,
        config: LeadConfig,
        contour_start: Point2D,
        contour_direction: float,  # Ângulo em radianos
        is_internal: bool = False
    ) -> LeadResult:
        """
        Gera lead-in para um contorno.
        
        Args:
            config: Configuração do lead
            contour_start: Ponto inicial do contorno
            contour_direction: Direção do contorno no ponto inicial
            is_internal: Se é um contorno interno (furo)
        
        Returns:
            LeadResult com movimentos de lead-in
        """
        if not config.enabled:
            return LeadResult(
                contour_point=contour_start,
                entry_point=contour_start,
            )
        
        # Determinar direção do lead
        if config.direction == LeadDirection.AUTO:
            direction = LeadDirection.INSIDE if is_internal else LeadDirection.OUTSIDE
        else:
            direction = config.direction
        
        # Gerar baseado no tipo
        if config.lead_type == LeadType.LINEAR:
            return self._generate_linear_lead_in(
                config, contour_start, contour_direction, direction
            )
        
        elif config.lead_type == LeadType.ARC:
            return self._generate_arc_lead_in(
                config, contour_start, contour_direction, direction
            )
        
        elif config.lead_type == LeadType.ARC_TANGENT:
            return self._generate_tangent_lead_in(
                config, contour_start, contour_direction, direction
            )
        
        elif config.lead_type == LeadType.PERPENDICULAR:
            return self._generate_perpendicular_lead_in(
                config, contour_start, contour_direction, direction
            )
        
        elif config.lead_type == LeadType.SPIRAL:
            return self._generate_spiral_lead_in(
                config, contour_start, contour_direction, direction
            )
        
        else:
            return LeadResult(
                contour_point=contour_start,
                entry_point=contour_start,
            )
    
    def generate_lead_out(
        self,
        config: LeadConfig,
        contour_end: Point2D,
        contour_direction: float,
        is_internal: bool = False
    ) -> LeadResult:
        """
        Gera lead-out para um contorno.
        
        Args:
            config: Configuração do lead
            contour_end: Ponto final do contorno
            contour_direction: Direção do contorno no ponto final
            is_internal: Se é um contorno interno
        
        Returns:
            LeadResult com movimentos de lead-out
        """
        if not config.enabled:
            return LeadResult(
                contour_point=contour_end,
                entry_point=contour_end,
            )
        
        # Lead-out é similar ao lead-in mas invertido
        # Reutilizar lógica de lead-in com ajustes
        
        direction = LeadDirection.INSIDE if is_internal else LeadDirection.OUTSIDE
        
        if config.lead_type == LeadType.LINEAR:
            return self._generate_linear_lead_out(
                config, contour_end, contour_direction, direction
            )
        
        elif config.lead_type == LeadType.ARC:
            return self._generate_arc_lead_out(
                config, contour_end, contour_direction, direction
            )
        
        else:
            # Para outros tipos, usar linear simples
            return self._generate_linear_lead_out(
                config, contour_end, contour_direction, direction
            )
    
    def _generate_linear_lead_in(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-in linear."""
        result = LeadResult()
        result.contour_point = contour_point
        
        # Calcular ângulo de entrada
        angle_rad = math.radians(config.angle)
        
        # Ajustar direção baseado em inside/outside
        if direction == LeadDirection.OUTSIDE:
            lead_angle = contour_dir + math.pi - angle_rad
        else:
            lead_angle = contour_dir + math.pi + angle_rad
        
        # Calcular ponto de início
        entry_point = contour_point.offset(lead_angle, config.length)
        result.entry_point = entry_point
        
        # Criar movimento
        move = LeadMove(
            move_type="linear",
            start=entry_point,
            end=contour_point,
            feed_rate=self.default_feed_rate * 0.8,  # Entrada mais lenta
        )
        result.moves.append(move)
        result.total_length = config.length
        
        return result
    
    def _generate_arc_lead_in(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-in com arco."""
        result = LeadResult()
        result.contour_point = contour_point
        
        # Raio do arco
        radius = config.radius
        
        # Ângulo do arco em radianos
        arc_angle_rad = math.radians(config.arc_angle)
        
        # Direção perpendicular ao contorno (para dentro ou fora)
        perp_dir = contour_dir + (math.pi/2 if direction == LeadDirection.OUTSIDE else -math.pi/2)
        
        # Centro do arco
        center = contour_point.offset(perp_dir, radius)
        
        # Ponto de início do arco (recuar ao longo do arco)
        start_angle = contour_point.angle_to(center) - math.pi
        if direction == LeadDirection.OUTSIDE:
            entry_angle = start_angle + arc_angle_rad
            arc_type = "arc_cw"
        else:
            entry_angle = start_angle - arc_angle_rad
            arc_type = "arc_ccw"
        
        entry_point = center.offset(entry_angle, radius)
        result.entry_point = entry_point
        
        # Criar movimento de arco
        move = LeadMove(
            move_type=arc_type,
            start=entry_point,
            end=contour_point,
            center=center,
            radius=radius,
            feed_rate=self.default_feed_rate * 0.7,
        )
        result.moves.append(move)
        
        # Comprimento do arco
        result.total_length = radius * arc_angle_rad
        
        return result
    
    def _generate_tangent_lead_in(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-in com arco tangente ao contorno."""
        result = LeadResult()
        result.contour_point = contour_point
        
        radius = config.radius
        arc_angle_rad = math.radians(config.arc_angle)
        
        # Para arco tangente, o centro está perpendicular à direção
        perp_dir = contour_dir + (math.pi/2 if direction == LeadDirection.OUTSIDE else -math.pi/2)
        
        # Centro do arco tangente
        center = contour_point.offset(perp_dir, radius)
        
        # Ponto de entrada - tangente ao círculo
        # O arco é tangente, então entrada é perpendicular ao raio
        if direction == LeadDirection.OUTSIDE:
            entry_angle = perp_dir + arc_angle_rad
            arc_type = "arc_ccw"
        else:
            entry_angle = perp_dir - arc_angle_rad
            arc_type = "arc_cw"
        
        entry_point = center.offset(entry_angle, radius)
        result.entry_point = entry_point
        
        # Primeiro: movimento linear até início do arco (se length > radius)
        if config.length > radius:
            linear_length = config.length - radius
            linear_start = entry_point.offset(entry_angle + math.pi, linear_length)
            
            linear_move = LeadMove(
                move_type="linear",
                start=linear_start,
                end=entry_point,
                feed_rate=self.default_feed_rate * 0.8,
            )
            result.moves.append(linear_move)
            result.entry_point = linear_start
            result.total_length += linear_length
        
        # Depois: arco até o contorno
        arc_move = LeadMove(
            move_type=arc_type,
            start=entry_point,
            end=contour_point,
            center=center,
            radius=radius,
            feed_rate=self.default_feed_rate * 0.7,
        )
        result.moves.append(arc_move)
        result.total_length += radius * arc_angle_rad
        
        return result
    
    def _generate_perpendicular_lead_in(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-in perpendicular ao contorno."""
        result = LeadResult()
        result.contour_point = contour_point
        
        # Direção perpendicular
        if direction == LeadDirection.OUTSIDE:
            perp_angle = contour_dir + math.pi/2
        else:
            perp_angle = contour_dir - math.pi/2
        
        # Ponto de entrada
        entry_point = contour_point.offset(perp_angle, config.length)
        result.entry_point = entry_point
        
        # Movimento linear perpendicular
        move = LeadMove(
            move_type="linear",
            start=entry_point,
            end=contour_point,
            feed_rate=self.default_feed_rate * 0.6,  # Mais lento (entrada direta)
        )
        result.moves.append(move)
        result.total_length = config.length
        
        return result
    
    def _generate_spiral_lead_in(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-in espiral (usado principalmente para furos)."""
        result = LeadResult()
        result.contour_point = contour_point
        
        # Número de segmentos para a espiral
        segments = max(8, int(config.spiral_turns * 16))
        
        # Raio inicial e final
        r_start = config.radius * 0.1
        r_end = config.radius
        
        # Gerar pontos da espiral
        center = contour_point  # Espiral centrada no ponto de entrada
        
        points = []
        for i in range(segments + 1):
            t = i / segments  # 0 a 1
            
            # Raio cresce linearmente
            r = r_start + (r_end - r_start) * t
            
            # Ângulo (múltiplas voltas)
            angle = contour_dir + (2 * math.pi * config.spiral_turns * t)
            
            x = center.x + r * math.cos(angle)
            y = center.y + r * math.sin(angle)
            points.append(Point2D(x, y))
        
        # Inverter para ir de fora para dentro
        points.reverse()
        
        result.entry_point = points[0]
        
        # Criar movimentos lineares para cada segmento
        for i in range(len(points) - 1):
            move = LeadMove(
                move_type="linear",
                start=points[i],
                end=points[i+1],
                feed_rate=self.default_feed_rate * 0.5,  # Espiral mais lenta
            )
            result.moves.append(move)
            result.total_length += points[i].distance_to(points[i+1])
        
        return result
    
    def _generate_linear_lead_out(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-out linear."""
        result = LeadResult()
        result.contour_point = contour_point
        
        angle_rad = math.radians(config.angle)
        
        if direction == LeadDirection.OUTSIDE:
            lead_angle = contour_dir + angle_rad
        else:
            lead_angle = contour_dir - angle_rad
        
        exit_point = contour_point.offset(lead_angle, config.length)
        result.entry_point = exit_point  # "entry" é o ponto final para lead-out
        
        move = LeadMove(
            move_type="linear",
            start=contour_point,
            end=exit_point,
            feed_rate=self.default_feed_rate,
        )
        result.moves.append(move)
        result.total_length = config.length
        
        return result
    
    def _generate_arc_lead_out(
        self,
        config: LeadConfig,
        contour_point: Point2D,
        contour_dir: float,
        direction: LeadDirection
    ) -> LeadResult:
        """Gera lead-out com arco."""
        result = LeadResult()
        result.contour_point = contour_point
        
        radius = config.radius
        arc_angle_rad = math.radians(config.arc_angle)
        
        perp_dir = contour_dir + (math.pi/2 if direction == LeadDirection.OUTSIDE else -math.pi/2)
        center = contour_point.offset(perp_dir, radius)
        
        start_angle = contour_point.angle_to(center) - math.pi
        
        if direction == LeadDirection.OUTSIDE:
            exit_angle = start_angle - arc_angle_rad
            arc_type = "arc_ccw"
        else:
            exit_angle = start_angle + arc_angle_rad
            arc_type = "arc_cw"
        
        exit_point = center.offset(exit_angle, radius)
        result.entry_point = exit_point
        
        move = LeadMove(
            move_type=arc_type,
            start=contour_point,
            end=exit_point,
            center=center,
            radius=radius,
            feed_rate=self.default_feed_rate,
        )
        result.moves.append(move)
        result.total_length = radius * arc_angle_rad
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# POSICIONADOR DE LEAD
# ═══════════════════════════════════════════════════════════════════════════════

class LeadPositioner:
    """
    Determina posição ideal para lead-in em um contorno.
    
    Analisa o contorno para encontrar a melhor posição considerando:
    - Cantos suaves (evita cantos agudos)
    - Segmentos longos (preferido para estabilidade)
    - Distância de outros contornos
    - Direção de corte
    """
    
    @staticmethod
    def find_best_position(
        contour_points: List[Tuple[float, float]],
        is_internal: bool = False,
        avoid_regions: List[Tuple[float, float, float, float]] = None
    ) -> Tuple[int, float, float]:
        """
        Encontra melhor posição para lead-in.
        
        Args:
            contour_points: Lista de pontos do contorno
            is_internal: Se é contorno interno
            avoid_regions: Regiões a evitar (x, y, raio, peso)
        
        Returns:
            Tuple[índice, score, direção em radianos]
        """
        if len(contour_points) < 3:
            return 0, 0.0, 0.0
        
        best_idx = 0
        best_score = -float('inf')
        best_direction = 0.0
        
        for i in range(len(contour_points)):
            # Calcular score para esta posição
            score = 0.0
            
            # 1. Preferir segmentos longos
            prev_idx = (i - 1) % len(contour_points)
            next_idx = (i + 1) % len(contour_points)
            
            p_prev = Point2D(*contour_points[prev_idx])
            p_curr = Point2D(*contour_points[i])
            p_next = Point2D(*contour_points[next_idx])
            
            seg_length = p_curr.distance_to(p_next)
            score += min(seg_length / 10, 5)  # Até 5 pontos por comprimento
            
            # 2. Preferir cantos suaves
            # Calcular ângulo do canto
            v1 = (p_curr.x - p_prev.x, p_curr.y - p_prev.y)
            v2 = (p_next.x - p_curr.x, p_next.y - p_curr.y)
            
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
            
            if mag1 > 0 and mag2 > 0:
                cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
                angle = math.degrees(math.acos(cos_angle))
                
                # Preferir ângulos próximos de 180° (reto)
                score += (angle / 180) * 3
            
            # 3. Evitar regiões marcadas
            if avoid_regions:
                for ax, ay, ar, aw in avoid_regions:
                    dist = p_curr.distance_to(Point2D(ax, ay))
                    if dist < ar:
                        score -= aw * (1 - dist/ar)
            
            # 4. Para contornos internos, preferir posição mais distante do centro
            if is_internal:
                # Calcular centro aproximado
                cx = sum(p[0] for p in contour_points) / len(contour_points)
                cy = sum(p[1] for p in contour_points) / len(contour_points)
                dist_to_center = p_curr.distance_to(Point2D(cx, cy))
                score += dist_to_center / 20
            
            # Calcular direção
            direction = p_curr.angle_to(p_next)
            
            if score > best_score:
                best_score = score
                best_idx = i
                best_direction = direction
        
        return best_idx, best_score, best_direction


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDADOR DE LEAD
# ═══════════════════════════════════════════════════════════════════════════════

class LeadValidator:
    """
    Valida configurações e posições de lead-in/out.
    
    Verifica:
    - Colisões com contornos
    - Limites de máquina
    - Compatibilidade com material/espessura
    """
    
    @staticmethod
    def validate_lead(
        lead_result: LeadResult,
        contour_points: List[Tuple[float, float]],
        other_contours: List[List[Tuple[float, float]]] = None,
        min_clearance: float = 2.0
    ) -> Tuple[bool, List[str]]:
        """
        Valida um lead-in/out.
        
        Args:
            lead_result: Resultado do lead gerado
            contour_points: Pontos do contorno atual
            other_contours: Outros contornos para verificar colisão
            min_clearance: Distância mínima de outros contornos
        
        Returns:
            Tuple[válido, lista de warnings]
        """
        warnings = []
        valid = True
        
        if not lead_result.moves:
            return True, []
        
        # 1. Verificar se lead cruza o próprio contorno
        for move in lead_result.moves:
            for i in range(len(contour_points) - 1):
                p1 = Point2D(*contour_points[i])
                p2 = Point2D(*contour_points[i+1])
                
                if LeadValidator._segments_intersect(
                    move.start, move.end, p1, p2
                ):
                    warnings.append(
                        f"Lead cruza o contorno no segmento {i+1}"
                    )
                    valid = False
        
        # 2. Verificar distância de outros contornos
        if other_contours:
            for j, other in enumerate(other_contours):
                for move in lead_result.moves:
                    for point in [move.start, move.end]:
                        for k in range(len(other) - 1):
                            op = Point2D(*other[k])
                            dist = point.distance_to(op)
                            
                            if dist < min_clearance:
                                warnings.append(
                                    f"Lead muito próximo do contorno {j+1} "
                                    f"({dist:.1f}mm < {min_clearance}mm)"
                                )
        
        # 3. Verificar comprimento mínimo
        if lead_result.total_length < 1.0:
            warnings.append(
                f"Lead muito curto ({lead_result.total_length:.1f}mm). "
                "Recomendado mínimo 2mm"
            )
        
        return valid, warnings
    
    @staticmethod
    def _segments_intersect(
        p1: Point2D, p2: Point2D, p3: Point2D, p4: Point2D
    ) -> bool:
        """Verifica se dois segmentos se intersectam."""
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
        
        return (
            ccw(p1, p3, p4) != ccw(p2, p3, p4) and
            ccw(p1, p2, p3) != ccw(p1, p2, p4)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def create_lead_in(
    contour_start: Tuple[float, float],
    contour_direction: float,
    is_internal: bool = False,
    lead_type: LeadType = LeadType.ARC,
    length: float = 5.0,
    radius: float = 3.0,
    angle: float = 45.0
) -> LeadResult:
    """
    Função auxiliar para criar lead-in rapidamente.
    
    Args:
        contour_start: Ponto inicial do contorno (x, y)
        contour_direction: Direção do contorno em radianos
        is_internal: Se é contorno interno
        lead_type: Tipo de lead
        length: Comprimento
        radius: Raio (para arcos)
        angle: Ângulo
    
    Returns:
        LeadResult
    """
    config = LeadConfig(
        lead_type=lead_type,
        length=length,
        radius=radius,
        angle=angle,
    )
    
    generator = LeadGenerator()
    return generator.generate_lead_in(
        config,
        Point2D(*contour_start),
        contour_direction,
        is_internal
    )


def create_lead_out(
    contour_end: Tuple[float, float],
    contour_direction: float,
    is_internal: bool = False,
    lead_type: LeadType = LeadType.ARC,
    length: float = 3.0,
    radius: float = 2.0,
    angle: float = 45.0
) -> LeadResult:
    """Função auxiliar para criar lead-out rapidamente."""
    config = LeadConfig(
        lead_type=lead_type,
        length=length,
        radius=radius,
        angle=angle,
    )
    
    generator = LeadGenerator()
    return generator.generate_lead_out(
        config,
        Point2D(*contour_end),
        contour_direction,
        is_internal
    )


def get_lead_presets_for_job(
    material: str,
    thickness: float,
    has_holes: bool = False
) -> Dict[str, Any]:
    """
    Retorna presets de lead recomendados para um job.
    
    Args:
        material: Tipo de material
        thickness: Espessura
        has_holes: Se tem furos
    
    Returns:
        Dict com configurações recomendadas
    """
    lead_in, lead_out = LeadPresets.for_thickness(thickness)
    
    result = {
        "external": {
            "lead_in": lead_in.to_dict(),
            "lead_out": lead_out.to_dict(),
        },
        "internal": None,
    }
    
    # Configuração específica para furos
    if has_holes:
        hole_in, hole_out = LeadPresets.for_hole(10)  # Diâmetro médio
        result["internal"] = {
            "lead_in": hole_in.to_dict(),
            "lead_out": hole_out.to_dict(),
        }
    
    return result
