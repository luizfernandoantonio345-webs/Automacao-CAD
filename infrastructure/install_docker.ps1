# ====================================================================
# install_docker.ps1 - Script Automático Instalação Docker Desktop
# Execute como Administrador: .\install_docker.ps1
# ====================================================================

param(
    [switch]$Force,
    [switch]$NoRestart
)

Write-Host "=== INSTALAÇÃO DOCKER DESKTOP - WINDOWS ===" -ForegroundColor Cyan
Write-Host "Este script instala Docker Desktop automaticamente`n" -ForegroundColor Yellow

# Verificar se está rodando como Admin
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERRO: Execute como Administrador!" -ForegroundColor Red
    Write-Host "Clique direito no PowerShell → 'Executar como administrador'" -ForegroundColor Yellow
    exit 1
}

# Verificar Windows version
$osInfo = Get-ComputerInfo
$windowsEdition = $osInfo.WindowsProductName
$windowsVersion = $osInfo.WindowsVersion

Write-Host "Windows Edition: $windowsEdition" -ForegroundColor Gray
Write-Host "Windows Version: $windowsVersion" -ForegroundColor Gray

if ($windowsEdition -notlike "*Pro*" -and $windowsEdition -notlike "*Enterprise*" -and $windowsEdition -notlike "*Education*") {
    Write-Host "AVISO: Docker Desktop requer Windows Pro/Enterprise/Education" -ForegroundColor Yellow
    Write-Host "Para Windows Home, use Docker Toolbox (legacy)`n" -ForegroundColor Yellow
    $continue = Read-Host "Continuar mesmo assim? (y/N)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        exit 0
    }
}

# Verificar se Docker já está instalado
try {
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        Write-Host "Docker já instalado: $dockerVersion" -ForegroundColor Green
        if (-not $Force) {
            Write-Host "Use -Force para reinstalar" -ForegroundColor Yellow
            exit 0
        }
    }
}
catch {
    Write-Host "Docker não encontrado - instalando..." -ForegroundColor Yellow
}

# Baixar instalador
$installerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

Write-Host "Baixando Docker Desktop Installer..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "Download concluído: $installerPath" -ForegroundColor Green
}
catch {
    Write-Host "ERRO: Falha no download: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Executar instalador
Write-Host "Executando instalador..." -ForegroundColor Cyan
Write-Host "IMPORTANTE: Marque 'Enable Hyper-V' se solicitado" -ForegroundColor Yellow
Write-Host "A instalação pode demorar alguns minutos...`n" -ForegroundColor Yellow

try {
    $process = Start-Process -FilePath $installerPath -ArgumentList "install --quiet" -Wait -PassThru
    if ($process.ExitCode -eq 0) {
        Write-Host "Instalação concluída com sucesso!" -ForegroundColor Green
    }
    else {
        Write-Host "ERRO: Instalação falhou (código: $($process.ExitCode))" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "ERRO: Falha na execução: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Limpar instalador
Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

# Verificar instalação
Write-Host "`nVerificando instalação..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker não encontrado após instalação" -ForegroundColor Red
}

try {
    $composeVersion = docker-compose --version
    Write-Host "✓ Docker Compose: $composeVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker Compose não encontrado" -ForegroundColor Red
}

# Instruções finais
Write-Host "`n=== PRÓXIMOS PASSOS ===" -ForegroundColor Cyan
Write-Host "1. Reinicie o computador (se solicitado)" -ForegroundColor White
Write-Host "2. Abra Docker Desktop e aguarde inicialização" -ForegroundColor White
Write-Host "3. Execute no terminal:" -ForegroundColor White
Write-Host "   cd 'c:\Users\Sueli\Desktop\Automação CAD'" -ForegroundColor Gray
Write-Host "   docker-compose up -d --build" -ForegroundColor Gray
Write-Host "   python test_celery_phase1.py" -ForegroundColor Gray
Write-Host "`n4. Acesse dashboards:" -ForegroundColor White
Write-Host "   Flower: http://localhost:5555" -ForegroundColor Gray
Write-Host "   Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor Gray

if (-not $NoRestart) {
    Write-Host "`nReiniciando em 10 segundos... (use -NoRestart para cancelar)" -ForegroundColor Yellow
    for ($i = 10; $i -gt 0; $i--) {
        Write-Host -NoNewline "`r$i... "
        Start-Sleep -Seconds 1
    }
    Write-Host "`nReiniciando..." -ForegroundColor Yellow
    Restart-Computer -Force
}
else {
    Write-Host "`nReinicie manualmente para completar instalação." -ForegroundColor Yellow
}

Write-Host "`nInstalação concluída! Sucesso!" -ForegroundColor Green