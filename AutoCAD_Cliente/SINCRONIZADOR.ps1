# =============================================================================
# ENGENHARIA CAD - SINCRONIZADOR v2.1
# Conecta com o backend, detecta CAD automaticamente, mostra status em tempo real
# Versão robusta com tratamento de TODOS os erros possíveis
# =============================================================================

param(
    [string]$BackendUrl = "https://automacao-cad-backend.vercel.app"
)

# IMPORTANTE: Capturar TODOS os erros na inicialização
$ErrorActionPreference = "Stop"

# Tentar configurar encoding (pode falhar em alguns terminais)
try {
    $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignorar erro de encoding - não é crítico
}

# Garantir que a janela NUNCA feche sem feedback
trap {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  ERRO NO SINCRONIZADOR" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Detalhes do erro:" -ForegroundColor Yellow
    Write-Host "$_" -ForegroundColor White
    Write-Host ""
    Write-Host "Stack trace:" -ForegroundColor DarkGray
    Write-Host "$($_.ScriptStackTrace)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor Cyan
    Write-Host ""
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
        Start-Sleep -Seconds 30
    }
    exit 1
}

# Cores para o terminal
$colors = @{
    Success = "Green"
    Error   = "Red"
    Warning = "Yellow"
    Info    = "Cyan"
    Dim     = "DarkGray"
    Header  = "Magenta"
}

$DROP_PATH = $null  # Será definido em Ensure-DropFolder
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
    Write-Host "+=========================================================================+" -ForegroundColor $colors.Header
    Write-Host "|           ENGENHARIA CAD - SINCRONIZADOR BRIDGE v2.1                   |" -ForegroundColor $colors.Header
    Write-Host "+=========================================================================+" -ForegroundColor $colors.Header
    Write-Host "|  Backend: $($BackendUrl.PadRight(55))|" -ForegroundColor $colors.Info
    Write-Host "+=========================================================================+" -ForegroundColor $colors.Header
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
    
    $connStatus = if ($global:isConnected) { "[OK] CONECTADO" } else { "[X] DESCONECTADO" }
    $connColor = if ($global:isConnected) { $colors.Success } else { $colors.Error }
    
    $cadStatus = if ($global:cadInfo.type) { "$($global:cadInfo.type) $($global:cadInfo.version)" } else { "Nao detectado" }
    
    Write-Host ""
    Write-Host "+-----------------------------------------------------------------------+" -ForegroundColor $colors.Info
    Write-Host "| STATUS: " -NoNewline -ForegroundColor $colors.Info
    Write-Host $connStatus.PadRight(20) -NoNewline -ForegroundColor $connColor
    Write-Host "Uptime: $uptimeStr".PadRight(30) -NoNewline -ForegroundColor $colors.Dim
    Write-Host "|" -ForegroundColor $colors.Info
    Write-Host "| CAD: $($cadStatus.PadRight(30))" -NoNewline -ForegroundColor $colors.Info
    Write-Host "Comandos: $($global:commandsExecuted)".PadRight(24) -NoNewline -ForegroundColor $colors.Success
    Write-Host "|" -ForegroundColor $colors.Info
    Write-Host "+-----------------------------------------------------------------------+" -ForegroundColor $colors.Info
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

