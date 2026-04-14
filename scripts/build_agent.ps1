param(
    [string]$OutputName = "ForgeLocalAgent",
    [switch]$SkipPyinstaller = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Forge Local Agent - Build (v2.0)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Validação de pre-requisitos
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "[ERRO] Python nao encontrado no PATH. Instale Python 3.8+ primeiro."
}

$pythonVersion = python --version 2>&1
Write-Host "[OK] Python: $pythonVersion"

# Installer do PyInstaller
if (-not $SkipPyinstaller) {
    Write-Host "[*] Atualizando pip e instalando PyInstaller..."
    python -m pip install --upgrade pip
    python -m pip install pyinstaller
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$distDir = Join-Path $root "dist"
$bundleDir = Join-Path $distDir "${OutputName}_installer"

Write-Host "[*] Compilando agente com PyInstaller..."
python -m PyInstaller `
    --onefile `
    --name $OutputName `
    --hidden-import=pywin32 `
    --hidden-import=win32serviceutil `
    --hidden-import=win32event `
    --hidden-import=servicemanager `
    agent/windows_service.py

if (-not (Test-Path (Join-Path $distDir "$OutputName.exe"))) {
    throw "[ERRO] PyInstaller nao gerou o .exe"
}

Write-Host "[OK] Executavel compilado"

# Empacotamento final
Write-Host "[*] Empacotando installer..."
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null
Copy-Item -Path (Join-Path $distDir "$OutputName.exe") -Destination $bundleDir -Force
Copy-Item -Path "agent/install.bat" -Destination $bundleDir -Force
Copy-Item -Path "requirements-agent.txt" -Destination $bundleDir -Force
Copy-Item -Path "README_AGENT_INSTALL.md" -Destination $bundleDir -Force -ErrorAction SilentlyContinue

Write-Host "==========================================" -ForegroundColor Green
Write-Host "[OK] Build concluido!" -ForegroundColor Green
Write-Host "Arquivo: $bundleDir\$OutputName.exe" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
