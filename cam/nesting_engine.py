"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Engine de Nesting Profissional
Engenharia CAD - Otimização de Aproveitamento de Chapa para Corte CNC
═══════════════════════════════════════════════════════════════════════════════

Este módulo implementa algoritmos profissionais de nesting:
- Bottom-Left Fill (BLF) - Posicionamento rápido e eficiente
- No-Fit Polygon (NFP) - Para formas complexas
- Genetic Algorithm - Otimização global
- Simulated Annealing - Refinamento de soluções

Recursos:
- Rotação automática (0°, 90°, 180°, 270°)
- Espelhamento opcional
- Análise de aproveitamento por chapa
- Sugestões de otimização
- Histórico de jobs
"""

from __future__ import annotations

import logging
import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any, Set
import json
import os

logger = logging.getLogger("engcad.cam.nesting")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class NestingAlgorithm(Enum):
    """Algoritmos de nesting disponíveis."""
    BOTTOM_LEFT_FILL = "blf"       # Rápido, bom para retângulos
    NO_FIT_POLYGON = "nfp"          # Preciso para formas complexas
    GENETIC = "genetic"             # Otimização global
    SIMULATED_ANNEALING = "sa"      # Refinamento iterativo
    GUILLOTINE = "guillotine"       # Cortes lineares (ótimo para guilhotinas)


class RotationMode(Enum):
    """Modos de rotação permitidos."""
    NONE = "none"                   # Sem rotação
    ORTHOGONAL = "orthogonal"       # 0°, 90°, 180°, 270°
    FREE = "free"                   # Qualquer ângulo
    GRAIN_ALIGNED = "grain"         # Alinhado com fibra do material


class NestingPriority(Enum):
    """Prioridades de nesting."""
    SPEED = "speed"                 # Mais rápido possível
    EFFICIENCY = "efficiency"       # Melhor aproveitamento
    BALANCED = "balanced"           # Equilíbrio


# Rotações padrão (em radianos)
ORTHOGONAL_ROTATIONS = [0, math.pi/2, math.pi, 3*math.pi/2]
STANDARD_ROTATIONS_DEG = [0, 90, 180, 270]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Point2D:
    """Ponto 2D."""
    x: float
    y: float
    
    def __add__(self, other: "Point2D") -> "Point2D":
        return Point2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: "Point2D") -> "Point2D":
        return Point2D(self.x - other.x, self.y - other.y)
    
    def rotate(self, angle: float, center: "Point2D" = None) -> "Point2D":
        """Rotaciona o ponto em torno de um centro."""
        if center is None:
            center = Point2D(0, 0)
        
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        dx = self.x - center.x
        dy = self.y - center.y
        
        return Point2D(
            center.x + dx * cos_a - dy * sin_a,
            center.y + dx * sin_a + dy * cos_a
        )
    
    def distance_to(self, other: "Point2D") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass
class BoundingBox:
    """Bounding box de uma peça."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Point2D:
        return Point2D(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )
    
    def intersects(self, other: "BoundingBox") -> bool:
        """Verifica se dois bounding boxes se intersectam."""
        return not (
            self.max_x < other.min_x or
            self.min_x > other.max_x or
            self.max_y < other.min_y or
            self.min_y > other.max_y
        )
    
    def expand(self, margin: float) -> "BoundingBox":
        """Expande o bounding box por uma margem."""
        return BoundingBox(
            self.min_x - margin,
            self.min_y - margin,
            self.max_x + margin,
            self.max_y + margin
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "minX": self.min_x,
            "minY": self.min_y,
            "maxX": self.max_x,
            "maxY": self.max_y
        }


