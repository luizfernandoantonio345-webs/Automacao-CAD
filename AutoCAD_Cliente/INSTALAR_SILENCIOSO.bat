@echo off
:: ============================================================================
:: ENGENHARIA CAD - INSTALADOR SILENCIOSO (Modo CMD Avancado)
:: Executa tudo automaticamente sem interacao do usuario
:: ============================================================================
:: USO: INSTALAR_SILENCIOSO.bat [opcoes]
::   /START   - Inicia o agente automaticamente apos instalacao
::   /DESKTOP - Cria atalho na area de trabalho
::   /QUIET   - Modo totalmente silencioso (sem output)
:: ============================================================================

setlocal enabledelayedexpansion
chcp 65001 > nul 2>&1

:: Processar argumentos
set "AUTO_START=0"
set "CREATE_DESKTOP=0"
set "QUIET_MODE=0"

:PARSE_ARGS
if "%~1"=="" goto :AFTER_ARGS
if /i "%~1"=="/START" set "AUTO_START=1"
if /i "%~1"=="/DESKTOP" set "CREATE_DESKTOP=1"
if /i "%~1"=="/QUIET" set "QUIET_MODE=1"
if /i "%~1"=="--start" set "AUTO_START=1"
if /i "%~1"=="--desktop" set "CREATE_DESKTOP=1"
if /i "%~1"=="--quiet" set "QUIET_MODE=1"
shift
goto :PARSE_ARGS
:AFTER_ARGS

:: Configuracoes
set "BACKEND_URL=https://automacao-cad-backend.vercel.app"
set "DEST=%USERPROFILE%\EngCAD-Agente"
set "GITHUB_RAW=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"
set "EXIT_CODE=0"

if "%QUIET_MODE%"=="0" (
    title Engenharia CAD - Instalacao Silenciosa
    color 0A
    echo [ENGCAD] Instalador Silencioso v3.0
    echo [ENGCAD] Destino: %DEST%
)

:: Criar pasta
if not exist "%DEST%" mkdir "%DEST%" 2>nul

:: Baixar arquivos via PowerShell
if "%QUIET_MODE%"=="0" echo [ENGCAD] Baixando arquivos...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
    "$wc = New-Object System.Net.WebClient; " ^
    "$wc.Encoding = [System.Text.Encoding]::UTF8; " ^
    "try { " ^
    "    $c = $wc.DownloadString('%BACKEND_URL%/api/agent/download'); " ^
    "    if ($c.Length -lt 100) { throw 'Conteudo invalido' }; " ^
    "    [IO.File]::WriteAllText('%DEST%\SINCRONIZADOR.ps1', $c, [Text.Encoding]::UTF8); " ^
    "} catch { " ^
    "    try { " ^
    "        $c = $wc.DownloadString('%GITHUB_RAW%/SINCRONIZADOR.ps1'); " ^
    "        [IO.File]::WriteAllText('%DEST%\SINCRONIZADOR.ps1', $c, [Text.Encoding]::UTF8); " ^
    "    } catch { exit 1 } " ^
    "}; " ^
    "try { " ^
    "    $c = $wc.DownloadString('%GITHUB_RAW%/DETECTAR_AUTOCAD.ps1'); " ^
    "    [IO.File]::WriteAllText('%DEST%\DETECTAR_AUTOCAD.ps1', $c, [Text.Encoding]::UTF8); " ^
    "} catch { }; " ^
    "exit 0"

if errorlevel 1 (
    if "%QUIET_MODE%"=="0" echo [ENGCAD] ERRO: Falha no download
    set "EXIT_CODE=1"
    goto :END
)

:: Verificar arquivo principal
if not exist "%DEST%\SINCRONIZADOR.ps1" (
    if "%QUIET_MODE%"=="0" echo [ENGCAD] ERRO: SINCRONIZADOR.ps1 nao encontrado
    set "EXIT_CODE=1"
    goto :END
)

:: Validar sintaxe
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$e = $null; " ^
    "[void][Management.Automation.Language.Parser]::ParseFile('%DEST%\SINCRONIZADOR.ps1', [ref]$null, [ref]$e); " ^
    "if ($e.Count -gt 0) { exit 1 }; exit 0"

if errorlevel 1 (
    if "%QUIET_MODE%"=="0" echo [ENGCAD] ERRO: Arquivo corrompido
    set "EXIT_CODE=1"
    goto :END
)

if "%QUIET_MODE%"=="0" echo [ENGCAD] Download OK

:: Criar script de inicializacao
> "%DEST%\INICIAR.bat" (
    echo @echo off
    echo chcp 65001 ^> nul 2^>^&1
    echo title Engenharia CAD - Agente
    echo cd /d "%DEST%"
    echo powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"
    echo pause
)

:: Criar atalho na area de trabalho se solicitado
if "%CREATE_DESKTOP%"=="1" (
    > "%USERPROFILE%\Desktop\EngCAD Agente.bat" (
        echo @echo off
        echo start "" "%DEST%\INICIAR.bat"
    )
    if "%QUIET_MODE%"=="0" echo [ENGCAD] Atalho criado na area de trabalho
)

if "%QUIET_MODE%"=="0" echo [ENGCAD] Instalacao concluida: %DEST%

:: Iniciar automaticamente se solicitado
if "%AUTO_START%"=="1" (
    if "%QUIET_MODE%"=="0" echo [ENGCAD] Iniciando agente...
    cd /d "%DEST%"
    start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"
)

:END
exit /b %EXIT_CODE%
