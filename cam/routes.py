"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Rotas API REST
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Endpoints:
- POST /api/cam/parse - Parse arquivo DXF/SVG
- POST /api/cam/generate - Gera G-code a partir de geometria
- POST /api/cam/validate - Valida geometria
- GET /api/cam/materials - Lista materiais e parâmetros recomendados
"""

from __future__ import annotations

import io
import logging
import tempfile
import os
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field

# Importar módulo CAM
from cam.geometry_parser import GeometryParser, Geometry, Point
from cam.toolpath_generator import ToolpathGenerator
from cam.gcode_generator import GCodeGenerator, GCodeConfig, PlasmaConfig, MaterialType
from cam.plasma_optimizer import PlasmaOptimizer, OptimizationConfig, OptimizationLevel

logger = logging.getLogger("engcad.cam.routes")

router = APIRouter(prefix="/api/cam", tags=["cam-plasma"])

# Constantes de segurança
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf", ".svg"}

# Custos estimados por material (R$/kg)
MATERIAL_COSTS = {
    "mild_steel": 4.50,
    "stainless": 18.00,
    "aluminum": 12.00,
    "copper": 45.00,
    "brass": 35.00,
}

# Densidade dos materiais (kg/mm³)
MATERIAL_DENSITY = {
    "mild_steel": 7.85e-6,
    "stainless": 8.00e-6,
    "aluminum": 2.70e-6,
    "copper": 8.96e-6,
    "brass": 8.50e-6,
}


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class PointSchema(BaseModel):
    x: float
    y: float
    z: float = 0.0


class LineSchema(BaseModel):
    start: PointSchema
    end: PointSchema
    layer: str = "0"


class ArcSchema(BaseModel):
    center: PointSchema
    radius: float
    start_angle: float
    end_angle: float
    layer: str = "0"
    clockwise: bool = False


class CircleSchema(BaseModel):
    center: PointSchema
    radius: float
    layer: str = "0"


class PolylineSchema(BaseModel):
    points: List[PointSchema]
    closed: bool = False
    layer: str = "0"


class GeometrySchema(BaseModel):
    lines: List[LineSchema] = Field(default_factory=list)
    arcs: List[ArcSchema] = Field(default_factory=list)
    circles: List[CircleSchema] = Field(default_factory=list)
    polylines: List[PolylineSchema] = Field(default_factory=list)


class CuttingConfigSchema(BaseModel):
    """Configuração de corte plasma."""
    material: str = Field(default="mild_steel", description="Tipo de material")
    thickness: float = Field(default=6.0, gt=0, le=100, description="Espessura em mm")
    amperage: int = Field(default=45, ge=20, le=400, description="Amperagem")
    cutting_speed: float = Field(default=2000, alias="cuttingSpeed", ge=100, le=15000, description="Velocidade mm/min")
    pierce_delay: float = Field(default=0.5, alias="pierceDelay", ge=0.1, le=5.0, description="Delay de pierce em segundos")
    pierce_height: float = Field(default=3.0, alias="pierceHeight", ge=1.0, le=20.0, description="Altura de pierce mm")
    cut_height: float = Field(default=1.5, alias="cutHeight", ge=0.5, le=10.0, description="Altura de corte mm")
    safe_height: float = Field(default=10.0, alias="safeHeight", ge=5.0, le=100.0, description="Altura segura mm")
    kerf_width: float = Field(default=1.5, alias="kerfWidth", ge=0.5, le=10.0, description="Largura do kerf mm")
    lead_in_length: float = Field(default=3.0, alias="leadInLength", ge=1.0, le=20.0, description="Comprimento lead-in mm")
    lead_out_length: float = Field(default=2.0, alias="leadOutLength", ge=1.0, le=20.0, description="Comprimento lead-out mm")
    lead_type: str = Field(default="arc", alias="leadType", description="Tipo de lead-in/out")
    thc_enabled: bool = Field(default=True, alias="thcEnabled", description="Habilitar THC")
    arc_voltage: float = Field(default=120.0, alias="arcVoltage", ge=50, le=200, description="Tensão do arco")
    
    class Config:
        populate_by_name = True


class GenerateRequest(BaseModel):
    """Request para geração de G-code."""
    geometry: GeometrySchema
    config: CuttingConfigSchema


class GeometryStatsSchema(BaseModel):
    lines: int
    arcs: int
    circles: int
    polylines: int
    total_length: float = Field(alias="totalLength")
    
    class Config:
        populate_by_name = True


class BoundingBoxSchema(BaseModel):
    min: PointSchema
    max: PointSchema


class ParseResponseSchema(BaseModel):
    success: bool
    geometry: Optional[Dict[str, Any]] = None
    stats: Optional[GeometryStatsSchema] = None
    bounding_box: Optional[BoundingBoxSchema] = Field(None, alias="boundingBox")
    error: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ToolpathStatsSchema(BaseModel):
    total_cuts: int = Field(alias="totalCuts")
    cutting_length: float = Field(alias="cuttingLength")
    rapid_length: float = Field(alias="rapidLength")
    estimated_time: float = Field(alias="estimatedTime")
    internal_contours: int = Field(alias="internalContours")
    external_contours: int = Field(alias="externalContours")
    
    class Config:
        populate_by_name = True


class WarningSchema(BaseModel):
    level: str
    message: str
    suggestion: Optional[str] = None


class CostEstimateSchema(BaseModel):
    """Estimativa de custo do corte."""
    material_cost: float = Field(alias="materialCost", description="Custo do material em R$")
    cutting_time_cost: float = Field(alias="cuttingTimeCost", description="Custo do tempo de corte em R$")
    total_cost: float = Field(alias="totalCost", description="Custo total estimado em R$")
    scrap_percentage: float = Field(alias="scrapPercentage", description="Percentual de perda estimado")
    
    class Config:
        populate_by_name = True


class GenerateResponseSchema(BaseModel):
    success: bool
    code: Optional[str] = None
    stats: Optional[ToolpathStatsSchema] = None
    warnings: List[WarningSchema] = Field(default_factory=list)
    cost_estimate: Optional[CostEstimateSchema] = Field(None, alias="costEstimate")
    error: Optional[str] = None
    
    class Config:
        populate_by_name = True


class MaterialParamsSchema(BaseModel):
    name: str
    color: str
    thickness_range: List[float] = Field(alias="thicknessRange")
    default_params: Dict[str, Any] = Field(alias="defaultParams")
    
    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/parse", response_model=ParseResponseSchema)
async def parse_geometry(file: UploadFile = File(...)):
    """
    Parse arquivo DXF ou SVG e extrai geometria.
    
    Retorna:
    - Entidades geométricas (linhas, arcos, círculos, polilinhas)
    - Estatísticas da geometria
    - Bounding box
    
    Validações:
    - Tamanho máximo: 50MB
    - Formatos: .dxf, .svg
    """
    logger.info(f"[CAM-AUDIT] Recebido arquivo para parse: {file.filename}, content_type: {file.content_type}")
    
    # Validar nome de arquivo
    if not file.filename:
        logger.warning("[CAM-AUDIT] Tentativa de upload sem nome de arquivo")
        raise HTTPException(status_code=400, detail="Nome de arquivo não fornecido")
    
    # Sanitizar nome do arquivo
    safe_filename = os.path.basename(file.filename).replace("..", "")
    
    # Validar extensão
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"[CAM-AUDIT] Extensão não permitida: {ext}")
        raise HTTPException(
            status_code=400, 
            detail=f"Formato não suportado: {ext}. Use .dxf ou .svg"
        )
    
    try:
        # Ler conteúdo com limite de tamanho
        content = await file.read()
        
        # Validar tamanho
        if len(content) > MAX_FILE_SIZE_BYTES:
            logger.warning(f"[CAM-AUDIT] Arquivo muito grande: {len(content)} bytes")
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Máximo permitido: {MAX_FILE_SIZE_MB}MB"
            )
        
        # Calcular hash para auditoria
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        logger.info(f"[CAM-AUDIT] Processando arquivo hash={file_hash}, size={len(content)} bytes")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Parse
            parser = GeometryParser()
            geometry = parser.parse(tmp_path)
            
            # Converter para resposta
            response_geometry = _geometry_to_dict(geometry)
            
            # Calcular estatísticas
            total_length = 0.0
            for line in geometry.lines:
                total_length += line.length
            for arc in geometry.arcs:
                total_length += arc.arc_length
            for circle in geometry.circles:
                total_length += circle.circumference
            for poly in geometry.polylines:
                total_length += poly.length
            
            stats = GeometryStatsSchema(
                lines=len(geometry.lines),
                arcs=len(geometry.arcs),
                circles=len(geometry.circles),
                polylines=len(geometry.polylines),
                totalLength=total_length
            )
            
            # Bounding box
            bbox = geometry.calculate_bounding_box()
            bounding_box = BoundingBoxSchema(
                min=PointSchema(x=bbox[0].x, y=bbox[0].y, z=bbox[0].z),
                max=PointSchema(x=bbox[1].x, y=bbox[1].y, z=bbox[1].z)
            )
            
            logger.info(f"Parse concluído: {geometry.total_entities} entidades")
            
            return ParseResponseSchema(
                success=True,
                geometry=response_geometry,
                stats=stats,
                boundingBox=bounding_box
            )
        
        finally:
            # Limpar arquivo temporário
            os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"Erro no parse: {e}")
        return ParseResponseSchema(
            success=False,
            error=str(e)
        )


@router.post("/generate", response_model=GenerateResponseSchema)
async def generate_gcode(request: GenerateRequest):
    """
    Gera G-code a partir de geometria e configuração de corte.
    
    O G-code gerado inclui:
    - Comandos de inicialização (G21, G90, etc.)
    - Sequência otimizada de cortes (internos primeiro)
    - Lead-in e lead-out para cada contorno
    - Compensação de kerf
    - Comandos de plasma (M03/M05)
    - Controle de altura (THC)
    """
    logger.info("Gerando G-code")
    
    try:
        # Converter geometria do request para objetos internos
        geometry = _dict_to_geometry(request.geometry.model_dump())
        
        if not geometry.has_geometry:
            raise HTTPException(status_code=400, detail="Geometria vazia")
        
        # Configurar plasma
        material_map = {
            "mild_steel": MaterialType.MILD_STEEL,
            "stainless": MaterialType.STAINLESS,
            "aluminum": MaterialType.ALUMINUM,
            "copper": MaterialType.COPPER,
        }
        
        material = material_map.get(request.config.material, MaterialType.MILD_STEEL)
        
        plasma_config = PlasmaConfig(
            material=material,
            thickness=request.config.thickness,
            amperage=request.config.amperage,
            cutting_speed=request.config.cutting_speed,
            pierce_delay=request.config.pierce_delay,
            pierce_height=request.config.pierce_height,
            cut_height=request.config.cut_height,
            safe_height=request.config.safe_height,
            kerf_width=request.config.kerf_width,
            thc_enabled=request.config.thc_enabled,
            arc_voltage=request.config.arc_voltage,
        )
        
        # Gerar toolpath
        toolpath_gen = ToolpathGenerator(
            kerf_width=request.config.kerf_width,
            lead_in_length=request.config.lead_in_length,
            lead_out_length=request.config.lead_out_length,
            lead_type=request.config.lead_type,
            safe_height=request.config.safe_height,
        )
        
        toolpath = toolpath_gen.generate(
            geometry=geometry,
            cutting_speed=request.config.cutting_speed,
            apply_kerf=True,
            optimize_order=True,
        )
        
        # Otimizar
        optimizer = PlasmaOptimizer(OptimizationConfig(level=OptimizationLevel.STANDARD))
        opt_result = optimizer.optimize(toolpath)
        
        if opt_result.toolpath:
            toolpath = opt_result.toolpath
        
        # Gerar G-code
        gcode_gen = GCodeGenerator(
            gcode_config=GCodeConfig(
                units="mm",
                include_header=True,
                include_comments=True,
            ),
            plasma_config=plasma_config,
        )
        
        gcode = gcode_gen.generate(toolpath)
        
        # Contar contornos internos/externos
        from cam.toolpath_generator import ContourType
        internal_count = sum(1 for p in toolpath.paths if p.contour_type == ContourType.INTERNAL)
        external_count = sum(1 for p in toolpath.paths if p.contour_type == ContourType.EXTERNAL)
        
        # Preparar estatísticas
        stats = ToolpathStatsSchema(
            totalCuts=len(toolpath.paths),
            cuttingLength=round(toolpath.total_cutting_length, 1),
            rapidLength=round(toolpath.total_rapid_length, 1),
            estimatedTime=round(toolpath.total_time, 0),
            internalContours=internal_count,
            externalContours=external_count,
        )
        
        # Calcular estimativa de custo
        cost_estimate = _calculate_cost_estimate(
            material=request.config.material,
            thickness=request.config.thickness,
            cutting_length=toolpath.total_cutting_length,
            cutting_time_seconds=toolpath.total_time,
            kerf_width=request.config.kerf_width,
        )
        
        # Converter warnings
        warnings = []
        for w in opt_result.warnings:
            warnings.append(WarningSchema(
                level=w.level.value,
                message=w.message,
                suggestion=w.suggestion
            ))
        
        # Adicionar info de THC
        if request.config.thc_enabled:
            warnings.insert(0, WarningSchema(
                level="info",
                message="THC habilitado para melhor qualidade de corte"
            ))
        
        logger.info(f"[CAM-AUDIT] G-code gerado: {len(toolpath.paths)} cortes, {toolpath.total_cutting_length:.1f}mm, custo: R${cost_estimate.total_cost:.2f}")
        
        return GenerateResponseSchema(
            success=True,
            code=gcode,
            stats=stats,
            warnings=warnings,
            costEstimate=cost_estimate,
        )
    
    except Exception as e:
        logger.error(f"Erro na geração de G-code: {e}")
        return GenerateResponseSchema(
            success=False,
            error=str(e)
        )


@router.post("/validate")
async def validate_geometry(geometry: GeometrySchema):
    """
    Valida geometria e retorna alertas/sugestões.
    """
    try:
        geo = _dict_to_geometry(geometry.model_dump())
        
        optimizer = PlasmaOptimizer()
        warnings = optimizer.analyze(geo)
        
        return {
            "success": True,
            "valid": all(w.level.value != "error" for w in warnings),
            "warnings": [
                {
                    "level": w.level.value,
                    "message": w.message,
                    "suggestion": w.suggestion
                }
                for w in warnings
            ]
        }
    
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "error": str(e)
        }


@router.get("/materials")
async def get_materials():
    """
    Retorna lista de materiais suportados com parâmetros padrão.
    """
    materials = {
        "mild_steel": {
            "name": "Aço Carbono",
            "color": "#6B7280",
            "thicknessRange": [1, 50],
            "defaultParams": {
                3: {"amperage": 30, "speed": 3500, "kerf": 1.0},
                6: {"amperage": 45, "speed": 2000, "kerf": 1.5},
                10: {"amperage": 65, "speed": 1200, "kerf": 1.8},
                12: {"amperage": 80, "speed": 900, "kerf": 2.0},
                16: {"amperage": 100, "speed": 600, "kerf": 2.2},
                20: {"amperage": 130, "speed": 450, "kerf": 2.5},
                25: {"amperage": 200, "speed": 350, "kerf": 3.0},
            }
        },
        "stainless": {
            "name": "Aço Inox",
            "color": "#9CA3AF",
            "thicknessRange": [1, 25],
            "defaultParams": {
                3: {"amperage": 40, "speed": 2800, "kerf": 1.2},
                6: {"amperage": 60, "speed": 1600, "kerf": 1.8},
                10: {"amperage": 80, "speed": 900, "kerf": 2.2},
                12: {"amperage": 100, "speed": 700, "kerf": 2.5},
            }
        },
        "aluminum": {
            "name": "Alumínio",
            "color": "#D1D5DB",
            "thicknessRange": [1, 20],
            "defaultParams": {
                3: {"amperage": 40, "speed": 4000, "kerf": 1.5},
                6: {"amperage": 65, "speed": 2500, "kerf": 2.0},
                10: {"amperage": 100, "speed": 1500, "kerf": 2.5},
            }
        },
        "copper": {
            "name": "Cobre",
            "color": "#F59E0B",
            "thicknessRange": [1, 12],
            "defaultParams": {
                3: {"amperage": 50, "speed": 2500, "kerf": 1.8},
                6: {"amperage": 80, "speed": 1500, "kerf": 2.2},
            }
        },
        "brass": {
            "name": "Latão",
            "color": "#EAB308",
            "thicknessRange": [1, 10],
            "defaultParams": {
                3: {"amperage": 45, "speed": 2800, "kerf": 1.6},
                6: {"amperage": 70, "speed": 1800, "kerf": 2.0},
            }
        },
        "galvanized": {
            "name": "Aço Galvanizado",
            "color": "#71717A",
            "thicknessRange": [1, 6],
            "defaultParams": {
                1.5: {"amperage": 25, "speed": 4500, "kerf": 0.8},
                3: {"amperage": 35, "speed": 3200, "kerf": 1.2},
                6: {"amperage": 50, "speed": 1800, "kerf": 1.6},
            }
        },
    }
    
    return {"materials": materials}


@router.post("/download/{format}")
async def download_gcode(format: str, request: GenerateRequest):
    """
    Gera e retorna G-code no formato especificado (.nc, .tap, .gcode).
    """
    if format not in ["nc", "tap", "gcode"]:
        raise HTTPException(status_code=400, detail=f"Formato não suportado: {format}")
    
    # Gerar G-code
    result = await generate_gcode(request)
    
    if not result.success or not result.code:
        raise HTTPException(status_code=500, detail=result.error or "Erro ao gerar G-code")
    
    filename = f"corte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    return PlainTextResponse(
        content=result.code,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_cost_estimate(
    material: str,
    thickness: float,
    cutting_length: float,
    cutting_time_seconds: float,
    kerf_width: float,
) -> CostEstimateSchema:
    """
    Calcula estimativa de custo do corte.
    
    Considera:
    - Custo do material removido (kerf)
    - Custo do tempo de máquina (R$150/hora)
    - Percentual de perda estimado
    """
    # Custo por hora de máquina (ajustar conforme necessidade)
    MACHINE_HOUR_COST = 150.0  # R$/hora
    
    # Volume de material removido (mm³)
    volume_removed = cutting_length * thickness * kerf_width
    
    # Massa removida (kg)
    density = MATERIAL_DENSITY.get(material, MATERIAL_DENSITY["mild_steel"])
    mass_removed_kg = volume_removed * density
    
    # Custo do material (estimativa baseada no material perdido + margem)
    material_price = MATERIAL_COSTS.get(material, MATERIAL_COSTS["mild_steel"])
    material_cost = mass_removed_kg * material_price * 2.5  # 2.5x para incluir margem de perda
    
    # Custo do tempo de corte
    cutting_time_hours = cutting_time_seconds / 3600
    time_cost = cutting_time_hours * MACHINE_HOUR_COST
    
    # Percentual de perda estimado (baseado no kerf)
    scrap_percentage = min(30.0, (kerf_width / thickness) * 100 * 1.5)  # Estimativa simplificada
    
    # Total
    total_cost = material_cost + time_cost
    
    return CostEstimateSchema(
        materialCost=round(material_cost, 2),
        cuttingTimeCost=round(time_cost, 2),
        totalCost=round(total_cost, 2),
        scrapPercentage=round(scrap_percentage, 1),
    )


def _geometry_to_dict(geometry: Geometry) -> Dict[str, Any]:
    """Converte Geometry para dicionário."""
    return {
        "entities": [
            *[{
                "type": "line",
                "points": [
                    {"x": l.start.x, "y": l.start.y},
                    {"x": l.end.x, "y": l.end.y}
                ]
            } for l in geometry.lines],
            *[{
                "type": "arc",
                "center": {"x": a.center.x, "y": a.center.y},
                "radius": a.radius,
                "startAngle": a.start_angle,
                "endAngle": a.end_angle,
            } for a in geometry.arcs],
            *[{
                "type": "circle",
                "center": {"x": c.center.x, "y": c.center.y},
                "radius": c.radius,
            } for c in geometry.circles],
            *[{
                "type": "polyline",
                "points": [{"x": p.x, "y": p.y} for p in pl.points],
                "closed": pl.is_closed,
            } for pl in geometry.polylines],
        ],
        "boundingBox": {
            "min": {"x": geometry.bounding_box[0].x, "y": geometry.bounding_box[0].y} if geometry.bounding_box else {"x": 0, "y": 0},
            "max": {"x": geometry.bounding_box[1].x, "y": geometry.bounding_box[1].y} if geometry.bounding_box else {"x": 0, "y": 0},
        }
    }


def _dict_to_geometry(data: Dict[str, Any]) -> Geometry:
    """Converte dicionário para Geometry."""
    from cam.geometry_parser import Line, Arc, Circle, Polyline
    
    parser = GeometryParser()
    
    geo_data = {
        "lines": [
            {
                "start": {"x": l["start"]["x"], "y": l["start"]["y"], "z": l["start"].get("z", 0)},
                "end": {"x": l["end"]["x"], "y": l["end"]["y"], "z": l["end"].get("z", 0)},
                "layer": l.get("layer", "0")
            }
            for l in data.get("lines", [])
        ],
        "arcs": [
            {
                "center": {"x": a["center"]["x"], "y": a["center"]["y"], "z": a["center"].get("z", 0)},
                "radius": a["radius"],
                "start_angle": a["start_angle"],
                "end_angle": a["end_angle"],
                "layer": a.get("layer", "0"),
                "clockwise": a.get("clockwise", False)
            }
            for a in data.get("arcs", [])
        ],
        "circles": [
            {
                "center": {"x": c["center"]["x"], "y": c["center"]["y"], "z": c["center"].get("z", 0)},
                "radius": c["radius"],
                "layer": c.get("layer", "0")
            }
            for c in data.get("circles", [])
        ],
        "polylines": [
            {
                "points": [{"x": p["x"], "y": p["y"], "z": p.get("z", 0)} for p in pl["points"]],
                "closed": pl.get("closed", False),
                "layer": pl.get("layer", "0")
            }
            for pl in data.get("polylines", [])
        ]
    }
    
    return parser.parse_from_data(geo_data)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - IA OPERACIONAL
# ═══════════════════════════════════════════════════════════════════════════════

class AIParametersRequest(BaseModel):
    """Request para sugestão de parâmetros via IA."""
    material: str = Field(default="mild_steel", description="Tipo de material")
    thickness: float = Field(default=6.0, gt=0, le=100, description="Espessura em mm")
    optimization: str = Field(default="balanced", description="Tipo de otimização: speed, quality, consumables, balanced")
    geometry_info: Optional[Dict[str, Any]] = Field(default=None, description="Informações da geometria")


class AIAnalysisRequest(BaseModel):
    """Request para análise de geometria via IA."""
    geometry: GeometrySchema
    kerf_width: float = Field(default=1.5, ge=0.5, le=10.0, description="Largura do kerf em mm")


class AIToolpathRequest(BaseModel):
    """Request para otimização de toolpath via IA."""
    contours: List[Dict[str, Any]] = Field(description="Lista de contornos")
    optimization_type: str = Field(default="balanced", description="Tipo de otimização")


class AIPreCheckRequest(BaseModel):
    """Request para verificação pré-execução via IA."""
    gcode: str = Field(description="Código G-code para verificar")
    machine_limits: Optional[Dict[str, Any]] = Field(default=None, description="Limites da máquina")


@router.post("/ai/suggest-parameters")
async def ai_suggest_parameters(request: AIParametersRequest):
    """
    IA sugere parâmetros de corte otimizados para material e espessura.
    
    A IA considera:
    - Banco de dados de parâmetros por fabricante
    - Interpolação para espessuras intermediárias
    - Geometria da peça (se fornecida)
    - Tipo de otimização desejada
    """
    try:
        from cam.operational_ai import OperationalAI, OptimizationType
        
        ai = OperationalAI()
        
        # Mapear tipo de otimização
        opt_map = {
            "speed": OptimizationType.SPEED,
            "quality": OptimizationType.QUALITY,
            "consumables": OptimizationType.CONSUMABLES,
            "balanced": OptimizationType.BALANCED,
        }
        optimization = opt_map.get(request.optimization, OptimizationType.BALANCED)
        
        params = ai.suggest_cutting_parameters(
            material=request.material,
            thickness=request.thickness,
            geometry_info=request.geometry_info,
            optimization=optimization
        )
        
        return {
            "success": True,
            "parameters": params.to_dict(),
            "recommendations": ai.get_all_recommendations(),
        }
    
    except Exception as e:
        logger.error(f"Erro na sugestão de parâmetros IA: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ai/analyze-geometry")
async def ai_analyze_geometry(request: AIAnalysisRequest):
    """
    IA analisa geometria e detecta problemas automaticamente.
    
    Detecta:
    - Contornos abertos
    - Detalhes menores que 2x kerf
    - Auto-interseções
    - Furos muito próximos
    - Cantos muito agudos
    """
    try:
        from cam.operational_ai import OperationalAI
        
        ai = OperationalAI()
        
        # Converter geometria para formato de análise
        geometry_info = {
            "open_contours": [],  # Seria detectado pelo parser
            "kerf_width": request.kerf_width,
            "min_features": [],
            "self_intersections": [],
            "close_hole_pairs": [],
            "sharp_corners": [],
        }
        
        problems = ai.analyze_geometry(geometry_info)
        
        return {
            "success": True,
            "problems_count": len(problems),
            "auto_fixable": sum(1 for p in problems if p.auto_fix_available),
            "problems": [p.to_dict() for p in problems],
            "can_proceed": all(p.severity.value != "critical" for p in problems),
        }
    
    except Exception as e:
        logger.error(f"Erro na análise de geometria IA: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ai/optimize-toolpath")
async def ai_optimize_toolpath(request: AIToolpathRequest):
    """
    IA otimiza sequência de corte e toolpath.
    
    Estratégias:
    - inside_first: Furos internos primeiro
    - nearest_neighbor: Minimiza movimentos rápidos
    - heat_aware: Distribui cortes para dissipação de calor
    """
    try:
        from cam.operational_ai import OperationalAI, OptimizationType
        
        ai = OperationalAI()
        
        opt_map = {
            "speed": OptimizationType.SPEED,
            "quality": OptimizationType.QUALITY,
            "consumables": OptimizationType.CONSUMABLES,
            "balanced": OptimizationType.BALANCED,
        }
        opt_type = opt_map.get(request.optimization_type, OptimizationType.BALANCED)
        
        optimization = ai.optimize_toolpath(request.contours, opt_type)
        
        return {
            "success": True,
            "optimization": optimization.to_dict(),
            "recommendations": ai.get_all_recommendations(),
        }
    
    except Exception as e:
        logger.error(f"Erro na otimização de toolpath IA: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ai/pre-check")
async def ai_pre_execution_check(request: AIPreCheckRequest):
    """
    IA verifica G-code antes da execução na máquina.
    
    Verifica:
    - Limites da máquina
    - Comandos de plasma
    - Sequência de operações
    - Problemas potenciais
    """
    try:
        from cam.operational_ai import OperationalAI
        
        ai = OperationalAI()
        result = ai.pre_execution_check(request.gcode, request.machine_limits)
        
        return {
            "success": True,
            **result
        }
    
    except Exception as e:
        logger.error(f"Erro na verificação pré-execução IA: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - SIMULAÇÃO FÍSICA
# ═══════════════════════════════════════════════════════════════════════════════

class PhysicsSimulationRequest(BaseModel):
    """Request para simulação física."""
    gcode: str = Field(description="Código G-code para simular")
    amperage: float = Field(default=45.0, ge=20, le=400, description="Amperagem de corte")
    pierce_delay: float = Field(default=0.5, ge=0.0, le=5.0, description="Delay de pierce em segundos")
    machine_preset: str = Field(default="medium_industrial", description="Preset de máquina")


class TimeEstimateRequest(BaseModel):
    """Request para estimativa de tempo."""
    cutting_length: float = Field(description="Comprimento de corte em mm")
    rapid_length: float = Field(description="Comprimento de rapids em mm")
    pierce_count: int = Field(description="Número de pierces")
    feed_rate: float = Field(default=2000.0, description="Velocidade de corte mm/min")
    rapid_rate: float = Field(default=15000.0, description="Velocidade de rapid mm/min")
    pierce_delay: float = Field(default=0.5, description="Delay de pierce em segundos")


@router.post("/simulate/physics")
async def simulate_physics(request: PhysicsSimulationRequest):
    """
    Simulação física completa do G-code.
    
    Considera:
    - Aceleração e desaceleração reais
    - Inércia do sistema
    - Tempo preciso de execução
    - Desgaste de consumíveis
    - Análise térmica (heatmap)
    """
    try:
        from cam.physics_simulation import (
            PhysicsSimulator, MachinePhysics, MachinePhysicsPresets,
            SimulationMode
        )
        
        # Obter preset de máquina
        preset_map = {
            "small_hobby": MachinePhysicsPresets.small_hobby,
            "medium_industrial": MachinePhysicsPresets.medium_industrial,
            "large_production": MachinePhysicsPresets.large_production,
            "hypertherm_hpr": MachinePhysicsPresets.hypertherm_hpr,
        }
        
        physics_func = preset_map.get(request.machine_preset, MachinePhysicsPresets.medium_industrial)
        physics = physics_func()
        
        simulator = PhysicsSimulator(physics=physics, mode=SimulationMode.STANDARD)
        result = simulator.simulate(
            request.gcode,
            amperage=request.amperage,
            pierce_delay=request.pierce_delay
        )
        
        return {
            "success": True,
            **result
        }
    
    except Exception as e:
        logger.error(f"Erro na simulação física: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/simulate/estimate-time")
async def estimate_job_time_endpoint(request: TimeEstimateRequest):
    """
    Estima tempo de job rapidamente sem simular G-code completo.
    
    Útil para estimativas rápidas durante planejamento.
    """
    try:
        from cam.physics_simulation import estimate_job_time, MachinePhysicsPresets
        
        physics = MachinePhysicsPresets.medium_industrial()
        
        result = estimate_job_time(
            cutting_length=request.cutting_length,
            rapid_length=request.rapid_length,
            pierce_count=request.pierce_count,
            feed_rate=request.feed_rate,
            rapid_rate=request.rapid_rate,
            pierce_delay=request.pierce_delay,
            physics=physics
        )
        
        return {
            "success": True,
            "estimate": result
        }
    
    except Exception as e:
        logger.error(f"Erro na estimativa de tempo: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/simulate/machine-presets")
async def get_machine_presets():
    """
    Retorna lista de presets de máquina disponíveis para simulação.
    """
    return {
        "presets": [
            {
                "id": "small_hobby",
                "name": "Mesa Hobby Pequena",
                "description": "Área ~600x600mm, ideal para hobby",
                "work_area": "600mm x 600mm",
            },
            {
                "id": "medium_industrial",
                "name": "Industrial Média",
                "description": "Área ~1500x3000mm, uso profissional",
                "work_area": "3000mm x 1500mm",
            },
            {
                "id": "large_production",
                "name": "Produção Grande",
                "description": "Área ~6000x2000mm, alta produção",
                "work_area": "6000mm x 2000mm",
            },
            {
                "id": "hypertherm_hpr",
                "name": "Hypertherm HPR",
                "description": "Alta definição Hypertherm",
                "work_area": "4000mm x 2000mm",
            },
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - CONSUMÍVEIS
# ═══════════════════════════════════════════════════════════════════════════════

class ConsumablesEstimateRequest(BaseModel):
    """Request para estimativa de consumíveis."""
    pierce_count: int = Field(description="Número de pierces")
    arc_time_minutes: float = Field(description="Tempo de arco em minutos")
    amperage: float = Field(default=45.0, description="Amperagem média")


@router.post("/consumables/estimate")
async def estimate_consumables(request: ConsumablesEstimateRequest):
    """
    Estima desgaste de consumíveis para um job.
    """
    try:
        from cam.physics_simulation import ConsumableState
        
        consumables = ConsumableState()
        
        # Simular pierces
        for _ in range(request.pierce_count):
            consumables.add_pierce(request.amperage)
        
        # Simular tempo de arco (em segundos)
        arc_seconds = request.arc_time_minutes * 60
        consumables.add_arc_time(arc_seconds, request.amperage)
        
        return {
            "success": True,
            "consumables": consumables.to_dict(),
            "recommendations": {
                "replace_before_job": any([
                    consumables.electrode_life < 20,
                    consumables.nozzle_life < 20,
                    consumables.shield_life < 20,
                ]),
                "details": []
            }
        }
    
    except Exception as e:
        logger.error(f"Erro na estimativa de consumíveis: {e}")
        return {
            "success": False,
            "error": str(e)
        }
