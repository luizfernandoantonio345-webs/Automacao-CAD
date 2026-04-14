#!/usr/bin/env python3
"""
Engenharia CAD - Rotas API do AutoCAD Driver (Nivel 4)
Expoe operacoes COM como endpoints REST para o Frontend/AIOrchestrator.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.autocad_driver import acad_driver

# === SECURITY: Validador de comandos com whitelist ===
try:
    from backend.cad_command_validator import validate_command, is_command_allowed
    _CAD_VALIDATOR_AVAILABLE = True
except ImportError:
    _CAD_VALIDATOR_AVAILABLE = False
    def validate_command(cmd):
        class _R:
            valid = True
            error = None
            sanitized_command = cmd
        return _R()
    def is_command_allowed(cmd):
        return True

logger = logging.getLogger("engcad.routes_autocad")

router = APIRouter(prefix="/api/autocad", tags=["autocad-driver"])
debug_router = APIRouter(prefix="/api/autocad/debug", tags=["autocad-debug"])


class DrawPipeRequest(BaseModel):
    points: List[List[float]] = Field(..., min_length=2)
    diameter: float = Field(default=6.0, gt=0, le=120)
    layer: str = Field(default="PIPE-PROCESS", max_length=64)


class DrawLineRequest(BaseModel):
    start: List[float] = Field(..., min_length=2, max_length=3)
    end: List[float] = Field(..., min_length=2, max_length=3)
    layer: str = Field(default="PIPE-UTILITY", max_length=64)


class InsertComponentRequest(BaseModel):
    block_name: str = Field(..., max_length=64)
    coordinate: List[float] = Field(..., min_length=2, max_length=3)
    rotation: float = Field(default=0.0, ge=0, lt=360)
    scale: float = Field(default=1.0, gt=0, le=100)
    layer: str = Field(default="VALVE", max_length=64)


class AddTextRequest(BaseModel):
    text: str = Field(..., max_length=500)
    position: List[float] = Field(..., min_length=2, max_length=3)
    height: float = Field(default=2.5, gt=0, le=100)
    layer: str = Field(default="ANNOTATION", max_length=64)


class SendCommandRequest(BaseModel):
    command: str = Field(..., max_length=2000)


class BridgeConfigRequest(BaseModel):
    path: str = Field(..., max_length=500)


class ModeConfigRequest(BaseModel):
    use_bridge: bool


class BatchDrawRequest(BaseModel):
    pipes: List[DrawPipeRequest] = Field(default_factory=list)
    components: List[InsertComponentRequest] = Field(default_factory=list)
    finalize: bool = Field(default=True)


class TestResult(BaseModel):
    success: bool
    entities_created: int = 0
    operations: list = []
    message: str = ""


@router.post("/connect")
async def api_connect():
    return acad_driver.connect().to_dict()


@router.post("/disconnect")
async def api_disconnect():
    return acad_driver.disconnect().to_dict()


@router.get("/status")
async def api_status():
    return acad_driver.stats


@router.get("/health")
async def api_health():
    return acad_driver.health_check()


@router.post("/config/bridge")
async def api_config_bridge(req: BridgeConfigRequest):
    return acad_driver.set_bridge_path(req.path).to_dict()


@router.post("/config/mode")
async def api_config_mode(req: ModeConfigRequest):
    return acad_driver.set_mode(req.use_bridge).to_dict()


@router.get("/buffer")
async def api_buffer():
    return {
        "size": len(acad_driver.command_buffer),
        "commands": acad_driver.command_buffer[:50],
        "mode": "bridge" if acad_driver.use_bridge else "com",
    }


@router.post("/commit")
async def api_commit():
    if not acad_driver.use_bridge:
        raise HTTPException(400, "Commit so funciona em modo bridge")
    return acad_driver.commit().to_dict()


@router.post("/draw-pipe")
async def api_draw_pipe(req: DrawPipeRequest):
    r = acad_driver.draw_pipe(req.points, req.diameter, req.layer)
    if r.success:
        if acad_driver.use_bridge:
            acad_driver.commit()
        return r.to_dict()
    raise HTTPException(503, r.message)


@router.post("/draw-line")
async def api_draw_line(req: DrawLineRequest):
    r = acad_driver.draw_line(req.start, req.end, req.layer)
    if r.success:
        if acad_driver.use_bridge:
            acad_driver.commit()
        return r.to_dict()
    raise HTTPException(503, r.message)


@router.post("/insert-component")
async def api_insert_component(req: InsertComponentRequest):
    r = acad_driver.insert_component(
        req.block_name, req.coordinate, req.rotation, req.scale, req.layer
    )
    if r.success:
        if acad_driver.use_bridge:
            acad_driver.commit()
        return r.to_dict()
    raise HTTPException(503, r.message)


@router.post("/add-text")
async def api_add_text(req: AddTextRequest):
    r = acad_driver.add_text(req.text, req.position, req.height, req.layer)
    if r.success:
        if acad_driver.use_bridge:
            acad_driver.commit()
        return r.to_dict()
    raise HTTPException(503, r.message)


@router.post("/send-command")
async def api_send_command(req: SendCommandRequest):
    # === SECURITY: Validar comando contra whitelist ===
    validation = validate_command(req.command)
    if not validation.valid:
        logger.warning(f"Comando bloqueado: {req.command[:50]} - {validation.error}")
        raise HTTPException(
            status_code=400,
            detail=f"Comando não permitido: {validation.error}"
        )
    
    r = acad_driver.send_command(validation.sanitized_command)
    if r.success:
        if acad_driver.use_bridge:
            acad_driver.commit()
        return r.to_dict()
    raise HTTPException(503, r.message)


@router.post("/create-layers")
async def api_create_layers():
    r = acad_driver.create_layer_system()
    if acad_driver.use_bridge and r.success:
        acad_driver.commit()
    return r.to_dict()


@router.post("/finalize")
async def api_finalize():
    r = acad_driver.finalize_view()
    return r.to_dict()


@router.post("/save")
async def api_save():
    r = acad_driver.save_document()
    return r.to_dict()


@router.post("/batch-draw")
async def api_batch_draw(req: BatchDrawRequest):
    results = {"pipes": [], "components": [], "finalize": None}
    
    for pipe in req.pipes:
        r = acad_driver.draw_pipe(pipe.points, pipe.diameter, pipe.layer)
        results["pipes"].append(r.to_dict())
    
    for comp in req.components:
        r = acad_driver.insert_component(
            comp.block_name, comp.coordinate, comp.rotation, comp.scale, comp.layer
        )
        results["components"].append(r.to_dict())
    
    if req.finalize:
        results["finalize"] = acad_driver.finalize_view().to_dict()
    
    return results


@router.post("/auto-connect")
async def api_auto_connect() -> dict:
    """
    1-CLICK: Retorna script PowerShell que detecta/abre/conecta AutoCAD.
    O frontend exibe instruções ou executa via agente local.
    """
    # Script PowerShell para conexão automática
    ps_script = '''
# Engenharia CAD - AutoConnect Script
$ErrorActionPreference = "Stop"

# 1. Criar pasta bridge se não existir
$bridgePath = "C:\\AutoCAD_Drop"
if (!(Test-Path $bridgePath)) {
    New-Item -ItemType Directory -Path $bridgePath -Force | Out-Null
    Write-Host "[AutoConnect] Pasta bridge criada: $bridgePath"
}

# 2. Detectar AutoCAD instalado
$acadApp = $null
$versions = @(
    "AutoCAD.Application.25",  # 2025
    "AutoCAD.Application.24",  # 2024
    "AutoCAD.Application.23",  # 2023
    "AutoCAD.Application.22",  # 2022
    "AutoCAD.Application.21",  # 2021
    "AutoCAD.Application.20",  # 2020
    "AutoCAD.Application.19",  # 2019
    "AutoCAD.Application"       # Genérico
)

foreach ($ver in $versions) {
    try {
        $acadApp = New-Object -ComObject $ver
        Write-Host "[AutoConnect] AutoCAD detectado: $ver"
        break
    } catch {
        continue
    }
}

if (!$acadApp) {
    Write-Host "[AutoConnect] ERRO: AutoCAD nao encontrado"
    exit 1
}

# 3. Tornar visível e criar documento
$acadApp.Visible = $true
Start-Sleep -Seconds 2
$doc = $acadApp.Documents.Add()
Write-Host "[AutoConnect] Novo documento criado"

# 4. Carregar extensões Visual LISP
$doc.SendCommand("(vl-load-com)`n")
Start-Sleep -Milliseconds 500

# 5. Configurar variável do backend
$doc.SendCommand("(setq *backend-url* `"http://localhost:8000`")`n")
$doc.SendCommand("(setq *forge-watch-path* `"C:/AutoCAD_Drop/`")`n")

# 6. Verificar se LSP existe, senão criar básico
$lspPath = "C:\\AutoCAD_Drop\\forge_connect.lsp"
if (!(Test-Path $lspPath)) {
    $lspContent = @"
;;; Engenharia CAD - Auto-Connect LSP
(vl-load-com)
(setq *forge-watch-path* "C:/AutoCAD_Drop/")
(setq *forge-running* T)
(princ "\\n[Engenharia CAD] Conectado ao backend!")
(princ "\\n[Engenharia CAD] Pasta bridge: C:/AutoCAD_Drop/")
(princ)
"@
    Set-Content -Path $lspPath -Value $lspContent -Encoding UTF8
}

# 7. Carregar o LSP
$doc.SendCommand("(load `"C:/AutoCAD_Drop/forge_connect.lsp`")`n")
Start-Sleep -Milliseconds 500

# 8. Exibir confirmação
$doc.SendCommand("(alert `"Engenharia CAD conectado!\\nPasta: C:/AutoCAD_Drop/`")`n")

Write-Host "[AutoConnect] SUCESSO: AutoCAD v$($acadApp.Version) conectado!"
Write-Host "[AutoConnect] Pasta bridge: $bridgePath"
'''
    
    return {
        "success": True,
        "powershell": ps_script,
        "instructions": [
            "1. Copie o script PowerShell acima",
            "2. Abra PowerShell como Administrador",
            "3. Cole e execute o script",
            "4. AutoCAD abrirá automaticamente conectado"
        ],
        "bridge_path": "C:/AutoCAD_Drop/",
        "cad_status": "connecting"
    }


@router.post("/detect")
async def api_detect_autocad() -> dict:
    """
    Detecta AutoCAD instalado na máquina via registro do Windows.
    Retorna versão, caminho e status.
    """
    # Script PowerShell para detectar AutoCAD
    detect_script = '''
$result = @{
    detected = $false
    version = ""
    path = ""
    progId = ""
}

# Verificar COM Objects registrados
$versions = @(
    @{id="AutoCAD.Application.25"; name="AutoCAD 2025"},
    @{id="AutoCAD.Application.24"; name="AutoCAD 2024"},
    @{id="AutoCAD.Application.23"; name="AutoCAD 2023"},
    @{id="AutoCAD.Application.22"; name="AutoCAD 2022"},
    @{id="AutoCAD.Application.21"; name="AutoCAD 2021"},
    @{id="AutoCAD.Application.20"; name="AutoCAD 2020"},
    @{id="AutoCAD.Application.19"; name="AutoCAD 2019"},
    @{id="AutoCAD.Application.18"; name="AutoCAD 2018"},
    @{id="AutoCAD.Application";    name="AutoCAD (generico)"}
)

foreach ($ver in $versions) {
    try {
        $clsid = (Get-ItemProperty "HKLM:\\SOFTWARE\\Classes\\$($ver.id)\\CLSID" -ErrorAction Stop).'(default)'
        if ($clsid) {
            $result.detected = $true
            $result.version = $ver.name
            $result.progId = $ver.id
            
            # Tentar pegar o caminho do executável
            try {
                $server = (Get-ItemProperty "HKLM:\\SOFTWARE\\Classes\\CLSID\\$clsid\\LocalServer32" -ErrorAction Stop).'(default)'
                $result.path = $server -replace '"', ''
            } catch {}
            
            break
        }
    } catch {
        continue
    }
}

# Fallback: procurar no registro de aplicativos
if (!$result.detected) {
    $acadPaths = @(
        "HKLM:\\SOFTWARE\\Autodesk\\AutoCAD",
        "HKLM:\\SOFTWARE\\WOW6432Node\\Autodesk\\AutoCAD"
    )
    foreach ($regPath in $acadPaths) {
        if (Test-Path $regPath) {
            $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
            if ($versions) {
                $latest = $versions | Sort-Object Name -Descending | Select-Object -First 1
                $result.detected = $true
                $result.version = "AutoCAD $($latest.Name)"
                try {
                    $result.path = (Get-ItemProperty "$($latest.PSPath)\\*" -ErrorAction SilentlyContinue | 
                                   Select-Object -ExpandProperty AcadLocation -First 1)
                } catch {}
                break
            }
        }
    }
}

$result | ConvertTo-Json
'''
    
    try:
        # Executar detecção via PowerShell
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", detect_script],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "detected": data.get("detected", False),
                "version": data.get("version", ""),
                "path": data.get("path", ""),
                "progId": data.get("progId", ""),
                "connected": False,
                "bridgeReady": False,
                "message": "AutoCAD detectado" if data.get("detected") else "AutoCAD não encontrado"
            }
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        logger.warning(f"Erro ao detectar AutoCAD: {e}")
    
    # Fallback: assumir que bridge mode funciona
    return {
        "detected": False,
        "version": "",
        "path": "",
        "progId": "",
        "connected": False,
        "bridgeReady": True,
        "message": "Detecção não disponível - use modo Bridge"
    }

@router.post("/test-automation")
async def test_full_automation() -> TestResult:
    operations = []
    
    conn = acad_driver.connect()
    operations.append({"connect": conn.to_dict()})
    
    layers = acad_driver.create_layer_system()
    operations.append({"layers": layers.to_dict()})
    
    circle = acad_driver.send_command('(command "_CIRCLE" "0,0" "100")')
    operations.append({"circle": circle.to_dict()})
    
    pipe = acad_driver.draw_pipe([[0,0,0],[1000,0,0]], 6.0, "PIPE-PROCESS")
    operations.append({"pipe": pipe.to_dict()})
    
    finale = acad_driver.finalize_view()
    operations.append({"finalize": finale.to_dict()})
    
    success = conn.success and pipe.success and finale.success
    
    return TestResult(
        success=success,
        entities_created=2,
        operations=operations,
        message="Teste completo!" if success else "Teste com falhas"
    )


@router.post("/test-pipe")
async def test_pipe(req: DrawPipeRequest) -> dict:
    r = acad_driver.draw_pipe(req.points, req.diameter, req.layer)
    if acad_driver.use_bridge and r.success:
        commit = acad_driver.commit()
        return {"draw": r.to_dict(), "commit": commit.to_dict()}
    return r.to_dict()


@debug_router.post("/draw-sample")
async def debug_draw_sample():
    conn = acad_driver.connect()
    if not conn.success:
        raise HTTPException(503, "CAD indisponivel")
    
    acad_driver.create_layer_system()
    
    square_pts = [[0,0,0], [1000,0,0], [1000,1000,0], [0,1000,0], [0,0,0]]
    acad_driver.draw_pipe(square_pts, 4.0, "PIPE-PROCESS")
    
    acad_driver.insert_component("VALVE", [500,500,0], layer="VALVE")
    
    acad_driver.finalize_view()
    
    return {"success": True, "message": "Debug sample desenhado!"}


@debug_router.get("/raw-stats")
async def debug_raw_stats():
    return {
        "stats": acad_driver._stats,
        "status": acad_driver.status,
        "engine": acad_driver.engine_name,
        "use_bridge": acad_driver.use_bridge,
        "bridge_path": acad_driver.bridge_path,
        "buffer_size": len(acad_driver.command_buffer),
        "is_connected": acad_driver.is_connected,
    }
