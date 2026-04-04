# ════════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD - SINCRONIZADOR INTELIGENTE v2.0
# Detecta AutoCAD automaticamente, abre e configura tudo sozinho!
# ════════════════════════════════════════════════════════════════════════════

$Host.UI.RawUI.WindowTitle = "Engenharia CAD - Sincronizador Inteligente"
$ErrorActionPreference = "SilentlyContinue"

# ── Configurações ──
$BACKEND_URL = "https://automacao-cad-backend.vercel.app"
$DROP_FOLDER = "C:\AutoCAD_Drop"
$LISP_FOLDER = "C:\EngenhariaCAD"
$POLL_INTERVAL = 3

# ── Cores ──
function Write-Status($msg) { Write-Host "[STATUS] $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Erro($msg) { Write-Host "[ERRO] $msg" -ForegroundColor Red }
function Write-Aviso($msg) { Write-Host "[AVISO] $msg" -ForegroundColor Yellow }
function Write-Cmd($msg) { Write-Host "[COMANDO] $msg" -ForegroundColor Magenta }

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Detectar AutoCAD/GstarCAD instalado
# ════════════════════════════════════════════════════════════════════════════
function Find-CADSoftware {
    Write-Status "Procurando softwares CAD instalados..."
    
    $cadPrograms = @()
    
    # Procurar no registro - AutoCAD
    $autocadKeys = @(
        "HKLM:\SOFTWARE\Autodesk\AutoCAD",
        "HKLM:\SOFTWARE\WOW6432Node\Autodesk\AutoCAD"
    )
    
    foreach ($key in $autocadKeys) {
        if (Test-Path $key) {
            $versions = Get-ChildItem $key -ErrorAction SilentlyContinue
            foreach ($ver in $versions) {
                $subKeys = Get-ChildItem $ver.PSPath -ErrorAction SilentlyContinue
                foreach ($sub in $subKeys) {
                    $acad = Get-ItemProperty $sub.PSPath -Name "AcadLocation" -ErrorAction SilentlyContinue
                    if ($acad.AcadLocation) {
                        $exePath = Join-Path $acad.AcadLocation "acad.exe"
                        if (Test-Path $exePath) {
                            $cadPrograms += @{
                                Name = "AutoCAD $($ver.PSChildName)"
                                Path = $exePath
                                Type = "AutoCAD"
                                Version = $ver.PSChildName
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Procurar GstarCAD
    $gstarPaths = @(
        "C:\Program Files\Gstarsoft\GstarCAD2024\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD2023\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD2022\gcad.exe",
        "C:\Program Files\Gstarsoft\GstarCAD\gcad.exe",
        "C:\Program Files (x86)\Gstarsoft\GstarCAD2024\gcad.exe",
        "C:\Program Files (x86)\Gstarsoft\GstarCAD2023\gcad.exe"
    )
    
    foreach ($path in $gstarPaths) {
        if (Test-Path $path) {
            $version = [regex]::Match($path, "GstarCAD(\d+)?").Groups[1].Value
            if (-not $version) { $version = "Unknown" }
            $cadPrograms += @{
                Name = "GstarCAD $version"
                Path = $path
                Type = "GstarCAD"
                Version = $version
            }
        }
    }
    
    # Procurar por processos já em execução
    $runningCAD = Get-Process -Name "acad", "gcad", "accoreconsole" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($runningCAD) {
        $cadPrograms = @(@{
            Name = "$($runningCAD.ProcessName) (Em execução)"
            Path = $runningCAD.Path
            Type = if ($runningCAD.ProcessName -like "*gcad*") { "GstarCAD" } else { "AutoCAD" }
            Version = "Running"
            Running = $true
        }) + $cadPrograms
    }
    
    # Procurar em Program Files se não encontrou
    if ($cadPrograms.Count -eq 0) {
        $searchPaths = @(
            "C:\Program Files\Autodesk\*\acad.exe",
            "C:\Program Files (x86)\Autodesk\*\acad.exe",
            "C:\Program Files\Gstarsoft\*\gcad.exe"
        )
        
        foreach ($pattern in $searchPaths) {
            $found = Get-ChildItem $pattern -ErrorAction SilentlyContinue
            foreach ($f in $found) {
                $cadPrograms += @{
                    Name = $f.Directory.Name
                    Path = $f.FullName
                    Type = if ($f.Name -eq "gcad.exe") { "GstarCAD" } else { "AutoCAD" }
                    Version = $f.Directory.Name
                }
            }
        }
    }
    
    return $cadPrograms
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Abrir CAD
# ════════════════════════════════════════════════════════════════════════════
function Start-CADSoftware($cadInfo) {
    if ($cadInfo.Running) {
        Write-OK "$($cadInfo.Name) já está em execução!"
        return $true
    }
    
    Write-Status "Abrindo $($cadInfo.Name)..."
    Start-Process $cadInfo.Path
    
    # Aguardar inicialização
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        $proc = Get-Process -Name "acad", "gcad" -ErrorAction SilentlyContinue
        if ($proc) {
            Start-Sleep -Seconds 5  # Dar tempo para carregar
            Write-OK "$($cadInfo.Name) iniciado com sucesso!"
            return $true
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
        Write-Host "." -NoNewline
    }
    
    Write-Erro "Timeout aguardando $($cadInfo.Name) iniciar"
    return $false
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Configurar pastas
# ════════════════════════════════════════════════════════════════════════════
function Initialize-Folders {
    Write-Status "Configurando pastas do sistema..."
    
    # Criar pasta de comandos
    if (-not (Test-Path $DROP_FOLDER)) {
        New-Item -ItemType Directory -Path $DROP_FOLDER -Force | Out-Null
        Write-OK "Pasta $DROP_FOLDER criada"
    }
    
    # Criar pasta do LISP
    if (-not (Test-Path $LISP_FOLDER)) {
        New-Item -ItemType Directory -Path $LISP_FOLDER -Force | Out-Null
        Write-OK "Pasta $LISP_FOLDER criada"
    }
    
    return $true
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Instalar LISP
# ════════════════════════════════════════════════════════════════════════════
function Install-LispFiles {
    $lispPath = Join-Path $LISP_FOLDER "forge_vigilante.lsp"
    
    Write-Status "Verificando arquivo LISP..."
    
    # Se já existe, verificar se precisa atualizar
    if (Test-Path $lispPath) {
        Write-OK "forge_vigilante.lsp já está instalado"
        return $true
    }
    
    # Procurar no diretório atual
    $localLisp = Join-Path $PSScriptRoot "forge_vigilante.lsp"
    if (Test-Path $localLisp) {
        Copy-Item $localLisp $lispPath -Force
        Write-OK "LISP copiado para $lispPath"
        return $true
    }
    
    # Criar LISP básico se não existir
    Write-Aviso "Criando forge_vigilante.lsp..."
    
    $lispContent = @'
;;; ═══════════════════════════════════════════════════════════════════════════
;;; ENGENHARIA CAD - FORGE VIGILANTE v2.0
;;; Monitor de comandos do sistema web
;;; ═══════════════════════════════════════════════════════════════════════════

(vl-load-com)

(defun C:FORGE_START ()
  (princ "\n╔═══════════════════════════════════════════════════════════════╗")
  (princ "\n║   ENGENHARIA CAD - FORGE VIGILANTE ATIVADO                   ║")
  (princ "\n║   Monitorando pasta: C:\\AutoCAD_Drop\\                        ║")
  (princ "\n╚═══════════════════════════════════════════════════════════════╝")
  (setq *forge-running* T)
  (forge-monitor-loop)
  (princ)
)

(defun C:FORGE_STOP ()
  (setq *forge-running* nil)
  (princ "\n[FORGE] Monitor desativado.")
  (princ)
)

(defun forge-monitor-loop ()
  (if *forge-running*
    (progn
      (forge-check-commands)
      (vl-cmdf "_.DELAY" 1000)
      (forge-monitor-loop)
    )
  )
)

(defun forge-check-commands ()
  (setq cmd-files (vl-directory-files "C:\\AutoCAD_Drop" "*.lsp" 1))
  (foreach f cmd-files
    (setq fpath (strcat "C:\\AutoCAD_Drop\\" f))
    (princ (strcat "\n[FORGE] Executando: " f))
    (load fpath)
    (vl-file-delete fpath)
  )
)

(defun C:FORGE_TEST ()
  (command "._CIRCLE" "0,0" "100")
  (command "._ZOOM" "E")
  (princ "\n[FORGE] Teste OK - Circulo desenhado!")
  (princ)
)

(princ "\n[FORGE VIGILANTE] Carregado! Digite FORGE_START para ativar.")
(princ)
'@
    
    $lispContent | Out-File -FilePath $lispPath -Encoding UTF8
    Write-OK "forge_vigilante.lsp criado em $lispPath"
    return $true
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Notificar backend sobre conexão
# ════════════════════════════════════════════════════════════════════════════
function Send-ConnectionStatus($connected, $cadInfo) {
    try {
        $body = @{
            connected = $connected
            cad_type = $cadInfo.Type
            cad_version = $cadInfo.Version
            timestamp = (Get-Date).ToString("o")
            machine = $env:COMPUTERNAME
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$BACKEND_URL/api/bridge/connection" `
            -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
        
        if ($connected) {
            Write-OK "Status CONECTADO enviado ao servidor!"
        } else {
            Write-Aviso "Status DESCONECTADO enviado ao servidor"
        }
    } catch {
        # Endpoint pode não existir ainda, ignorar
    }
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO: Loop principal de polling
# ════════════════════════════════════════════════════════════════════════════
function Start-CommandPolling($cadInfo) {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║        ENGENHARIA CAD - SINCRONIZADOR ATIVO                      ║" -ForegroundColor Green  
    Write-Host "║                                                                   ║" -ForegroundColor Green
    Write-Host "║   CAD: $($cadInfo.Name.PadRight(50))  ║" -ForegroundColor Green
    Write-Host "║   Pasta de comandos: $($DROP_FOLDER.PadRight(40))  ║" -ForegroundColor Green
    Write-Host "║                                                                   ║" -ForegroundColor Green
    Write-Host "║   IMPORTANTE: No $($cadInfo.Type), execute:                          ║" -ForegroundColor Yellow
    Write-Host "║   1. APPLOAD -> Selecione $LISP_FOLDER\forge_vigilante.lsp    ║" -ForegroundColor Yellow
    Write-Host "║   2. Digite FORGE_START e pressione Enter                        ║" -ForegroundColor Yellow
    Write-Host "║                                                                   ║" -ForegroundColor Green
    Write-Host "║   Pressione Ctrl+C para encerrar                                 ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    $connected = $false
    $lastCommandId = 0
    $commandsExecuted = 0
    
    while ($true) {
        try {
            # Buscar comandos pendentes
            $response = Invoke-RestMethod -Uri "$BACKEND_URL/api/bridge/pending" `
                -Method GET -TimeoutSec 10
            
            if (-not $connected) {
                $connected = $true
                Send-ConnectionStatus $true $cadInfo
                Write-OK "Conectado ao servidor! Aguardando comandos..."
            }
            
            if ($response.commands -and $response.commands.Count -gt 0) {
                foreach ($cmd in $response.commands) {
                    if ($cmd.id -gt $lastCommandId) {
                        Write-Cmd "Recebido: $($cmd.operation) (ID: $($cmd.id))"
                        
                        # Salvar LISP na pasta de comandos
                        $filename = "cmd_$($cmd.id)_$(Get-Date -Format 'HHmmss').lsp"
                        $filepath = Join-Path $DROP_FOLDER $filename
                        
                        $cmd.lisp_code | Out-File -FilePath $filepath -Encoding UTF8
                        Write-OK "Comando salvo: $filename"
                        
                        # Confirmar execução
                        try {
                            Invoke-RestMethod -Uri "$BACKEND_URL/api/bridge/ack/$($cmd.id)" `
                                -Method POST -TimeoutSec 5 | Out-Null
                        } catch {}
                        
                        $lastCommandId = $cmd.id
                        $commandsExecuted++
                        
                        Write-OK "Total de comandos executados: $commandsExecuted"
                    }
                }
            }
            
            # Mostrar heartbeat a cada 30 segundos
            if ((Get-Date).Second -lt 3) {
                Write-Host "." -NoNewline -ForegroundColor DarkGray
            }
            
        } catch {
            if ($connected) {
                $connected = $false
                Send-ConnectionStatus $false $cadInfo
                Write-Erro "Conexão perdida com o servidor!"
            }
            Write-Aviso "Tentando reconectar em ${POLL_INTERVAL}s..."
        }
        
        Start-Sleep -Seconds $POLL_INTERVAL
    }
}

# ════════════════════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

Clear-Host
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                   ║" -ForegroundColor Cyan
Write-Host "║       ███████╗███╗   ██╗ ██████╗ ███████╗███╗   ██╗██╗  ██╗      ║" -ForegroundColor Cyan
Write-Host "║       ██╔════╝████╗  ██║██╔════╝ ██╔════╝████╗  ██║██║  ██║      ║" -ForegroundColor Cyan
Write-Host "║       █████╗  ██╔██╗ ██║██║  ███╗█████╗  ██╔██╗ ██║███████║      ║" -ForegroundColor Cyan
Write-Host "║       ██╔══╝  ██║╚██╗██║██║   ██║██╔══╝  ██║╚██╗██║██╔══██║      ║" -ForegroundColor Cyan
Write-Host "║       ███████╗██║ ╚████║╚██████╔╝███████╗██║ ╚████║██║  ██║      ║" -ForegroundColor Cyan
Write-Host "║       ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝      ║" -ForegroundColor Cyan
Write-Host "║                      CAD AUTOMATION SYSTEM                       ║" -ForegroundColor Cyan
Write-Host "║                         Versão 2.0                               ║" -ForegroundColor Cyan
Write-Host "║                                                                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Passo 1: Detectar CAD
$cadList = Find-CADSoftware

if ($cadList.Count -eq 0) {
    Write-Host ""
    Write-Erro "═══════════════════════════════════════════════════════════════"
    Write-Erro "    NENHUM SOFTWARE CAD ENCONTRADO!"
    Write-Erro ""
    Write-Erro "    Por favor, instale um dos seguintes:"
    Write-Erro "    - AutoCAD (qualquer versão)"
    Write-Erro "    - GstarCAD (qualquer versão)"
    Write-Erro "═══════════════════════════════════════════════════════════════"
    Write-Host ""
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Mostrar CADs encontrados
Write-Host ""
Write-OK "Software(s) CAD encontrado(s):"
Write-Host ""

for ($i = 0; $i -lt $cadList.Count; $i++) {
    $cad = $cadList[$i]
    $marker = if ($cad.Running) { "[EM EXECUÇÃO]" } else { "" }
    Write-Host "  [$($i + 1)] $($cad.Name) $marker" -ForegroundColor Yellow
    Write-Host "      $($cad.Path)" -ForegroundColor DarkGray
}

Write-Host ""

# Selecionar CAD
$selectedCad = $null
if ($cadList.Count -eq 1) {
    $selectedCad = $cadList[0]
    Write-Status "Usando: $($selectedCad.Name)"
} else {
    $choice = Read-Host "Digite o número do CAD a usar (ou Enter para o primeiro)"
    if ([string]::IsNullOrEmpty($choice)) {
        $selectedCad = $cadList[0]
    } else {
        $idx = [int]$choice - 1
        if ($idx -ge 0 -and $idx -lt $cadList.Count) {
            $selectedCad = $cadList[$idx]
        } else {
            $selectedCad = $cadList[0]
        }
    }
}

Write-Host ""

# Passo 2: Configurar pastas
Initialize-Folders

# Passo 3: Instalar LISP
Install-LispFiles

# Passo 4: Abrir CAD se necessário
if (-not $selectedCad.Running) {
    $openCad = Read-Host "Abrir $($selectedCad.Name) automaticamente? (S/n)"
    if ($openCad -ne "n" -and $openCad -ne "N") {
        Start-CADSoftware $selectedCad
    }
}

Write-Host ""

# Passo 5: Iniciar polling
Start-CommandPolling $selectedCad
