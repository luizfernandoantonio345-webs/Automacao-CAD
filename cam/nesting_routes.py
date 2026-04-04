"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Rotas de Nesting e Biblioteca de Peças
Engenharia CAD - APIs REST para Nesting Profissional
═══════════════════════════════════════════════════════════════════════════════

Endpoints:
- POST /api/cam/nesting/run - Executa nesting de peças
- GET /api/cam/nesting/jobs - Lista jobs de nesting
- GET /api/cam/nesting/job/{id} - Obtém resultado de um job

- GET /api/cam/library/pieces - Lista peças da biblioteca
- POST /api/cam/library/pieces - Salva nova peça
- GET /api/cam/library/pieces/{id} - Obtém peça específica
- DELETE /api/cam/library/pieces/{id} - Remove peça

- POST /api/cam/export/dxf - Exporta geometria para DXF
- POST /api/cam/simulate - Simula tempo de corte
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from cam.nesting_engine import (
    NestingEngine, NestingAlgorithm, NestingPriority, RotationMode,
    NestingPiece, NestingSheet, Polygon, Point2D, PieceLibrary,
    create_rectangle_piece, create_circle_piece, create_flange_piece
)

logger = logging.getLogger("engcad.cam.nesting_routes")


class UTF8JSONResponse(JSONResponse):
    """JSONResponse com encoding UTF-8 para caracteres acentuados."""
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
        ).encode('utf-8')

router = APIRouter(prefix="/api/cam", tags=["cam-nesting"])

# Storage para resultados de nesting (em produção usar Redis/DB)
_nesting_jobs: Dict[str, Dict[str, Any]] = {}
_piece_library = PieceLibrary()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class PointSchema(BaseModel):
    x: float
    y: float


class PolygonSchema(BaseModel):
    points: List[PointSchema]
    is_hole: bool = False


class PieceSchema(BaseModel):
    id: Optional[str] = None
    name: str
    contour: PolygonSchema
    holes: List[PolygonSchema] = Field(default_factory=list)
    quantity: int = 1
    priority: int = 0
    allow_rotation: bool = True
    allowed_rotations: List[float] = Field(default=[0, 90, 180, 270])


class QuickPieceSchema(BaseModel):
    """Criação rápida de peças parametrizadas."""
    type: str = Field(..., description="rectangle, circle, flange, l_shape, u_shape")
    name: str
    width: Optional[float] = None
    height: Optional[float] = None
    diameter: Optional[float] = None
    inner_diameter: Optional[float] = None  # Para flanges
    holes: Optional[List[Dict[str, float]]] = None  # [{x, y, diameter}]
    bolt_holes: Optional[int] = None  # Para flanges
    bolt_diameter: Optional[float] = None
    leg_width: Optional[float] = None  # Para L e U
    leg_height: Optional[float] = None
    quantity: int = 1


class SheetSchema(BaseModel):
    width: float = Field(default=3000, ge=100, le=12000)
    height: float = Field(default=1500, ge=100, le=6000)
    material: str = "mild_steel"
    thickness: float = Field(default=6.0, ge=0.5, le=100)
    margin: float = Field(default=10, ge=0, le=100)
    spacing: float = Field(default=5, ge=0, le=50)
    cost_per_kg: float = Field(default=4.50, ge=0)


class NestingConfigSchema(BaseModel):
    algorithm: str = Field(default="blf", description="blf, nfp, genetic, guillotine")
    priority: str = Field(default="balanced", description="speed, efficiency, balanced")
    rotation_mode: str = Field(default="orthogonal", description="none, orthogonal, free")
    max_sheets: int = Field(default=10, ge=1, le=100)
    cutting_speed: float = Field(default=2000, ge=100, le=15000, alias="cuttingSpeed")
    cost_per_hour: float = Field(default=150, ge=0, alias="costPerHour")
    
    class Config:
        populate_by_name = True


class RunNestingRequest(BaseModel):
    pieces: List[PieceSchema]
    sheet: SheetSchema
    config: NestingConfigSchema = Field(default_factory=NestingConfigSchema)


class ExportDXFRequest(BaseModel):
    placements: List[Dict[str, Any]]
    sheet: SheetSchema
    include_layers: bool = True
    layers: Dict[str, str] = Field(default_factory=lambda: {
        "contour": "CONTORNOS",
        "holes": "FUROS",
        "nesting": "NESTING",
        "annotations": "ANOTACOES"
    })


