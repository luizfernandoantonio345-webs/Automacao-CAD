# =============================================================================
# ENGENHARIA CAD - DETECTOR AUTOMÁTICO DE AutoCAD/GstarCAD
# Detecta instalação, abre o CAD e carrega o sistema automaticamente
# =============================================================================

param(
    [switch]$SilentMode = $false
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Status($msg, $type = "info") {
    $color = switch ($type) {
        "success" { "Green" }
        "error"   { "Red" }
        "warning" { "Yellow" }
        default   { "Cyan" }
    }
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $msg" -ForegroundColor $color
}

function Find-CADInstallation {
    Write-Status "Procurando instalações de CAD no sistema..."
    
    $cadPaths = @()
    
    # AutoCAD paths
    $autocadPaths = @(
        "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2021\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2020\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2019\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD LT 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD LT 2023\acad.exe"
    )
    
    # GstarCAD paths
    $gstarcadPaths = @(
        "C:\Program Files\Gstarsoft\GstarCAD 2024\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2023\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2022\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD Pro\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD\gcad.exe"
    )
    
    # ZWCAD paths
    $zwcadPaths = @(
        "C:\Program Files\ZWSOFT\ZWCAD 2024\ZWCAD.exe",
        "C:\Program Files\ZWSOFT\ZWCAD 2023\ZWCAD.exe"
    )
    
    # BricsCAD paths
    $bricscadPaths = @(
        "C:\Program Files\Bricsys\BricsCAD V24\bricscad.exe",
        "C:\Program Files\Bricsys\BricsCAD V23\bricscad.exe"
    )
    
    $allPaths = $autocadPaths + $gstarcadPaths + $zwcadPaths + $bricscadPaths
    
    foreach ($path in $allPaths) {
        if (Test-Path $path) {
            $type = if ($path -match "acad\.exe") { "AutoCAD" }
                    elseif ($path -match "gcad\.exe") { "GstarCAD" }
                    elseif ($path -match "ZWCAD\.exe") { "ZWCAD" }
                    elseif ($path -match "bricscad\.exe") { "BricsCAD" }
                    else { "Unknown" }
            
            # Extract version from path
            $version = if ($path -match "(\d{4})") { $matches[1] } else { "Unknown" }
            
            $cadPaths += @{
                Path = $path
                Type = $type
                Version = $version
            }
        }
    }
    
    # Search registry for AutoCAD
    try {
        $regPaths = @(
            "HKLM:\SOFTWARE\Autodesk\AutoCAD",
            "HKLM:\SOFTWARE\WOW6432Node\Autodesk\AutoCAD"
        )
        foreach ($regPath in $regPaths) {
            if (Test-Path $regPath) {
                Get-ChildItem $regPath -ErrorAction SilentlyContinue | ForEach-Object {
                    $subKey = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
                    if ($subKey.Location -and (Test-Path "$($subKey.Location)\acad.exe")) {
                        $cadPaths += @{
                            Path = "$($subKey.Location)\acad.exe"
                            Type = "AutoCAD"
                            Version = $_.PSChildName -replace 'R', ''
                        }
                    }
                }
            }
        }
    } catch {}
    
    # Remove duplicates
    $uniquePaths = @{}
    foreach ($cad in $cadPaths) {
        $key = $cad.Path.ToLower()
        if (-not $uniquePaths.ContainsKey($key)) {
            $uniquePaths[$key] = $cad
        }
    }
    
    return $uniquePaths.Values
}

function Start-CAD($cadInfo) {
    Write-Status "Iniciando $($cadInfo.Type) $($cadInfo.Version)..." "info"
    
    try {
        Start-Process -FilePath $cadInfo.Path -PassThru
        Write-Status "$($cadInfo.Type) iniciado com sucesso!" "success"
        return $true
    } catch {
        Write-Status "Erro ao iniciar CAD: $_" "error"
        return $false
    }
}

function Setup-EngenhariaCAD {
    Write-Status "Configurando ambiente Engenharia CAD..."
    
    # Criar pastas necessárias
    $engPath = "C:\EngenhariaCAD"
    $dropPath = "C:\AutoCAD_Drop"
    
    if (-not (Test-Path $engPath)) {
        New-Item -ItemType Directory -Path $engPath -Force | Out-Null
        Write-Status "Pasta $engPath criada" "success"
    }
    
    if (-not (Test-Path $dropPath)) {
        New-Item -ItemType Directory -Path $dropPath -Force | Out-Null
        Write-Status "Pasta $dropPath criada" "success"
    }
    
    # Copiar arquivo LISP
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $lispSource = Join-Path $scriptDir "forge_vigilante.lsp"
    $lispDest = Join-Path $engPath "forge_vigilante.lsp"
    
    if (Test-Path $lispSource) {
        Copy-Item $lispSource $lispDest -Force
        Write-Status "forge_vigilante.lsp copiado para $engPath" "success"
    } else {
        Write-Status "forge_vigilante.lsp não encontrado na pasta do script" "warning"
    }
    
    return @{
        EngenhariaPath = $engPath
        DropPath = $dropPath
        LispPath = $lispDest
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          ENGENHARIA CAD - DETECTOR AUTOMÁTICO DE CAD             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Detectar CAD
$cads = Find-CADInstallation

if ($cads.Count -eq 0) {
    Write-Status "Nenhum CAD compatível encontrado no sistema." "error"
    Write-Host ""
    Write-Host "CADs suportados:" -ForegroundColor Yellow
    Write-Host "  - AutoCAD 2019-2024"
    Write-Host "  - AutoCAD LT 2023-2024"
    Write-Host "  - GstarCAD 2022-2024"
    Write-Host "  - ZWCAD 2023-2024"
    Write-Host "  - BricsCAD V23-V24"
    Write-Host ""
    
    $result = @{
        found = $false
        cads = @()
    }
} else {
    Write-Status "Encontrado(s) $($cads.Count) CAD(s):" "success"
    
    $cadList = @()
    $i = 1
    foreach ($cad in $cads) {
        Write-Host "  [$i] $($cad.Type) $($cad.Version): $($cad.Path)" -ForegroundColor Green
        $cadList += @{
            index = $i
            type = $cad.Type
            version = $cad.Version
            path = $cad.Path
        }
        $i++
    }
    
    $result = @{
        found = $true
        cads = $cadList
        selected = $cadList[0]  # Default to first found
    }
    
    # Se não for modo silencioso e tiver mais de um CAD, perguntar qual usar
    if (-not $SilentMode -and $cads.Count -gt 1) {
        Write-Host ""
        $choice = Read-Host "Escolha o CAD para usar (1-$($cads.Count)) [1]"
        if ($choice -match "^\d+$" -and [int]$choice -ge 1 -and [int]$choice -le $cads.Count) {
            $result.selected = $cadList[[int]$choice - 1]
        }
    }
    
    # Setup ambiente
    $env = Setup-EngenhariaCAD
    $result.environment = $env
    
    if (-not $SilentMode) {
        Write-Host ""
        Write-Host "┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Green
        Write-Host "│ PRÓXIMOS PASSOS:                                                 │" -ForegroundColor Green
        Write-Host "│                                                                  │" -ForegroundColor Green
        Write-Host "│ 1. Execute INICIAR_SINCRONIZADOR.bat para conectar ao sistema   │" -ForegroundColor Green
        Write-Host "│ 2. No CAD, digite APPLOAD e carregue:                            │" -ForegroundColor Green
        Write-Host "│    C:\EngenhariaCAD\forge_vigilante.lsp                          │" -ForegroundColor Green
        Write-Host "│ 3. Digite FORGE_START na linha de comando do CAD                │" -ForegroundColor Green
        Write-Host "│ 4. Pronto! O sistema web já pode enviar comandos                │" -ForegroundColor Green
        Write-Host "└──────────────────────────────────────────────────────────────────┘" -ForegroundColor Green
    }
}

# Exportar resultado como JSON para uso por outros scripts
$jsonResult = $result | ConvertTo-Json -Depth 5
$jsonPath = Join-Path $env:TEMP "engcad_detection.json"
$jsonResult | Out-File -FilePath $jsonPath -Encoding UTF8

Write-Host ""
Write-Host "Resultado salvo em: $jsonPath" -ForegroundColor DarkGray
Write-Host ""

return $result
