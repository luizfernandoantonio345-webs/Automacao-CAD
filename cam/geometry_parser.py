"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Parser de Geometria DXF/SVG
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Responsável por:
- Importar arquivos DXF e SVG
- Extrair entidades geométricas (linhas, arcos, polilinhas, círculos)
- Normalizar coordenadas para o sistema de referência da máquina
- Detectar contornos fechados e hierarquia (interno/externo)
"""

from __future__ import annotations

import logging
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union, Any
from enum import Enum

# Tenta importar ezdxf, mas funciona sem ele usando parser embutido
# Nota: Python 3.14+ pode ter problemas de compatibilidade, por isso capturamos Exception
try:
    import ezdxf
    EZDXF_AVAILABLE = True
except Exception:
    # ImportError, ModuleNotFoundError, ou erros de compatibilidade Python 3.14+
    ezdxf = None  # type: ignore
    EZDXF_AVAILABLE = False

logger = logging.getLogger("engcad.cam.geometry_parser")


class GeometryType(Enum):
    """Tipos de entidades geométricas suportadas."""
    LINE = "line"
    ARC = "arc"
    CIRCLE = "circle"
    POLYLINE = "polyline"
    SPLINE = "spline"


@dataclass
class Point:
    """Ponto 2D/3D."""
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: "Point") -> float:
        """Calcula distância euclidiana até outro ponto."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def to_tuple(self) -> Tuple[float, float]:
        """Retorna tupla (x, y)."""
        return (self.x, self.y)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return False
        tolerance = 0.001  # 1 micrômetro
        return (
            abs(self.x - other.x) < tolerance and
            abs(self.y - other.y) < tolerance and
            abs(self.z - other.z) < tolerance
        )
    
    def __hash__(self) -> int:
        return hash((round(self.x, 3), round(self.y, 3), round(self.z, 3)))


@dataclass
class Line:
    """Segmento de linha."""
    start: Point
    end: Point
    layer: str = "0"
    
    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)
    
    @property
    def midpoint(self) -> Point:
        return Point(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
            (self.start.z + self.end.z) / 2
        )


