"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Exportador DXF com Múltiplos Layers
Engenharia CAD - Exportação Profissional para AutoCAD
═══════════════════════════════════════════════════════════════════════════════

Gera arquivos DXF compatíveis com AutoCAD e outros softwares CAD.

Layers padrão:
- CONTORNOS: Contornos externos das peças
- FUROS: Furos e recortes internos
- NESTING: Layout do nesting na chapa
- ANOTACOES: Textos e dimensões
- TOOLPATH: Caminho de corte otimizado
- BORDER: Borda da chapa
- GRID: Grid de referência

Recursos:
- DXF R12 (compatibilidade máxima)
- DXF R2010 (features avançadas)
- Cores por layer
- Linetypes customizados
- Blocos para peças repetidas
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class DXFColor:
    """Cores padrão AutoCAD por índice."""
    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    WHITE = 7
    GRAY = 8
    LIGHT_GRAY = 9


class DXFLineType:
    """Tipos de linha padrão."""
    CONTINUOUS = "CONTINUOUS"
    CENTER = "CENTER"
    DASHED = "DASHED"
    HIDDEN = "HIDDEN"
    PHANTOM = "PHANTOM"


class DXFExporter:
    """
    Exportador de geometria para formato DXF.
    
    Suporta criação de arquivos DXF com múltiplos layers,
    cores, tipos de linha e anotações.
    """
    
    def __init__(self, version: str = "R12"):
        """
        Inicializa o exportador.
        
        Args:
            version: Versão do DXF ("R12" ou "R2010")
        """
        self.version = version
        self.entities: List[str] = []
        self.layers: Dict[str, Dict[str, Any]] = {}
        self.handle_counter = 256
        
    def _next_handle(self) -> str:
        """Gera próximo handle único."""
        h = hex(self.handle_counter)[2:].upper()
        self.handle_counter += 1
        return h
    
    def add_layer(
        self, 
        name: str, 
        color: int = DXFColor.WHITE, 
        linetype: str = DXFLineType.CONTINUOUS
    ):
        """Adiciona um layer ao DXF."""
        self.layers[name] = {
            "color": color,
            "linetype": linetype
        }
    
    def add_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        layer: str = "0"
    ):
        """Adiciona uma linha."""
        self.entities.append(self._format_line(start, end, layer))
    
    def add_circle(
        self,
        center: Tuple[float, float],
        radius: float,
        layer: str = "0"
    ):
        """Adiciona um círculo."""
        self.entities.append(self._format_circle(center, radius, layer))
    
    def add_arc(
        self,
        center: Tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str = "0"
    ):
        """Adiciona um arco."""
        self.entities.append(self._format_arc(center, radius, start_angle, end_angle, layer))
    
    def add_polyline(
        self,
        points: List[Tuple[float, float]],
        closed: bool = False,
        layer: str = "0"
    ):
        """Adiciona uma polilinha."""
        if self.version == "R12":
            self.entities.append(self._format_polyline_r12(points, closed, layer))
        else:
            self.entities.append(self._format_lwpolyline(points, closed, layer))
    
    def add_text(
        self,
        position: Tuple[float, float],
        text: str,
        height: float = 5.0,
        rotation: float = 0.0,
        layer: str = "0"
    ):
        """Adiciona texto."""
        self.entities.append(self._format_text(position, text, height, rotation, layer))
    
    def add_rectangle(
        self,
        corner: Tuple[float, float],
        width: float,
        height: float,
        layer: str = "0"
    ):
        """Adiciona um retângulo como polilinha fechada."""
        x, y = corner
        points = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height)
        ]
        self.add_polyline(points, closed=True, layer=layer)
    
    def _format_line(self, start: Tuple[float, float], end: Tuple[float, float], layer: str) -> str:
        """Formata entidade LINE."""
        return f"""  0
LINE
  8
{layer}
 10
{start[0]:.6f}
 20
{start[1]:.6f}
 30
0.0
 11
{end[0]:.6f}
 21
{end[1]:.6f}
 31
0.0"""
    
    def _format_circle(self, center: Tuple[float, float], radius: float, layer: str) -> str:
        """Formata entidade CIRCLE."""
        return f"""  0
CIRCLE
  8
{layer}
 10
{center[0]:.6f}
 20
{center[1]:.6f}
 30
0.0
 40
{radius:.6f}"""
    
    def _format_arc(
        self, 
        center: Tuple[float, float], 
        radius: float, 
        start_angle: float, 
        end_angle: float, 
        layer: str
    ) -> str:
        """Formata entidade ARC."""
        return f"""  0
ARC
  8
{layer}
 10
{center[0]:.6f}
 20
{center[1]:.6f}
 30
0.0
 40
{radius:.6f}
 50
{start_angle:.6f}
 51
{end_angle:.6f}"""
    
    def _format_polyline_r12(
        self, 
        points: List[Tuple[float, float]], 
        closed: bool, 
        layer: str
    ) -> str:
        """Formata POLYLINE para DXF R12."""
        flags = 1 if closed else 0
        
        lines = [f"""  0
POLYLINE
  8
{layer}
 66
1
 70
{flags}"""]
        
        for point in points:
            lines.append(f"""  0
VERTEX
  8
{layer}
 10
{point[0]:.6f}
 20
{point[1]:.6f}
 30
0.0""")
        
        lines.append("""  0
SEQEND""")
        
        return "\n".join(lines)
    
    def _format_lwpolyline(
        self, 
        points: List[Tuple[float, float]], 
        closed: bool, 
        layer: str
    ) -> str:
        """Formata LWPOLYLINE para DXF R2010+."""
        flags = 1 if closed else 0
        
        lines = [f"""  0
LWPOLYLINE
  8
{layer}
 90
{len(points)}
 70
{flags}
 43
0.0"""]
        
        for point in points:
            lines.append(f""" 10
{point[0]:.6f}
 20
{point[1]:.6f}""")
        
        return "\n".join(lines)
    
    def _format_text(
        self,
        position: Tuple[float, float],
        text: str,
        height: float,
        rotation: float,
        layer: str
    ) -> str:
        """Formata entidade TEXT."""
        return f"""  0
TEXT
  8
{layer}
 10
{position[0]:.6f}
 20
{position[1]:.6f}
 30
0.0
 40
{height:.6f}
  1
{text}
 50
{rotation:.6f}"""
    
    def _generate_header(self) -> str:
        """Gera seção HEADER do DXF."""
        return """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1009
  9
$INSBASE
 10
0.0
 20
0.0
 30
0.0
  9
$EXTMIN
 10
0.0
 20
0.0
 30
0.0
  9
$EXTMAX
 10
5000.0
 20
3000.0
 30
0.0
  9
$LIMMIN
 10
0.0
 20
0.0
  9
$LIMMAX
 10
5000.0
 20
3000.0
  9
$MEASUREMENT
 70
1
  0
ENDSEC"""
    
    def _generate_tables(self) -> str:
        """Gera seção TABLES com layers."""
        lines = ["""  0
SECTION
  2
TABLES
  0
TABLE
  2
LAYER
 70
""" + str(len(self.layers) + 1)]  # +1 para layer 0
        
        # Layer 0 padrão
        lines.append("""  0
LAYER
  2
0
 70
0
 62
7
  6
CONTINUOUS""")
        
        # Layers customizados
        for name, props in self.layers.items():
            lines.append(f"""  0
LAYER
  2
{name}
 70
0
 62
{props['color']}
  6
{props['linetype']}""")
        
        lines.append("""  0
ENDTAB
  0
ENDSEC""")
        
        return "\n".join(lines)
    
    def _generate_entities(self) -> str:
        """Gera seção ENTITIES do DXF."""
        lines = ["""  0
SECTION
  2
ENTITIES"""]
        
        for entity in self.entities:
            lines.append(entity)
        
        lines.append("""  0
ENDSEC""")
        
        return "\n".join(lines)
    
    def generate(self) -> str:
        """Gera o arquivo DXF completo."""
        parts = [
            self._generate_header(),
            self._generate_tables(),
            self._generate_entities(),
            "  0\nEOF"
        ]
        
        return "\n".join(parts)
    
    def export_nesting(
        self,
        placements: List[Dict[str, Any]],
        sheet_width: float,
        sheet_height: float,
        include_layers: bool = True,
        layers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Exporta resultado de nesting para DXF.
        
        Args:
            placements: Lista de posicionamentos [{pieceId, x, y, rotation, contour, holes}]
            sheet_width: Largura da chapa
            sheet_height: Altura da chapa
            include_layers: Se deve criar layers separados
            layers: Nomes dos layers customizados
            
        Returns:
            Conteúdo do arquivo DXF
        """
        # Configurar layers padrão
        layer_names = layers or {
            "contour": "CONTORNOS",
            "holes": "FUROS",
            "nesting": "NESTING",
            "annotations": "ANOTACOES",
            "border": "BORDA"
        }
        
        if include_layers:
            self.add_layer(layer_names["contour"], DXFColor.GREEN, DXFLineType.CONTINUOUS)
            self.add_layer(layer_names["holes"], DXFColor.CYAN, DXFLineType.CONTINUOUS)
            self.add_layer(layer_names["nesting"], DXFColor.GRAY, DXFLineType.DASHED)
            self.add_layer(layer_names["annotations"], DXFColor.WHITE, DXFLineType.CONTINUOUS)
            self.add_layer(layer_names["border"], DXFColor.RED, DXFLineType.CONTINUOUS)
        
        # Desenhar borda da chapa
        self.add_rectangle((0, 0), sheet_width, sheet_height, layer_names["border"])
        
        # Desenhar cada peça posicionada
        for placement in placements:
            px = placement.get("x", 0)
            py = placement.get("y", 0)
            rotation = placement.get("rotation", 0)
            piece_name = placement.get("pieceName", "Peça")
            
            # Contorno da peça
            contour = placement.get("contour", [])
            if contour:
                transformed_points = self._transform_points(contour, px, py, rotation)
                self.add_polyline(transformed_points, closed=True, layer=layer_names["contour"])
            
            # Furos
            holes = placement.get("holes", [])
            for hole in holes:
                if isinstance(hole, list):  # Lista de pontos
                    transformed_points = self._transform_points(hole, px, py, rotation)
                    self.add_polyline(transformed_points, closed=True, layer=layer_names["holes"])
                elif isinstance(hole, dict) and "center" in hole:  # Círculo
                    cx, cy = self._transform_point(
                        hole["center"]["x"], 
                        hole["center"]["y"], 
                        px, py, rotation
                    )
                    self.add_circle((cx, cy), hole.get("radius", 10), layer=layer_names["holes"])
            
            # Anotação com nome da peça
            if include_layers:
                # Calcular centro aproximado
                if contour:
                    cx = sum(p.get("x", 0) for p in contour) / len(contour)
                    cy = sum(p.get("y", 0) for p in contour) / len(contour)
                    tx, ty = self._transform_point(cx, cy, px, py, rotation)
                    self.add_text((tx, ty), piece_name, height=10, layer=layer_names["annotations"])
        
        # Adicionar metadados
        self.add_text(
            (10, sheet_height + 20),
            f"Nesting gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            height=8,
            layer=layer_names["annotations"]
        )
        self.add_text(
            (10, sheet_height + 35),
            f"Chapa: {sheet_width}x{sheet_height}mm | Pecas: {len(placements)}",
            height=8,
            layer=layer_names["annotations"]
        )
        
        return self.generate()
    
    def _transform_points(
        self,
        points: List[Dict[str, float]],
        offset_x: float,
        offset_y: float,
        rotation: float
    ) -> List[Tuple[float, float]]:
        """Transforma lista de pontos aplicando offset e rotação."""
        transformed = []
        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        
        for p in points:
            x = p.get("x", 0)
            y = p.get("y", 0)
            
            # Rotacionar
            rx = x * cos_r - y * sin_r
            ry = x * sin_r + y * cos_r
            
            # Transladar
            transformed.append((rx + offset_x, ry + offset_y))
        
        return transformed
    
    def _transform_point(
        self,
        x: float,
        y: float,
        offset_x: float,
        offset_y: float,
        rotation: float
    ) -> Tuple[float, float]:
        """Transforma um ponto aplicando offset e rotação."""
        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        
        rx = x * cos_r - y * sin_r
        ry = x * sin_r + y * cos_r
        
        return (rx + offset_x, ry + offset_y)
    
    def export_toolpath(
        self,
        toolpath_data: Dict[str, Any],
        include_rapids: bool = True
    ) -> str:
        """
        Exporta toolpath para DXF.
        
        Args:
            toolpath_data: Dados do toolpath com paths e rapids
            include_rapids: Se deve incluir movimentos rápidos
        """
        self.add_layer("TOOLPATH_CUTTING", DXFColor.GREEN, DXFLineType.CONTINUOUS)
        self.add_layer("TOOLPATH_RAPIDS", DXFColor.YELLOW, DXFLineType.DASHED)
        self.add_layer("TOOLPATH_PIERCE", DXFColor.MAGENTA, DXFLineType.CONTINUOUS)
        
        paths = toolpath_data.get("paths", [])
        
        for path in paths:
            points = path.get("points", [])
            is_rapid = path.get("isRapid", False)
            
            if is_rapid and not include_rapids:
                continue
            
            layer = "TOOLPATH_RAPIDS" if is_rapid else "TOOLPATH_CUTTING"
            
            if len(points) >= 2:
                tuples = [(p.get("x", 0), p.get("y", 0)) for p in points]
                self.add_polyline(tuples, closed=False, layer=layer)
            
            # Marcar ponto de pierce
            if not is_rapid and points:
                pierce_point = points[0]
                self.add_circle(
                    (pierce_point.get("x", 0), pierce_point.get("y", 0)),
                    2.0,
                    layer="TOOLPATH_PIERCE"
                )
        
        return self.generate()


def export_geometry_to_dxf(
    entities: List[Dict[str, Any]],
    filename: Optional[str] = None,
    layers: Optional[Dict[str, int]] = None
) -> str:
    """
    Função utilitária para exportar geometria para DXF.
    
    Args:
        entities: Lista de entidades [{type, points/center/radius, layer}]
        filename: Nome do arquivo opcional
        layers: Mapeamento layer -> cor
        
    Returns:
        Conteúdo DXF ou caminho do arquivo salvo
    """
    exporter = DXFExporter()
    
    # Adicionar layers
    default_layers = {
        "CONTORNO": DXFColor.GREEN,
        "FUROS": DXFColor.CYAN,
        "CONSTRUCAO": DXFColor.GRAY,
    }
    layer_colors = layers or default_layers
    
    for name, color in layer_colors.items():
        exporter.add_layer(name, color)
    
    # Adicionar entidades
    for entity in entities:
        entity_type = entity.get("type", "line")
        layer = entity.get("layer", "0")
        
        if entity_type == "line":
            points = entity.get("points", [])
            if len(points) >= 2:
                exporter.add_line(
                    (points[0]["x"], points[0]["y"]),
                    (points[1]["x"], points[1]["y"]),
                    layer
                )
        
        elif entity_type == "circle":
            center = entity.get("center", {"x": 0, "y": 0})
            radius = entity.get("radius", 10)
            exporter.add_circle((center["x"], center["y"]), radius, layer)
        
        elif entity_type == "arc":
            center = entity.get("center", {"x": 0, "y": 0})
            radius = entity.get("radius", 10)
            start = entity.get("startAngle", 0)
            end = entity.get("endAngle", 360)
            exporter.add_arc((center["x"], center["y"]), radius, start, end, layer)
        
        elif entity_type == "polyline":
            points = entity.get("points", [])
            closed = entity.get("closed", False)
            if points:
                tuples = [(p["x"], p["y"]) for p in points]
                exporter.add_polyline(tuples, closed, layer)
    
    content = exporter.generate()
    
    if filename:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return filename
    
    return content
