"""
═══════════════════════════════════════════════════════════════════════════════
CONTROLE DINÂMICO DE VELOCIDADE - Sistema Adaptativo de Feed Rate
═══════════════════════════════════════════════════════════════════════════════

Sistema profissional de controle de velocidade adaptativo para corte plasma:
- Redução automática de velocidade em curvas
- Ajuste de feed rate baseado em ângulo da trajetória
- Corner slowdown (desaceleração em cantos)
- Arc speed compensation (compensação em arcos)
- Lookahead planning (planejamento antecipado)

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.cam.speed_control")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SpeedMode(Enum):
    """Modos de controle de velocidade."""
    CONSTANT = "constant"           # Velocidade constante
    ADAPTIVE = "adaptive"           # Adaptativo automático
    PRECISION = "precision"         # Máxima precisão (mais lento)
    PRODUCTION = "production"       # Máxima produção (mais rápido)
    CUSTOM = "custom"               # Configuração customizada


class CornerType(Enum):
    """Tipos de canto detectados."""
    SHARP = "sharp"                 # Canto afiado (< 45°)
    MEDIUM = "medium"               # Canto médio (45° - 90°)
    GENTLE = "gentle"               # Canto suave (> 90°)
    SMOOTH = "smooth"               # Curva suave (sem ângulo definido)


class PathSegmentType(Enum):
    """Tipos de segmento de trajetória."""
    LINEAR = "linear"
    ARC_SMALL = "arc_small"         # Arco pequeno (raio < 5mm)
    ARC_MEDIUM = "arc_medium"       # Arco médio (5-25mm)
    ARC_LARGE = "arc_large"         # Arco grande (> 25mm)
    CORNER = "corner"               # Canto/vértice


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
        """Retorna ângulo em radianos para outro ponto."""
        return math.atan2(other.y - self.y, other.x - self.x)


@dataclass
class SpeedConfig:
    """Configuração de controle de velocidade."""
    
    # Velocidade base
    base_speed: float = 2000.0          # mm/min
    min_speed: float = 200.0            # mm/min - velocidade mínima
    max_speed: float = 15000.0          # mm/min - velocidade máxima
    
    # Modo de operação
    mode: SpeedMode = SpeedMode.ADAPTIVE
    
    # Controle de cantos
    corner_slowdown_enabled: bool = True
    min_corner_angle: float = 30.0      # graus - abaixo disso, desacelera
    max_corner_slowdown: float = 0.3    # 30% da velocidade base
    corner_decel_distance: float = 3.0  # mm - distância para desaceleração
    corner_accel_distance: float = 5.0  # mm - distância para aceleração
    
    # Controle de arcos
    arc_speed_enabled: bool = True
    min_arc_radius: float = 2.0         # mm - raio mínimo para corte
    arc_speed_factor_small: float = 0.4  # Fator para arcos pequenos
    arc_speed_factor_medium: float = 0.7 # Fator para arcos médios
    arc_speed_factor_large: float = 0.9  # Fator para arcos grandes
    
    # Lookahead
    lookahead_enabled: bool = True
    lookahead_segments: int = 5          # Número de segmentos à frente
    
    # Limites de aceleração
    max_acceleration: float = 5000.0    # mm/s²
    max_jerk: float = 50.0              # mm/s³
    
    # Compensação térmica
    thermal_slowdown_enabled: bool = False
    max_heat_accumulation: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_speed": self.base_speed,
            "min_speed": self.min_speed,
            "max_speed": self.max_speed,
            "mode": self.mode.value,
            "corner_slowdown_enabled": self.corner_slowdown_enabled,
            "arc_speed_enabled": self.arc_speed_enabled,
            "lookahead_enabled": self.lookahead_enabled,
        }


@dataclass
class PathSegment:
    """Segmento de trajetória com informações de velocidade."""
    
    # Geometria
    start: Point2D
    end: Point2D
    segment_type: PathSegmentType = PathSegmentType.LINEAR
    
    # Para arcos
    center: Optional[Point2D] = None
    radius: float = 0.0
    is_clockwise: bool = False
    
    # Velocidades calculadas
    entry_speed: float = 0.0            # Velocidade de entrada
    exit_speed: float = 0.0             # Velocidade de saída
    max_speed: float = 0.0              # Velocidade máxima no segmento
    recommended_speed: float = 0.0       # Velocidade recomendada
    
    # Ângulos
    entry_angle: float = 0.0            # Ângulo de entrada (radianos)
    exit_angle: float = 0.0             # Ângulo de saída (radianos)
    corner_angle: float = 180.0         # Ângulo do canto (graus)
    
    # Metadados
    length: float = 0.0
    estimated_time: float = 0.0         # segundos
    
    def calculate_length(self) -> float:
        """Calcula comprimento do segmento."""
        if self.segment_type == PathSegmentType.LINEAR:
            self.length = self.start.distance_to(self.end)
        else:
            # Arco - calcular comprimento do arco
            if self.radius > 0:
                chord = self.start.distance_to(self.end)
                # Aproximação usando fórmula do arco
                if chord < 2 * self.radius:
                    angle = 2 * math.asin(chord / (2 * self.radius))
                    self.length = angle * self.radius
                else:
                    self.length = chord
        return self.length


@dataclass 
class SpeedProfile:
    """Perfil de velocidade para uma trajetória completa."""
    
    segments: List[PathSegment] = field(default_factory=list)
    
    # Estatísticas
    total_length: float = 0.0
    total_time: float = 0.0
    average_speed: float = 0.0
    min_speed_used: float = 0.0
    max_speed_used: float = 0.0
    
    # Análise
    corner_count: int = 0
    arc_count: int = 0
    slowdown_count: int = 0
    
    def calculate_statistics(self):
        """Calcula estatísticas do perfil."""
        if not self.segments:
            return
        
        self.total_length = sum(s.length for s in self.segments)
        self.total_time = sum(s.estimated_time for s in self.segments)
        
        speeds = [s.recommended_speed for s in self.segments if s.recommended_speed > 0]
        if speeds:
            self.average_speed = sum(speeds) / len(speeds)
            self.min_speed_used = min(speeds)
            self.max_speed_used = max(speeds)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALISADOR DE TRAJETÓRIA
# ═══════════════════════════════════════════════════════════════════════════════

class PathAnalyzer:
    """Analisa trajetórias para cálculo de velocidade."""
    
    @staticmethod
    def calculate_angle_between_vectors(
        v1_start: Point2D, v1_end: Point2D,
        v2_start: Point2D, v2_end: Point2D
    ) -> float:
        """
        Calcula ângulo entre dois vetores (em graus).
        
        Returns:
            Ângulo entre 0 e 180 graus
        """
        # Vetores
        dx1 = v1_end.x - v1_start.x
        dy1 = v1_end.y - v1_start.y
        dx2 = v2_end.x - v2_start.x
        dy2 = v2_end.y - v2_start.y
        
        # Produto escalar
        dot = dx1 * dx2 + dy1 * dy2
        
        # Magnitudes
        mag1 = math.sqrt(dx1*dx1 + dy1*dy1)
        mag2 = math.sqrt(dx2*dx2 + dy2*dy2)
        
        if mag1 == 0 or mag2 == 0:
            return 180.0
        
        # Cosseno do ângulo
        cos_angle = dot / (mag1 * mag2)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp para evitar erros de arredondamento
        
        # Ângulo em graus
        angle = math.degrees(math.acos(cos_angle))
        
        return angle
    
    @staticmethod
    def classify_corner(angle: float) -> CornerType:
        """Classifica tipo de canto pelo ângulo."""
        if angle < 45:
            return CornerType.SHARP
        elif angle < 90:
            return CornerType.MEDIUM
        elif angle < 150:
            return CornerType.GENTLE
        else:
            return CornerType.SMOOTH
    
    @staticmethod
    def classify_arc_segment(radius: float) -> PathSegmentType:
        """Classifica tipo de arco pelo raio."""
        if radius < 5:
            return PathSegmentType.ARC_SMALL
        elif radius < 25:
            return PathSegmentType.ARC_MEDIUM
        else:
            return PathSegmentType.ARC_LARGE
    
    @staticmethod
    def analyze_path(
        points: List[Tuple[float, float]],
        arcs: List[Dict] = None
    ) -> List[PathSegment]:
        """
        Analisa uma trajetória e retorna segmentos com informações geométricas.
        
        Args:
            points: Lista de pontos (x, y)
            arcs: Lista de arcos com {start_idx, end_idx, center, radius, cw}
        
        Returns:
            Lista de PathSegments
        """
        segments = []
        arc_dict = {}
        
        # Indexar arcos por índice de início
        if arcs:
            for arc in arcs:
                arc_dict[arc.get("start_idx", -1)] = arc
        
        # Criar segmentos
        for i in range(len(points) - 1):
            start = Point2D(points[i][0], points[i][1])
            end = Point2D(points[i+1][0], points[i+1][1])
            
            # Verificar se é um arco
            if i in arc_dict:
                arc = arc_dict[i]
                center = Point2D(arc["center"][0], arc["center"][1])
                segment = PathSegment(
                    start=start,
                    end=end,
                    segment_type=PathAnalyzer.classify_arc_segment(arc["radius"]),
                    center=center,
                    radius=arc["radius"],
                    is_clockwise=arc.get("cw", False),
                )
            else:
                segment = PathSegment(
                    start=start,
                    end=end,
                    segment_type=PathSegmentType.LINEAR,
                )
            
            segment.calculate_length()
            
            # Calcular ângulos
            segment.entry_angle = start.angle_to(end)
            segment.exit_angle = segment.entry_angle
            
            segments.append(segment)
        
        # Calcular ângulos de canto entre segmentos
        for i in range(len(segments) - 1):
            seg1 = segments[i]
            seg2 = segments[i + 1]
            
            angle = PathAnalyzer.calculate_angle_between_vectors(
                seg1.start, seg1.end,
                seg2.start, seg2.end
            )
            
            seg1.corner_angle = angle
            seg2.entry_angle = seg1.exit_angle
        
        return segments


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROLADOR DE VELOCIDADE
# ═══════════════════════════════════════════════════════════════════════════════

class SpeedController:
    """
    Controlador principal de velocidade adaptativa.
    
    Calcula velocidades ótimas para cada segmento considerando:
    - Geometria da trajetória
    - Ângulos de canto
    - Raios de arco
    - Limites de aceleração
    - Qualidade de corte desejada
    """
    
    def __init__(self, config: SpeedConfig = None):
        """
        Inicializa o controlador.
        
        Args:
            config: Configuração de velocidade
        """
        self.config = config or SpeedConfig()
    
    def calculate_corner_speed(self, corner_angle: float) -> float:
        """
        Calcula velocidade para um canto.
        
        Args:
            corner_angle: Ângulo do canto em graus (0-180)
        
        Returns:
            Fator de velocidade (0-1)
        """
        if not self.config.corner_slowdown_enabled:
            return 1.0
        
        if corner_angle >= 180:
            # Sem mudança de direção
            return 1.0
        
        if corner_angle <= self.config.min_corner_angle:
            # Canto muito afiado - velocidade mínima
            return self.config.max_corner_slowdown
        
        # Interpolação linear entre ângulo mínimo e 180°
        # Quanto maior o ângulo, maior a velocidade
        range_angle = 180 - self.config.min_corner_angle
        normalized = (corner_angle - self.config.min_corner_angle) / range_angle
        
        # Fator de velocidade: de max_corner_slowdown até 1.0
        factor = self.config.max_corner_slowdown + \
                 normalized * (1.0 - self.config.max_corner_slowdown)
        
        return factor
    
    def calculate_arc_speed(self, radius: float) -> float:
        """
        Calcula velocidade para um arco.
        
        Arcos menores requerem velocidades menores para
        manter a qualidade do corte.
        
        Args:
            radius: Raio do arco em mm
        
        Returns:
            Fator de velocidade (0-1)
        """
        if not self.config.arc_speed_enabled:
            return 1.0
        
        if radius < self.config.min_arc_radius:
            # Raio muito pequeno - pode não ser cortável
            logger.warning(f"Raio {radius}mm abaixo do mínimo {self.config.min_arc_radius}mm")
            return self.config.arc_speed_factor_small * 0.5
        
        # Classificar arco
        segment_type = PathAnalyzer.classify_arc_segment(radius)
        
        factors = {
            PathSegmentType.ARC_SMALL: self.config.arc_speed_factor_small,
            PathSegmentType.ARC_MEDIUM: self.config.arc_speed_factor_medium,
            PathSegmentType.ARC_LARGE: self.config.arc_speed_factor_large,
        }
        
        return factors.get(segment_type, 1.0)
    
    def calculate_segment_speed(
        self,
        segment: PathSegment,
        prev_segment: PathSegment = None,
        next_segment: PathSegment = None
    ) -> float:
        """
        Calcula velocidade recomendada para um segmento.
        
        Args:
            segment: Segmento atual
            prev_segment: Segmento anterior (para lookahead reverso)
            next_segment: Próximo segmento (para lookahead)
        
        Returns:
            Velocidade recomendada em mm/min
        """
        base = self.config.base_speed
        factor = 1.0
        
        # Fator de arco
        if segment.segment_type != PathSegmentType.LINEAR:
            factor *= self.calculate_arc_speed(segment.radius)
        
        # Fator de canto (entrada)
        if prev_segment:
            corner_factor = self.calculate_corner_speed(prev_segment.corner_angle)
            factor = min(factor, corner_factor)
        
        # Fator de canto (saída) - lookahead
        if next_segment and self.config.lookahead_enabled:
            corner_factor = self.calculate_corner_speed(segment.corner_angle)
            factor = min(factor, corner_factor)
        
        # Aplicar fator
        speed = base * factor
        
        # Limitar aos limites configurados
        speed = max(self.config.min_speed, min(speed, self.config.max_speed))
        
        return speed
    
    def process_path(
        self,
        segments: List[PathSegment]
    ) -> SpeedProfile:
        """
        Processa uma trajetória completa e calcula velocidades.
        
        Args:
            segments: Lista de segmentos da trajetória
        
        Returns:
            SpeedProfile com velocidades calculadas
        """
        profile = SpeedProfile()
        
        if not segments:
            return profile
        
        # Primeira passada: calcular velocidades base para cada segmento
        for i, segment in enumerate(segments):
            prev_seg = segments[i-1] if i > 0 else None
            next_seg = segments[i+1] if i < len(segments)-1 else None
            
            segment.recommended_speed = self.calculate_segment_speed(
                segment, prev_seg, next_seg
            )
            
            # Calcular tempo
            if segment.recommended_speed > 0:
                segment.estimated_time = (segment.length / segment.recommended_speed) * 60
        
        # Segunda passada: suavização com lookahead
        if self.config.lookahead_enabled:
            self._smooth_speeds(segments)
        
        # Terceira passada: verificar limites de aceleração
        self._check_acceleration_limits(segments)
        
        # Montar perfil
        profile.segments = segments
        profile.calculate_statistics()
        
        # Contar eventos
        for seg in segments:
            if seg.segment_type != PathSegmentType.LINEAR:
                profile.arc_count += 1
            if seg.corner_angle < 150:
                profile.corner_count += 1
            if seg.recommended_speed < self.config.base_speed * 0.9:
                profile.slowdown_count += 1
        
        return profile
    
    def _smooth_speeds(self, segments: List[PathSegment]):
        """
        Suaviza transições de velocidade usando lookahead.
        
        Evita mudanças bruscas considerando segmentos futuros.
        """
        n = len(segments)
        lookahead = min(self.config.lookahead_segments, n)
        
        # Forward pass - considerar velocidades futuras
        for i in range(n):
            end_idx = min(i + lookahead, n)
            
            # Encontrar menor velocidade nos próximos segmentos
            min_future = min(
                segments[j].recommended_speed 
                for j in range(i, end_idx)
            )
            
            # Se velocidade atual é maior que mínima futura,
            # começar a desacelerar gradualmente
            if segments[i].recommended_speed > min_future * 1.5:
                # Calcular velocidade de transição
                steps_to_min = end_idx - i
                if steps_to_min > 0:
                    speed_drop = (segments[i].recommended_speed - min_future) / steps_to_min
                    # Ajustar velocidade considerando desaceleração
                    new_speed = min_future + speed_drop * (end_idx - i - 1)
                    segments[i].recommended_speed = min(
                        segments[i].recommended_speed,
                        new_speed
                    )
        
        # Backward pass - garantir aceleração suave
        for i in range(n - 2, -1, -1):
            current = segments[i].recommended_speed
            next_speed = segments[i + 1].recommended_speed
            
            # Verificar se precisa ajustar para aceleração suave
            max_accel_delta = self.config.max_acceleration * 0.1  # Aproximação
            if next_speed - current > max_accel_delta:
                # Limitar velocidade para permitir aceleração
                segments[i].recommended_speed = min(
                    current,
                    next_speed - max_accel_delta
                )
    
    def _check_acceleration_limits(self, segments: List[PathSegment]):
        """
        Verifica e ajusta velocidades para respeitar limites de aceleração.
        """
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]
            
            # Calcular aceleração necessária
            v1 = current.recommended_speed / 60  # mm/s
            v2 = next_seg.recommended_speed / 60  # mm/s
            
            # Distância disponível para aceleração
            dist = current.length
            
            if dist > 0:
                # a = (v2² - v1²) / (2 * d)
                required_accel = abs(v2*v2 - v1*v1) / (2 * dist)
                
                if required_accel > self.config.max_acceleration:
                    # Ajustar velocidades para respeitar limite
                    if v2 > v1:
                        # Acelerando - limitar velocidade final
                        max_v2 = math.sqrt(
                            v1*v1 + 2 * self.config.max_acceleration * dist
                        )
                        next_seg.recommended_speed = min(
                            next_seg.recommended_speed,
                            max_v2 * 60
                        )
                    else:
                        # Desacelerando - pode precisar começar mais devagar
                        min_v1 = math.sqrt(
                            v2*v2 + 2 * self.config.max_acceleration * dist
                        )
                        if min_v1 * 60 < current.recommended_speed:
                            current.recommended_speed = min_v1 * 60
    
    def generate_speed_commands(
        self,
        profile: SpeedProfile,
        include_comments: bool = True
    ) -> List[str]:
        """
        Gera comandos de velocidade para G-code.
        
        Args:
            profile: Perfil de velocidade calculado
            include_comments: Incluir comentários explicativos
        
        Returns:
            Lista de strings de G-code
        """
        lines = []
        current_speed = 0
        
        for i, segment in enumerate(profile.segments):
            speed = int(segment.recommended_speed)
            
            # Só emitir F se velocidade mudou
            if speed != current_speed:
                if include_comments:
                    reason = self._get_speed_reason(segment)
                    lines.append(f"F{speed} ({reason})")
                else:
                    lines.append(f"F{speed}")
                current_speed = speed
        
        return lines
    
    def _get_speed_reason(self, segment: PathSegment) -> str:
        """Retorna razão para velocidade do segmento."""
        if segment.segment_type != PathSegmentType.LINEAR:
            return f"Arco R{segment.radius:.1f}"
        if segment.corner_angle < 90:
            return f"Canto {segment.corner_angle:.0f}°"
        if segment.corner_angle < 150:
            return f"Curva {segment.corner_angle:.0f}°"
        return "Reta"


# ═══════════════════════════════════════════════════════════════════════════════
# PERFIS PREDEFINIDOS
# ═══════════════════════════════════════════════════════════════════════════════

class SpeedProfiles:
    """Perfis de velocidade predefinidos."""
    
    @staticmethod
    def production(base_speed: float = 2500) -> SpeedConfig:
        """Perfil para máxima produtividade."""
        return SpeedConfig(
            base_speed=base_speed,
            min_speed=500,
            mode=SpeedMode.PRODUCTION,
            corner_slowdown_enabled=True,
            min_corner_angle=25,  # Menos conservador
            max_corner_slowdown=0.4,
            arc_speed_enabled=True,
            arc_speed_factor_small=0.5,
            arc_speed_factor_medium=0.8,
            lookahead_enabled=True,
            lookahead_segments=3,
        )
    
    @staticmethod
    def precision(base_speed: float = 1500) -> SpeedConfig:
        """Perfil para máxima precisão."""
        return SpeedConfig(
            base_speed=base_speed,
            min_speed=200,
            mode=SpeedMode.PRECISION,
            corner_slowdown_enabled=True,
            min_corner_angle=45,  # Mais conservador
            max_corner_slowdown=0.2,
            arc_speed_enabled=True,
            arc_speed_factor_small=0.3,
            arc_speed_factor_medium=0.6,
            arc_speed_factor_large=0.8,
            lookahead_enabled=True,
            lookahead_segments=7,
        )
    
    @staticmethod
    def balanced(base_speed: float = 2000) -> SpeedConfig:
        """Perfil balanceado (padrão)."""
        return SpeedConfig(
            base_speed=base_speed,
            mode=SpeedMode.ADAPTIVE,
        )
    
    @staticmethod
    def for_material(
        material: str,
        thickness: float,
        quality: str = "balanced"
    ) -> SpeedConfig:
        """
        Retorna configuração otimizada para material/espessura.
        
        Args:
            material: Tipo de material
            thickness: Espessura em mm
            quality: "production", "precision", ou "balanced"
        """
        # Velocidades base por material (mm/min para 6mm)
        MATERIAL_SPEEDS = {
            "mild_steel": 2000,
            "stainless": 1600,
            "aluminum": 2500,
            "copper": 1200,
            "brass": 1400,
        }
        
        base = MATERIAL_SPEEDS.get(material.lower(), 2000)
        
        # Ajustar por espessura (relação inversa)
        thickness_factor = 6.0 / max(thickness, 1.0)
        base = int(base * min(2.0, max(0.3, thickness_factor)))
        
        # Aplicar perfil de qualidade
        if quality == "production":
            return SpeedProfiles.production(base)
        elif quality == "precision":
            return SpeedProfiles.precision(base)
        else:
            return SpeedProfiles.balanced(base)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_adaptive_speed(
    base_speed: float,
    corner_angle: float = 180,
    arc_radius: float = None,
    config: SpeedConfig = None
) -> float:
    """
    Função auxiliar para cálculo rápido de velocidade.
    
    Args:
        base_speed: Velocidade base
        corner_angle: Ângulo do canto (graus)
        arc_radius: Raio do arco (se aplicável)
        config: Configuração (usa padrão se None)
    
    Returns:
        Velocidade ajustada
    """
    cfg = config or SpeedConfig(base_speed=base_speed)
    controller = SpeedController(cfg)
    
    factor = 1.0
    
    # Fator de canto
    factor *= controller.calculate_corner_speed(corner_angle)
    
    # Fator de arco
    if arc_radius is not None:
        factor *= controller.calculate_arc_speed(arc_radius)
    
    return base_speed * factor


def analyze_toolpath_speeds(
    points: List[Tuple[float, float]],
    arcs: List[Dict] = None,
    config: SpeedConfig = None
) -> SpeedProfile:
    """
    Analisa um toolpath e retorna perfil de velocidades.
    
    Args:
        points: Lista de pontos (x, y)
        arcs: Lista de arcos
        config: Configuração de velocidade
    
    Returns:
        SpeedProfile com análise completa
    """
    segments = PathAnalyzer.analyze_path(points, arcs)
    controller = SpeedController(config or SpeedConfig())
    return controller.process_path(segments)
