@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul 2>&1
title Engenharia CAD - Instalador do Agente AutoCAD v3.0
color 0B

:: ============================================================================
:: ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD v3.0
:: Baixa e instala automaticamente do servidor backend
:: ============================================================================

echo.
echo +=========================================================================+
echo ^|        ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD v3.0              ^|
echo +=========================================================================+
echo.

:: Configuracoes
set "BACKEND_URL=https://automacao-cad-backend.vercel.app"
set "DEST=%USERPROFILE%\EngCAD-Agente"
set "GITHUB_RAW=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"

:: =====================================================================
:: PASSO 0: Verificar requisitos
:: =====================================================================
echo [0/5] Verificando requisitos do sistema...

where powershell >nul 2>&1
if errorlevel 1 (
    echo      [ERRO] PowerShell nao encontrado!
    goto :ERROR_WAIT
)
echo      [OK] PowerShell disponivel

:: Verificar conexao de rede
ping -n 1 google.com >nul 2>&1
if errorlevel 1 (
    echo      [AVISO] Sem conexao com internet - verificando rede local...
) else (
    echo      [OK] Conexao com internet ativa
)

:: =====================================================================
:: PASSO 1: Criar pasta de instalacao
:: =====================================================================
echo.
echo [1/5] Criando pasta de instalacao...

if not exist "%DEST%" (
    mkdir "%DEST%" 2>nul
    if errorlevel 1 (
        echo      [ERRO] Nao foi possivel criar: %DEST%
        goto :ERROR_WAIT
    )
)
echo      [OK] %DEST%

:: =====================================================================
:: PASSO 2: Baixar arquivos do servidor
:: =====================================================================
echo.
echo [2/5] Baixando arquivos do servidor...
echo.

