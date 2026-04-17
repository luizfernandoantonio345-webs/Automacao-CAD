@echo off
setlocal EnableDelayedExpansion

:: Requer execucao como Administrador
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Execute como Administrador.
  exit /b 1
)

echo =============================================
echo Forge CAD Local Agent - Install (seguro)
echo =============================================

:: Verificar Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Python nao encontrado no PATH.
  exit /b 1
)

:: Criar usuario dedicado engcad-agent (sem login interativo)
net user engcad-agent >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [INFO] Criando usuario engcad-agent...
  :: Senha gerada aleatoriamente via PowerShell
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[System.Web.Security.Membership]::GeneratePassword(20,4)" 2^>nul`) do set AGENT_PASS=%%P
  if "!AGENT_PASS!"=="" set AGENT_PASS=Ag3nt@%RANDOM%%RANDOM%
  net user engcad-agent "!AGENT_PASS!" /add /passwordchg:no /expires:never /comment:"ForgeCAD Agent Service Account"
  if !ERRORLEVEL! neq 0 (
    echo [ERRO] Falha ao criar usuario engcad-agent.
    exit /b 1
  )
  echo [OK] Usuario engcad-agent criado.
) else (
  echo [INFO] Usuario engcad-agent ja existe, reusando.
)

:: Negar direitos de login interativo e acesso de rede desnecessario
net localgroup "Remote Desktop Users" engcad-agent /delete >nul 2>&1
net localgroup "Administrators" engcad-agent /delete >nul 2>&1

:: Permissoes minimas: leitura no diretorio do agente, escrita em logs/
set AGENT_DIR=%~dp0
icacls "%AGENT_DIR%" /inheritance:r >nul 2>&1
icacls "%AGENT_DIR%" /grant:r "engcad-agent:(OI)(CI)(RX)" >nul 2>&1
icacls "%AGENT_DIR%logs" /grant:r "engcad-agent:(OI)(CI)(M)" >nul 2>&1
echo [OK] Permissoes aplicadas.

:: Bootstrap de dependencias
python agent\bootstrap.py --install-only
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha no bootstrap de dependencias.
  exit /b 1
)

:: Instalar e iniciar servico como engcad-agent (nao SYSTEM)
python agent\windows_service.py install
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao instalar o servico.
  exit /b 1
)

:: Reconfigurar servico para rodar como engcad-agent
sc.exe config ForgeLocalAgent obj= ".\engcad-agent" >nul 2>&1

python agent\windows_service.py start
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao iniciar o servico.
  exit /b 1
)

echo [OK] Servico ForgeLocalAgent instalado e iniciado como engcad-agent.
endlocal
exit /b 0

