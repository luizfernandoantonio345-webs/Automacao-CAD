@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    Engenharia CAD - Sistema de Automação
echo    Inicialização Rápida e Segura
echo ========================================
echo.

set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%"
set "ENV_FILE=%ROOT%integration\python_api\.env"
set "ENG_AUTH_SECRET="

if not exist "%ENV_FILE%" (
    echo ERRO: Arquivo .env nao encontrado em integration\python_api\.env
    pause
    exit /b 1
)

for /f "tokens=1,* delims==" %%A in ('findstr /b "ENG_AUTH_SECRET=" "%ENV_FILE%"') do (
    set "ENG_AUTH_SECRET=%%B"
)

if "%ENG_AUTH_SECRET%"=="" (
    echo ERRO: ENG_AUTH_SECRET nao encontrado no arquivo .env
    pause
    exit /b 1
)

echo [1/6] Limpando processos conflitantes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/6] Verificando dependências...
where python >nul 2>&1 || (
    echo ERRO: Python não encontrado!
    echo Instale Python 3.8+ de https://python.org
    pause
    exit /b 1
)
where node >nul 2>&1 || (
    echo ERRO: Node.js não encontrado!
    echo Instale Node.js de https://nodejs.org
    pause
    exit /b 1
)

echo [3/6] Verificando arquivos...
if not exist "%ROOT%integration\python_api\app.py" (
    echo ERRO: Arquivo backend não encontrado!
    pause
    exit /b 1
)
if not exist "%ROOT%frontend\package.json" (
    echo ERRO: Arquivo frontend não encontrado!
    pause
    exit /b 1
)

echo [4/6] Iniciando backend...
start "Engenharia CAD Backend" /min cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT% && set ENG_AUTH_SECRET=%ENG_AUTH_SECRET% && python integration\python_api\app.py && pause"

echo [5/6] Aguardando inicialização...
timeout /t 5 /nobreak >nul

echo [6/6] Iniciando frontend...
start "Engenharia CAD Frontend" cmd /c "cd /d %ROOT%frontend && set REACT_APP_API_URL=http://127.0.0.1:8000 && npm start"

echo.
echo ========================================
echo    Sistema Iniciado com Sucesso!
echo ========================================
echo.
echo URLs de acesso:
echo Backend API: http://localhost:8000
echo Aplicação Web: http://localhost:3000
echo.
echo Como acessar:
echo 1. Abra http://localhost:3000 no navegador
echo 2. Clique em "Acesso Público (Demo)"
echo 3. Comece a usar o sistema!
echo.
echo Dica: Mantenha esta janela aberta para controle
echo.
pause