@dataclass
class Arc:
    """Arco de círculo."""
    center: Point
    radius: float
    start_angle: float  # graus
    end_angle: float    # graus
    layer: str = "0"
    clockwise: bool = False
    
    @property
    def start_point(self) -> Point:
        """Ponto inicial do arco."""
        rad = math.radians(self.start_angle)
        return Point(
            self.center.x + self.radius * math.cos(rad),
            self.center.y + self.radius * math.sin(rad),
            self.center.z
        )
    
    @property
    def end_point(self) -> Point:
        """Ponto final do arco."""
        rad = math.radians(self.end_angle)
        return Point(
            self.center.x + self.radius * math.cos(rad),
            self.center.y + self.radius * math.sin(rad),
            self.center.z
        )
    
    @property
    def arc_length(self) -> float:
        """Comprimento do arco."""
        angle_diff = abs(self.end_angle - self.start_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return math.radians(angle_diff) * self.radius


@dataclass
class Circle:
    """Círculo completo."""
    center: Point
    radius: float
    layer: str = "0"
    
    @property
    def circumference(self) -> float:
        return 2 * math.pi * self.radius
    
    @property
    def area(self) -> float:
        return math.pi * self.radius ** 2


@dataclass
class Polyline:
    """Polilinha (sequência de pontos conectados)."""
    points: List[Point] = field(default_factory=list)
    closed: bool = False
    layer: str = "0"
    bulges: List[float] = field(default_factory=list)  # Para arcos em polilinhas
    
    @property
    def is_closed(self) -> bool:
        """Verifica se a polilinha é fechada."""
        if self.closed:
            return True
        if len(self.points) >= 3:
            return self.points[0] == self.points[-1]
        return False
    
    @property
    def length(self) -> float:
        """Comprimento total da polilinha."""
        total = 0.0
        for i in range(len(self.points) - 1):
            total += self.points[i].distance_to(self.points[i + 1])
        if self.closed and self.points:
            total += self.points[-1].distance_to(self.points[0])
        return total
    
    @property
    def bounding_box(self) -> Tuple[Point, Point]:
        """Retorna bounding box (min, max)."""
        if not self.points:
            return (Point(0, 0), Point(0, 0))
        
        min_x = min(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        max_x = max(p.x for p in self.points)
        max_y = max(p.y for p in self.points)
        
        return (Point(min_x, min_y), Point(max_x, max_y))
    
    @property
    def centroid(self) -> Point:
        """Calcula centróide da polilinha."""
        if not self.points:
            return Point(0, 0)
        
        sum_x = sum(p.x for p in self.points)
        sum_y = sum(p.y for p in self.points)
        n = len(self.points)
        
        return Point(sum_x / n, sum_y / n)
    
    def area(self) -> float:
        """Calcula área (fórmula do cadarço) - só válido para polilinhas fechadas."""
        if not self.is_closed or len(self.points) < 3:
            return 0.0
        
        n = len(self.points)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        
        return abs(area) / 2.0
    
    def is_inside(self, other: "Polyline") -> bool:
        """Verifica se esta polilinha está dentro de outra (ray casting)."""
        if not self.is_closed or not other.is_closed:
            return False
        
        # Usa o centróide como ponto de teste
        test_point = self.centroid
        return other.contains_point(test_point)
    
    def contains_point(self, point: Point) -> bool:
        """Verifica se um ponto está dentro da polilinha (ray casting algorithm)."""
        if not self.is_closed:
            return False
        
        n = len(self.points)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = self.points[i].x, self.points[i].y
            xj, yj = self.points[j].x, self.points[j].y
            
            if ((yi > point.y) != (yj > point.y)) and \
               (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside


@dataclass
class Geometry:
    """Container para todas as geometrias de um desenho."""
    lines: List[Line] = field(default_factory=list)
    arcs: List[Arc] = field(default_factory=list)
    circles: List[Circle] = field(default_factory=list)
    polylines: List[Polyline] = field(default_factory=list)
    
    # Metadados
    filename: str = ""
    units: str = "mm"
    bounding_box: Optional[Tuple[Point, Point]] = None
    
    @property
    def total_entities(self) -> int:
        return len(self.lines) + len(self.arcs) + len(self.circles) + len(self.polylines)
    
    @property
    def has_geometry(self) -> bool:
        return self.total_entities > 0
    
    def calculate_bounding_box(self) -> Tuple[Point, Point]:
        """Calcula bounding box de todas as geometrias."""
        all_points: List[Point] = []
        
        for line in self.lines:
            all_points.extend([line.start, line.end])
        
        for arc in self.arcs:
            all_points.extend([arc.start_point, arc.end_point])
        
        for circle in self.circles:
            all_points.extend([
                Point(circle.center.x - circle.radius, circle.center.y - circle.radius),
                Point(circle.center.x + circle.radius, circle.center.y + circle.radius)
            ])
        
        for polyline in self.polylines:
            all_points.extend(polyline.points)
        
        if not all_points:
            return (Point(0, 0), Point(0, 0))
        
        min_x = min(p.x for p in all_points)
        min_y = min(p.y for p in all_points)
        max_x = max(p.x for p in all_points)
        max_y = max(p.y for p in all_points)
        
        self.bounding_box = (Point(min_x, min_y), Point(max_x, max_y))
        return self.bounding_box


class GeometryParser:
    """Parser de geometria para arquivos DXF e SVG."""
    
    SUPPORTED_FORMATS = [".dxf", ".svg"]
    
    def __init__(self, tolerance: float = 0.01):
        """
        Inicializa o parser.
        
        Args:
            tolerance: Tolerância para conexão de pontos (mm)
        """
        self.tolerance = tolerance
    
    def parse(self, file_path: Union[str, Path]) -> Geometry:
        """
        Parse um arquivo de geometria.
        
        Args:
            file_path: Caminho para o arquivo DXF ou SVG
            
        Returns:
            Geometry: Objeto contendo todas as geometrias extraídas
            
        Raises:
            ValueError: Se o formato não for suportado
            FileNotFoundError: Se o arquivo não existir
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix == ".dxf":
            return self._parse_dxf(path)
        elif suffix == ".svg":
            return self._parse_svg(path)
        else:
            raise ValueError(
                f"Formato não suportado: {suffix}. "
                f"Formatos aceitos: {', '.join(self.SUPPORTED_FORMATS)}"
            )
    
    def parse_from_data(self, data: dict) -> Geometry:
        """
        Parse geometria a partir de dados JSON (do CAD interno).
        
        Args:
            data: Dict com estrutura {lines: [], arcs: [], circles: [], polylines: []}
            
        Returns:
            Geometry: Objeto contendo todas as geometrias
        """
        geometry = Geometry()
        
        # Processar linhas
        for line_data in data.get("lines", []):
            geometry.lines.append(Line(
                start=Point(**line_data["start"]),
                end=Point(**line_data["end"]),
                layer=line_data.get("layer", "0")
            ))
        
        # Processar arcos
        for arc_data in data.get("arcs", []):
            geometry.arcs.append(Arc(
                center=Point(**arc_data["center"]),
                radius=arc_data["radius"],
                start_angle=arc_data["start_angle"],
                end_angle=arc_data["end_angle"],
                layer=arc_data.get("layer", "0"),
                clockwise=arc_data.get("clockwise", False)
            ))
        
        # Processar círculos
        for circle_data in data.get("circles", []):
            geometry.circles.append(Circle(
                center=Point(**circle_data["center"]),
                radius=circle_data["radius"],
                layer=circle_data.get("layer", "0")
            ))
        
        # Processar polilinhas
        for poly_data in data.get("polylines", []):
            points = [Point(**p) for p in poly_data.get("points", [])]
            geometry.polylines.append(Polyline(
                points=points,
                closed=poly_data.get("closed", False),
                layer=poly_data.get("layer", "0")
            ))
        
        geometry.calculate_bounding_box()
        return geometry
    
    def _parse_dxf(self, path: Path) -> Geometry:
        """Parse arquivo DXF usando ezdxf ou parser embutido."""
        logger.info(f"Parseando DXF: {path}")
        
        if EZDXF_AVAILABLE:
            return self._parse_dxf_ezdxf(path)
        else:
            logger.info("ezdxf não disponível, usando parser DXF embutido")
            return self._parse_dxf_builtin(path)
    
    def _parse_dxf_builtin(self, path: Path) -> Geometry:
        """Parser DXF embutido simples (sem dependências externas)."""
        geometry = Geometry(filename=path.name, units="mm")
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"Erro ao ler arquivo DXF: {e}")
        
        # Dividir em linhas e processar pares código/valor
        lines = content.split('\n')
        i = 0
        entities_section = False
        current_entity = None
        entity_data: dict = {}
        
        while i < len(lines) - 1:
            try:
                code = int(lines[i].strip())
                value = lines[i + 1].strip()
            except (ValueError, IndexError):
                i += 1
                continue
            
            # Detectar seção ENTITIES
            if code == 2 and value.upper() == "ENTITIES":
                entities_section = True
                i += 2
                continue
            elif code == 0 and value.upper() == "ENDSEC" and entities_section:
                # Finalizar última entidade
                if current_entity:
                    self._process_builtin_entity(current_entity, entity_data, geometry)
                break
            
            if entities_section:
                if code == 0:
                    # Nova entidade - processar a anterior
                    if current_entity:
                        self._process_builtin_entity(current_entity, entity_data, geometry)
                    current_entity = value.upper()
                    entity_data = {"layer": "0"}
                else:
                    # Dado da entidade atual
                    if current_entity:
                        if code == 8:  # Layer
                            entity_data["layer"] = value
                        elif code == 10:
                            entity_data["x1"] = float(value)
                        elif code == 11:
                            entity_data["x2"] = float(value)
                        elif code == 20:
                            entity_data["y1"] = float(value)
                        elif code == 21:
                            entity_data["y2"] = float(value)
                        elif code == 30:
                            entity_data["z1"] = float(value)
                        elif code == 31:
                            entity_data["z2"] = float(value)
                        elif code == 40:
                            entity_data["radius"] = float(value)
                        elif code == 50:
                            entity_data["start_angle"] = float(value)
                        elif code == 51:
                            entity_data["end_angle"] = float(value)
                        elif code == 70:
                            entity_data["flags"] = int(value)
            
            i += 2
        
        geometry.calculate_bounding_box()
        logger.info(
            f"DXF parseado (parser embutido): {geometry.total_entities} entidades "
            f"({len(geometry.lines)} linhas, {len(geometry.arcs)} arcos, "
            f"{len(geometry.circles)} círculos, {len(geometry.polylines)} polilinhas)"
        )
        
        return geometry
    
    def _process_builtin_entity(self, entity_type: str, data: dict, geometry: Geometry) -> None:
        """Processa entidade do parser DXF embutido."""
        layer = data.get("layer", "0")
        
        if entity_type == "LINE":
            x1 = data.get("x1", 0)
            y1 = data.get("y1", 0)
            x2 = data.get("x2", 0)
            y2 = data.get("y2", 0)
            geometry.lines.append(Line(
                start=Point(x1, y1),
                end=Point(x2, y2),
                layer=layer
            ))
        
        elif entity_type == "CIRCLE":
            cx = data.get("x1", 0)
            cy = data.get("y1", 0)
            r = data.get("radius", 0)
            geometry.circles.append(Circle(
                center=Point(cx, cy),
                radius=r,
                layer=layer
            ))
        
        elif entity_type == "ARC":
            cx = data.get("x1", 0)
            cy = data.get("y1", 0)
            r = data.get("radius", 0)
            start_angle = data.get("start_angle", 0)
            end_angle = data.get("end_angle", 360)
            geometry.arcs.append(Arc(
                center=Point(cx, cy),
                radius=r,
                start_angle=start_angle,
                end_angle=end_angle,
                layer=layer
            ))
    
    def _parse_dxf_ezdxf(self, path: Path) -> Geometry:
        """Parse arquivo DXF usando ezdxf (biblioteca externa)."""
        try:
            doc = ezdxf.readfile(str(path))
        except Exception as e:
            logger.error(f"Erro ao ler DXF: {e}")
            raise ValueError(f"Erro ao ler arquivo DXF: {e}")
        
        geometry = Geometry(filename=path.name)
        msp = doc.modelspace()
        
        # Detectar unidades
        if doc.header.get("$INSUNITS", 0) == 4:
            geometry.units = "mm"
        elif doc.header.get("$INSUNITS", 0) == 1:
            geometry.units = "inch"
        
        for entity in msp:
            self._process_dxf_entity(entity, geometry)
        
        geometry.calculate_bounding_box()
        logger.info(
            f"DXF parseado: {geometry.total_entities} entidades "
            f"({len(geometry.lines)} linhas, {len(geometry.arcs)} arcos, "
            f"{len(geometry.circles)} círculos, {len(geometry.polylines)} polilinhas)"
        )
        
        return geometry
    
    def _process_dxf_entity(self, entity: Any, geometry: Geometry) -> None:
        """Processa uma entidade DXF individual."""
        dxftype = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "0")
        
        if dxftype == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            geometry.lines.append(Line(
                start=Point(start.x, start.y, start.z if hasattr(start, 'z') else 0),
                end=Point(end.x, end.y, end.z if hasattr(end, 'z') else 0),
                layer=layer
            ))
        
        elif dxftype == "ARC":
            geometry.arcs.append(Arc(
                center=Point(entity.dxf.center.x, entity.dxf.center.y),
                radius=entity.dxf.radius,
                start_angle=entity.dxf.start_angle,
                end_angle=entity.dxf.end_angle,
                layer=layer
            ))
        
        elif dxftype == "CIRCLE":
            geometry.circles.append(Circle(
                center=Point(entity.dxf.center.x, entity.dxf.center.y),
                radius=entity.dxf.radius,
                layer=layer
            ))
        
        elif dxftype in ("LWPOLYLINE", "POLYLINE"):
            points = []
            bulges = []
            
            if hasattr(entity, "get_points"):
                # LWPOLYLINE
                for x, y, start_width, end_width, bulge in entity.get_points("xyseb"):
                    points.append(Point(x, y))
                    bulges.append(bulge)
            elif hasattr(entity, "vertices"):
                # POLYLINE 2D/3D
                for vertex in entity.vertices:
                    loc = vertex.dxf.location
                    points.append(Point(loc.x, loc.y, loc.z if hasattr(loc, 'z') else 0))
                    bulges.append(getattr(vertex.dxf, "bulge", 0))
            
            if points:
                geometry.polylines.append(Polyline(
                    points=points,
                    closed=entity.is_closed if hasattr(entity, "is_closed") else False,
                    layer=layer,
                    bulges=bulges
                ))
        
        elif dxftype == "SPLINE":
            # Converter spline para polilinha aproximada
            try:
                points = []
                for point in entity.flattening(0.1):  # Tolerância de 0.1mm
                    points.append(Point(point.x, point.y))
                
                if points:
                    geometry.polylines.append(Polyline(
                        points=points,
                        closed=entity.closed if hasattr(entity, "closed") else False,
                        layer=layer
                    ))
            except Exception as e:
                logger.warning(f"Não foi possível converter SPLINE: {e}")
        
        elif dxftype == "ELLIPSE":
            # Converter elipse para polilinha aproximada
            try:
                points = []
                for point in entity.flattening(0.1):
                    points.append(Point(point.x, point.y))
                
                if points:
                    geometry.polylines.append(Polyline(
                        points=points,
                        closed=True,
                        layer=layer
                    ))
            except Exception as e:
                logger.warning(f"Não foi possível converter ELLIPSE: {e}")
    
    def _parse_svg(self, path: Path) -> Geometry:
        """Parse arquivo SVG."""
        logger.info(f"Parseando SVG: {path}")
        
        try:
            tree = ET.parse(str(path))
            root = tree.getroot()
        except Exception as e:
            logger.error(f"Erro ao ler SVG: {e}")
            raise ValueError(f"Erro ao ler arquivo SVG: {e}")
        
        geometry = Geometry(filename=path.name)
        
        # Namespace do SVG
        ns = {"svg": "http://www.w3.org/2000/svg"}
        
        # Processar elementos
        self._process_svg_element(root, geometry, ns)
        
        geometry.calculate_bounding_box()
        logger.info(f"SVG parseado: {geometry.total_entities} entidades")
        
        return geometry
    
    def _process_svg_element(self, element: ET.Element, geometry: Geometry, ns: dict) -> None:
        """Processa elementos SVG recursivamente."""
        tag = element.tag.replace(f"{{{ns['svg']}}}", "").lower()
        
        if tag == "line":
            x1 = float(element.get("x1", 0))
            y1 = float(element.get("y1", 0))
            x2 = float(element.get("x2", 0))
            y2 = float(element.get("y2", 0))
            geometry.lines.append(Line(
                start=Point(x1, y1),
                end=Point(x2, y2)
            ))
        
        elif tag == "circle":
            cx = float(element.get("cx", 0))
            cy = float(element.get("cy", 0))
            r = float(element.get("r", 0))
            geometry.circles.append(Circle(
                center=Point(cx, cy),
                radius=r
            ))
        
        elif tag == "rect":
            x = float(element.get("x", 0))
            y = float(element.get("y", 0))
            w = float(element.get("width", 0))
            h = float(element.get("height", 0))
            
            # Converter retângulo em polilinha
            geometry.polylines.append(Polyline(
                points=[
                    Point(x, y),
                    Point(x + w, y),
                    Point(x + w, y + h),
                    Point(x, y + h),
                    Point(x, y)
                ],
                closed=True
            ))
        
        elif tag == "polygon":
            points_str = element.get("points", "")
            points = self._parse_svg_points(points_str)
            if points:
                geometry.polylines.append(Polyline(points=points, closed=True))
        
        elif tag == "polyline":
            points_str = element.get("points", "")
            points = self._parse_svg_points(points_str)
            if points:
                geometry.polylines.append(Polyline(points=points, closed=False))
        
        elif tag == "path":
            path_data = element.get("d", "")
            self._parse_svg_path(path_data, geometry)
        
        # Processar filhos
        for child in element:
            self._process_svg_element(child, geometry, ns)
    
    def _parse_svg_points(self, points_str: str) -> List[Point]:
        """Parse string de pontos SVG (x,y x,y ...)."""
        points = []
        
        # Limpar e dividir
        points_str = points_str.strip()
        if not points_str:
            return points
        
        # Dividir por espaço ou vírgula
        parts = re.split(r"[\s,]+", points_str)
        
        for i in range(0, len(parts) - 1, 2):
            try:
                x = float(parts[i])
                y = float(parts[i + 1])
                points.append(Point(x, y))
            except (ValueError, IndexError):
                continue
        
        return points
    
    def _parse_svg_path(self, path_data: str, geometry: Geometry) -> None:
        """Parse elemento path do SVG (comandos M, L, C, A, Z, etc.)."""
        if not path_data:
            return
        
        # Parser simplificado de path SVG
        commands = re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)", path_data)
        
        current_pos = Point(0, 0)
        start_pos = Point(0, 0)
        points: List[Point] = []
        
        for cmd, args in commands:
            args = args.strip()
            nums = [float(x) for x in re.findall(r"-?[\d.]+", args)]
            
            if cmd in "Mm":
                # Move to
                if points and len(points) >= 2:
                    geometry.polylines.append(Polyline(points=points[:], closed=False))
                
                if cmd == "M":
                    current_pos = Point(nums[0], nums[1]) if len(nums) >= 2 else current_pos
                else:
                    current_pos = Point(current_pos.x + nums[0], current_pos.y + nums[1]) if len(nums) >= 2 else current_pos
                
                start_pos = current_pos
                points = [current_pos]
            
            elif cmd in "Ll":
                # Line to
                if cmd == "L":
                    for i in range(0, len(nums) - 1, 2):
                        current_pos = Point(nums[i], nums[i + 1])
                        points.append(current_pos)
                else:
                    for i in range(0, len(nums) - 1, 2):
                        current_pos = Point(current_pos.x + nums[i], current_pos.y + nums[i + 1])
                        points.append(current_pos)
            
            elif cmd == "H":
                # Horizontal line absolute
                for x in nums:
                    current_pos = Point(x, current_pos.y)
                    points.append(current_pos)
            
            elif cmd == "h":
                # Horizontal line relative
                for dx in nums:
                    current_pos = Point(current_pos.x + dx, current_pos.y)
                    points.append(current_pos)
            
            elif cmd == "V":
                # Vertical line absolute
                for y in nums:
                    current_pos = Point(current_pos.x, y)
                    points.append(current_pos)
            
            elif cmd == "v":
                # Vertical line relative
                for dy in nums:
                    current_pos = Point(current_pos.x, current_pos.y + dy)
                    points.append(current_pos)
            
            elif cmd in "Zz":
                # Close path
                if points:
                    points.append(start_pos)
                    geometry.polylines.append(Polyline(points=points[:], closed=True))
                    points = []
                current_pos = start_pos
        
        # Adicionar última polilinha se houver
        if len(points) >= 2:
            geometry.polylines.append(Polyline(points=points, closed=False))
