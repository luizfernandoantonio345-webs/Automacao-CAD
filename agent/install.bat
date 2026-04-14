@echo off
setlocal

echo =============================================
echo Forge CAD Local Agent - Install
echo =============================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Python nao encontrado no PATH.
  exit /b 1
)

python agent\bootstrap.py --install-only
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha no bootstrap de dependencias.
  exit /b 1
)

python agent\windows_service.py install
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao instalar o servico.
  exit /b 1
)

python agent\windows_service.py start
if %ERRORLEVEL% neq 0 (
  echo [ERRO] Falha ao iniciar o servico.
  exit /b 1
)

echo [OK] Servico ForgeLocalAgent instalado e iniciado.
exit /b 0
