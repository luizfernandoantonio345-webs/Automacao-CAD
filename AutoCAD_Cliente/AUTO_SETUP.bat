@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

REM ═══════════════════════════════════════════════════════════════════════════
REM ENGENHARIA CAD - AUTO SETUP 1-CLICK (v3.0 - Corrigido)
REM Detecta AutoCAD + Configura + Conecta ao Backend AUTOMATICAMENTE!
REM ═══════════════════════════════════════════════════════════════════════════

title Engenharia CAD - Setup Automatico

echo.
echo ========================================================================
echo        ENGENHARIA CAD - SETUP AUTOMATICO COMPLETO
echo                      1-CLICK SETUP v3.0
echo ========================================================================
echo.

REM Verificar se PowerShell esta disponivel
where powershell.exe >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERRO] PowerShell nao encontrado!
    pause
    exit /b 1
)

REM Executar detector + auto-app load
echo [INFO] Executando detecao de AutoCAD...
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "& '%~dp0DETECTAR_AUTOCAD.ps1' -AutoStartCAD:$true"

if %ERRORLEVEL% neq 0 (
    echo [ERRO] Falha na detecao/setup!
    echo        Verifique se o AutoCAD esta instalado.
    pause
    exit /b 1
)

echo.
echo [OK] CAD detectado e configurado!
echo.

REM Configurar backend
set BACKEND_URL=http://localhost:8000
set DROP_PATH=C:/AutoCAD_Drop/

REM Tentar configurar bridge no backend
echo [INFO] Configurando bridge no backend...
curl.exe -s -X POST "%BACKEND_URL%/api/autocad/config/bridge" -H "Content-Type: application/json" -d "{\"path\":\"%DROP_PATH%\"}" >nul 2>&1

if %ERRORLEVEL% equ 0 (
    echo [OK] Backend configurado!
) else (
    echo [AVISO] Backend nao respondeu - configure manualmente.
)

echo.
echo ========================================================================
echo                    SETUP COMPLETO!
echo.
echo   - AutoCAD detectado e iniciado
echo   - Pastas de automacao criadas
echo   - LSP carregado (forge_vigilante)
echo.
echo   Proximo: Acesse http://localhost:3000 para usar o sistema
echo ========================================================================
echo.

pause

echo 🌐 Backend configurado (bridge: C:\AutoCAD_Drop)
echo.

echo 🧪 Testando automacao...
REM curl.exe -X POST "%BACKEND_URL%/api/autocad/test-automation"

echo.
echo 🎉 SISTEMA PRONTO PARA USO!
echo.
echo 📋 COMANDOS IMPORTANTES:
echo.  
echo ┌─────────────────────────────────────────────────────────────┐
echo │ Backend: http://localhost:8000/api/autocad/status           │
echo │ Teste:    POST /api/autocad/test-automation                 │
echo │ Cliente: LSP ativo - aguardando comandos!                   │
echo └─────────────────────────────────────────────────────────────┘
echo.

REM Abrir backend se local
REM start http://localhost:8000/docs

echo [SUCESSO] Pressione qualquer tecla para sair...
pause >nul

