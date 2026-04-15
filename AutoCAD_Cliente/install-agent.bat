@echo off
chcp 65001 > nul
title Engenharia CAD - Instalacao do Agente AutoCAD
color 0B

echo.
echo ================================================================
echo    ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD
echo ================================================================
echo.

:: Diretorio de instalacao
set "DEST=%USERPROFILE%\EngCAD-Agente"

echo [1/5] Criando pasta de instalacao...
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 (
    echo ERRO: Nao foi possivel criar a pasta "%DEST%"
    goto :ERROR
)
echo      OK: %DEST%
echo.

:: URLs dos arquivos
set "BASE=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"

echo [2/5] Baixando arquivos do agente...

:: Criar script temporario de download (evita problemas com ^ no CMD)
echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 > "%DEST%\_download.ps1"
echo Write-Host '      Baixando SINCRONIZADOR.ps1...' >> "%DEST%\_download.ps1"
echo (New-Object System.Net.WebClient).DownloadFile('%BASE%/SINCRONIZADOR.ps1', '%DEST%\SINCRONIZADOR.ps1') >> "%DEST%\_download.ps1"
echo Write-Host '      Baixando DETECTAR_AUTOCAD.ps1...' >> "%DEST%\_download.ps1"
echo (New-Object System.Net.WebClient).DownloadFile('%BASE%/DETECTAR_AUTOCAD.ps1', '%DEST%\DETECTAR_AUTOCAD.ps1') >> "%DEST%\_download.ps1"
echo Write-Host '      Baixando INICIAR_SINCRONIZADOR.bat...' >> "%DEST%\_download.ps1"
echo (New-Object System.Net.WebClient).DownloadFile('%BASE%/INICIAR_SINCRONIZADOR.bat', '%DEST%\INICIAR_SINCRONIZADOR.bat') >> "%DEST%\_download.ps1"
echo Write-Host '      OK!' -ForegroundColor Green >> "%DEST%\_download.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\_download.ps1"
del "%DEST%\_download.ps1" 2>nul

echo.

echo [3/5] Verificando arquivos baixados...
if not exist "%DEST%\SINCRONIZADOR.ps1" (
    echo ERRO: Arquivo SINCRONIZADOR.ps1 nao encontrado apos download.
    goto :ERROR
)
echo      OK: SINCRONIZADOR.ps1 verificado
if not exist "%DEST%\DETECTAR_AUTOCAD.ps1" (
    echo ERRO: Arquivo DETECTAR_AUTOCAD.ps1 nao encontrado apos download.
    goto :ERROR
)
echo      OK: DETECTAR_AUTOCAD.ps1 verificado
echo.

echo [4/5] Testando conexao com o backend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $r = Invoke-WebRequest -Uri 'https://automacao-cad-backend.vercel.app/health' -TimeoutSec 10 -UseBasicParsing; Write-Host '      OK: Backend online!' -ForegroundColor Green } catch { Write-Host '      Aviso: Backend offline (modo local)' -ForegroundColor Yellow }"
echo.

echo [5/5] Iniciando agente sincronizador...
echo.
echo ================================================================
echo    O AGENTE VAI INICIAR AGORA
echo    Esta janela ficara aberta mostrando o status
echo    Para PARAR o agente: feche esta janela (X)
echo ================================================================
echo.
echo Pressione qualquer tecla para iniciar o agente...
pause > nul

cd /d "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\SINCRONIZADOR.ps1"

echo.
echo ================================================================
echo    AGENTE ENCERRADO
echo ================================================================
echo.
echo O agente foi encerrado.
echo.
echo Para reiniciar, execute:
echo   %DEST%\INICIAR_SINCRONIZADOR.bat
echo.
goto :END

:ERROR
echo.
echo ================================================================
echo    ERRO NA INSTALACAO
echo ================================================================
echo.
echo Ocorreu um erro durante a instalacao.
echo Verifique sua conexao com a internet.
echo.

:END
echo.
echo Pressione qualquer tecla para fechar...
pause > nul