function Start-AutoCADIfNeeded {
    # Se CAD já está rodando, não precisa abrir
    $processes = Get-Process | Where-Object { $_.Name -match "acad|gcad|zwcad|bricscad" }
    if ($processes) {
        Write-Status "CAD já está em execução." "Info"
        return $true
    }
    
    # Verificar se existe licença válida no backend
    try {
        $licenseCheck = Invoke-RestMethod -Uri "$BackendUrl/api/license/status/$env:USERNAME" `
            -Method GET -TimeoutSec 10 -ErrorAction Stop
        
        if ($licenseCheck.tier -and $licenseCheck.tier -ne "demo") {
            Write-Status "Licença $($licenseCheck.tier) detectada. Iniciando CAD automaticamente..." "Success"
        }
        else {
            Write-Status "Licença demo — CAD não será aberto automaticamente." "Warning"
            return $false
        }
    }
    catch {
        Write-Status "Não foi possível verificar licença. Tentando abrir CAD..." "Warning"
    }
    
    # Procurar executável do CAD
    $cadPaths = @(
        "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2024\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2023\gcad.exe"
    )
    
    foreach ($cadPath in $cadPaths) {
        if (Test-Path $cadPath) {
            Write-Status "Abrindo CAD: $cadPath" "Success"
            Start-Process -FilePath $cadPath -WindowStyle Normal
            
            # Aguardar o CAD iniciar (máximo 30 segundos)
            $waited = 0
            while ($waited -lt 30) {
                Start-Sleep -Seconds 2
                $waited += 2
                $running = Get-Process | Where-Object { $_.Name -match "acad|gcad" }
                if ($running) {
                    Write-Status "CAD iniciado com sucesso!" "Success"
                    [Console]::Beep(600, 200)
                    [Console]::Beep(800, 200)
                    [Console]::Beep(1000, 300)
                    Detect-CAD | Out-Null
                    return $true
                }
            }
            Write-Status "CAD demorou para iniciar. Continuando..." "Warning"
            return $false
        }
    }
    
    Write-Status "Nenhum CAD instalado encontrado." "Warning"
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
    
    Write-Status "================================================================" "Header"
    Write-Status "  COMANDO RECEBIDO! ID: $($cmd.id)" "Success"
    Write-Status "  Operacao: $($cmd.operation)" "Info"
    Write-Status "================================================================" "Header"
    
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
    # Tentar C:\AutoCAD_Drop primeiro (preferido para LSP)
    $primaryPath = "C:\AutoCAD_Drop"
    $fallbackPath = Join-Path $env:USERPROFILE "AutoCAD_Drop"
    
    # Tentar criar a pasta primária
    try {
        if (-not (Test-Path $primaryPath)) {
            New-Item -ItemType Directory -Path $primaryPath -Force -ErrorAction Stop | Out-Null
        }
        $script:DROP_PATH = $primaryPath
        Write-Status "Pasta de comandos: $primaryPath" "Success"
        return
    } catch {
        Write-Status "Nao foi possivel criar $primaryPath (requer admin)" "Warning"
    }
    
    # Usar fallback na pasta do usuário
    try {
        if (-not (Test-Path $fallbackPath)) {
            New-Item -ItemType Directory -Path $fallbackPath -Force -ErrorAction Stop | Out-Null
        }
        $script:DROP_PATH = $fallbackPath
        Write-Status "Usando pasta alternativa: $fallbackPath" "Warning"
    } catch {
        Write-Status "ERRO: Nao foi possivel criar pasta de comandos!" "Error"
        $script:DROP_PATH = $fallbackPath  # Tentar usar mesmo assim
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP - Execução principal com tratamento de erros
# ─────────────────────────────────────────────────────────────────────────────

try {
    Write-Header
} catch {
    Write-Host "ENGENHARIA CAD - SINCRONIZADOR v2.1" -ForegroundColor Cyan
    Write-Host ""
}

# Após inicialização visual, ignorar erros de rede para não fechar o loop
$ErrorActionPreference = "SilentlyContinue"

# Configurar pasta de comandos (com fallback)
try {
    Ensure-DropFolder
} catch {
    Write-Status "Aviso: Erro ao criar pasta de comandos" "Warning"
    $script:DROP_PATH = Join-Path $env:USERPROFILE "AutoCAD_Drop"
}

# Detectar CAD (não é crítico se falhar)
try {
    $cadDetected = Detect-CAD
} catch {
    Write-Status "Aviso: Erro ao detectar CAD - continuando..." "Warning"
    $cadDetected = $false
}

# Tentar abrir CAD se não detectado (não é crítico)
if (-not $cadDetected) {
    try {
        Start-AutoCADIfNeeded | Out-Null
    } catch {
        Write-Status "Aviso: Nao foi possivel iniciar CAD automaticamente" "Warning"
    }
}

Write-Status "Iniciando conexao com o backend..." "Info"

# Tentar conectar (não é crítico se falhar)
try {
    Send-ConnectionStatus $true | Out-Null
} catch {
    Write-Status "Aviso: Backend offline - tentarei reconectar..." "Warning"
}

$lastDashboard = Get-Date
$lastHeartbeat = Get-Date
$reconnectAttempts = 0

Write-Host ""
Write-Status "Aguardando comandos do sistema web..." "Success"
Write-Host ""
Write-Host "Pressione Ctrl+C para encerrar" -ForegroundColor $colors.Dim
Write-Host ""

# Loop principal infinito - NUNCA deve fechar sozinho
while ($true) {
    try {
        # Atualizar dashboard a cada 10 segundos
        if (((Get-Date) - $lastDashboard).TotalSeconds -ge 10) {
            try { Show-Dashboard } catch { }
            $lastDashboard = Get-Date
        }
        
        # Heartbeat a cada 5 segundos
        if (((Get-Date) - $lastHeartbeat).TotalSeconds -ge $HEARTBEAT_INTERVAL) {
            $sent = Send-ConnectionStatus $true
            if ($sent) {
                $reconnectAttempts = 0
            } else {
                $reconnectAttempts++
                if ($reconnectAttempts % 12 -eq 0) {  # A cada minuto
                    Write-Status "Backend offline há $([math]::Floor($reconnectAttempts * 5 / 60)) min - tentando reconectar..." "Warning"
                }
            }
            $lastHeartbeat = Get-Date
        }
        
        # Buscar comandos pendentes (só se conectado)
        if ($global:isConnected) {
            $commands = Get-PendingCommands
            
            if ($commands -and $commands.Count -gt 0) {
                foreach ($cmd in $commands) {
                    try {
                        Process-Command $cmd
                    } catch {
                        Write-Status "Erro ao processar comando: $_" "Error"
                    }
                }
            }
        }
        
        # Indicador visual de atividade
        Write-Host "." -NoNewline -ForegroundColor $colors.Dim
        
        Start-Sleep -Seconds $POLL_INTERVAL
    }
    catch {
        # Capturar qualquer erro no loop e continuar
        Write-Status "Erro no loop: $_ - continuando..." "Warning"
        Start-Sleep -Seconds 5
    }
}

# Este código só executa se o loop for interrompido (Ctrl+C)
Write-Host ""
Write-Status "Desconectando do backend..." "Warning"
try { Send-ConnectionStatus $false } catch { }
Write-Status "Sincronizador encerrado." "Info"
Write-Host ""
Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor Cyan
try { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") } catch { Start-Sleep -Seconds 5 }
