@echo off
chcp 65001 > nul
title Engenharia CAD - AutoConnect

echo.
echo ════════════════════════════════════════════════════════════════════════
echo    ENGENHARIA CAD - CONEXAO AUTOMATICA COM AUTOCAD
echo ════════════════════════════════════════════════════════════════════════
echo.

:: Configuracoes
set "BACKEND_URL=http://localhost:8000"
set "BRIDGE_PATH=C:\AutoCAD_Drop"

:: 1. Criar pasta bridge
echo [1/5] Criando pasta bridge...
if not exist "%BRIDGE_PATH%" (
    mkdir "%BRIDGE_PATH%"
    echo       Pasta criada: %BRIDGE_PATH%
) else (
    echo       Pasta ja existe: %BRIDGE_PATH%
)

:: 2. Validar licenca via API
echo [2/5] Validando licenca...
powershell -ExecutionPolicy Bypass -Command ^
"try { $hwid = (Get-WmiObject Win32_ComputerSystemProduct).UUID; $body = @{username='cliente';hwid=$hwid} | ConvertTo-Json; $resp = Invoke-RestMethod -Uri '%BACKEND_URL%/api/license/validate' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10; if($resp.authorized){ Write-Host '       Licenca OK: ' $resp.message; exit 0 } else { Write-Host '       Licenca pendente (modo demo)'; exit 0 } } catch { Write-Host '       Backend offline - continuando em modo local'; exit 0 }"

:: 3. Detectar AutoCAD
echo [3/5] Detectando AutoCAD instalado...
powershell -ExecutionPolicy Bypass -Command ^
"$found = $false; $versions = @('AutoCAD.Application.25','AutoCAD.Application.24','AutoCAD.Application.23','AutoCAD.Application.22','AutoCAD.Application.21','AutoCAD.Application.20','AutoCAD.Application'); foreach($v in $versions){ try { $test = New-Object -ComObject $v -ErrorAction Stop; $found = $true; Write-Host '       Encontrado:' $v; $test = $null; break } catch { continue } }; if(-not $found){ Write-Host '       AutoCAD nao detectado via COM'; exit 1 }; exit 0"

if %ERRORLEVEL% neq 0 (
    echo.
    echo    AVISO: AutoCAD nao foi detectado nesta maquina.
    echo    O sistema funcionara em modo Bridge (pasta drop).
    echo.
    goto :bridge_mode
)

:: 4. Abrir AutoCAD e conectar
echo [4/5] Abrindo AutoCAD e conectando...
powershell -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference = 'Stop'; try { $versions = @('AutoCAD.Application.25','AutoCAD.Application.24','AutoCAD.Application.23','AutoCAD.Application.22','AutoCAD.Application.21','AutoCAD.Application.20','AutoCAD.Application'); $app = $null; foreach($v in $versions){ try { $app = New-Object -ComObject $v; break } catch { continue } }; if(-not $app){ throw 'AutoCAD nao encontrado' }; $app.Visible = $true; Start-Sleep 3; $doc = $app.Documents.Add(); $doc.SendCommand([char]40 + 'vl-load-com' + [char]41 + [char]10); Start-Sleep 1; $doc.SendCommand([char]40 + 'setq *forge-watch-path* ' + [char]34 + 'C:/AutoCAD_Drop/' + [char]34 + [char]41 + [char]10); $doc.SendCommand([char]40 + 'setq *forge-running* T' + [char]41 + [char]10); $doc.SendCommand([char]40 + 'setq *backend-url* ' + [char]34 + '%BACKEND_URL%' + [char]34 + [char]41 + [char]10); $doc.SendCommand([char]40 + 'alert ' + [char]34 + 'Engenharia CAD Conectado!' + [char]92 + 'nPasta: C:/AutoCAD_Drop/' + [char]34 + [char]41 + [char]10); Write-Host '       AutoCAD aberto e configurado!'; exit 0 } catch { Write-Host '       Erro:' $_.Exception.Message; exit 1 }"

if %ERRORLEVEL% neq 0 (
    echo       Falha ao abrir AutoCAD - usando modo Bridge
    goto :bridge_mode
)

goto :success

:bridge_mode
echo.
echo [4/5] Configurando modo Bridge...
echo       Pasta monitorada: %BRIDGE_PATH%
echo       Coloque arquivos job_*.lsp nesta pasta
echo       O AutoCAD executara automaticamente quando aberto

:success
:: 5. Finalizar
echo [5/5] Configuracao concluida!
echo.
echo ════════════════════════════════════════════════════════════════════════
echo    ENGENHARIA CAD - CONECTADO!
echo ════════════════════════════════════════════════════════════════════════
echo.
echo    Pasta Bridge:  %BRIDGE_PATH%
echo    Backend:       %BACKEND_URL%
echo.
echo    Para testar, acesse no navegador:
echo    %BACKEND_URL%/docs
echo.
echo    Ou execute:
echo    curl -X POST %BACKEND_URL%/api/autocad/test-automation
echo.
echo ════════════════════════════════════════════════════════════════════════
echo.
pause

