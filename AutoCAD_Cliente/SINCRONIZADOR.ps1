# =============================================================================
# ENGENHARIA CAD - SINCRONIZADOR v2.0
# Conecta com o backend, detecta CAD automaticamente, mostra status em tempo real
# =============================================================================

param(
    [string]$BackendUrl = "https://automacao-cad-backend.vercel.app"
)

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Cores para o terminal
$colors = @{
    Success = "Green"
    Error   = "Red"
    Warning = "Yellow"
    Info    = "Cyan"
    Dim     = "DarkGray"
    Header  = "Magenta"
}

$DROP_PATH = "C:\AutoCAD_Drop"
$POLL_INTERVAL = 3
$HEARTBEAT_INTERVAL = 5

# Estado global
$global:isConnected = $false
$global:cadInfo = @{ type = $null; version = $null }
$global:commandsExecuted = 0
$global:lastError = $null
$global:startTime = Get-Date

function Write-Header {
    Clear-Host
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor $colors.Header
    Write-Host "║           ENGENHARIA CAD - SINCRONIZADOR BRIDGE v2.0                  ║" -ForegroundColor $colors.Header
    Write-Host "╠═══════════════════════════════════════════════════════════════════════╣" -ForegroundColor $colors.Header
    Write-Host "║  Backend: $($BackendUrl.PadRight(55))║" -ForegroundColor $colors.Info
    Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor $colors.Header
    Write-Host ""
}

function Write-Status($msg, $type = "Info") {
    $color = $colors[$type]
    if (-not $color) { $color = "White" }
    $timestamp = (Get-Date).ToString("HH:mm:ss")
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor $colors.Dim
    Write-Host $msg -ForegroundColor $color
}

function Show-Dashboard {
    $uptime = (Get-Date) - $global:startTime
    $uptimeStr = "{0:D2}:{1:D2}:{2:D2}" -f $uptime.Hours, $uptime.Minutes, $uptime.Seconds
    
    $connStatus = if ($global:isConnected) { "🟢 CONECTADO" } else { "🔴 DESCONECTADO" }
    $connColor = if ($global:isConnected) { $colors.Success } else { $colors.Error }
    
    $cadStatus = if ($global:cadInfo.type) { "$($global:cadInfo.type) $($global:cadInfo.version)" } else { "Não detectado" }
    
    Write-Host ""
    Write-Host "┌─────────────────────────────────────────────────────────────────────┐" -ForegroundColor $colors.Info
    Write-Host "│ STATUS: " -NoNewline -ForegroundColor $colors.Info
    Write-Host $connStatus.PadRight(20) -NoNewline -ForegroundColor $connColor
    Write-Host "Uptime: $uptimeStr".PadRight(30) -NoNewline -ForegroundColor $colors.Dim
    Write-Host "│" -ForegroundColor $colors.Info
    Write-Host "│ CAD: $($cadStatus.PadRight(30))" -NoNewline -ForegroundColor $colors.Info
    Write-Host "Comandos: $($global:commandsExecuted)".PadRight(24) -NoNewline -ForegroundColor $colors.Success
    Write-Host "│" -ForegroundColor $colors.Info
    Write-Host "└─────────────────────────────────────────────────────────────────────┘" -ForegroundColor $colors.Info
    Write-Host ""
}

function Detect-CAD {
    Write-Status "Detectando CAD instalado..." "Info"
    
    # Importar resultado do detector se existir
    $jsonPath = Join-Path $env:TEMP "engcad_detection.json"
    if (Test-Path $jsonPath) {
        try {
            $detection = Get-Content $jsonPath -Raw | ConvertFrom-Json
            if ($detection.found -and $detection.selected) {
                $global:cadInfo.type = $detection.selected.type
                $global:cadInfo.version = $detection.selected.version
                Write-Status "CAD detectado: $($global:cadInfo.type) $($global:cadInfo.version)" "Success"
                return $true
            }
        }
        catch {}
    }
    
    # Detecção rápida
    $processes = Get-Process | Where-Object { $_.Name -match "acad|gcad|zwcad|bricscad" }
    if ($processes) {
        $proc = $processes[0]
        $global:cadInfo.type = switch -Regex ($proc.Name) {
            "acad" { "AutoCAD" }
            "gcad" { "GstarCAD" }
            "zwcad" { "ZWCAD" }
            "bricscad" { "BricsCAD" }
            default { "CAD" }
        }
        $global:cadInfo.version = "Em execução"
        Write-Status "CAD em execução: $($global:cadInfo.type)" "Success"
        return $true
    }
    
    # Verificar instalações comuns
    $paths = @(
        @{ Path = "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe"; Type = "AutoCAD"; Version = "2024" },
        @{ Path = "C:\Program Files\Autodesk\AutoCAD 2023\acad.exe"; Type = "AutoCAD"; Version = "2023" },
        @{ Path = "C:\Program Files\Gstarsoft\GstarCAD 2024\gcad.exe"; Type = "GstarCAD"; Version = "2024" },
        @{ Path = "C:\Program Files\Gstarsoft\GstarCAD 2023\gcad.exe"; Type = "GstarCAD"; Version = "2023" }
    )
    
    foreach ($p in $paths) {
        if (Test-Path $p.Path) {
            $global:cadInfo.type = $p.Type
            $global:cadInfo.version = $p.Version
            Write-Status "CAD encontrado: $($p.Type) $($p.Version)" "Success"
            return $true
        }
    }
    
    Write-Status "Nenhum CAD detectado. O sistema funcionará em modo offline." "Warning"
    $global:cadInfo.type = "Desconhecido"
    $global:cadInfo.version = "-"
    return $false
}

