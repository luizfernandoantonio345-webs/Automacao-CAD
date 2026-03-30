# docker_compatibility_helper.ps1
# Detecta versão do Windows e oferece opções para continuar quando Docker Desktop não é suportado.

function Get-WindowsInfo {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    [pscustomobject]@{
        Caption = $os.Caption
        Version = $os.Version
        BuildNumber = $os.BuildNumber
        Architecture = $os.OSArchitecture
    }
}

function Show-CurrentStatus {
    $info = Get-WindowsInfo
    Write-Host "Windows: $($info.Caption)" -ForegroundColor Cyan
    Write-Host "Versão: $($info.Version)" -ForegroundColor Cyan
    Write-Host "Build: $($info.BuildNumber)" -ForegroundColor Cyan
    Write-Host "Arquitetura: $($info.Architecture)" -ForegroundColor Cyan
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "docker instalado: $(docker --version)" -ForegroundColor Green
    } else {
        Write-Host "docker não encontrado" -ForegroundColor Yellow
    }
}

function Install-DockerToolbox {
    $url = "https://github.com/docker/toolbox/releases/download/v19.03.1/DockerToolbox-19.03.1.exe"
    $dest = "$env:TEMP\DockerToolbox-19.03.1.exe"
    Write-Host "Baixando Docker Toolbox (legacy) para Windows incompatível..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    Write-Host "Executando instalador: $dest" -ForegroundColor Yellow
    Start-Process -FilePath $dest -ArgumentList "/S" -Wait
    Write-Host "Concluído instalação Docker Toolbox. Reinicie o PC e abra o Docker Quickstart Terminal." -ForegroundColor Green
}

function Install-WSL2-IfPossible {
    Write-Host "Tentando habilitar WSL2 + Ubuntu (requer Windows 10 1903+ e kernel atualizado)." -ForegroundColor Cyan
    wsl --install -d Ubuntu
    if ($LASTEXITCODE -eq 0) {
        Write-Host "WSL2 instalado com Ubuntu. Instale docker no WSL: sudo apt update && sudo apt install -y docker.io" -ForegroundColor Green
        Write-Host "Use: sudo service docker start" -ForegroundColor Green
    } else {
        Write-Host "WSL2 não pôde ser instalado automaticamente. Verifique requisitos de Windows e use upgrade" -ForegroundColor Red
    }
}

function Main {
    Write-Host "=== HELPER: Compatibilidade Docker no Windows ===" -ForegroundColor White
    Show-CurrentStatus

    $osInfo = Get-WindowsInfo
    # Windows 10 >= 10.0.19045 or Windows 11 >= 10.0.22631
    [version]$v = $osInfo.Version
    [bool]$supportsDockerDesktop = ($v -ge [version]"10.0.19045")

    if ($supportsDockerDesktop) {
        Write-Host "Seu Windows aparenta suportar Docker Desktop. Tente instalar novamente após reiniciar." -ForegroundColor Green
        return
    }

    Write-Host "Seu Windows não suporta Docker Desktop moderno. Opções:" -ForegroundColor Yellow
    Write-Host "1) Upgrade de Windows para 10 Pro/Enterprise 22H2 ou 11 (recomendado)." -ForegroundColor White
    Write-Host "2) Docker Toolbox (legacy) para compatibilidade mínima" -ForegroundColor White
    Write-Host "3) Instalar WSL2 + Ubuntu e docker.io no WSL" -ForegroundColor White

    $choice = Read-Host "Escolha 1, 2 ou 3"
    switch ($choice) {
        '1' {
            Write-Host "Atualize seu Windows via Windows Update ou imagem oficial Microsoft." -ForegroundColor Green
        }
        '2' {
            Install-DockerToolbox
        }
        '3' {
            Install-WSL2-IfPossible
        }
        default {
            Write-Host "Opção inválida. Executando verificação de status novamente." -ForegroundColor Red
            Show-CurrentStatus
        }
    }
}

Main
