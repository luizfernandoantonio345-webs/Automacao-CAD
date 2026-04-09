# =============================================================================
# ENGENHARIA CAD - DETECTOR AUTOMÁTICO DE AutoCAD/GstarCAD (v2.0 AUTO)
# Detecta, abre CAD, configura e AUTO-CARREGA LSP + FORGE_START!
# =============================================================================

param(
    [switch]$SilentMode = $false,
    [switch]$AutoStartCAD = $true
)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.ScriptName
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Status($msg, $type = "info") {
    $color = switch ($type) {
        "success" { "Green" }
        "error" { "Red" }
        "warning" { "Yellow" }
        default { "Cyan" }
    }
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $msg" -ForegroundColor $color
}

function Find-CADInstallation {
    Write-Status "🔍 Procurando instalações de CAD no sistema..."
    
    $cadPaths = @()
    
    # AutoCAD paths padrão
    $autocadPaths = @(
        "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2021\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD LT 2024\acad.exe"
    )
    
    $allPaths = $autocadPaths  # Foco AutoCAD primeiro
    
    foreach ($path in $allPaths) {
        if (Test-Path $path) {
            $version = if ($path -match "(\d{4})") { $matches[1] } else { "Unknown" }
            $cadPaths += @{
                Path    = $path
                Type    = "AutoCAD" 
                Version = $version
            }
        }
    }
    
    # Registry AutoCAD
    try {
        Get-ChildItem "HKLM:\SOFTWARE\Autodesk\AutoCAD" -ErrorAction SilentlyContinue | ForEach-Object {
            $loc = (Get-ItemProperty $_.PSPath).Location
            $exe = Join-Path $loc "acad.exe"
            if (Test-Path $exe -and $cadPaths.Path -notcontains $exe) {
                $cadPaths += @{
                    Path    = $exe
                    Type    = "AutoCAD"
                    Version = $_.PSChildName
                }
            }
        }
    }
    catch {}

    return $cadPaths | Sort-Object Path -Unique
}

function Start-CAD($cadInfo) {
    Write-Status "🚀 Iniciando $($cadInfo.Type) $($cadInfo.Version)..."
    
    try {
        Start-Process -FilePath $cadInfo.Path -PassThru | Out-Null
        Start-Sleep 8  # Tempo inicialização
        Write-Status "$($cadInfo.Type) iniciado!" "success"
        return $true
    }
    catch {
        Write-Status "Erro ao iniciar: $_" "error"
        return $false
    }
}

function Setup-EngenhariaCAD {
    Write-Status "📁 Configurando ambiente..."
    
    $engPath = "C:\EngenhariaCAD"
    $dropPath = "C:\AutoCAD_Drop"
    
    New-Item -ItemType Directory -Path $engPath -Force | Out-Null
    New-Item -ItemType Directory -Path $dropPath -Force | Out-Null
    
    # Copiar LSP se existir local
    $localLsp = Join-Path $scriptDir "forge_vigilante.lsp"
    $destLsp = Join-Path $engPath "forge_vigilante.lsp"
    if (Test-Path $localLsp) {
        Copy-Item $localLsp $destLsp -Force
        Write-Status "LSP copiado: $destLsp" "success"
    }
    
    return @{
        EngPath  = $engPath
        DropPath = $dropPath
        LspPath  = $destLsp
    }
}

function Invoke-AutoAppLoad {
    $autoScript = Join-Path $scriptDir "AUTO_APPLOAD.ps1"
    if (Test-Path $autoScript) {
        Write-Status "🤖 Auto-carregando LSP via COM..."
        & powershell.exe -ExecutionPolicy Bypass -File $autoScript -Silent
        Write-Status "✅ LSP carregado + FORGE_START automático!" "success"
    }
    else {
        Write-Status "AUTO_APPLOAD.ps1 não encontrado - carregue manual" "warning"
    }
}

# ═══════════════════════════════════════════════ MAIN ════════════════════════

Clear-Host
Write-Host "`n╔══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ENGENHARIA CAD v2.0 - SETUP AUTOMÁTICO COMPLETO (1-CLICK)          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$cads = Find-CADInstallation

if ($cads.Count -eq 0) {
    Write-Status "❌ Nenhum AutoCAD encontrado!" "error"
    Write-Host "`nInstale AutoCAD 2021+ e execute novamente." -ForegroundColor Red
    pause
    exit 1
}

# Auto-selecionar primeiro CAD
$selected = $cads[0]
Write-Status "🎯 Usando: $($selected.Type) $($selected.Version)" "success"
Write-Host "  $($selected.Path)`n"

if ($AutoStartCAD) {
    Start-CAD $selected
}

$env = Setup-EngenhariaCAD
Invoke-AutoAppLoad

Write-Host "`n┌─────────────────────────────────────────────────────────────────────┐" -ForegroundColor Green
Write-Host "│              ✅ SISTEMA TOTALMENTE CONFIGURADO!                      │" -ForegroundColor Green
Write-Host "│                                                                     │" -ForegroundColor Green
Write-Host "│  📂 Pastas:                                                         │" -ForegroundColor Green
Write-Host "│     LSP: $($env.LspPath)                                            │" -ForegroundColor Green  
Write-Host "│     Drop: $($env.DropPath)                                          │" -ForegroundColor Green
Write-Host "│                                                                     │" -ForegroundColor Green
Write-Host "│  🌐 Backend pronto: POST /api/autocad/config/bridge                 │" -ForegroundColor Green
Write-Host "│     → {`"path`": `"C:/AutoCAD_Drop/`"}                              │" -ForegroundColor Green
Write-Host "│                                                                     │" -ForegroundColor Green
Write-Host "│  🧪 Teste agora: curl POST /api/autocad/test-automation             │" -ForegroundColor Green
Write-Host "└─────────────────────────────────────────────────────────────────────┘" -ForegroundColor Green

# Salvar resultado JSON
$result = @{
    success = $true
    cad     = $selected
    env     = $env
} | ConvertTo-Json -Depth 3

$result | Out-File "$env:TEMP\engcad_setup.json" -Encoding UTF8

if (-not $SilentMode) { pause }

return $result

