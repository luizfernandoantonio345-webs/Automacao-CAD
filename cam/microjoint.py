"""
═══════════════════════════════════════════════════════════════════════════════
MICRO-JOINTS (TABS) - Sistema de Pontes de Fixação
═══════════════════════════════════════════════════════════════════════════════

Sistema industrial para inserção de micro-joints (tabs/pontes) em peças cortadas:
- Inserção manual e automática
- Configuração de tamanho, quantidade e distribuição
- Tabs internas e externas
- Remoção fácil após corte
- Cálculo de resistência por material

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.cam.microjoint")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TabType(Enum):
    """Tipos de micro-joint."""
    STANDARD = "standard"           # Tab padrão (interrupção do corte)
    TAPERED = "tapered"             # Tab afilada (mais fácil de remover)
    DOGBONE = "dogbone"             # Tab com formato de osso
    BRIDGE = "bridge"               # Ponte completa
    PARTIAL = "partial"             # Tab parcial (penetração reduzida)


class TabDistribution(Enum):
    """Métodos de distribuição de tabs."""
    UNIFORM = "uniform"             # Distribuição uniforme
    CORNERS = "corners"             # Preferência em cantos
    LONG_EDGES = "long_edges"       # Em segmentos longos
    WEIGHT_BASED = "weight_based"   # Baseado no peso da peça
    CUSTOM = "custom"               # Posições customizadas
    SMART = "smart"                 # IA determina melhores posições


class TabPosition(Enum):
    """Posição da tab em relação ao contorno."""
    CENTER = "center"               # Centralizada no segmento
    START = "start"                 # No início do segmento
    END = "end"                     # No final do segmento
    CUSTOM = "custom"               # Posição customizada


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
    
    def midpoint_to(self, other: "Point2D") -> "Point2D":
        return Point2D((self.x + other.x) / 2, (self.y + other.y) / 2)
    
    def interpolate_to(self, other: "Point2D", t: float) -> "Point2D":
        """Interpola entre este ponto e outro (t=0 é este, t=1 é outro)."""
        return Point2D(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t
        )
    
    def offset_perpendicular(
        self, 
        other: "Point2D", 
        distance: float, 
        left: bool = True
    ) -> "Point2D":
        """Cria ponto perpendicular à linha para outro ponto."""
        dx = other.x - self.x
        dy = other.y - self.y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return Point2D(self.x, self.y)
        
        # Normalizar e rotacionar 90°
        if left:
            px, py = -dy/length, dx/length
        else:
            px, py = dy/length, -dx/length
        
        return Point2D(self.x + px * distance, self.y + py * distance)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class TabConfig:
    """Configuração de micro-joint."""
    
    # Habilitação
    enabled: bool = True
    
    # Tipo
    tab_type: TabType = TabType.STANDARD
    
    # Dimensões
    width: float = 2.0              # mm - largura da tab
    height: float = 0.0             # mm - altura (0 = penetração total)
    taper_angle: float = 30.0       # graus - ângulo para tabs afiladas
    
    # Quantidade e distribuição
    count: int = 4                  # Número de tabs por contorno
    distribution: TabDistribution = TabDistribution.UNIFORM
    min_spacing: float = 20.0       # mm - espaçamento mínimo entre tabs
    max_spacing: float = 200.0      # mm - espaçamento máximo
    
    # Posicionamento
    avoid_corners: bool = True      # Evitar cantos
    corner_distance: float = 5.0    # mm - distância mínima de cantos
    prefer_straights: bool = True   # Preferir segmentos retos
    
    # Para peso/material
    min_weight_for_tabs: float = 0.5  # kg - peso mínimo para usar tabs
    tabs_per_kg: float = 2.0        # Tabs adicionais por kg
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "tab_type": self.tab_type.value,
            "width": self.width,
            "height": self.height,
            "count": self.count,
            "distribution": self.distribution.value,
            "min_spacing": self.min_spacing,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TabConfig":
        return cls(
            enabled=data.get("enabled", True),
            tab_type=TabType(data.get("tab_type", "standard")),
            width=data.get("width", 2.0),
            height=data.get("height", 0.0),
            count=data.get("count", 4),
            distribution=TabDistribution(data.get("distribution", "uniform")),
            min_spacing=data.get("min_spacing", 20.0),
        )


@dataclass
class Tab:
    """Uma micro-joint individual."""
    
    # Posição
    position: Point2D               # Centro da tab
    segment_index: int = 0          # Índice do segmento no contorno
    position_on_segment: float = 0.5  # 0-1, posição no segmento
    
    # Geometria
    start_point: Point2D = None     # Início da tab (onde para de cortar)
    end_point: Point2D = None       # Fim da tab (onde retoma corte)
    
    # Configuração
    width: float = 2.0
    height: float = 0.0
    tab_type: TabType = TabType.STANDARD
    
    # Metadados
    id: str = ""
    enabled: bool = True
    manual: bool = False            # Se foi posicionada manualmente
    
    @property
    def length(self) -> float:
        """Comprimento da tab (material não cortado)."""
        if self.start_point and self.end_point:
            return self.start_point.distance_to(self.end_point)
        return self.width
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_tuple(),
            "segment_index": self.segment_index,
            "position_on_segment": self.position_on_segment,
            "width": self.width,
            "height": self.height,
            "tab_type": self.tab_type.value,
            "enabled": self.enabled,
            "manual": self.manual,
        }


@dataclass
class TabResult:
    """Resultado da geração de tabs para um contorno."""
    
    tabs: List[Tab] = field(default_factory=list)
    total_tab_length: float = 0.0   # Comprimento total de tabs
    contour_length: float = 0.0     # Comprimento total do contorno
    coverage_ratio: float = 0.0     # Razão de cobertura (tabs/contorno)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tabs": [t.to_dict() for t in self.tabs],
            "total_tab_length": self.total_tab_length,
            "contour_length": self.contour_length,
            "coverage_ratio": self.coverage_ratio,
            "warnings": self.warnings,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TABELAS DE PARÂMETROS
# ═══════════════════════════════════════════════════════════════════════════════

class TabParameters:
    """Parâmetros recomendados por material e espessura."""
    
    # {material: {espessura: (largura_tab, altura_tab, tabs_por_metro)}}
    MATERIAL_PARAMS = {
        "mild_steel": {
            1.0: (1.5, 0.0, 30),
            2.0: (2.0, 0.0, 25),
            3.0: (2.5, 0.0, 20),
            6.0: (3.0, 0.0, 15),
            10.0: (4.0, 0.0, 12),
            12.0: (5.0, 0.0, 10),
            16.0: (6.0, 0.0, 8),
            20.0: (7.0, 0.0, 6),
        },
        "stainless": {
            1.0: (2.0, 0.0, 35),
            2.0: (2.5, 0.0, 30),
            3.0: (3.0, 0.0, 25),
            6.0: (4.0, 0.0, 18),
            10.0: (5.0, 0.0, 15),
        },
        "aluminum": {
            1.0: (1.0, 0.0, 20),
            2.0: (1.5, 0.0, 18),
            3.0: (2.0, 0.0, 15),
            6.0: (2.5, 0.0, 12),
            10.0: (3.0, 0.0, 10),
        },
    }
    
    @classmethod
    def get_params(
        cls,
        material: str,
        thickness: float
    ) -> Tuple[float, float, int]:
        """
        Retorna parâmetros recomendados.
        
        Returns:
            Tuple[largura, altura, tabs_por_metro]
        """
        material = material.lower().replace(' ', '_')
        table = cls.MATERIAL_PARAMS.get(material, cls.MATERIAL_PARAMS["mild_steel"])
        
        # Encontrar espessura mais próxima
        thicknesses = sorted(table.keys())
        closest = min(thicknesses, key=lambda t: abs(t - thickness))
        
        width, height, density = table[closest]
        
        # Ajustar por espessura
        ratio = thickness / closest if closest > 0 else 1.0
        width = width * (0.8 + ratio * 0.2)
        
        return width, height, density
    
    @classmethod
    def calculate_tab_count(
        cls,
        contour_length: float,
        tabs_per_meter: int,
        min_tabs: int = 2,
        max_tabs: int = 20
    ) -> int:
        """Calcula número recomendado de tabs."""
        count = int(math.ceil(contour_length / 1000 * tabs_per_meter))
        return max(min_tabs, min(count, max_tabs))


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR DE TABS
# ═══════════════════════════════════════════════════════════════════════════════

class TabGenerator:
    """
    Gerador de micro-joints (tabs).
    
    Calcula posições e geometrias de tabs para manter
    peças fixas na chapa durante o corte.
    """
    
    def __init__(self, config: TabConfig = None):
        self.config = config or TabConfig()
        self._tab_counter = 0
    
    def _generate_tab_id(self) -> str:
        """Gera ID único para tab."""
        self._tab_counter += 1
        return f"tab_{self._tab_counter:04d}"
    
    def generate_tabs(
        self,
        contour_points: List[Tuple[float, float]],
        is_closed: bool = True,
        is_internal: bool = False,
        existing_tabs: List[Tab] = None
    ) -> TabResult:
        """
        Gera tabs para um contorno.
        
        Args:
            contour_points: Lista de pontos do contorno
            is_closed: Se o contorno é fechado
            is_internal: Se é um contorno interno (furo)
            existing_tabs: Tabs já existentes (manuais)
        
        Returns:
            TabResult com tabs geradas
        """
        if not self.config.enabled or len(contour_points) < 2:
            return TabResult()
        
        result = TabResult()
        
        # Calcular comprimento total do contorno
        contour_length = self._calculate_contour_length(contour_points, is_closed)
        result.contour_length = contour_length
        
        # Verificar se precisa de tabs
        if contour_length < self.config.min_spacing:
            result.warnings.append(
                f"Contorno muito curto ({contour_length:.1f}mm) para tabs"
            )
            return result
        
        # Contornos internos geralmente não precisam de tabs
        if is_internal and contour_length < 100:
            result.warnings.append("Furos pequenos geralmente não precisam de tabs")
            return result
        
        # Analisar segmentos
        segments = self._analyze_segments(contour_points, is_closed)
        
        # Determinar posições das tabs
        if self.config.distribution == TabDistribution.UNIFORM:
            positions = self._distribute_uniform(segments, contour_length)
        elif self.config.distribution == TabDistribution.CORNERS:
            positions = self._distribute_corners(segments, contour_points)
        elif self.config.distribution == TabDistribution.LONG_EDGES:
            positions = self._distribute_long_edges(segments)
        elif self.config.distribution == TabDistribution.SMART:
            positions = self._distribute_smart(segments, contour_points, is_internal)
        else:
            positions = self._distribute_uniform(segments, contour_length)
        
        # Criar tabs nas posições calculadas
        for pos in positions:
            tab = self._create_tab(pos, segments, contour_points)
            if tab:
                result.tabs.append(tab)
        
        # Adicionar tabs existentes (manuais)
        if existing_tabs:
            for tab in existing_tabs:
                if tab.enabled:
                    result.tabs.append(tab)
        
        # Calcular estatísticas
        result.total_tab_length = sum(t.length for t in result.tabs)
        result.coverage_ratio = result.total_tab_length / contour_length if contour_length > 0 else 0
        
        # Avisos
        if result.coverage_ratio > 0.2:
            result.warnings.append(
                f"Cobertura de tabs alta ({result.coverage_ratio*100:.1f}%). "
                "Considere reduzir tamanho ou quantidade."
            )
        
        return result
    
    def _calculate_contour_length(
        self,
        points: List[Tuple[float, float]],
        is_closed: bool
    ) -> float:
        """Calcula comprimento total do contorno."""
        length = 0.0
        
        for i in range(len(points) - 1):
            p1 = Point2D(*points[i])
            p2 = Point2D(*points[i+1])
            length += p1.distance_to(p2)
        
        if is_closed and len(points) > 2:
            p1 = Point2D(*points[-1])
            p2 = Point2D(*points[0])
            length += p1.distance_to(p2)
        
        return length
    
    def _analyze_segments(
        self,
        points: List[Tuple[float, float]],
        is_closed: bool
    ) -> List[Dict[str, Any]]:
        """
        Analisa segmentos do contorno.
        
        Returns:
            Lista de dicts com informações de cada segmento
        """
        segments = []
        n = len(points)
        
        for i in range(n - 1):
            p1 = Point2D(*points[i])
            p2 = Point2D(*points[i+1])
            
            # Calcular ângulo do segmento
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            angle = math.atan2(dy, dx)
            
            # Calcular ângulo do canto (com próximo segmento)
            corner_angle = 180.0
            if i < n - 2:
                p3 = Point2D(*points[i+2])
                dx2 = p3.x - p2.x
                dy2 = p3.y - p2.y
                angle2 = math.atan2(dy2, dx2)
                corner_angle = abs(math.degrees(angle2 - angle))
                if corner_angle > 180:
                    corner_angle = 360 - corner_angle
            
            segments.append({
                "index": i,
                "start": p1,
                "end": p2,
                "length": p1.distance_to(p2),
                "angle": angle,
                "corner_angle": corner_angle,
                "is_straight": corner_angle > 170,  # Quase reto
                "cumulative_length": sum(s["length"] for s in segments),
            })
        
        # Fechar o contorno se necessário
        if is_closed and n > 2:
            p1 = Point2D(*points[-1])
            p2 = Point2D(*points[0])
            segments.append({
                "index": n - 1,
                "start": p1,
                "end": p2,
                "length": p1.distance_to(p2),
                "angle": math.atan2(p2.y - p1.y, p2.x - p1.x),
                "corner_angle": 180.0,
                "is_straight": True,
                "cumulative_length": sum(s["length"] for s in segments),
            })
        
        return segments
    
    def _distribute_uniform(
        self,
        segments: List[Dict],
        contour_length: float
    ) -> List[Dict[str, Any]]:
        """Distribui tabs uniformemente."""
        positions = []
        
        if self.config.count <= 0:
            return positions
        
        # Espaçamento entre tabs
        spacing = contour_length / self.config.count
        
        # Garantir espaçamento mínimo e máximo
        if spacing < self.config.min_spacing:
            actual_count = max(2, int(contour_length / self.config.min_spacing))
            spacing = contour_length / actual_count
        elif spacing > self.config.max_spacing:
            actual_count = int(math.ceil(contour_length / self.config.max_spacing))
            spacing = contour_length / actual_count
        else:
            actual_count = self.config.count
        
        # Calcular posições
        cumulative = 0.0
        for i in range(actual_count):
            target_length = spacing * (i + 0.5)  # Centro de cada intervalo
            
            # Encontrar segmento correspondente
            for seg in segments:
                seg_start = seg["cumulative_length"]
                seg_end = seg_start + seg["length"]
                
                if seg_start <= target_length < seg_end:
                    # Posição relativa no segmento
                    t = (target_length - seg_start) / seg["length"] if seg["length"] > 0 else 0.5
                    
                    positions.append({
                        "segment_index": seg["index"],
                        "position_on_segment": t,
                        "absolute_position": target_length,
                    })
                    break
        
        return positions
    
    def _distribute_corners(
        self,
        segments: List[Dict],
        contour_points: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        """Distribui tabs perto de cantos."""
        positions = []
        
        # Encontrar cantos (mudanças de direção significativas)
        corners = []
        for i, seg in enumerate(segments):
            if seg["corner_angle"] < 160:  # Canto significativo
                corners.append({
                    "index": i,
                    "angle": seg["corner_angle"],
                    "position": seg["cumulative_length"] + seg["length"],
                })
        
        # Se não há cantos suficientes, usar distribuição uniforme
        if len(corners) < self.config.count:
            return self._distribute_uniform(
                segments, 
                sum(s["length"] for s in segments)
            )
        
        # Selecionar os cantos mais significativos
        corners.sort(key=lambda c: c["angle"])
        selected = corners[:self.config.count]
        
        # Criar posições perto dos cantos (não exatamente no canto)
        for corner in selected:
            seg_idx = corner["index"]
            seg = segments[seg_idx]
            
            # Posicionar um pouco antes do canto
            offset = min(self.config.corner_distance, seg["length"] * 0.3)
            t = 1.0 - (offset / seg["length"]) if seg["length"] > 0 else 0.5
            
            positions.append({
                "segment_index": seg_idx,
                "position_on_segment": t,
                "absolute_position": corner["position"] - offset,
            })
        
        return positions
    
    def _distribute_long_edges(
        self,
        segments: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Distribui tabs em segmentos longos."""
        positions = []
        
        # Ordenar segmentos por comprimento
        sorted_segments = sorted(segments, key=lambda s: s["length"], reverse=True)
        
        # Selecionar os segmentos mais longos
        selected = []
        for seg in sorted_segments:
            if len(selected) >= self.config.count:
                break
            
            # Verificar se está longe o suficiente de outros selecionados
            too_close = False
            for sel in selected:
                dist = abs(seg["cumulative_length"] - sel["cumulative_length"])
                if dist < self.config.min_spacing:
                    too_close = True
                    break
            
            if not too_close:
                selected.append(seg)
        
        # Criar posições no centro de cada segmento
        for seg in selected:
            positions.append({
                "segment_index": seg["index"],
                "position_on_segment": 0.5,
                "absolute_position": seg["cumulative_length"] + seg["length"] * 0.5,
            })
        
        return positions
    
    def _distribute_smart(
        self,
        segments: List[Dict],
        contour_points: List[Tuple[float, float]],
        is_internal: bool
    ) -> List[Dict[str, Any]]:
        """
        Distribuição inteligente considerando múltiplos fatores.
        
        Considera:
        - Comprimento do segmento
        - Distância de cantos
        - Distribuição uniforme
        - Evitar áreas problemáticas
        """
        positions = []
        contour_length = sum(s["length"] for s in segments)
        
        # Calcular score para cada posição possível
        candidates = []
        
        for seg in segments:
            if seg["length"] < self.config.width * 2:
                continue  # Segmento muito curto
            
            # Gerar algumas posições candidatas no segmento
            num_candidates = max(1, int(seg["length"] / 5))
            
            for i in range(num_candidates):
                t = (i + 0.5) / num_candidates
                abs_pos = seg["cumulative_length"] + seg["length"] * t
                
                # Calcular score
                score = 0.0
                
                # Preferir segmentos longos
                score += min(seg["length"] / 50, 3)
                
                # Preferir longe de cantos
                dist_to_corner = min(
                    seg["length"] * t,
                    seg["length"] * (1 - t)
                )
                if dist_to_corner > self.config.corner_distance:
                    score += 2
                
                # Preferir segmentos retos
                if seg["is_straight"]:
                    score += 1
                
                candidates.append({
                    "segment_index": seg["index"],
                    "position_on_segment": t,
                    "absolute_position": abs_pos,
                    "score": score,
                })
        
        # Ordenar por score
        candidates.sort(key=lambda c: c["score"], reverse=True)
        
        # Selecionar candidatos mantendo espaçamento
        for cand in candidates:
            if len(positions) >= self.config.count:
                break
            
            # Verificar espaçamento
            too_close = False
            for pos in positions:
                dist = abs(cand["absolute_position"] - pos["absolute_position"])
                # Considerar wrap-around para contornos fechados
                dist = min(dist, contour_length - dist)
                
                if dist < self.config.min_spacing:
                    too_close = True
                    break
            
            if not too_close:
                positions.append(cand)
        
        return positions
    
    def _create_tab(
        self,
        position: Dict[str, Any],
        segments: List[Dict],
        contour_points: List[Tuple[float, float]]
    ) -> Optional[Tab]:
        """Cria uma tab em uma posição."""
        seg_idx = position["segment_index"]
        t = position["position_on_segment"]
        
        if seg_idx >= len(segments):
            return None
        
        seg = segments[seg_idx]
        
        # Calcular centro da tab
        center = seg["start"].interpolate_to(seg["end"], t)
        
        # Calcular pontos de início e fim da tab
        half_width = self.config.width / 2
        
        # Posição ao longo do segmento
        t_start = t - (half_width / seg["length"]) if seg["length"] > 0 else 0
        t_end = t + (half_width / seg["length"]) if seg["length"] > 0 else 1
        
        t_start = max(0, t_start)
        t_end = min(1, t_end)
        
        start_point = seg["start"].interpolate_to(seg["end"], t_start)
        end_point = seg["start"].interpolate_to(seg["end"], t_end)
        
        return Tab(
            id=self._generate_tab_id(),
            position=center,
            segment_index=seg_idx,
            position_on_segment=t,
            start_point=start_point,
            end_point=end_point,
            width=self.config.width,
            height=self.config.height,
            tab_type=self.config.tab_type,
            enabled=True,
            manual=False,
        )
    
    def add_manual_tab(
        self,
        position: Tuple[float, float],
        segment_index: int,
        width: float = None
    ) -> Tab:
        """
        Adiciona uma tab manualmente em uma posição específica.
        
        Args:
            position: Posição (x, y) da tab
            segment_index: Índice do segmento
            width: Largura (usa config se None)
        
        Returns:
            Tab criada
        """
        return Tab(
            id=self._generate_tab_id(),
            position=Point2D(*position),
            segment_index=segment_index,
            width=width or self.config.width,
            height=self.config.height,
            tab_type=self.config.tab_type,
            enabled=True,
            manual=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# APLICADOR DE TABS NO TOOLPATH
# ═══════════════════════════════════════════════════════════════════════════════

class TabApplicator:
    """
    Aplica tabs em um toolpath existente.
    
    Modifica a trajetória de corte para criar interrupções
    (tabs) onde necessário.
    """
    
    @staticmethod
    def apply_tabs_to_toolpath(
        toolpath_points: List[Tuple[float, float]],
        tabs: List[Tab],
        lift_height: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Aplica tabs a um toolpath.
        
        Retorna lista de movimentos modificados incluindo
        lifts sobre as tabs.
        
        Args:
            toolpath_points: Pontos do toolpath original
            tabs: Lista de tabs a aplicar
            lift_height: Altura para levantar sobre tabs
        
        Returns:
            Lista de movimentos com tabs aplicadas
        """
        if not tabs:
            # Sem tabs, retornar movimentos lineares simples
            moves = []
            for i in range(len(toolpath_points) - 1):
                moves.append({
                    "type": "cut",
                    "start": toolpath_points[i],
                    "end": toolpath_points[i+1],
                })
            return moves
        
        moves = []
        
        # Ordenar tabs por segmento e posição
        sorted_tabs = sorted(
            [t for t in tabs if t.enabled],
            key=lambda t: (t.segment_index, t.position_on_segment)
        )
        
        tab_idx = 0
        
        for i in range(len(toolpath_points) - 1):
            start = toolpath_points[i]
            end = toolpath_points[i+1]
            
            # Verificar se há tabs neste segmento
            segment_tabs = [
                t for t in sorted_tabs
                if t.segment_index == i
            ]
            
            if not segment_tabs:
                # Sem tabs neste segmento
                moves.append({
                    "type": "cut",
                    "start": start,
                    "end": end,
                })
            else:
                # Processar tabs no segmento
                current_pos = start
                
                for tab in segment_tabs:
                    # Cortar até o início da tab
                    if tab.start_point:
                        tab_start = tab.start_point.to_tuple()
                    else:
                        # Calcular baseado na posição
                        p1 = Point2D(*start)
                        p2 = Point2D(*end)
                        t = max(0, tab.position_on_segment - tab.width / (2 * p1.distance_to(p2)))
                        tab_start = p1.interpolate_to(p2, t).to_tuple()
                    
                    if current_pos != tab_start:
                        moves.append({
                            "type": "cut",
                            "start": current_pos,
                            "end": tab_start,
                        })
                    
                    # Levantar sobre a tab
                    if tab.end_point:
                        tab_end = tab.end_point.to_tuple()
                    else:
                        p1 = Point2D(*start)
                        p2 = Point2D(*end)
                        t = min(1, tab.position_on_segment + tab.width / (2 * p1.distance_to(p2)))
                        tab_end = p1.interpolate_to(p2, t).to_tuple()
                    
                    moves.append({
                        "type": "lift_start",
                        "position": tab_start,
                        "height": lift_height,
                        "tab_id": tab.id,
                    })
                    
                    moves.append({
                        "type": "rapid_over_tab",
                        "start": tab_start,
                        "end": tab_end,
                        "height": lift_height,
                        "tab_id": tab.id,
                    })
                    
                    moves.append({
                        "type": "plunge",
                        "position": tab_end,
                        "tab_id": tab.id,
                    })
                    
                    current_pos = tab_end
                
                # Completar o segmento após última tab
                if current_pos != end:
                    moves.append({
                        "type": "cut",
                        "start": current_pos,
                        "end": end,
                    })
        
        return moves
    
    @staticmethod
    def generate_gcode_with_tabs(
        moves: List[Dict[str, Any]],
        cut_feed: float = 2000,
        rapid_feed: float = 10000,
        pierce_sequence: str = None,
        decimal_places: int = 3
    ) -> List[str]:
        """
        Gera G-code com tabs aplicadas.
        
        Args:
            moves: Movimentos com tabs
            cut_feed: Feed rate de corte
            rapid_feed: Feed rate rápido
            pierce_sequence: G-code para re-pierce (após tab)
            decimal_places: Casas decimais
        
        Returns:
            Lista de linhas de G-code
        """
        lines = []
        plasma_on = True
        
        def fmt(val):
            return f"{val:.{decimal_places}f}"
        
        for move in moves:
            if move["type"] == "cut":
                x, y = move["end"]
                lines.append(f"G01 X{fmt(x)} Y{fmt(y)} F{int(cut_feed)}")
            
            elif move["type"] == "lift_start":
                # Desligar plasma e levantar
                lines.append(f"(Tab: {move.get('tab_id', '')})")
                lines.append("M05 (Plasma OFF - Tab)")
                lines.append(f"G00 Z{fmt(move['height'])}")
                plasma_on = False
            
            elif move["type"] == "rapid_over_tab":
                x, y = move["end"]
                lines.append(f"G00 X{fmt(x)} Y{fmt(y)} (Sobre tab)")
            
            elif move["type"] == "plunge":
                x, y = move["position"]
                # Re-pierce após tab
                if pierce_sequence:
                    lines.append(pierce_sequence)
                else:
                    lines.append("G00 Z3.0 (Pierce height)")
                    lines.append("M03 (Plasma ON)")
                    lines.append("G04 P200 (Pierce delay)")
                    lines.append("G01 Z1.5 F500 (Cut height)")
                plasma_on = True
        
        return lines


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES PREDEFINIDAS
# ═══════════════════════════════════════════════════════════════════════════════

class TabPresets:
    """Configurações predefinidas de tabs."""
    
    @staticmethod
    def light_parts(thickness: float = 3.0) -> TabConfig:
        """Para peças leves que precisam de poucos tabs."""
        return TabConfig(
            width=2.0,
            count=2,
            distribution=TabDistribution.UNIFORM,
            min_spacing=50.0,
        )
    
    @staticmethod
    def medium_parts(thickness: float = 6.0) -> TabConfig:
        """Para peças médias."""
        return TabConfig(
            width=3.0,
            count=4,
            distribution=TabDistribution.SMART,
            min_spacing=30.0,
        )
    
    @staticmethod
    def heavy_parts(thickness: float = 12.0) -> TabConfig:
        """Para peças pesadas que precisam de mais suporte."""
        return TabConfig(
            width=5.0,
            count=6,
            distribution=TabDistribution.UNIFORM,
            min_spacing=40.0,
            max_spacing=150.0,
        )
    
    @staticmethod
    def fine_detail() -> TabConfig:
        """Para peças com detalhes finos."""
        return TabConfig(
            tab_type=TabType.TAPERED,
            width=1.5,
            count=4,
            taper_angle=45.0,
            distribution=TabDistribution.CORNERS,
        )
    
    @staticmethod
    def for_material(
        material: str,
        thickness: float,
        contour_length: float
    ) -> TabConfig:
        """
        Retorna configuração otimizada para material/espessura.
        """
        width, height, tabs_per_m = TabParameters.get_params(material, thickness)
        count = TabParameters.calculate_tab_count(contour_length, tabs_per_m)
        
        return TabConfig(
            width=width,
            height=height,
            count=count,
            distribution=TabDistribution.SMART,
            min_spacing=max(20, contour_length / (count * 2)),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tabs_for_contour(
    contour_points: List[Tuple[float, float]],
    material: str = "mild_steel",
    thickness: float = 6.0,
    config: TabConfig = None
) -> TabResult:
    """
    Função auxiliar para gerar tabs rapidamente.
    
    Args:
        contour_points: Pontos do contorno
        material: Tipo de material
        thickness: Espessura
        config: Configuração (auto se None)
    
    Returns:
        TabResult
    """
    if config is None:
        contour_length = 0
        for i in range(len(contour_points) - 1):
            p1 = Point2D(*contour_points[i])
            p2 = Point2D(*contour_points[i+1])
            contour_length += p1.distance_to(p2)
        
        config = TabPresets.for_material(material, thickness, contour_length)
    
    generator = TabGenerator(config)
    return generator.generate_tabs(contour_points)


def estimate_removal_time(tabs: List[Tab], material: str = "mild_steel") -> float:
    """
    Estima tempo para remover tabs manualmente.
    
    Args:
        tabs: Lista de tabs
        material: Tipo de material
    
    Returns:
        Tempo estimado em segundos
    """
    # Tempo base por tab (segundos)
    BASE_TIMES = {
        "mild_steel": 5.0,
        "stainless": 7.0,
        "aluminum": 3.0,
        "copper": 4.0,
    }
    
    base_time = BASE_TIMES.get(material.lower(), 5.0)
    
    total_time = 0.0
    for tab in tabs:
        if tab.enabled:
            # Tempo proporcional à largura
            factor = tab.width / 2.0
            total_time += base_time * factor
    
    return total_time
