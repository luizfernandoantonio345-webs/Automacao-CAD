@echo off
chcp 65001 >nul 2>&1
title Engenharia CAD - Instalador do Agente
setlocal EnableDelayedExpansion

:: ============================================================================
:: agentaautocad.bat - Instalador do Agente CAD (2 cliques)
:: Verifica SHA-256, detecta versao AutoCAD, cria config.json e Scheduled Task
:: ============================================================================

echo.
echo +========================================================================+
echo ^|         ENGENHARIA CAD - INSTALADOR DO AGENTE v1.0                    ^|
echo +========================================================================+
echo.

:: Requer admin
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [AVISO] Recomendado executar como Administrador.
  echo.
)

:: Definir variaveis
set "AGENT_DIR=%USERPROFILE%\EngCADAgent"
set "AGENT_EXE=sincronizador.ps1"
set "CONFIG_FILE=%AGENT_DIR%\config.json"
set "LOG_DIR=%AGENT_DIR%\logs"
set "BACKEND_URL=https://automacao-cad-backend.vercel.app"
set "EXPECTED_HASH="

:: Criar estrutura de diretorios
if not exist "%AGENT_DIR%" mkdir "%AGENT_DIR%"
if not exist "%LOG_DIR%"   mkdir "%LOG_DIR%"

:: Copiar arquivos do agente
echo [1/5] Copiando arquivos do agente...
copy /y "%~dp0SINCRONIZADOR.ps1" "%AGENT_DIR%\%AGENT_EXE%" >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao copiar SINCRONIZADOR.ps1
  pause & exit /b 1
)

:: Verificar SHA-256 do script copiado (se hash esperado definido)
if not "!EXPECTED_HASH!"=="" (
  echo [2/5] Verificando integridade SHA-256...
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command ^
    "(Get-FileHash '%AGENT_DIR%\%AGENT_EXE%' -Algorithm SHA256).Hash"`) do set ACTUAL_HASH=%%H
  if /i "!ACTUAL_HASH!" neq "!EXPECTED_HASH!" (
    echo [ERRO] Hash SHA-256 invalido! Arquivo pode estar corrompido.
    echo  Esperado: !EXPECTED_HASH!
    echo  Obtido  : !ACTUAL_HASH!
    del /f /q "%AGENT_DIR%\%AGENT_EXE%"
    pause & exit /b 1
  )
  echo [OK] Integridade verificada.
) else (
  echo [2/5] Verificacao de hash pulada (EXPECTED_HASH nao definido).
)

:: Detectar AutoCAD instalado via registro
echo [3/5] Detectando versao do AutoCAD...
set "ACAD_VERSION=Desconhecido"
set "ACAD_PATH="

for %%V in (2026 2025 2024 2023 2022 2021 2020) do (
  if "!ACAD_PATH!"=="" (
    set "TEST_PATH=C:\Program Files\Autodesk\AutoCAD %%V\acad.exe"
    if exist "!TEST_PATH!" (
      set "ACAD_VERSION=%%V"
      set "ACAD_PATH=!TEST_PATH!"
    )
  )
)

:: Verificar GstarCAD se nao encontrou AutoCAD
if "!ACAD_PATH!"=="" (
  for %%V in (2024 2023 2022) do (
    if "!ACAD_PATH!"=="" (
      set "TEST_PATH=C:\Program Files\Gstarsoft\GstarCAD %%V\gcad.exe"
      if exist "!TEST_PATH!" (
        set "ACAD_VERSION=GstarCAD %%V"
        set "ACAD_PATH=!TEST_PATH!"
      )
    )
  )
)

if "!ACAD_PATH!"=="" (
  echo [AVISO] Nenhum CAD detectado. Continuando com versao desconhecida.
) else (
  echo [OK] CAD detectado: !ACAD_VERSION! em !ACAD_PATH!
)

:: Criar config.json
echo [4/5] Criando config.json...
(
  echo {
  echo   "backend_url": "%BACKEND_URL%",
  echo   "cad_version": "!ACAD_VERSION!",
  echo   "cad_path": "!ACAD_PATH!",
  echo   "drop_path": "C:\\AutoCAD_Drop",
  echo   "poll_interval_sec": 3,
  echo   "heartbeat_interval_sec": 30,
  echo   "log_dir": "%LOG_DIR:\=\\%",
  echo   "installed_at": "%DATE% %TIME%",
  echo   "machine": "%COMPUTERNAME%"
  echo }
) > "%CONFIG_FILE%"
echo [OK] config.json criado.

:: Registrar Scheduled Task para iniciar automaticamente
echo [5/5] Criando Scheduled Task...
schtasks /query /tn "EngCADAgent" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  schtasks /delete /tn "EngCADAgent" /f >nul 2>&1
)

schtasks /create ^
  /tn "EngCADAgent" ^
  /tr "powershell.exe -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File \"%AGENT_DIR%\%AGENT_EXE%\"" ^
  /sc onlogon ^
  /ru "%USERNAME%" ^
  /rl limited ^
  /f >nul 2>&1

if %ERRORLEVEL% equ 0 (
  echo [OK] Scheduled Task criada (inicia ao fazer login).
) else (
  echo [AVISO] Falha ao criar Scheduled Task. Inicie manualmente.
)

echo.
echo +========================================================================+
echo ^|  INSTALACAO CONCLUIDA!                                                ^|
echo ^|  O agente sera iniciado automaticamente no proximo login.             ^|
echo ^|  Para iniciar agora: pressione qualquer tecla.                        ^|
echo +========================================================================+
echo.
pause

:: Iniciar agente imediatamente
start "" powershell.exe -NonInteractive -WindowStyle Normal -ExecutionPolicy Bypass -File "%AGENT_DIR%\%AGENT_EXE%"

endlocal
exit /b 0
