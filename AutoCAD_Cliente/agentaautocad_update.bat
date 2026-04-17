@echo off
chcp 65001 >nul 2>&1
title Engenharia CAD - Atualizador do Agente
setlocal EnableDelayedExpansion

:: ============================================================================
:: agentaautocad_update.bat - Auto-atualizacao do agente com backup
:: Baixa nova versao do backend, verifica SHA-256, faz backup e substitui
:: ============================================================================

set "AGENT_DIR=%USERPROFILE%\EngCADAgent"
set "AGENT_EXE=sincronizador.ps1"
set "BACKUP_DIR=%AGENT_DIR%\backup"
set "UPDATE_URL=https://automacao-cad-backend.vercel.app/api/agent/download"
set "TEMP_FILE=%TEMP%\engcad_agent_update.ps1"

echo.
echo +========================================================================+
echo ^|         ENGENHARIA CAD - ATUALIZADOR DO AGENTE                        ^|
echo +========================================================================+
echo.

if not exist "%AGENT_DIR%" (
  echo [ERRO] Agente nao instalado. Execute agentaautocad.bat primeiro.
  pause & exit /b 1
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Parar Scheduled Task antes de atualizar
echo [1/5] Parando agente...
schtasks /end /tn "EngCADAgent" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Fazer backup da versao atual
echo [2/5] Criando backup...
set "BACKUP_FILE=%BACKUP_DIR%\%AGENT_EXE%.%DATE:/=-%_%TIME::=-%_bak"
set "BACKUP_FILE=!BACKUP_FILE: =_!"
copy /y "%AGENT_DIR%\%AGENT_EXE%" "!BACKUP_FILE!" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  echo [OK] Backup salvo: !BACKUP_FILE!
) else (
  echo [AVISO] Nao foi possivel criar backup. Continuando...
)

:: Baixar nova versao
echo [3/5] Baixando nova versao de %UPDATE_URL%...
powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "Invoke-WebRequest -Uri '%UPDATE_URL%' -OutFile '%TEMP_FILE%' -UseBasicParsing" ^
  >nul 2>&1

if not exist "%TEMP_FILE%" (
  echo [ERRO] Falha ao baixar atualizacao. Restaurando backup...
  copy /y "!BACKUP_FILE!" "%AGENT_DIR%\%AGENT_EXE%" >nul 2>&1
  pause & exit /b 1
)

:: Verificar SHA-256 do arquivo baixado via endpoint de metadados
echo [4/5] Verificando integridade SHA-256...
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command ^
  "(Get-FileHash '%TEMP_FILE%' -Algorithm SHA256).Hash"`) do set ACTUAL_HASH=%%H

:: Buscar hash esperado do servidor
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "(Invoke-RestMethod '%UPDATE_URL%?meta=1').sha256" 2^>nul`) do set EXPECTED_HASH=%%H

if "!EXPECTED_HASH!"=="" (
  echo [AVISO] Hash do servidor nao disponivel. Pulando verificacao.
) else (
  if /i "!ACTUAL_HASH!" neq "!EXPECTED_HASH!" (
    echo [ERRO] Hash SHA-256 invalido! Arquivo pode estar corrompido ou adulterado.
    echo  Esperado: !EXPECTED_HASH!
    echo  Obtido  : !ACTUAL_HASH!
    del /f /q "%TEMP_FILE%"
    echo [INFO] Restaurando backup...
    copy /y "!BACKUP_FILE!" "%AGENT_DIR%\%AGENT_EXE%" >nul 2>&1
    pause & exit /b 1
  )
  echo [OK] Integridade verificada.
)

:: Substituir arquivo
echo [5/5] Aplicando atualizacao...
copy /y "%TEMP_FILE%" "%AGENT_DIR%\%AGENT_EXE%" >nul 2>&1
del /f /q "%TEMP_FILE%" >nul 2>&1

if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao substituir arquivo. Restaurando backup...
  copy /y "!BACKUP_FILE!" "%AGENT_DIR%\%AGENT_EXE%" >nul 2>&1
  pause & exit /b 1
)

:: Reiniciar agente
schtasks /run /tn "EngCADAgent" >nul 2>&1

echo.
echo +========================================================================+
echo ^|  ATUALIZACAO CONCLUIDA! Agente reiniciado.                            ^|
echo +========================================================================+
echo.
timeout /t 3 /nobreak >nul
endlocal
exit /b 0