class SimulationRequest(BaseModel):
    cutting_length: float = Field(..., alias="cuttingLength")
    cutting_speed: float = Field(..., alias="cuttingSpeed")
    pierce_count: int = Field(default=1, alias="pierceCount")
    pierce_delay: float = Field(default=0.5, alias="pierceDelay")
    rapid_length: float = Field(default=0, alias="rapidLength")
    rapid_speed: float = Field(default=10000, alias="rapidSpeed")
    
    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - NESTING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/nesting/run")
async def run_nesting(request: RunNestingRequest, background_tasks: BackgroundTasks):
    """
    Executa nesting de peças na chapa.
    
    Algoritmos disponíveis:
    - blf: Bottom-Left Fill (rápido, bom para retângulos)
    - nfp: No-Fit Polygon (preciso para formas complexas)
    - genetic: Algoritmo Genético (otimização global)
    - guillotine: Cortes guilhotina
    """
    logger.info(f"[NESTING] Iniciando: {len(request.pieces)} tipos de peças")
    
    try:
        # Converter peças do request
        pieces = []
        for p in request.pieces:
            contour = Polygon([Point2D(pt.x, pt.y) for pt in p.contour.points])
            holes = [
                Polygon([Point2D(pt.x, pt.y) for pt in h.points], is_hole=True)
                for h in p.holes
            ]
            pieces.append(NestingPiece(
                id=p.id or f"piece_{len(pieces)+1}",
                name=p.name,
                contour=contour,
                holes=holes,
                quantity=p.quantity,
                priority=p.priority,
                allow_rotation=p.allow_rotation,
                allowed_rotations=p.allowed_rotations
            ))
        
        # Configurar chapa
        sheet = NestingSheet(
            id="sheet_1",
            width=request.sheet.width,
            height=request.sheet.height,
            material=request.sheet.material,
            thickness=request.sheet.thickness,
            margin=request.sheet.margin,
            spacing=request.sheet.spacing,
            cost_per_kg=request.sheet.cost_per_kg
        )
        
        # Mapear algoritmo
        algo_map = {
            "blf": NestingAlgorithm.BOTTOM_LEFT_FILL,
            "nfp": NestingAlgorithm.NO_FIT_POLYGON,
            "genetic": NestingAlgorithm.GENETIC,
            "guillotine": NestingAlgorithm.GUILLOTINE,
            "sa": NestingAlgorithm.SIMULATED_ANNEALING
        }
        priority_map = {
            "speed": NestingPriority.SPEED,
            "efficiency": NestingPriority.EFFICIENCY,
            "balanced": NestingPriority.BALANCED
        }
        rotation_map = {
            "none": RotationMode.NONE,
            "orthogonal": RotationMode.ORTHOGONAL,
            "free": RotationMode.FREE,
            "grain": RotationMode.GRAIN_ALIGNED
        }
        
        # Executar nesting
        engine = NestingEngine(
            algorithm=algo_map.get(request.config.algorithm, NestingAlgorithm.BOTTOM_LEFT_FILL),
            priority=priority_map.get(request.config.priority, NestingPriority.BALANCED),
            rotation_mode=rotation_map.get(request.config.rotation_mode, RotationMode.ORTHOGONAL),
            cutting_speed_mm_min=request.config.cutting_speed,
            cost_per_hour=request.config.cost_per_hour
        )
        
        result = engine.nest(pieces, sheet, request.config.max_sheets)
        
        # Armazenar resultado
        _nesting_jobs[result.job_id] = result.to_dict()
        
        logger.info(f"[NESTING] Concluído: job={result.job_id}, eficiência={result.statistics.efficiency:.1f}%")
        
        return UTF8JSONResponse(content=result.to_dict())
        
    except Exception as e:
        logger.error(f"[NESTING] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no nesting: {str(e)}")


@router.get("/nesting/jobs")
async def list_nesting_jobs(limit: int = 20):
    """Lista jobs de nesting recentes."""
    jobs = list(_nesting_jobs.values())
    jobs.sort(key=lambda j: j.get("createdAt", ""), reverse=True)
    return {"jobs": jobs[:limit]}


@router.get("/nesting/job/{job_id}")
async def get_nesting_job(job_id: str):
    """Obtém resultado de um job de nesting."""
    if job_id not in _nesting_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return _nesting_jobs[job_id]