function Send-ConnectionStatus($connected) {
    $body = @{
        connected   = $connected
        cad_type    = $global:cadInfo.type
        cad_version = $global:cadInfo.version
        machine     = $env:COMPUTERNAME
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/bridge/connection" `
            -Method POST -Body $body -ContentType "application/json" `
            -TimeoutSec 10 -ErrorAction Stop
        
        $global:isConnected = $true
        return $true
    }
    catch {
        $global:isConnected = $false
        $global:lastError = $_.Exception.Message
        return $false
    }
}

function Get-PendingCommands {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/bridge/pending" `
            -Method GET -TimeoutSec 10 -ErrorAction Stop
        
        $global:isConnected = $true
        return $response.commands
    }
    catch {
        $global:isConnected = $false
        $global:lastError = $_.Exception.Message
        return @()
    }
}

function Process-Command($cmd) {
    $filename = "cmd_$($cmd.id)_$(Get-Date -Format 'yyyyMMdd_HHmmss').lsp"
    $filepath = Join-Path $DROP_PATH $filename
    
    Write-Status "═══════════════════════════════════════════════════════════════" "Header"
    Write-Status "  COMANDO RECEBIDO! ID: $($cmd.id)" "Success"
    Write-Status "  Operação: $($cmd.operation)" "Info"
    Write-Status "═══════════════════════════════════════════════════════════════" "Header"
    
    try {
        # Salvar arquivo LISP
        $cmd.lisp_code | Out-File -FilePath $filepath -Encoding UTF8 -Force
        Write-Status "Arquivo salvo: $filename" "Success"
        
        # Confirmar recebimento
        $ackResponse = Invoke-RestMethod -Uri "$BackendUrl/api/bridge/ack/$($cmd.id)" `
            -Method POST -TimeoutSec 10 -ErrorAction Stop
        
        $global:commandsExecuted++
        Write-Status "Comando $($cmd.id) confirmado. AutoCAD irá executar." "Success"
        
        # Beep de sucesso
        [Console]::Beep(800, 150)
        [Console]::Beep(1000, 150)
        
        return $true
    }
    catch {
        Write-Status "Erro ao processar comando: $_" "Error"
        return $false
    }
}

function Ensure-DropFolder {
    if (-not (Test-Path $DROP_PATH)) {
        New-Item -ItemType Directory -Path $DROP_PATH -Force | Out-Null
        Write-Status "Pasta $DROP_PATH criada" "Success"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

Write-Header
Ensure-DropFolder
Detect-CAD

Write-Status "Iniciando conexão com o backend..." "Info"
Send-ConnectionStatus $true

$lastDashboard = Get-Date
$lastHeartbeat = Get-Date

Write-Host ""
Write-Status "🎯 Aguardando comandos do sistema web..." "Success"
Write-Host ""
Write-Host "Pressione Ctrl+C para encerrar" -ForegroundColor $colors.Dim
Write-Host ""

try {
    while ($true) {
        # Atualizar dashboard a cada 10 segundos
        if (((Get-Date) - $lastDashboard).TotalSeconds -ge 10) {
            Show-Dashboard
            $lastDashboard = Get-Date
        }
        
        # Heartbeat a cada 5 segundos
        if (((Get-Date) - $lastHeartbeat).TotalSeconds -ge $HEARTBEAT_INTERVAL) {
            Send-ConnectionStatus $true | Out-Null
            $lastHeartbeat = Get-Date
        }
        
        # Buscar comandos pendentes
        $commands = Get-PendingCommands
        
        if ($commands -and $commands.Count -gt 0) {
            foreach ($cmd in $commands) {
                Process-Command $cmd
            }
        }
        
        # Cursor piscando para indicar que está ativo
        Write-Host "." -NoNewline -ForegroundColor $colors.Dim
        
        Start-Sleep -Seconds $POLL_INTERVAL
    }
}
finally {
    Write-Host ""
    Write-Status "Desconectando do backend..." "Warning"
    Send-ConnectionStatus $false
    Write-Status "Sincronizador encerrado." "Info"
}
