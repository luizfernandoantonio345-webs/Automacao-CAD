@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul 2>&1
title Engenharia CAD - Instalacao do Agente AutoCAD
color 0B

echo.
echo ================================================================
echo    ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD
echo ================================================================
echo.

:: =====================================================================
:: PASSO 0: Verificar requisitos do sistema
:: =====================================================================

echo [0/6] Verificando requisitos do sistema...

where powershell >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERRO CRITICO: PowerShell nao encontrado!
    echo Windows 7 ou superior ja vem com PowerShell.
    goto :ERROR_WAIT
)
echo      OK: PowerShell encontrado.

:: =====================================================================
:: PASSO 1: Criar pasta de instalacao
:: =====================================================================

set "DEST=%USERPROFILE%\EngCAD-Agente"

echo.
echo [1/6] Criando pasta de instalacao...

if not exist "%DEST%" (
    mkdir "%DEST%" 2>nul
    if errorlevel 1 (
        echo      ERRO: Nao foi possivel criar a pasta
        goto :ERROR_WAIT
    )
)
echo      OK: %DEST%

:: =====================================================================
:: PASSO 2: Criar script de download robusto
:: =====================================================================

echo.
echo [2/6] Preparando download...

set "BASE_URL=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"

:: Criar script PowerShell de download com try/catch
> "%DEST%\_download.ps1" (
    echo $ErrorActionPreference = 'Stop'
    echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    echo $baseUrl = '%BASE_URL%'
    echo $dest = '%DEST%'
    echo $wc = New-Object System.Net.WebClient
    echo $success = $true
    echo Write-Host '      Conectando ao GitHub...' -ForegroundColor Cyan
    echo try {
    echo     Write-Host '      Baixando SINCRONIZADOR.ps1...' -NoNewline
    echo     $wc.DownloadFile^("$baseUrl/SINCRONIZADOR.ps1", "$dest\SINCRONIZADOR.ps1"^)
    echo     Write-Host ' OK' -ForegroundColor Green
    echo } catch { Write-Host ' FALHOU' -ForegroundColor Red; Write-Host "         $^($_^)" -ForegroundColor Yellow; $success = $false }
    echo try {
    echo     Write-Host '      Baixando DETECTAR_AUTOCAD.ps1...' -NoNewline
    echo     $wc.DownloadFile^("$baseUrl/DETECTAR_AUTOCAD.ps1", "$dest\DETECTAR_AUTOCAD.ps1"^)
    echo     Write-Host ' OK' -ForegroundColor Green
    echo } catch { Write-Host ' FALHOU' -ForegroundColor Red; Write-Host "         $^($_^)" -ForegroundColor Yellow; $success = $false }
    echo try {
    echo     Write-Host '      Baixando INICIAR_SINCRONIZADOR.bat...' -NoNewline
    echo     $wc.DownloadFile^("$baseUrl/INICIAR_SINCRONIZADOR.bat", "$dest\INICIAR_SINCRONIZADOR.bat"^)
    echo     Write-Host ' OK' -ForegroundColor Green
    echo } catch { Write-Host ' FALHOU' -ForegroundColor Red; Write-Host "         $^($_^)" -ForegroundColor Yellow; $success = $false }
    echo if ^($success^) { exit 0 } else { exit 1 }
)

:: =====================================================================
:: PASSO 3: Executar download
:: =====================================================================

echo.
echo [3/6] Baixando arquivos do agente...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\_download.ps1"
set "DOWNLOAD_RESULT=%errorlevel%"

del "%DEST%\_download.ps1" 2>nul

if not "%DOWNLOAD_RESULT%"=="0" (
    echo.
    echo ERRO: Nao foi possivel baixar todos os arquivos.
    echo.
    echo Possiveis causas:
    echo   1. Sem conexao com a internet
    echo   2. GitHub fora do ar
    echo   3. Firewall/antivirus bloqueando
    echo.
    goto :ERROR_WAIT
)

:: =====================================================================
:: PASSO 4: Verificar arquivos baixados
:: =====================================================================

echo.
echo [4/6] Verificando arquivos...

if not exist "%DEST%\SINCRONIZADOR.ps1" (
    echo      ERRO: SINCRONIZADOR.ps1 nao encontrado!
    goto :ERROR_WAIT
)
echo      OK: SINCRONIZADOR.ps1

if not exist "%DEST%\DETECTAR_AUTOCAD.ps1" (
    echo      ERRO: DETECTAR_AUTOCAD.ps1 nao encontrado!
    goto :ERROR_WAIT
)
echo      OK: DETECTAR_AUTOCAD.ps1

:: =====================================================================
:: PASSO 5: Testar conexao com backend
:: =====================================================================

echo.
echo [5/6] Testando conexao com o servidor...

powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://automacao-cad-backend.vercel.app/health' -TimeoutSec 10 -UseBasicParsing | Out-Null; Write-Host '      OK: Servidor online!' -ForegroundColor Green } catch { Write-Host '      AVISO: Servidor offline - modo local' -ForegroundColor Yellow }"

:: =====================================================================
:: PASSO 6: Iniciar agente
:: =====================================================================

echo.
echo [6/6] Pronto para iniciar!
echo.
echo ================================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ================================================================
echo.
echo IMPORTANTE:
echo   - Esta janela ficara aberta mostrando o status
echo   - Para PARAR: feche esta janela (X) ou Ctrl+C
echo   - Para REINICIAR: execute INICIAR_SINCRONIZADOR.bat
echo.
echo Pressione qualquer tecla para iniciar o agente...
pause > nul

cd /d "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"

echo.
echo ================================================================
echo    AGENTE ENCERRADO
echo ================================================================
echo.
echo Para reiniciar: %DEST%\INICIAR_SINCRONIZADOR.bat
echo.
pause
goto :EOF

:ERROR_WAIT
echo.
echo ================================================================
echo    INSTALACAO FALHOU
echo ================================================================
echo.
echo A janela fechara em 60 segundos...
echo Ou pressione qualquer tecla para fechar agora.
echo.
timeout /t 60
goto :EOF
