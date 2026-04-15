@echo off
chcp 65001 > nul
title Engenharia CAD - Instalacao do Agente AutoCAD
color 0B

echo.
echo ================================================================
echo    ENGENHARIA CAD - INSTALADOR DO AGENTE AUTOCAD
echo ================================================================
echo.

:: Diretorio de instalacao sem acentos, sem espacos, sem admin
set "DEST=%USERPROFILE%\EngCAD-Agente"

echo [1/5] Criando pasta de instalacao...
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 (
    echo ERRO: Nao foi possivel criar a pasta "%DEST%"
    goto :ERROR
)
echo      OK: %DEST%
echo.

:: URLs dos arquivos no repositorio (raw GitHub)
set "BASE=https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente"

echo [2/5] Baixando arquivos do agente...

:: Usar WebClient.DownloadFile - funciona em qualquer Windows 7+ sem alias
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
   try { ^
     Write-Host '      Baixando SINCRONIZADOR.ps1...'; ^
     (New-Object System.Net.WebClient).DownloadFile('%BASE%/SINCRONIZADOR.ps1', '%DEST%\SINCRONIZADOR.ps1'); ^
     Write-Host '      Baixando DETECTAR_AUTOCAD.ps1...'; ^
     (New-Object System.Net.WebClient).DownloadFile('%BASE%/DETECTAR_AUTOCAD.ps1', '%DEST%\DETECTAR_AUTOCAD.ps1'); ^
     Write-Host '      Baixando INICIAR_SINCRONIZADOR.bat...'; ^
     (New-Object System.Net.WebClient).DownloadFile('%BASE%/INICIAR_SINCRONIZADOR.bat', '%DEST%\INICIAR_SINCRONIZADOR.bat'); ^
     Write-Host '      OK: Todos os arquivos baixados!' -ForegroundColor Green; ^
   } catch { ^
     Write-Host ('      ERRO: ' + $_.Exception.Message) -ForegroundColor Red; ^
     exit 1; ^
   }"

if errorlevel 1 (
    echo.
    echo ERRO ao baixar arquivos. Verifique sua conexao com a internet.
    goto :ERROR
)

echo.

echo [3/5] Verificando arquivos baixados...
if not exist "%DEST%\SINCRONIZADOR.ps1" (
    echo ERRO: Arquivo SINCRONIZADOR.ps1 nao encontrado apos download.
    goto :ERROR
)
echo      OK: SINCRONIZADOR.ps1 verificado
echo.

echo [4/5] Testando conexao com o backend...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
   try { ^
     $resp = Invoke-WebRequest -Uri 'https://automacao-cad-backend.vercel.app/health' -TimeoutSec 10 -UseBasicParsing; ^
     if ($resp.StatusCode -eq 200) { ^
       Write-Host '      OK: Backend online!' -ForegroundColor Green; ^
     } else { ^
       Write-Host '      Aviso: Backend respondeu com status' $resp.StatusCode -ForegroundColor Yellow; ^
     } ^
   } catch { ^
     Write-Host '      Aviso: Nao foi possivel conectar ao backend (modo offline)' -ForegroundColor Yellow; ^
   }"

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
echo O agente foi encerrado. Isso pode ter ocorrido por:
echo   - Voce fechou a janela
echo   - Ocorreu um erro no script
echo   - O CAD foi fechado
echo.
echo Para reiniciar, execute:
echo   %DEST%\INICIAR_SINCRONIZADOR.bat
echo.
echo Ou clique novamente no botao "Instalar / Executar Agente" no site.
echo.
goto :END

:ERROR
echo.
echo ================================================================
echo    ERRO NA INSTALACAO
echo ================================================================
echo.
echo Ocorreu um erro durante a instalacao.
echo Verifique:
echo   1. Sua conexao com a internet
echo   2. Se o Windows bloqueou o download (antivirus/firewall)
echo   3. Se voce tem permissao para criar pastas em %USERPROFILE%
echo.

:END
echo.
echo Pressione qualquer tecla para fechar...
pause > nul
