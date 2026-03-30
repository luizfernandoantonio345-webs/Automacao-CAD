param(
    [switch]$Clean,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Configurações
$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = $RootPath
$EnvFile = Join-Path $RootPath "integration\python_api\.env"

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )
    if (!(Test-Path $Path)) {
        return ""
    }
    $line = Get-Content $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (!$line) {
        return ""
    }
    return ($line -split "=", 2)[1].Trim()
}

$EngAuthSecret = Get-EnvValue -Path $EnvFile -Key "ENG_AUTH_SECRET"
if ([string]::IsNullOrWhiteSpace($EngAuthSecret)) {
    Write-Error "ENG_AUTH_SECRET não encontrado em integration\python_api\.env"
    exit 1
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "    Engenharia CAD - Sistema de Automação" -ForegroundColor Cyan
Write-Host "    Inicialização Rápida e Segura" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Port {
    param([int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("localhost", $Port)
        $tcpClient.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-ForPort {
    param([int]$Port, [int]$Timeout = 30)
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $Timeout) {
        if (Test-Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

# 1. Limpar processos se solicitado
if ($Clean) {
    Write-Host "[1/6] Limpando processos conflitantes..." -ForegroundColor Yellow
    Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*node*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} else {
    Write-Host "[1/6] Verificando processos existentes..." -ForegroundColor Yellow
}

# 2. Verificar dependências
Write-Host "[2/6] Verificando dependências..." -ForegroundColor Yellow
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python não encontrado! Instale o Python 3.8+"
    exit 1
}
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js não encontrado! Instale o Node.js"
    exit 1
}

# 3. Verificar arquivos necessários
Write-Host "[3/6] Verificando arquivos do sistema..." -ForegroundColor Yellow
$requiredFiles = @(
    "integration\python_api\app.py",
    "frontend\package.json",
    "engenharia_automacao\app\auth.py"
)
foreach ($file in $requiredFiles) {
    if (!(Test-Path (Join-Path $RootPath $file))) {
        Write-Error "Arquivo necessário não encontrado: $file"
        exit 1
    }
}

# 4. Iniciar backend
Write-Host "[4/6] Iniciando backend..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "python" -ArgumentList "integration\python_api\app.py" -WorkingDirectory $RootPath -PassThru -WindowStyle Hidden -Environment @{
    "PYTHONPATH" = $PythonPath
    "ENG_AUTH_SECRET" = $EngAuthSecret
}

# 5. Aguardar backend ficar pronto
Write-Host "[5/6] Aguardando backend inicializar..." -ForegroundColor Yellow
if (!(Wait-ForPort 8000 30)) {
    Write-Error "Backend não iniciou corretamente (porta 8000 não disponível)"
    $backendProcess | Stop-Process -Force
    exit 1
}

# 6. Iniciar frontend
Write-Host "[6/6] Iniciando frontend..." -ForegroundColor Yellow
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory (Join-Path $RootPath "frontend") -PassThru -WindowStyle Normal -Environment @{
    "REACT_APP_API_URL" = "http://127.0.0.1:8000"
}

# 7. Aguardar frontend
Write-Host "[7/7] Aguardando frontend inicializar..." -ForegroundColor Yellow
if (!(Wait-ForPort 3000 60)) {
    Write-Warning "Frontend pode estar demorando para iniciar (porta 3000)"
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "    Sistema Iniciado com Sucesso!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Para acessar: Clique em 'Acesso Público (Demo)'" -ForegroundColor Cyan
Write-Host ""

if ($Debug) {
    Write-Host "Processos iniciados:" -ForegroundColor Gray
    Write-Host "  Backend PID: $($backendProcess.Id)" -ForegroundColor Gray
    Write-Host "  Frontend PID: $($frontendProcess.Id)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Pressione Ctrl+C para parar..." -ForegroundColor Gray
    try {
        Wait-Process -Id $backendProcess.Id
    } catch {
        # Ignorar interrupções
    }
} else {
    Write-Host "Pressione qualquer tecla para abrir o navegador..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    # Abrir navegador
    Start-Process "http://localhost:3000"
}

# Cleanup ao sair
Write-Host "Parando serviços..." -ForegroundColor Yellow
$backendProcess | Stop-Process -Force -ErrorAction SilentlyContinue
$frontendProcess | Stop-Process -Force -ErrorAction SilentlyContinue
