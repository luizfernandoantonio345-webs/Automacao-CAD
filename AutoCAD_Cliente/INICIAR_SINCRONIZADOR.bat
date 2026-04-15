@echo off
chcp 65001 > nul 2>&1
title ENGENHARIA CAD - Sincronizador
color 0B

echo.
echo ================================================================
echo    ENGENHARIA CAD - INICIANDO SINCRONIZADOR
echo ================================================================
echo.

cd /d "%~dp0"

:: Verificar se os arquivos necessários existem
if not exist "SINCRONIZADOR.ps1" (
    echo.
    echo ERRO: Arquivo SINCRONIZADOR.ps1 nao encontrado!
    echo.
    echo Este arquivo deveria estar em: %~dp0
    echo.
    echo Por favor, baixe o instalador novamente pelo site:
    echo https://automacao-cad-frontend.vercel.app
    echo.
    pause
    exit /b 1
)

:: Executar detector se existir (opcional)
if exist "DETECTAR_AUTOCAD.ps1" (
    echo [INFO] Verificando instalacao de CAD...
    powershell -NoProfile -ExecutionPolicy Bypass -File "DETECTAR_AUTOCAD.ps1" -SilentMode 2>nul
    echo.
)

echo [INFO] Iniciando sincronizador...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "SINCRONIZADOR.ps1"

echo.
echo ================================================================
echo    SINCRONIZADOR ENCERRADO
echo ================================================================
echo.
pause
