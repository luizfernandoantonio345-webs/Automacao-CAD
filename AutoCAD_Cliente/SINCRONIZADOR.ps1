# =============================================================================
# ENGENHARIA CAD - SINCRONIZADOR v2.2
# Conecta com o backend, detecta e abre CAD automaticamente
# Versão robusta com conexão automática e diagnóstico detalhado
# =============================================================================

param(
    [string]$BackendUrl = "https://automacao-cad-backend.vercel.app"
)

# ===========================================================================
# SEGURANCA: Forcar TLS 1.2+ e validar URL antes de qualquer operacao de rede
# ===========================================================================
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

# Rejeitar URLs sem HTTPS para evitar Man-in-the-Middle
if ($BackendUrl -notmatch '^https://') {
    Write-Error "[SEGURANCA] BackendUrl deve usar HTTPS. Valor recebido: $BackendUrl"
    exit 1
}

# IMPORTANTE: Capturar TODOS os erros na inicializacao
$ErrorActionPreference = "Stop"

# Tentar configurar encoding (pode falhar em alguns terminais)
try {
    $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
}
catch {
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
    }
    catch {
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
$HTTP_TIMEOUT_SEC = 30
$MAX_RECONNECT_SLEEP_SEC = 10

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
    Write-Host "|           ENGENHARIA CAD - SINCRONIZADOR BRIDGE v2.2                   |" -ForegroundColor $colors.Header
    Write-Host "+=========================================================================+" -ForegroundColor $colors.Header
    Write-Host "|  Backend: $($BackendUrl.PadRight(55))|" -ForegroundColor $colors.Info
    Write-Host "|  O CAD sera aberto automaticamente se detectado                        |" -ForegroundColor $colors.Dim
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

function Get-RequestErrorSummary($err) {
    try {
        $msg = $err.Exception.Message
        $statusCode = $null
        $statusText = $null

        if ($err.Exception.Response -and $err.Exception.Response.StatusCode) {
            $statusCode = [int]$err.Exception.Response.StatusCode
            $statusText = $err.Exception.Response.StatusDescription
        }

        if ($statusCode) {
            if ($statusText) {
                return "HTTP $($statusCode) ($($statusText)): $msg"
            }
            return "HTTP $($statusCode): $msg"
        }

        return $msg
    }
    catch {
        return "Erro de rede desconhecido"
    }
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
    
    Write-Status "CAD não está rodando. Tentando abrir automaticamente..." "Info"
    
    # Procurar executável do CAD em múltiplos locais
    $cadPaths = @(
        # AutoCAD (versões recentes)
        "C:\Program Files\Autodesk\AutoCAD 2026\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2025\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2021\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD 2020\acad.exe",
        # AutoCAD LT
        "C:\Program Files\Autodesk\AutoCAD LT 2024\acad.exe",
        "C:\Program Files\Autodesk\AutoCAD LT 2023\acad.exe",
        # GstarCAD
        "C:\Program Files\Gstarsoft\GstarCAD 2024\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2023\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD 2022\gcad.exe",
        # ZWCAD
        "C:\Program Files\ZWSOFT\ZWCAD 2024\ZWCAD.exe",
        "C:\Program Files\ZWSOFT\ZWCAD 2023\ZWCAD.exe",
        # BricsCAD
        "C:\Program Files\Bricsys\BricsCAD V24\bricscad.exe",
        "C:\Program Files\Bricsys\BricsCAD V23\bricscad.exe"
    )
    
    # Também buscar via registro do Windows
    $regPaths = @(
        "HKLM:\SOFTWARE\Autodesk\AutoCAD",
        "HKLM:\SOFTWARE\Gstarsoft\GstarCAD"
    )
    
    foreach ($regPath in $regPaths) {
        try {
            if (Test-Path $regPath) {
                $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
                foreach ($v in $versions) {
                    $exePath = (Get-ItemProperty -Path $v.PSPath -Name "Location" -ErrorAction SilentlyContinue).Location
                    if ($exePath) {
                        $acadExe = Join-Path $exePath "acad.exe"
                        $gcadExe = Join-Path $exePath "gcad.exe"
                        if (Test-Path $acadExe) { $cadPaths += $acadExe }
                        if (Test-Path $gcadExe) { $cadPaths += $gcadExe }
                    }
                }
            }
        }
        catch { }
    }
    
    foreach ($cadPath in $cadPaths) {
        if (Test-Path $cadPath) {
            Write-Status "Abrindo CAD: $cadPath" "Success"
            Start-Process -FilePath $cadPath -WindowStyle Normal
            
            # Aguardar o CAD iniciar (máximo 45 segundos)
            $waited = 0
            Write-Host "  Aguardando CAD iniciar" -NoNewline -ForegroundColor $colors.Dim
            while ($waited -lt 45) {
                Start-Sleep -Seconds 3
                $waited += 3
                Write-Host "." -NoNewline -ForegroundColor $colors.Dim
                $running = Get-Process | Where-Object { $_.Name -match "acad|gcad|zwcad|bricscad" }
                if ($running) {
                    Write-Host ""
                    Write-Status "CAD iniciado com sucesso!" "Success"
                    Write-Host ""
                    Write-Host "  +----------------------------------------------------------+" -ForegroundColor $colors.Success
                    Write-Host "  |  IMPORTANTE: No AutoCAD, execute o comando FORGE_START  |" -ForegroundColor $colors.Warning
                    Write-Host "  |  para ativar o monitoramento de comandos.               |" -ForegroundColor $colors.Warning
                    Write-Host "  +----------------------------------------------------------+" -ForegroundColor $colors.Success
                    Write-Host ""
                    try { [Console]::Beep(600, 150); [Console]::Beep(800, 150); [Console]::Beep(1000, 200) } catch { }
                    Detect-CAD | Out-Null
                    return $true
                }
            }
            Write-Host ""
            Write-Status "CAD demorou para iniciar. Continuando sem ele..." "Warning"
            return $false
        }
    }
    
    Write-Status "Nenhum CAD instalado encontrado. Abra o AutoCAD manualmente." "Warning"
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
            -TimeoutSec $HTTP_TIMEOUT_SEC -ErrorAction Stop
        
        $global:isConnected = $true
        $global:lastError = $null
        return $true
    }
    catch {
        $global:isConnected = $false
        $global:lastError = Get-RequestErrorSummary $_
        return $false
    }
}

