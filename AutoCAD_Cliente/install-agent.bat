@echo off
chcp 65001 > nul
title Engenharia CAD - Instalacao do Agente AutoCAD
color 0B

echo.
echo ================================================================
echo    ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD
echo ================================================================
echo.

:: Diretorio de instalacao sem acentos, sem espacos, sem admin
set "DEST=%USERPROFILE%\EngCAD-Agente"

echo [1/4] Criando pasta de instalacao...
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 (
    echo ERRO: Nao foi possivel criar a pasta "%DEST%"
    pause
    exit /b 1
)
echo      OK: %DEST%
echo.

:: URLs dos arquivos no repositorio (raw GitHub)
set "BASE=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"

echo [2/4] Baixando arquivos do agente...

:: Usar WebClient.DownloadFile - funciona em qualquer Windows 7+ sem alias
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
   (New-Object System.Net.WebClient).DownloadFile('%BASE%/SINCRONIZADOR.ps1', '%DEST%\SINCRONIZADOR.ps1'); ^
   (New-Object System.Net.WebClient).DownloadFile('%BASE%/DETECTAR_AUTOCAD.ps1', '%DEST%\DETECTAR_AUTOCAD.ps1'); ^
   (New-Object System.Net.WebClient).DownloadFile('%BASE%/INICIAR_SINCRONIZADOR.bat', '%DEST%\INICIAR_SINCRONIZADOR.bat')"

if errorlevel 1 (
    echo.
    echo ERRO ao baixar arquivos. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

echo      OK: SINCRONIZADOR.ps1
echo      OK: DETECTAR_AUTOCAD.ps1
echo      OK: INICIAR_SINCRONIZADOR.bat
echo.

echo [3/4] Verificando arquivos baixados...
if not exist "%DEST%\SINCRONIZADOR.ps1" (
    echo ERRO: Arquivo SINCRONIZADOR.ps1 nao encontrado apos download.
    pause
    exit /b 1
)
echo      OK: Todos os arquivos verificados.
echo.

echo [4/4] Iniciando agente...
echo.
cd /d "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"

echo.
echo ================================================================
echo    Agente encerrado.
echo    Para reiniciar: execute "%DEST%\INICIAR_SINCRONIZADOR.bat"
echo ================================================================
pause