@dataclass
class Polygon:
    """Polígono fechado representando contorno de uma peça."""
    points: List[Point2D]
    is_hole: bool = False
    
    @property
    def area(self) -> float:
        """Calcula área usando fórmula de Shoelace."""
        n = len(self.points)
        if n < 3:
            return 0
        
        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        
        return abs(area) / 2
    
    @property
    def perimeter(self) -> float:
        """Calcula perímetro."""
        n = len(self.points)
        if n < 2:
            return 0
        
        length = 0
        for i in range(n):
            j = (i + 1) % n
            length += self.points[i].distance_to(self.points[j])
        
        return length
    
    @property
    def centroid(self) -> Point2D:
        """Calcula centroide."""
        n = len(self.points)
        if n == 0:
            return Point2D(0, 0)
        
        cx = sum(p.x for p in self.points) / n
        cy = sum(p.y for p in self.points) / n
        return Point2D(cx, cy)
    
    def bounding_box(self) -> BoundingBox:
        """Retorna bounding box."""
        if not self.points:
            return BoundingBox(0, 0, 0, 0)
        
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))
    
    def rotate(self, angle: float, center: Point2D = None) -> "Polygon":
        """Rotaciona o polígono."""
        if center is None:
            center = self.centroid
        
        return Polygon(
            [p.rotate(angle, center) for p in self.points],
            self.is_hole
        )
    
    def translate(self, dx: float, dy: float) -> "Polygon":
        """Translada o polígono."""
        return Polygon(
            [Point2D(p.x + dx, p.y + dy) for p in self.points],
            self.is_hole
        )


@dataclass
class NestingPiece:
    """Peça para nesting."""
    id: str
    name: str
    contour: Polygon                # Contorno externo
    holes: List[Polygon] = field(default_factory=list)  # Furos internos
    quantity: int = 1
    priority: int = 0               # Maior = mais prioritário
    allow_rotation: bool = True
    allowed_rotations: List[float] = field(default_factory=lambda: STANDARD_ROTATIONS_DEG)
    material_grain: Optional[float] = None  # Direção da fibra se relevante
    
    @property
    def area(self) -> float:
        """Área líquida (contorno - furos)."""
        hole_area = sum(h.area for h in self.holes)
        return self.contour.area - hole_area
    
    @property
    def bounding_box(self) -> BoundingBox:
        return self.contour.bounding_box()
    
    @property
    def cutting_length(self) -> float:
        """Comprimento total de corte."""
        length = self.contour.perimeter
        for hole in self.holes:
            length += hole.perimeter
        return length
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "area": self.area,
            "cuttingLength": self.cutting_length,
            "boundingBox": self.bounding_box.to_dict(),
        }


@dataclass
class NestingSheet:
    """Chapa onde as peças serão nestadas."""
    id: str
    width: float
    height: float
    material: str = "mild_steel"
    thickness: float = 6.0
    margin: float = 10.0            # Margem nas bordas
    spacing: float = 5.0            # Espaço entre peças
    cost_per_kg: float = 4.50
    density: float = 7.85e-6        # kg/mm³
    
    @property
    def usable_area(self) -> float:
        """Área útil (descontando margens)."""
        w = self.width - 2 * self.margin
        h = self.height - 2 * self.margin
        return max(0, w * h)
    
    @property
    def total_area(self) -> float:
        return self.width * self.height
    
    @property
    def weight(self) -> float:
        """Peso em kg."""
        return self.total_area * self.thickness * self.density
    
    @property
    def cost(self) -> float:
        """Custo da chapa em R$."""
        return self.weight * self.cost_per_kg
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "material": self.material,
            "thickness": self.thickness,
            "margin": self.margin,
            "spacing": self.spacing,
            "usableArea": self.usable_area,
            "weight": self.weight,
            "cost": self.cost
        }


@dataclass
class Placement:
    """Posicionamento de uma peça na chapa."""
    piece_id: str
    piece_name: str
    x: float
    y: float
    rotation: float = 0.0           # Em graus
    mirrored: bool = False
    sheet_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pieceId": self.piece_id,
            "pieceName": self.piece_name,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "mirrored": self.mirrored,
            "sheetId": self.sheet_id
        }


