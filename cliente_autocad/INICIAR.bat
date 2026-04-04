@echo off
title Engenharia CAD - Sincronizador Inteligente
color 0B
echo.
echo ========================================================
echo    ENGENHARIA CAD - SINCRONIZADOR INTELIGENTE v2.0
echo ========================================================
echo.
echo Iniciando sistema de deteccao automatica...
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0SINCRONIZADOR_INTELIGENTE.ps1"
if errorlevel 1 (
    echo.
    echo [ERRO] Ocorreu um problema. Verifique a mensagem acima.
    echo.
    pause
)