@router.post("/nesting/quick-piece")
async def create_quick_piece(request: QuickPieceSchema):
    """
    Cria peça parametrizada rapidamente.
    
    Tipos suportados:
    - rectangle: Retângulo simples
    - circle: Círculo
    - flange: Flange com furos de parafuso
    """
    try:
        if request.type == "rectangle":
            if not request.width or not request.height:
                raise HTTPException(400, "width e height são obrigatórios para retângulo")
            
            holes = []
            if request.holes:
                holes = [(h["x"], h["y"], h["diameter"]) for h in request.holes]
            
            piece = create_rectangle_piece(
                width=request.width,
                height=request.height,
                name=request.name,
                holes=holes,
                quantity=request.quantity
            )
            
        elif request.type == "circle":
            if not request.diameter:
                raise HTTPException(400, "diameter é obrigatório para círculo")
            
            piece = create_circle_piece(
                diameter=request.diameter,
                name=request.name,
                center_hole_diameter=request.inner_diameter or 0,
                quantity=request.quantity
            )
            
        elif request.type == "flange":
            if not request.diameter or not request.inner_diameter:
                raise HTTPException(400, "diameter e inner_diameter são obrigatórios para flange")
            
            piece = create_flange_piece(
                outer_diameter=request.diameter,
                inner_diameter=request.inner_diameter,
                bolt_holes=request.bolt_holes or 4,
                bolt_diameter=request.bolt_diameter or 18,
                name=request.name,
                quantity=request.quantity
            )
            
        else:
            raise HTTPException(400, f"Tipo de peça não suportado: {request.type}")
        
        return {
            "success": True,
            "piece": piece.to_dict(),
            "contour": [{"x": p.x, "y": p.y} for p in piece.contour.points],
            "holes": [[{"x": p.x, "y": p.y} for p in h.points] for h in piece.holes]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - BIBLIOTECA DE PEÇAS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/library/pieces")
async def list_library_pieces(category: Optional[str] = None):
    """Lista peças da biblioteca."""
    pieces = _piece_library.list_pieces(category)
    
    # Adicionar peças pré-definidas
    predefined = [
        {"id": "preset_flange_150", "name": "Flange 150mm", "category": "flanges", "preset": True},
        {"id": "preset_flange_200", "name": "Flange 200mm", "category": "flanges", "preset": True},
        {"id": "preset_flange_250", "name": "Flange 250mm", "category": "flanges", "preset": True},
        {"id": "preset_plate_100x100", "name": "Chapa 100x100", "category": "chapas", "preset": True},
        {"id": "preset_plate_200x100", "name": "Chapa 200x100", "category": "chapas", "preset": True},
        {"id": "preset_ring_100_50", "name": "Anel 100x50", "category": "aneis", "preset": True},
    ]
    
    return {"pieces": predefined + pieces}


@router.post("/library/pieces")
async def save_library_piece(piece: PieceSchema, category: str = "custom"):
    """Salva uma peça na biblioteca."""
    try:
        contour = Polygon([Point2D(pt.x, pt.y) for pt in piece.contour.points])
        holes = [
            Polygon([Point2D(pt.x, pt.y) for pt in h.points], is_hole=True)
            for h in piece.holes
        ]
        
        nesting_piece = NestingPiece(
            id=piece.id or f"lib_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=piece.name,
            contour=contour,
            holes=holes,
            priority=piece.priority,
            allow_rotation=piece.allow_rotation
        )
        
        piece_id = _piece_library.save_piece(nesting_piece, category)
        
        return {"success": True, "id": piece_id, "message": f"Peça '{piece.name}' salva com sucesso"}
        
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/library/pieces/{piece_id}")
async def get_library_piece(piece_id: str):
    """Obtém uma peça da biblioteca."""
    
    # Verificar se é preset
    if piece_id.startswith("preset_"):
        preset_pieces = {
            "preset_flange_150": lambda: create_flange_piece(150, 75, 4, 16, name="Flange 150mm"),
            "preset_flange_200": lambda: create_flange_piece(200, 100, 8, 18, name="Flange 200mm"),
            "preset_flange_250": lambda: create_flange_piece(250, 125, 8, 20, name="Flange 250mm"),
            "preset_plate_100x100": lambda: create_rectangle_piece(100, 100, "Chapa 100x100"),
            "preset_plate_200x100": lambda: create_rectangle_piece(200, 100, "Chapa 200x100"),
            "preset_ring_100_50": lambda: create_circle_piece(100, "Anel 100x50", center_hole_diameter=50),
        }
        
        if piece_id in preset_pieces:
            piece = preset_pieces[piece_id]()
            return {
                "piece": piece.to_dict(),
                "contour": [{"x": p.x, "y": p.y} for p in piece.contour.points],
                "holes": [[{"x": p.x, "y": p.y} for p in h.points] for h in piece.holes]
            }
    
    piece = _piece_library.load_piece(piece_id)
    if not piece:
        raise HTTPException(404, "Peça não encontrada")
    
    return {
        "piece": piece.to_dict(),
        "contour": [{"x": p.x, "y": p.y} for p in piece.contour.points],
        "holes": [[{"x": p.x, "y": p.y} for p in h.points] for h in piece.holes]
    }


@router.delete("/library/pieces/{piece_id}")
async def delete_library_piece(piece_id: str):
    """Remove uma peça da biblioteca."""
    if piece_id.startswith("preset_"):
        raise HTTPException(400, "Não é possível remover peças pré-definidas")
    
    if _piece_library.delete_piece(piece_id):
        return {"success": True, "message": "Peça removida"}
    
    raise HTTPException(404, "Peça não encontrada")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - EXPORTAÇÃO DXF
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/export/dxf")
async def export_dxf(request: ExportDXFRequest):
    """
    Exporta geometria nestada para arquivo DXF com layers.
    
    Layers padrão:
    - CONTORNOS: Contornos externos das peças
    - FUROS: Furos e recortes internos
    - NESTING: Linhas de layout do nesting
    - ANOTACOES: Textos e anotações
    """
    try:
        from cam.dxf_exporter import DXFExporter
        
        exporter = DXFExporter()
        
        # Criar DXF com layers
        dxf_content = exporter.export_nesting(
            placements=request.placements,
            sheet_width=request.sheet.width,
            sheet_height=request.sheet.height,
            include_layers=request.include_layers,
            layers=request.layers
        )
        
        # Salvar em arquivo temporário
        filename = f"nesting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dxf"
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(dxf_content)
        
        return FileResponse(
            tmp_path,
            media_type="application/dxf",
            filename=filename
        )
        
    except ImportError:
        # Fallback se módulo não existir ainda
        raise HTTPException(501, "Exportação DXF ainda não implementada")
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - SIMULAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/simulate")
async def simulate_cutting(request: SimulationRequest):
    """
    Simula tempo de corte total.
    
    Considera:
    - Tempo de corte (comprimento / velocidade)
    - Tempo de pierce (delays)
    - Tempo de deslocamento rápido
    - Tempo de setup estimado
    """
    # Tempo de corte efetivo
    cutting_time_min = request.cutting_length / request.cutting_speed
    
    # Tempo de pierce (cada penetração)
    pierce_time_min = (request.pierce_count * request.pierce_delay) / 60
    
    # Tempo de deslocamento rápido
    rapid_time_min = request.rapid_length / request.rapid_speed if request.rapid_speed > 0 else 0
    
    # Tempo de setup (estimativa fixa)
    setup_time_min = 2.0  # 2 minutos para preparação
    
    # Total
    total_time_min = cutting_time_min + pierce_time_min + rapid_time_min + setup_time_min
    
    # Formatar tempos
    def format_time(minutes: float) -> str:
        if minutes < 1:
            return f"{minutes * 60:.0f}s"
        elif minutes < 60:
            mins = int(minutes)
            secs = int((minutes - mins) * 60)
            return f"{mins}min {secs}s" if secs > 0 else f"{mins}min"
        else:
            hours = int(minutes / 60)
            mins = int(minutes % 60)
            return f"{hours}h {mins}min"
    
    return {
        "success": True,
        "simulation": {
            "cuttingTime": cutting_time_min,
            "pierceTime": pierce_time_min,
            "rapidTime": rapid_time_min,
            "setupTime": setup_time_min,
            "totalTime": total_time_min,
            "formatted": {
                "cuttingTime": format_time(cutting_time_min),
                "pierceTime": format_time(pierce_time_min),
                "rapidTime": format_time(rapid_time_min),
                "setupTime": format_time(setup_time_min),
                "totalTime": format_time(total_time_min),
            },
            "breakdown": [
                {"label": "Corte", "value": cutting_time_min, "percentage": cutting_time_min / total_time_min * 100},
                {"label": "Pierce", "value": pierce_time_min, "percentage": pierce_time_min / total_time_min * 100},
                {"label": "Rapids", "value": rapid_time_min, "percentage": rapid_time_min / total_time_min * 100},
                {"label": "Setup", "value": setup_time_min, "percentage": setup_time_min / total_time_min * 100},
            ]
        }
    }


@router.get("/consumables/estimate")
async def estimate_consumables(
    cutting_time_minutes: float,
    amperage: int = 45,
    material: str = "mild_steel"
):
    """
    Estima consumo de consumíveis.
    
    Baseado em dados típicos de tochas plasma:
    - Eletrodo: ~2h a 45A, ~1h a 100A
    - Bico: ~1h a 45A, ~0.5h a 100A
    - Gás: ~30 L/min para ar comprimido
    """
    # Vida útil base em minutos
    electrode_life_min = 120 * (45 / amperage)  # Ajusta por amperagem
    nozzle_life_min = 60 * (45 / amperage)
    
    # Consumo
    electrodes_used = cutting_time_minutes / electrode_life_min
    nozzles_used = cutting_time_minutes / nozzle_life_min
    
    # Gás (ajusta por material - inox usa mais nitrogênio)
    gas_flow_lpm = 30 if material != "stainless" else 45
    gas_used_liters = cutting_time_minutes * gas_flow_lpm
    
    # Custos estimados
    ELECTRODE_COST = 25.0  # R$ cada
    NOZZLE_COST = 35.0     # R$ cada
    GAS_COST_PER_LITER = 0.02  # R$ para ar comprimido
    
    consumables_cost = (
        electrodes_used * ELECTRODE_COST +
        nozzles_used * NOZZLE_COST +
        gas_used_liters * GAS_COST_PER_LITER
    )
    
    return {
        "estimate": {
            "electrodes": {
                "quantity": round(electrodes_used, 2),
                "unitCost": ELECTRODE_COST,
                "totalCost": round(electrodes_used * ELECTRODE_COST, 2),
                "lifeMinutes": round(electrode_life_min, 0)
            },
            "nozzles": {
                "quantity": round(nozzles_used, 2),
                "unitCost": NOZZLE_COST,
                "totalCost": round(nozzles_used * NOZZLE_COST, 2),
                "lifeMinutes": round(nozzle_life_min, 0)
            },
            "gas": {
                "liters": round(gas_used_liters, 0),
                "flowRate": gas_flow_lpm,
                "unitCost": GAS_COST_PER_LITER,
                "totalCost": round(gas_used_liters * GAS_COST_PER_LITER, 2)
            },
            "totalConsumablesCost": round(consumables_cost, 2)
        },
        "recommendations": [
            f"Verifique eletrodo após {int(electrode_life_min)}min de uso",
            f"Inspecione bico a cada {int(nozzle_life_min)}min",
            "Mantenha pressão de ar entre 4-6 bar",
            "Drene condensado do compressor diariamente" if material != "stainless" else "Use nitrogênio de alta pureza para inox"
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RASTREABILIDADE - QR CODE
# ═══════════════════════════════════════════════════════════════════════════════

class QRCodeRequest(BaseModel):
    """Request para geração de QR Code de rastreabilidade."""
    piece_id: str = Field(..., alias="pieceId")
    piece_name: str = Field(..., alias="pieceName")
    job_id: str = Field(..., alias="jobId")
    material: str = "mild_steel"
    thickness: float = 6.0
    quantity: int = 1
    operator: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        populate_by_name = True


class TrackedPiece(BaseModel):
    """Peça rastreável no sistema."""
    tracking_code: str = Field(..., alias="trackingCode")
    piece_id: str = Field(..., alias="pieceId")
    piece_name: str = Field(..., alias="pieceName")
    job_id: str = Field(..., alias="jobId")
    material: str
    thickness: float
    quantity: int
    operator: Optional[str] = None
    created_at: str = Field(..., alias="createdAt")
    qr_data: str = Field(..., alias="qrData")
    status: str = "pending"  # pending, cutting, completed, shipped
    
    class Config:
        populate_by_name = True


# Storage de peças rastreadas (em produção usar DB)
_tracked_pieces: Dict[str, Dict[str, Any]] = {}


@router.post("/traceability/generate")
async def generate_traceability_code(request: QRCodeRequest):
    """
    Gera código de rastreabilidade único para uma peça.
    
    O código inclui:
    - ID único da peça
    - Data/hora de criação
    - Material e espessura
    - Referência do job
    """
    import hashlib
    import base64
    from datetime import datetime, UTC
    
    # Gerar código único
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    unique_data = f"{request.job_id}:{request.piece_id}:{timestamp}"
    hash_digest = hashlib.sha256(unique_data.encode()).hexdigest()[:12].upper()
    tracking_code = f"ENG-{hash_digest}"
    
    # Dados para QR Code (JSON compacto)
    qr_data = {
        "tc": tracking_code,
        "pid": request.piece_id,
        "jid": request.job_id,
        "mat": request.material,
        "thk": request.thickness,
        "qty": request.quantity,
        "op": request.operator,
        "ts": timestamp
    }
    
    # Base64 para QR
    import json
    qr_payload = base64.b64encode(json.dumps(qr_data).encode()).decode()
    
    # Salvar no storage
    tracked = {
        "trackingCode": tracking_code,
        "pieceId": request.piece_id,
        "pieceName": request.piece_name,
        "jobId": request.job_id,
        "material": request.material,
        "thickness": request.thickness,
        "quantity": request.quantity,
        "operator": request.operator,
        "notes": request.notes,
        "createdAt": datetime.now(UTC).isoformat(),
        "qrData": qr_payload,
        "status": "pending",
        "history": [
            {"action": "created", "timestamp": datetime.now(UTC).isoformat(), "user": request.operator}
        ]
    }
    _tracked_pieces[tracking_code] = tracked
    
    # Gerar G-code de marcação (para gravação no material)
    marking_gcode = generate_marking_gcode(tracking_code, request.piece_id)
    
    return {
        "success": True,
        "trackingCode": tracking_code,
        "qrPayload": qr_payload,
        "markingGcode": marking_gcode,
        "piece": tracked
    }


def generate_marking_gcode(tracking_code: str, piece_id: str) -> str:
    """Gera G-code para gravar código de rastreabilidade na peça."""
    # Gravar texto com baixa potência (marcação superficial)
    gcode = f"""; ══════════════════════════════════════════
; MARCAÇÃO DE RASTREABILIDADE
; Código: {tracking_code}
; Peça: {piece_id}
; ══════════════════════════════════════════
G90 G40 G49 ; Modos absolutos
G21 ; Milímetros

; Posicionar para gravação (ajustar conforme peça)
G0 X10 Y10 Z5
M06 T99 ; Trocar para ferramenta de gravação

; Parâmetros de gravação (baixa potência)
M62 P0 ; Modo gravação
F500 ; Velocidade lenta para gravação

; Gravar código: {tracking_code}
; (Usar ciclo de gravação de texto do controlador)
G0 Z1
G1 Z0.1 ; Profundidade de gravação
; TEXTO: "{tracking_code}"

G0 Z5 ; Recuar
M63 P0 ; Fim modo gravação

; Retornar para corte normal
M06 T1 ; Trocar para tocha plasma
"""
    return gcode


@router.get("/traceability/{tracking_code}")
async def get_tracked_piece(tracking_code: str):
    """Consulta informações de uma peça pelo código de rastreabilidade."""
    if tracking_code not in _tracked_pieces:
        raise HTTPException(status_code=404, detail="Código de rastreabilidade não encontrado")
    
    return _tracked_pieces[tracking_code]


@router.put("/traceability/{tracking_code}/status")
async def update_piece_status(tracking_code: str, status: str, operator: Optional[str] = None):
    """Atualiza status de uma peça rastreada."""
    from datetime import datetime, UTC
    
    if tracking_code not in _tracked_pieces:
        raise HTTPException(status_code=404, detail="Código não encontrado")
    
    valid_statuses = ["pending", "cutting", "completed", "inspected", "shipped", "rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {valid_statuses}")
    
    piece = _tracked_pieces[tracking_code]
    piece["status"] = status
    piece["history"].append({
        "action": f"status_changed_to_{status}",
        "timestamp": datetime.now(UTC).isoformat(),
        "user": operator
    })
    
    return {"success": True, "trackingCode": tracking_code, "newStatus": status}


@router.get("/traceability/search")
async def search_tracked_pieces(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    material: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
):
    """Busca peças rastreadas com filtros."""
    results = []
    
    for code, piece in _tracked_pieces.items():
        # Aplicar filtros
        if job_id and piece.get("jobId") != job_id:
            continue
        if status and piece.get("status") != status:
            continue
        if material and piece.get("material") != material:
            continue
        
        results.append(piece)
        if len(results) >= limit:
            break
    
    return {
        "total": len(results),
        "pieces": results
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OTIMIZAÇÃO TÉRMICA AVANÇADA
# ═══════════════════════════════════════════════════════════════════════════════

class ThermalOptimizationRequest(BaseModel):
    """Request para otimização térmica do toolpath."""
    cutting_paths: List[Dict[str, Any]] = Field(..., alias="cuttingPaths")
    material: str = "mild_steel"
    thickness: float = 6.0
    amperage: int = 45
    max_heat_density: float = Field(default=1000.0, alias="maxHeatDensity")  # J/mm²
    min_cooling_distance: float = Field(default=50.0, alias="minCoolingDistance")  # mm
    enable_zone_optimization: bool = Field(default=True, alias="enableZoneOptimization")
    
    class Config:
        populate_by_name = True


class ThermalZone(BaseModel):
    """Zona térmica identificada."""
    id: str
    center_x: float = Field(..., alias="centerX")
    center_y: float = Field(..., alias="centerY")
    radius: float
    heat_level: float = Field(..., alias="heatLevel")  # 0-100
    cooling_time_required: float = Field(..., alias="coolingTimeRequired")  # segundos
    
    class Config:
        populate_by_name = True


@router.post("/thermal/optimize")
async def optimize_thermal_sequence(request: ThermalOptimizationRequest):
    """
    Otimiza sequência de corte para minimizar distorção térmica.
    
    Estratégias:
    1. Alternância de zonas - cortar em áreas distantes para permitir resfriamento
    2. Análise de densidade de calor - evitar acúmulo em regiões pequenas
    3. Priorização de internos primeiro - furos antes de contornos
    4. Sequenciamento espiral - do centro para as bordas
    """
    import math
    
    paths = request.cutting_paths
    if not paths:
        return {"success": False, "error": "Nenhum caminho de corte fornecido"}
    
    # Calcular centro de cada path
    for i, path in enumerate(paths):
        if "points" in path:
            pts = path["points"]
            cx = sum(p.get("x", 0) for p in pts) / len(pts)
            cy = sum(p.get("y", 0) for p in pts) / len(pts)
            path["centroid"] = {"x": cx, "y": cy}
            path["index"] = i
    
    # Parâmetros térmicos por material
    MATERIAL_THERMAL = {
        "mild_steel": {"conductivity": 50, "diffusivity": 12, "warp_threshold": 0.8},
        "stainless": {"conductivity": 16, "diffusivity": 4, "warp_threshold": 0.6},
        "aluminum": {"conductivity": 200, "diffusivity": 85, "warp_threshold": 0.9},
        "copper": {"conductivity": 400, "diffusivity": 115, "warp_threshold": 0.95},
    }
    
    thermal_props = MATERIAL_THERMAL.get(request.material, MATERIAL_THERMAL["mild_steel"])
    
    # Input de calor estimado (J/mm)
    # P = V * I, Q = P * t/v (simplificado)
    voltage = 120  # Estimativa
    power = voltage * request.amperage  # Watts
    heat_input_per_mm = power / 2000 * 60  # J/mm (assumindo velocidade média)
    
    # Identificar zonas térmicas críticas
    thermal_zones = []
    zone_radius = request.min_cooling_distance / 2
    
    # Agrupar paths próximos
    visited = set()
    for i, path in enumerate(paths):
        if i in visited:
            continue
        
        zone_paths = [path]
        visited.add(i)
        cx, cy = path["centroid"]["x"], path["centroid"]["y"]
        
        for j, other in enumerate(paths):
            if j in visited:
                continue
            ox, oy = other["centroid"]["x"], other["centroid"]["y"]
            dist = math.sqrt((cx - ox)**2 + (cy - oy)**2)
            if dist < request.min_cooling_distance:
                zone_paths.append(other)
                visited.add(j)
        
        if len(zone_paths) > 1:
            # Calcular calor acumulado na zona
            total_length = sum(p.get("length", 100) for p in zone_paths)
            heat_density = (heat_input_per_mm * total_length) / (math.pi * zone_radius**2)
            heat_level = min(100, (heat_density / request.max_heat_density) * 100)
            
            # Tempo de resfriamento necessário (simplificado)
            cooling_time = (heat_level / 100) * 30 * (1 / thermal_props["diffusivity"] * 10)
            
            thermal_zones.append({
                "id": f"zone_{len(thermal_zones)+1}",
                "centerX": cx,
                "centerY": cy,
                "radius": zone_radius,
                "heatLevel": round(heat_level, 1),
                "coolingTimeRequired": round(cooling_time, 1),
                "pathCount": len(zone_paths),
                "pathIndices": [p["index"] for p in zone_paths]
            })
    
    # Otimizar sequência
    optimized_sequence = []
    remaining = list(range(len(paths)))
    current_pos = {"x": 0, "y": 0}
    last_zone = None
    
    while remaining:
        best_idx = None
        best_score = float('inf')
        
        for idx in remaining:
            path = paths[idx]
            cx, cy = path["centroid"]["x"], path["centroid"]["y"]
            
            # Distância do ponto atual
            dist = math.sqrt((current_pos["x"] - cx)**2 + (current_pos["y"] - cy)**2)
            
            # Penalizar se estiver na mesma zona térmica quente
            zone_penalty = 0
            for zone in thermal_zones:
                zone_dist = math.sqrt((zone["centerX"] - cx)**2 + (zone["centerY"] - cy)**2)
                if zone_dist < zone["radius"] and zone["heatLevel"] > 70:
                    if last_zone and zone["id"] == last_zone:
                        zone_penalty = 1000  # Penalidade alta para mesma zona
                    else:
                        zone_penalty = zone["heatLevel"] * 2
            
            # Priorizar furos/internos
            internal_bonus = -50 if path.get("isInternal", False) else 0
            
            score = dist + zone_penalty + internal_bonus
            
            if score < best_score:
                best_score = score
                best_idx = idx
        
        if best_idx is not None:
            path = paths[best_idx]
            optimized_sequence.append(best_idx)
            current_pos = path["centroid"]
            remaining.remove(best_idx)
            
            # Atualizar última zona
            for zone in thermal_zones:
                zone_dist = math.sqrt((zone["centerX"] - current_pos["x"])**2 + 
                                     (zone["centerY"] - current_pos["y"])**2)
                if zone_dist < zone["radius"]:
                    last_zone = zone["id"]
                    break
    
    # Calcular métricas de otimização
    original_heat_risk = sum(z["heatLevel"] for z in thermal_zones) / max(1, len(thermal_zones))
    
    # Sugestões
    suggestions = []
    high_risk_zones = [z for z in thermal_zones if z["heatLevel"] > 70]
    if high_risk_zones:
        suggestions.append({
            "type": "warning",
            "message": f"{len(high_risk_zones)} zona(s) com alto risco de distorção",
            "action": "Considere pausas de resfriamento entre cortes nessas áreas"
        })
    
    if request.thickness > 10 and request.material in ["stainless", "mild_steel"]:
        suggestions.append({
            "type": "info",
            "message": "Material espesso pode requerer pré-aquecimento",
            "action": "Considere aquecer a chapa a 50-80°C antes do corte"
        })
    
    if len(paths) > 20:
        suggestions.append({
            "type": "optimization",
            "message": "Muitos cortes próximos detectados",
            "action": "Sequência otimizada para alternância de zonas"
        })
    
    return {
        "success": True,
        "optimizedSequence": optimized_sequence,
        "thermalZones": thermal_zones,
        "metrics": {
            "totalPaths": len(paths),
            "thermalZonesIdentified": len(thermal_zones),
            "averageHeatRisk": round(original_heat_risk, 1),
            "highRiskZones": len(high_risk_zones),
            "estimatedCoolingPauses": len(high_risk_zones),
            "warpRiskLevel": "high" if original_heat_risk > 70 else "medium" if original_heat_risk > 40 else "low"
        },
        "suggestions": suggestions,
        "materialProperties": {
            "name": request.material,
            "thermalConductivity": thermal_props["conductivity"],
            "thermalDiffusivity": thermal_props["diffusivity"],
            "warpThreshold": thermal_props["warp_threshold"]
        }
    }


@router.get("/thermal/material-data")
async def get_thermal_material_data():
    """Retorna dados térmicos dos materiais."""
    return {
        "materials": {
            "mild_steel": {
                "name": "Aço Carbono",
                "thermalConductivity": 50,  # W/m·K
                "thermalDiffusivity": 12,   # mm²/s
                "warpThreshold": 0.8,
                "preHeatTemp": 50,           # °C recomendado
                "maxHeatInput": 1500         # J/mm
            },
            "stainless": {
                "name": "Aço Inox",
                "thermalConductivity": 16,
                "thermalDiffusivity": 4,
                "warpThreshold": 0.6,
                "preHeatTemp": 80,
                "maxHeatInput": 1000
            },
            "aluminum": {
                "name": "Alumínio",
                "thermalConductivity": 200,
                "thermalDiffusivity": 85,
                "warpThreshold": 0.9,
                "preHeatTemp": 0,
                "maxHeatInput": 800
            },
            "copper": {
                "name": "Cobre",
                "thermalConductivity": 400,
                "thermalDiffusivity": 115,
                "warpThreshold": 0.95,
                "preHeatTemp": 0,
                "maxHeatInput": 600
            }
        }
    }
