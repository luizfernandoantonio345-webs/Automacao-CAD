@echo off
chcp 65001 >nul 2>&1
title Engenharia CAD - Instalador

:: ============================================================================
:: ENGENHARIA CAD - INSTALADOR
:: Execute este arquivo como Administrador para melhor experiência
:: ============================================================================

echo.
echo ╔═══════════════════════════════════════════════════════════════════════╗
echo ║           ENGENHARIA CAD - INSTALADOR                                 ║
echo ╚═══════════════════════════════════════════════════════════════════════╝
echo.

:: Verificar se está rodando como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVISO] Recomendado executar como Administrador.
    echo         Clique com botao direito e selecione "Executar como administrador"
    echo.
    echo Continuando mesmo assim...
    echo.
)

:: Definir diretório do script
cd /d "%~dp0"

:: Executar instalador PowerShell
echo Iniciando instalacao...
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0INSTALAR.ps1"

if %errorLevel% neq 0 (
    echo.
    echo [ERRO] A instalacao encontrou problemas.
    echo        Verifique o log em: %USERPROFILE%\engcad_install.log
    echo.
)

pause