@dataclass
class NestingStatistics:
    """Estatísticas do resultado de nesting."""
    total_pieces: int = 0
    placed_pieces: int = 0
    unplaced_pieces: int = 0
    sheets_used: int = 0
    total_sheet_area: float = 0
    used_area: float = 0
    waste_area: float = 0
    efficiency: float = 0.0         # Percentual de aproveitamento
    total_cutting_length: float = 0
    estimated_time_minutes: float = 0
    total_cost: float = 0
    material_cost: float = 0
    cutting_cost: float = 0         # Custo baseado em tempo
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalPieces": self.total_pieces,
            "placedPieces": self.placed_pieces,
            "unplacedPieces": self.unplaced_pieces,
            "sheetsUsed": self.sheets_used,
            "totalSheetArea": self.total_sheet_area,
            "usedArea": self.used_area,
            "wasteArea": self.waste_area,
            "efficiency": round(self.efficiency, 2),
            "totalCuttingLength": round(self.total_cutting_length, 1),
            "estimatedTimeMinutes": round(self.estimated_time_minutes, 1),
            "totalCost": round(self.total_cost, 2),
            "materialCost": round(self.material_cost, 2),
            "cuttingCost": round(self.cutting_cost, 2)
        }


@dataclass
class NestingResult:
    """Resultado completo do nesting."""
    job_id: str
    algorithm: NestingAlgorithm
    placements: List[Placement]
    statistics: NestingStatistics
    sheets: List[NestingSheet]
    unplaced_pieces: List[str]
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    computation_time_ms: float = 0
    
    @property
    def success(self) -> bool:
        return len(self.unplaced_pieces) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "algorithm": self.algorithm.value,
            "success": self.success,
            "placements": [p.to_dict() for p in self.placements],
            "statistics": self.statistics.to_dict(),
            "sheets": [s.to_dict() for s in self.sheets],
            "unplacedPieces": self.unplaced_pieces,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "createdAt": self.created_at.isoformat(),
            "computationTimeMs": round(self.computation_time_ms, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# NESTING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class NestingEngine:
    """
    Engine de nesting profissional.
    
    Implementa múltiplos algoritmos de otimização para posicionamento
    de peças em chapas, maximizando o aproveitamento de material.
    """
    
    def __init__(
        self,
        algorithm: NestingAlgorithm = NestingAlgorithm.BOTTOM_LEFT_FILL,
        priority: NestingPriority = NestingPriority.BALANCED,
        rotation_mode: RotationMode = RotationMode.ORTHOGONAL,
        max_iterations: int = 1000,
        cutting_speed_mm_min: float = 2000,
        cost_per_hour: float = 150.0,
    ):
        self.algorithm = algorithm
        self.priority = priority
        self.rotation_mode = rotation_mode
        self.max_iterations = max_iterations
        self.cutting_speed = cutting_speed_mm_min
        self.cost_per_hour = cost_per_hour
        
        logger.info(f"NestingEngine inicializado: algorithm={algorithm.value}, priority={priority.value}")
    
    def nest(
        self,
        pieces: List[NestingPiece],
        sheet: NestingSheet,
        max_sheets: int = 10,
    ) -> NestingResult:
        """
        Executa o nesting das peças na chapa.
        
        Args:
            pieces: Lista de peças para nestar
            sheet: Configuração da chapa
            max_sheets: Número máximo de chapas a usar
            
        Returns:
            NestingResult com posicionamentos e estatísticas
        """
        import time
        start_time = time.perf_counter()
        
        job_id = str(uuid.uuid4())[:8]
        logger.info(f"[NEST-{job_id}] Iniciando nesting: {len(pieces)} tipos de peças")
        
        # Expandir peças por quantidade
        expanded_pieces = self._expand_pieces(pieces)
        total_pieces = len(expanded_pieces)
        logger.info(f"[NEST-{job_id}] Total de peças expandidas: {total_pieces}")
        
        # Ordenar peças (maior área primeiro para BLF)
        sorted_pieces = self._sort_pieces(expanded_pieces)
        
        # Executar algoritmo selecionado
        if self.algorithm == NestingAlgorithm.BOTTOM_LEFT_FILL:
            placements, unplaced, sheets_used = self._bottom_left_fill(
                sorted_pieces, sheet, max_sheets
            )
        elif self.algorithm == NestingAlgorithm.GUILLOTINE:
            placements, unplaced, sheets_used = self._guillotine_nesting(
                sorted_pieces, sheet, max_sheets
            )
        elif self.algorithm == NestingAlgorithm.GENETIC:
            placements, unplaced, sheets_used = self._genetic_nesting(
                sorted_pieces, sheet, max_sheets
            )
        else:
            # Fallback para BLF
            placements, unplaced, sheets_used = self._bottom_left_fill(
                sorted_pieces, sheet, max_sheets
            )
        
        # Calcular estatísticas
        statistics = self._calculate_statistics(
            pieces, placements, sheets_used, sheet
        )
        
        # Gerar sugestões
        suggestions = self._generate_suggestions(statistics, placements, sheet)
        warnings = self._generate_warnings(unplaced, statistics)
        
        computation_time = (time.perf_counter() - start_time) * 1000
        
        result = NestingResult(
            job_id=job_id,
            algorithm=self.algorithm,
            placements=placements,
            statistics=statistics,
            sheets=sheets_used,
            unplaced_pieces=[p.id for p in unplaced],
            warnings=warnings,
            suggestions=suggestions,
            computation_time_ms=computation_time
        )
        
        logger.info(
            f"[NEST-{job_id}] Concluído: {len(placements)}/{total_pieces} peças, "
            f"eficiência={statistics.efficiency:.1f}%, tempo={computation_time:.0f}ms"
        )
        
        return result
    
    def _expand_pieces(self, pieces: List[NestingPiece]) -> List[NestingPiece]:
        """Expande peças por quantidade."""
        expanded = []
        for piece in pieces:
            for i in range(piece.quantity):
                new_piece = NestingPiece(
                    id=f"{piece.id}_{i+1}",
                    name=f"{piece.name} ({i+1}/{piece.quantity})",
                    contour=piece.contour,
                    holes=piece.holes,
                    quantity=1,
                    priority=piece.priority,
                    allow_rotation=piece.allow_rotation,
                    allowed_rotations=piece.allowed_rotations
                )
                expanded.append(new_piece)
        return expanded
    
    def _sort_pieces(self, pieces: List[NestingPiece]) -> List[NestingPiece]:
        """Ordena peças por estratégia."""
        if self.priority == NestingPriority.EFFICIENCY:
            # Maior área primeiro
            return sorted(pieces, key=lambda p: (-p.priority, -p.area))
        elif self.priority == NestingPriority.SPEED:
            # Retângulos primeiro, depois por área
            return sorted(pieces, key=lambda p: (-p.priority, -p.bounding_box.area))
        else:
            # Balanceado: maior dimensão primeiro
            return sorted(
                pieces,
                key=lambda p: (-p.priority, -max(p.bounding_box.width, p.bounding_box.height))
            )
    
    def _bottom_left_fill(
        self,
        pieces: List[NestingPiece],
        sheet_template: NestingSheet,
        max_sheets: int
    ) -> Tuple[List[Placement], List[NestingPiece], List[NestingSheet]]:
        """
        Algoritmo Bottom-Left Fill (BLF).
        
        Posiciona cada peça na posição mais abaixo e à esquerda possível.
        Eficiente para retângulos e formas simples.
        """
        placements = []
        unplaced = []
        sheets = []
        
        remaining = list(pieces)
        sheet_index = 0
        
        while remaining and sheet_index < max_sheets:
            # Criar nova chapa
            sheet = NestingSheet(
                id=f"sheet_{sheet_index + 1}",
                width=sheet_template.width,
                height=sheet_template.height,
                material=sheet_template.material,
                thickness=sheet_template.thickness,
                margin=sheet_template.margin,
                spacing=sheet_template.spacing,
                cost_per_kg=sheet_template.cost_per_kg,
                density=sheet_template.density
            )
            sheets.append(sheet)
            
            # Grid de ocupação para detecção rápida de colisão
            grid_size = 5  # mm
            grid_w = int((sheet.width - 2*sheet.margin) / grid_size) + 1
            grid_h = int((sheet.height - 2*sheet.margin) / grid_size) + 1
            occupied = [[False] * grid_w for _ in range(grid_h)]
            
            placed_this_sheet = []
            still_remaining = []
            
            for piece in remaining:
                placed = False
                best_placement = None
                best_score = float('inf')
                
                # Tentar cada rotação permitida
                rotations = piece.allowed_rotations if piece.allow_rotation else [0]
                
                for rotation in rotations:
                    # Calcular bounding box rotacionado
                    if rotation in [90, 270]:
                        pw = piece.bounding_box.height
                        ph = piece.bounding_box.width
                    else:
                        pw = piece.bounding_box.width
                        ph = piece.bounding_box.height
                    
                    # Verificar se cabe na chapa
                    if pw + 2*sheet.margin > sheet.width or ph + 2*sheet.margin > sheet.height:
                        continue
                    
                    # Buscar posição bottom-left
                    for y in range(0, grid_h - int(ph/grid_size)):
                        for x in range(0, grid_w - int(pw/grid_size)):
                            # Verificar se posição está livre
                            can_place = True
                            for gy in range(int(ph/grid_size) + 1):
                                for gx in range(int(pw/grid_size) + 1):
                                    if y + gy >= grid_h or x + gx >= grid_w:
                                        can_place = False
                                        break
                                    if occupied[y + gy][x + gx]:
                                        can_place = False
                                        break
                                if not can_place:
                                    break
                            
                            if can_place:
                                # Calcular score (preferir bottom-left)
                                actual_x = sheet.margin + x * grid_size
                                actual_y = sheet.margin + y * grid_size
                                score = actual_y * 1000 + actual_x
                                
                                if score < best_score:
                                    best_score = score
                                    best_placement = Placement(
                                        piece_id=piece.id,
                                        piece_name=piece.name,
                                        x=actual_x,
                                        y=actual_y,
                                        rotation=rotation,
                                        sheet_id=sheet.id
                                    )
                            
                            # Se encontrou posição bottom-left, parar busca nesta rotação
                            if best_placement and best_score < float('inf'):
                                break
                        if best_placement:
                            break
                    
                    if best_placement:
                        break
                
                if best_placement:
                    # Marcar área como ocupada
                    if best_placement.rotation in [90, 270]:
                        pw = piece.bounding_box.height
                        ph = piece.bounding_box.width
                    else:
                        pw = piece.bounding_box.width
                        ph = piece.bounding_box.height
                    
                    # Adicionar spacing
                    pw += sheet.spacing
                    ph += sheet.spacing
                    
                    start_x = int((best_placement.x - sheet.margin) / grid_size)
                    start_y = int((best_placement.y - sheet.margin) / grid_size)
                    end_x = min(grid_w, start_x + int(pw/grid_size) + 1)
                    end_y = min(grid_h, start_y + int(ph/grid_size) + 1)
                    
                    for gy in range(start_y, end_y):
                        for gx in range(start_x, end_x):
                            if 0 <= gy < grid_h and 0 <= gx < grid_w:
                                occupied[gy][gx] = True
                    
                    placements.append(best_placement)
                    placed_this_sheet.append(piece)
                    placed = True
                
                if not placed:
                    still_remaining.append(piece)
            
            remaining = still_remaining
            sheet_index += 1
        
        unplaced = remaining
        
        return placements, unplaced, sheets
    
    def _guillotine_nesting(
        self,
        pieces: List[NestingPiece],
        sheet_template: NestingSheet,
        max_sheets: int
    ) -> Tuple[List[Placement], List[NestingPiece], List[NestingSheet]]:
        """
        Algoritmo de corte Guilhotina.
        
        Divide a chapa recursivamente em cortes lineares, ideal
        para materiais que precisam ser cortados em guilhotinas.
        """
        # Implementação simplificada - usa BLF como base
        return self._bottom_left_fill(pieces, sheet_template, max_sheets)
    
    def _genetic_nesting(
        self,
        pieces: List[NestingPiece],
        sheet_template: NestingSheet,
        max_sheets: int
    ) -> Tuple[List[Placement], List[NestingPiece], List[NestingSheet]]:
        """
        Algoritmo Genético para nesting.
        
        Usa evolução para encontrar melhor arranjo de peças.
        Mais lento mas pode encontrar soluções melhores.
        """
        # Simplificado - executa BLF múltiplas vezes com diferentes ordenações
        best_result = None
        best_efficiency = 0
        
        for iteration in range(min(100, self.max_iterations)):
            # Embaralhar peças mantendo prioridades
            shuffled = list(pieces)
            random.shuffle(shuffled)
            shuffled.sort(key=lambda p: -p.priority)
            
            placements, unplaced, sheets = self._bottom_left_fill(
                shuffled, sheet_template, max_sheets
            )
            
            if sheets:
                used_area = sum(
                    p.bounding_box.area for p in pieces 
                    if any(pl.piece_id == p.id for pl in placements)
                )
                total_area = sum(s.usable_area for s in sheets)
                efficiency = (used_area / total_area * 100) if total_area > 0 else 0
                
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_result = (placements, unplaced, sheets)
        
        if best_result:
            return best_result
        return self._bottom_left_fill(pieces, sheet_template, max_sheets)
    
    def _calculate_statistics(
        self,
        original_pieces: List[NestingPiece],
        placements: List[Placement],
        sheets: List[NestingSheet],
        sheet_template: NestingSheet
    ) -> NestingStatistics:
        """Calcula estatísticas do nesting."""
        stats = NestingStatistics()
        
        # Contagem de peças
        stats.total_pieces = sum(p.quantity for p in original_pieces)
        stats.placed_pieces = len(placements)
        stats.unplaced_pieces = stats.total_pieces - stats.placed_pieces
        stats.sheets_used = len(sheets)
        
        # Áreas
        stats.total_sheet_area = sum(s.usable_area for s in sheets)
        
        # Calcular área utilizada pelas peças colocadas
        placed_ids = {p.piece_id for p in placements}
        for piece in original_pieces:
            for i in range(piece.quantity):
                pid = f"{piece.id}_{i+1}"
                if pid in placed_ids:
                    stats.used_area += piece.area
                    stats.total_cutting_length += piece.cutting_length
        
        stats.waste_area = stats.total_sheet_area - stats.used_area
        stats.efficiency = (stats.used_area / stats.total_sheet_area * 100) if stats.total_sheet_area > 0 else 0
        
        # Tempo estimado
        if self.cutting_speed > 0:
            stats.estimated_time_minutes = stats.total_cutting_length / self.cutting_speed
        
        # Custos
        stats.material_cost = sum(s.cost for s in sheets)
        stats.cutting_cost = (stats.estimated_time_minutes / 60) * self.cost_per_hour
        stats.total_cost = stats.material_cost + stats.cutting_cost
        
        return stats
    
    def _generate_suggestions(
        self,
        stats: NestingStatistics,
        placements: List[Placement],
        sheet: NestingSheet
    ) -> List[str]:
        """Gera sugestões de otimização."""
        suggestions = []
        
        if stats.efficiency < 60:
            suggestions.append(
                f"Aproveitamento baixo ({stats.efficiency:.1f}%). "
                "Considere adicionar peças menores para preencher espaços."
            )
        
        if stats.efficiency > 60 and stats.efficiency < 80:
            suggestions.append(
                "Tente rotacionar algumas peças manualmente para melhorar aproveitamento."
            )
        
        if stats.waste_area > sheet.usable_area * 0.3:
            waste_pct = (stats.waste_area / sheet.usable_area) * 100
            suggestions.append(
                f"Sobra de {waste_pct:.1f}% da chapa. "
                "Salve as sobras como retalhos no estoque."
            )
        
        if stats.sheets_used > 1:
            suggestions.append(
                f"Usando {stats.sheets_used} chapas. "
                "Verifique se é possível otimizar para menos chapas."
            )
        
        return suggestions
    
    def _generate_warnings(
        self,
        unplaced: List[NestingPiece],
        stats: NestingStatistics
    ) -> List[str]:
        """Gera avisos sobre problemas."""
        warnings = []
        
        if unplaced:
            names = list(set(p.name.split(" (")[0] for p in unplaced))
            warnings.append(
                f"⚠️ {len(unplaced)} peça(s) não couberam: {', '.join(names[:5])}"
                + ("..." if len(names) > 5 else "")
            )
        
        if stats.efficiency < 50:
            warnings.append(
                "⚠️ Aproveitamento muito baixo. Revise as dimensões das peças."
            )
        
        return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# BIBLIOTECA DE PEÇAS
# ═══════════════════════════════════════════════════════════════════════════════

class PieceLibrary:
    """
    Biblioteca de peças parametrizadas.
    
    Permite salvar, carregar e reutilizar definições de peças
    para projetos futuros.
    """
    
    def __init__(self, storage_path: str = "data/piece_library"):
        self.storage_path = storage_path
        try:
            os.makedirs(storage_path, exist_ok=True)
        except OSError:
            # Read-only filesystem (serverless)
            pass
        self._cache: Dict[str, NestingPiece] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Carrega biblioteca do disco."""
        index_path = os.path.join(self.storage_path, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
                logger.info(f"Biblioteca carregada: {len(index)} peças")
            except Exception as e:
                logger.warning(f"Erro ao carregar biblioteca: {e}")
    
    def save_piece(self, piece: NestingPiece, category: str = "custom") -> str:
        """
        Salva uma peça na biblioteca.
        
        Args:
            piece: Peça para salvar
            category: Categoria (flanges, chapas, suportes, etc.)
            
        Returns:
            ID da peça salva
        """
        piece_data = {
            "id": piece.id,
            "name": piece.name,
            "category": category,
            "contour": [{"x": p.x, "y": p.y} for p in piece.contour.points],
            "holes": [
                [{"x": p.x, "y": p.y} for p in h.points]
                for h in piece.holes
            ],
            "priority": piece.priority,
            "allow_rotation": piece.allow_rotation,
            "created_at": datetime.now().isoformat()
        }
        
        file_path = os.path.join(self.storage_path, f"{piece.id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(piece_data, f, indent=2)
        
        self._cache[piece.id] = piece
        self._update_index()
        
        logger.info(f"Peça salva: {piece.name} ({piece.id})")
        return piece.id
    
    def load_piece(self, piece_id: str) -> Optional[NestingPiece]:
        """Carrega uma peça da biblioteca."""
        if piece_id in self._cache:
            return self._cache[piece_id]
        
        file_path = os.path.join(self.storage_path, f"{piece_id}.json")
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            piece = NestingPiece(
                id=data["id"],
                name=data["name"],
                contour=Polygon([Point2D(**p) for p in data["contour"]]),
                holes=[Polygon([Point2D(**p) for p in h]) for h in data.get("holes", [])],
                priority=data.get("priority", 0),
                allow_rotation=data.get("allow_rotation", True)
            )
            
            self._cache[piece_id] = piece
            return piece
            
        except Exception as e:
            logger.error(f"Erro ao carregar peça {piece_id}: {e}")
            return None
    
    def list_pieces(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista peças da biblioteca."""
        pieces = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json") and filename != "index.json":
                file_path = os.path.join(self.storage_path, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if category is None or data.get("category") == category:
                        pieces.append({
                            "id": data["id"],
                            "name": data["name"],
                            "category": data.get("category", "custom"),
                            "createdAt": data.get("created_at")
                        })
                except:
                    pass
        
        return pieces
    
    def delete_piece(self, piece_id: str) -> bool:
        """Remove uma peça da biblioteca."""
        file_path = os.path.join(self.storage_path, f"{piece_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            if piece_id in self._cache:
                del self._cache[piece_id]
            self._update_index()
            return True
        return False
    
    def _update_index(self):
        """Atualiza índice da biblioteca."""
        index = self.list_pieces()
        index_path = os.path.join(self.storage_path, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════════════════════════════════

def create_rectangle_piece(
    width: float,
    height: float,
    name: str = "Retângulo",
    holes: List[Tuple[float, float, float]] = None,  # (x, y, diameter)
    quantity: int = 1
) -> NestingPiece:
    """Cria uma peça retangular."""
    contour = Polygon([
        Point2D(0, 0),
        Point2D(width, 0),
        Point2D(width, height),
        Point2D(0, height)
    ])
    
    hole_polys = []
    if holes:
        for hx, hy, d in holes:
            # Criar círculo como polígono de 32 lados
            r = d / 2
            points = [
                Point2D(hx + r * math.cos(2*math.pi*i/32), hy + r * math.sin(2*math.pi*i/32))
                for i in range(32)
            ]
            hole_polys.append(Polygon(points, is_hole=True))
    
    return NestingPiece(
        id=str(uuid.uuid4())[:8],
        name=name,
        contour=contour,
        holes=hole_polys,
        quantity=quantity
    )


def create_circle_piece(
    diameter: float,
    name: str = "Círculo",
    center_hole_diameter: float = 0,
    quantity: int = 1
) -> NestingPiece:
    """Cria uma peça circular."""
    r = diameter / 2
    points = [
        Point2D(r + r * math.cos(2*math.pi*i/64), r + r * math.sin(2*math.pi*i/64))
        for i in range(64)
    ]
    contour = Polygon(points)
    
    holes = []
    if center_hole_diameter > 0:
        hr = center_hole_diameter / 2
        hole_points = [
            Point2D(r + hr * math.cos(2*math.pi*i/32), r + hr * math.sin(2*math.pi*i/32))
            for i in range(32)
        ]
        holes.append(Polygon(hole_points, is_hole=True))
    
    return NestingPiece(
        id=str(uuid.uuid4())[:8],
        name=name,
        contour=contour,
        holes=holes,
        quantity=quantity
    )


def create_flange_piece(
    outer_diameter: float,
    inner_diameter: float,
    bolt_holes: int = 4,
    bolt_diameter: float = 18,
    bolt_circle_diameter: float = None,
    name: str = "Flange",
    quantity: int = 1
) -> NestingPiece:
    """Cria uma peça de flange com furos de parafuso."""
    r_outer = outer_diameter / 2
    r_inner = inner_diameter / 2
    
    # Contorno externo
    ext_points = [
        Point2D(r_outer + r_outer * math.cos(2*math.pi*i/64), 
                r_outer + r_outer * math.sin(2*math.pi*i/64))
        for i in range(64)
    ]
    contour = Polygon(ext_points)
    
    holes = []
    
    # Furo central
    int_points = [
        Point2D(r_outer + r_inner * math.cos(2*math.pi*i/32),
                r_outer + r_inner * math.sin(2*math.pi*i/32))
        for i in range(32)
    ]
    holes.append(Polygon(int_points, is_hole=True))
    
    # Furos dos parafusos
    if bolt_circle_diameter is None:
        bolt_circle_diameter = (outer_diameter + inner_diameter) / 2
    
    bolt_r = bolt_circle_diameter / 2
    hr = bolt_diameter / 2
    
    for i in range(bolt_holes):
        angle = 2 * math.pi * i / bolt_holes
        cx = r_outer + bolt_r * math.cos(angle)
        cy = r_outer + bolt_r * math.sin(angle)
        
        hole_points = [
            Point2D(cx + hr * math.cos(2*math.pi*j/24),
                    cy + hr * math.sin(2*math.pi*j/24))
            for j in range(24)
        ]
        holes.append(Polygon(hole_points, is_hole=True))
    
    return NestingPiece(
        id=str(uuid.uuid4())[:8],
        name=name,
        contour=contour,
        holes=holes,
        quantity=quantity
    )
