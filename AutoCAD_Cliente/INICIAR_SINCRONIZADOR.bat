@echo off
chcp 65001 > nul
title ENGENHARIA CAD - Sincronizador
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║    ENGENHARIA CAD - INICIANDO SINCRONIZADOR                   ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Executar detector primeiro
echo [INFO] Verificando instalacao de CAD...
powershell -ExecutionPolicy Bypass -File "DETECTAR_AUTOCAD.ps1" -SilentMode

echo.
echo [INFO] Iniciando sincronizador...
echo.

powershell -ExecutionPolicy Bypass -File "SINCRONIZADOR.ps1"

echo.
echo [AVISO] Sincronizador encerrado.
pause