function Get-PendingCommands {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/bridge/pending" `
            -Method GET -TimeoutSec $HTTP_TIMEOUT_SEC -ErrorAction Stop
        
        $global:isConnected = $true
        $global:lastError = $null
        return $response.commands
    }
    catch {
        $global:isConnected = $false
        $global:lastError = Get-RequestErrorSummary $_
        return @()
    }
}

# Lista branca de operacoes permitidas
$ALLOWED_OPERATIONS = @(
    'draw_pipe', 'draw_line', 'draw_circle', 'draw_arc', 'draw_polyline',
    'insert_block', 'move_entity', 'rotate_entity', 'scale_entity',
    'set_layer', 'set_color', 'set_linetype',
    'generate_bom', 'export_dxf', 'save_drawing',
    'clash_check', 'run_script'
)

function Process-Command($cmd) {
    # Validar operacao contra a lista branca
    if ($cmd.operation -notin $ALLOWED_OPERATIONS) {
        Write-Status "[SEGURANCA] Operacao rejeitada (nao permitida): $($cmd.operation)" "Error"
        return $false
    }

    # Validar que o codigo LISP nao contem chamadas de sistema perigosas
    $dangerousPatterns = @('shell', 'command', 'startapp', 'dos', 'exec', 'system')
    $lispLower = $cmd.lisp_code.ToLower()
    foreach ($pattern in $dangerousPatterns) {
        if ($lispLower -match "\($pattern\s") {
            Write-Status "[SEGURANCA] Codigo LISP rejeitado (padrao proibido: $pattern)" "Error"
            return $false
        }
    }

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
    }
    catch {
        Write-Status "Nao foi possivel criar $primaryPath (requer admin)" "Warning"
    }
    
    # Usar fallback na pasta do usuário
    try {
        if (-not (Test-Path $fallbackPath)) {
            New-Item -ItemType Directory -Path $fallbackPath -Force -ErrorAction Stop | Out-Null
        }
        $script:DROP_PATH = $fallbackPath
        Write-Status "Usando pasta alternativa: $fallbackPath" "Warning"
    }
    catch {
        Write-Status "ERRO: Nao foi possivel criar pasta de comandos!" "Error"
        $script:DROP_PATH = $fallbackPath  # Tentar usar mesmo assim
    }
}

