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

:: Criar script PowerShell de download com UTF-8 e try/catch
> "%DEST%\_download.ps1" (
    echo $ErrorActionPreference = 'Stop'
    echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    echo $baseUrl = '%BASE_URL%'
    echo $dest = '%DEST%'
    echo $wc = New-Object System.Net.WebClient
    echo $wc.Encoding = [System.Text.Encoding]::UTF8
    echo $success = $true
    echo Write-Host '      Conectando ao GitHub...' -ForegroundColor Cyan
    echo try {
    echo     Write-Host '      Baixando SINCRONIZADOR.ps1...' -NoNewline
    echo     $content = $wc.DownloadString^("$baseUrl/SINCRONIZADOR.ps1"^)
    echo     [System.IO.File]::WriteAllText^("$dest\SINCRONIZADOR.ps1", $content, [System.Text.Encoding]::UTF8^)
    echo     Write-Host ' OK' -ForegroundColor Green
    echo } catch { Write-Host ' FALHOU' -ForegroundColor Red; Write-Host "         $^($_^)" -ForegroundColor Yellow; $success = $false }
    echo try {
    echo     Write-Host '      Baixando DETECTAR_AUTOCAD.ps1...' -NoNewline
    echo     $content = $wc.DownloadString^("$baseUrl/DETECTAR_AUTOCAD.ps1"^)
    echo     [System.IO.File]::WriteAllText^("$dest\DETECTAR_AUTOCAD.ps1", $content, [System.Text.Encoding]::UTF8^)
    echo     Write-Host ' OK' -ForegroundColor Green
    echo } catch { Write-Host ' FALHOU' -ForegroundColor Red; Write-Host "         $^($_^)" -ForegroundColor Yellow; $success = $false }
    echo try {
    echo     Write-Host '      Baixando INICIAR_SINCRONIZADOR.bat...' -NoNewline
    echo     $content = $wc.DownloadString^("$baseUrl/INICIAR_SINCRONIZADOR.bat"^)
    echo     [System.IO.File]::WriteAllText^("$dest\INICIAR_SINCRONIZADOR.bat", $content, [System.Text.Encoding]::UTF8^)
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

:: Validar sintaxe do SINCRONIZADOR.ps1
echo      Validando sintaxe...
> "%TEMP%\_validate.ps1" (
    echo $errors = $null
    echo [void][System.Management.Automation.Language.Parser]::ParseFile^('%DEST%\SINCRONIZADOR.ps1', [ref]$null, [ref]$errors^)
    echo if ^($errors.Count -gt 0^) {
    echo     Write-Host '      ERRO: Arquivo corrompido durante download!' -ForegroundColor Red
    echo     $errors ^| ForEach-Object { Write-Host "         Linha $^($_.Extent.StartLineNumber^): $^($_.Message^)" -ForegroundColor Yellow }
    echo     exit 1
    echo }
    echo Write-Host '      OK: Sintaxe valida' -ForegroundColor Green
    echo exit 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\_validate.ps1"
set "VALIDATE_RESULT=%errorlevel%"
del "%TEMP%\_validate.ps1" 2>nul

if not "%VALIDATE_RESULT%"=="0" (
    echo.
    echo ERRO: Arquivo SINCRONIZADOR.ps1 foi corrompido.
    echo.
    echo Tente novamente. Se persistir:
    echo   1. Desative temporariamente o antivirus
    echo   2. Baixe manualmente de: %BASE_URL%/SINCRONIZADOR.ps1
    echo.
    goto :ERROR_WAIT
)

:: =====================================================================
:: PASSO 5: Testar conexao com backend
:: =====================================================================

echo.
echo [5/6] Testando conexao com o servidor...

:: Criar script temporario para teste de conexao
echo $ProgressPreference='SilentlyContinue' > "%TEMP%\test_conn.ps1"
echo [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 >> "%TEMP%\test_conn.ps1"
echo try { >> "%TEMP%\test_conn.ps1"
echo     $r = Invoke-WebRequest -Uri 'https://automacao-cad-backend.vercel.app/health' -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop >> "%TEMP%\test_conn.ps1"
echo     Write-Host '      OK: Servidor online!' -ForegroundColor Green >> "%TEMP%\test_conn.ps1"
echo } catch { >> "%TEMP%\test_conn.ps1"
echo     Write-Host '      AVISO: Servidor offline - modo local ativado' -ForegroundColor Yellow >> "%TEMP%\test_conn.ps1"
echo } >> "%TEMP%\test_conn.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\test_conn.ps1"
del "%TEMP%\test_conn.ps1" 2>nul

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