:: Criar script PowerShell para download robusto
> "%TEMP%\engcad_download.ps1" (
    echo $ErrorActionPreference = 'Stop'
    echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    echo.
    echo $backendUrl = '%BACKEND_URL%'
    echo $githubUrl = '%GITHUB_RAW%'
    echo $dest = '%DEST%'
    echo.
    echo Write-Host '      Conectando ao servidor...' -ForegroundColor Cyan
    echo.
    echo # Arquivos para baixar
    echo $files = @^(
    echo     @{ Name = 'SINCRONIZADOR.ps1'; Primary = "$backendUrl/api/agent/download"; Fallback = "$githubUrl/SINCRONIZADOR.ps1" },
    echo     @{ Name = 'DETECTAR_AUTOCAD.ps1'; Primary = "$githubUrl/DETECTAR_AUTOCAD.ps1"; Fallback = $null },
    echo     @{ Name = 'INICIAR_SINCRONIZADOR.bat'; Primary = "$githubUrl/INICIAR_SINCRONIZADOR.bat"; Fallback = $null }
    echo ^)
    echo.
    echo $wc = New-Object System.Net.WebClient
    echo $wc.Encoding = [System.Text.Encoding]::UTF8
    echo $success = $true
    echo.
    echo foreach ^($file in $files^) {
    echo     $downloaded = $false
    echo     Write-Host "      Baixando $^($file.Name^)... " -NoNewline
    echo.
    echo     # Tentar URL primaria
    echo     try {
    echo         $content = $wc.DownloadString^($file.Primary^)
    echo         if ^($content -and $content.Length -gt 100^) {
    echo             [System.IO.File]::WriteAllText^("$dest\$^($file.Name^)", $content, [System.Text.Encoding]::UTF8^)
    echo             Write-Host 'OK' -ForegroundColor Green
    echo             $downloaded = $true
    echo         }
    echo     } catch {
    echo         # Tentar fallback
    echo         if ^($file.Fallback^) {
    echo             try {
    echo                 $content = $wc.DownloadString^($file.Fallback^)
    echo                 if ^($content -and $content.Length -gt 100^) {
    echo                     [System.IO.File]::WriteAllText^("$dest\$^($file.Name^)", $content, [System.Text.Encoding]::UTF8^)
    echo                     Write-Host 'OK ^(fallback^)' -ForegroundColor Yellow
    echo                     $downloaded = $true
    echo                 }
    echo             } catch { }
    echo         }
    echo     }
    echo.
    echo     if ^(-not $downloaded^) {
    echo         Write-Host 'FALHOU' -ForegroundColor Red
    echo         $success = $false
    echo     }
    echo }
    echo.
    echo if ^($success^) { exit 0 } else { exit 1 }
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\engcad_download.ps1"
set "DOWNLOAD_RESULT=%errorlevel%"
del "%TEMP%\engcad_download.ps1" 2>nul

if not "%DOWNLOAD_RESULT%"=="0" (
    echo.
    echo [ERRO] Falha no download. Possiveis causas:
    echo        - Sem conexao com internet
    echo        - Firewall bloqueando
    echo        - Servidor temporariamente offline
    echo.
    goto :ERROR_WAIT
)

:: =====================================================================
:: PASSO 3: Validar arquivos baixados
:: =====================================================================
echo.
echo [3/5] Validando arquivos...

if not exist "%DEST%\SINCRONIZADOR.ps1" (
    echo      [ERRO] SINCRONIZADOR.ps1 nao encontrado!
    goto :ERROR_WAIT
)
echo      [OK] SINCRONIZADOR.ps1

if not exist "%DEST%\DETECTAR_AUTOCAD.ps1" (
    echo      [AVISO] DETECTAR_AUTOCAD.ps1 nao encontrado ^(opcional^)
) else (
    echo      [OK] DETECTAR_AUTOCAD.ps1
)

:: Validar sintaxe PowerShell
> "%TEMP%\engcad_validate.ps1" (
    echo $errors = $null
    echo [void][System.Management.Automation.Language.Parser]::ParseFile^('%DEST%\SINCRONIZADOR.ps1', [ref]$null, [ref]$errors^)
    echo if ^($errors.Count -gt 0^) {
    echo     Write-Host '      [ERRO] Arquivo corrompido!' -ForegroundColor Red
    echo     exit 1
    echo }
    echo Write-Host '      [OK] Sintaxe validada' -ForegroundColor Green
    echo exit 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\engcad_validate.ps1"
set "VALIDATE_RESULT=%errorlevel%"
del "%TEMP%\engcad_validate.ps1" 2>nul

if not "%VALIDATE_RESULT%"=="0" (
    echo.
    echo [ERRO] O arquivo SINCRONIZADOR.ps1 esta corrompido.
    echo        Tente novamente ou baixe manualmente.
    goto :ERROR_WAIT
)

:: =====================================================================
:: PASSO 4: Testar conexao com backend
:: =====================================================================
echo.
echo [4/5] Testando conexao com o servidor...

> "%TEMP%\engcad_test.ps1" (
    echo $ProgressPreference = 'SilentlyContinue'
    echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    echo try {
    echo     $r = Invoke-WebRequest -Uri '%BACKEND_URL%/health' -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    echo     $data = $r.Content ^| ConvertFrom-Json
    echo     Write-Host "      [OK] Servidor online - Status: $^($data.status^)" -ForegroundColor Green
    echo } catch {
    echo     Write-Host '      [AVISO] Servidor offline - modo local sera usado' -ForegroundColor Yellow
    echo }
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\engcad_test.ps1"
del "%TEMP%\engcad_test.ps1" 2>nul

:: =====================================================================
:: PASSO 5: Criar atalhos e finalizar
:: =====================================================================
echo.
echo [5/5] Finalizando instalacao...

:: Criar atalho para iniciar rapido
> "%DEST%\INICIAR.bat" (
    echo @echo off
    echo chcp 65001 ^> nul 2^>^&1
    echo title Engenharia CAD - Agente
    echo cd /d "%DEST%"
    echo powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"
    echo pause
)
echo      [OK] Atalho INICIAR.bat criado

:: Criar atalho na area de trabalho
> "%USERPROFILE%\Desktop\EngCAD Agente.bat" (
    echo @echo off
    echo cd /d "%DEST%"
    echo start "" "%DEST%\INICIAR.bat"
)
echo      [OK] Atalho na area de trabalho criado

echo.
echo +=========================================================================+
echo ^|                    INSTALACAO CONCLUIDA!                               ^|
echo +=========================================================================+
echo.
echo   Pasta: %DEST%
echo.
echo   Para iniciar o agente:
echo     - Clique em "EngCAD Agente" na area de trabalho
echo     - Ou execute: %DEST%\INICIAR.bat
echo.
echo   IMPORTANTE:
echo     - Mantenha a janela do agente aberta enquanto usa o sistema
echo     - O AutoCAD sera detectado e conectado automaticamente
echo.
echo +=========================================================================+
echo.

set /p "START_NOW=Deseja iniciar o agente agora? (S/N): "
if /i "%START_NOW%"=="S" (
    echo.
    echo Iniciando agente...
    cd /d "%DEST%"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"
)

echo.
echo Pressione qualquer tecla para fechar...
pause > nul
goto :EOF

:ERROR_WAIT
echo.
echo +=========================================================================+
echo ^|                       INSTALACAO FALHOU                                ^|
echo +=========================================================================+
echo.
echo Verifique:
echo   1. Conexao com a internet
echo   2. Firewall/antivirus bloqueando
echo   3. Tente executar como Administrador
echo.
echo Para suporte: github.com/luizfernandoantonio345-webs/Automacao-CAD
echo.
echo Fechando em 60 segundos...
timeout /t 60
goto :EOF