# -----------------------------------------------------------------------------
# MAIN LOOP - Execucao principal com tratamento de erros
# -----------------------------------------------------------------------------

try {
    Write-Header
}
catch {
    Write-Host "ENGENHARIA CAD - SINCRONIZADOR v2.1" -ForegroundColor Cyan
    Write-Host ""
}

# Após inicialização visual, ignorar erros de rede para não fechar o loop
$ErrorActionPreference = "SilentlyContinue"

# Configurar pasta de comandos (com fallback)
try {
    Ensure-DropFolder
}
catch {
    Write-Status "Aviso: Erro ao criar pasta de comandos" "Warning"
    $script:DROP_PATH = Join-Path $env:USERPROFILE "AutoCAD_Drop"
}

# Detectar CAD (não é crítico se falhar)
try {
    $cadDetected = Detect-CAD
}
catch {
    Write-Status "Aviso: Erro ao detectar CAD - continuando..." "Warning"
    $cadDetected = $false
}

# Sempre tentar abrir CAD automaticamente se não estiver rodando
try {
    $cadStarted = Start-AutoCADIfNeeded
    if ($cadStarted) {
        # Re-detectar após abrir
        Detect-CAD | Out-Null
    }
}
catch {
    Write-Status "Aviso: Nao foi possivel iniciar CAD automaticamente" "Warning"
}

Write-Status "Iniciando conexao com o backend..." "Info"

# Tentar conectar (não é crítico se falhar)
try {
    $preflightConnected = Send-ConnectionStatus $true
    if ($preflightConnected) {
        Write-Status "Conexao com bridge estabelecida." "Success"
    }
    else {
        Write-Status "Bridge indisponivel no momento: $($global:lastError)" "Warning"
    }
}
catch {
    Write-Status "Aviso: Backend offline - tentarei reconectar..." "Warning"
}

$lastDashboard = Get-Date
$lastHeartbeat = Get-Date
$reconnectAttempts = 0

Write-Host ""
Write-Host "+=========================================================================+" -ForegroundColor $colors.Success
Write-Host "|                   SINCRONIZADOR ATIVO E CONECTADO                      |" -ForegroundColor $colors.Success
Write-Host "+=========================================================================+" -ForegroundColor $colors.Success
Write-Host ""
Write-Host "  O sistema esta pronto para receber comandos do site web." -ForegroundColor $colors.Info
Write-Host "  Mantenha esta janela aberta enquanto estiver trabalhando." -ForegroundColor $colors.Dim
Write-Host ""
Write-Host "  Pressione Ctrl+C para encerrar" -ForegroundColor $colors.Dim
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
            $wasConnected = $global:isConnected
            $sent = Send-ConnectionStatus $true
            if ($sent) {
                if (-not $wasConnected -and $reconnectAttempts -gt 0) {
                    Write-Host ""
                    Write-Status "RECONECTADO! Backend online novamente." "Success"
                    try { [Console]::Beep(800, 100); [Console]::Beep(1000, 100) } catch { }
                }
                $reconnectAttempts = 0
            }
            else {
                $reconnectAttempts++
                if ($reconnectAttempts % 12 -eq 0) {
                    # A cada minuto
                    $details = if ($global:lastError) { " | ultimo erro: $($global:lastError)" } else { "" }
                    Write-Status "Backend offline há $([math]::Floor($reconnectAttempts * 5 / 60)) min - tentando reconectar...$details" "Warning"
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
                    }
                    catch {
                        Write-Status "Erro ao processar comando: $_" "Error"
                    }
                }
            }
        }
        
        # Indicador visual de atividade
        Write-Host "." -NoNewline -ForegroundColor $colors.Dim

        $sleepSecs = if ($global:isConnected) {
            $POLL_INTERVAL
        }
        else {
            [Math]::Min($POLL_INTERVAL + [Math]::Floor($reconnectAttempts / 4), $MAX_RECONNECT_SLEEP_SEC)
        }
        Start-Sleep -Seconds $sleepSecs
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
