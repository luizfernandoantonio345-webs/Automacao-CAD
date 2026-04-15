# =============================================================================
# ENGENHARIA CAD - INSTALADOR COMPLETO v2.0
# =============================================================================
# Este script instala e configura o Engenharia CAD no computador do cliente
# =============================================================================

param(
    [switch]$Uninstall,
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

# Configurações
$INSTALL_PATH = "C:\EngenhariaCAD"
$DROP_PATH = "C:\AutoCAD_Drop"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_FILE = Join-Path $env:USERPROFILE "engcad_install.log"

# Cores
$colors = @{
    Success = "Green"
    Error   = "Red"
    Warning = "Yellow"
    Info    = "Cyan"
    Header  = "Magenta"
}

function Write-Log {
    param([string]$Message, [string]$Type = "Info")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Type] $Message"
    Add-Content -Path $LOG_FILE -Value $logLine -ErrorAction SilentlyContinue
    
    if (-not $Silent) {
        $color = $colors[$Type]
        if (-not $color) { $color = "White" }
        Write-Host $logLine -ForegroundColor $color
    }
}

function Show-Banner {
    if ($Silent) { return }
    Clear-Host
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor $colors.Header
    Write-Host "║                                                                       ║" -ForegroundColor $colors.Header
    Write-Host "║           ENGENHARIA CAD - INSTALADOR v2.0                           ║" -ForegroundColor $colors.Header
    Write-Host "║                                                                       ║" -ForegroundColor $colors.Header
    Write-Host "║   Sistema de Automação CAD/CAM com Inteligência Artificial           ║" -ForegroundColor $colors.Header
    Write-Host "║                                                                       ║" -ForegroundColor $colors.Header
    Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor $colors.Header
    Write-Host ""
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Find-AutoCADInstallations {
    Write-Log "Procurando instalações do AutoCAD..." "Info"
    
    $found = @()
    
    # Buscar no registro
    $regPaths = @(
        "HKLM:\SOFTWARE\Autodesk\AutoCAD",
        "HKLM:\SOFTWARE\WOW6432Node\Autodesk\AutoCAD"
    )
    
    foreach ($regPath in $regPaths) {
        if (Test-Path $regPath) {
            try {
                $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
                foreach ($version in $versions) {
                    $releases = Get-ChildItem $version.PSPath -ErrorAction SilentlyContinue
                    foreach ($release in $releases) {
                        $location = (Get-ItemProperty -Path $release.PSPath -Name "AcadLocation" -ErrorAction SilentlyContinue).AcadLocation
                        if ($location -and (Test-Path (Join-Path $location "acad.exe"))) {
                            $found += @{
                                Path = $location
                                Version = $version.PSChildName
                                Release = $release.PSChildName
                            }
                        }
                    }
                }
            }
            catch { }
        }
    }
    
    # Buscar em caminhos comuns
    $commonPaths = @(
        "C:\Program Files\Autodesk\AutoCAD 2026",
        "C:\Program Files\Autodesk\AutoCAD 2025",
        "C:\Program Files\Autodesk\AutoCAD 2024",
        "C:\Program Files\Autodesk\AutoCAD 2023",
        "C:\Program Files\Autodesk\AutoCAD 2022",
        "C:\Program Files\Autodesk\AutoCAD 2021",
        "C:\Program Files\Autodesk\AutoCAD 2020"
    )
    
    foreach ($path in $commonPaths) {
        if ((Test-Path $path) -and (Test-Path (Join-Path $path "acad.exe"))) {
            $alreadyFound = $found | Where-Object { $_.Path -eq $path }
            if (-not $alreadyFound) {
                $versionMatch = [regex]::Match($path, "AutoCAD (\d{4})")
                $found += @{
                    Path = $path
                    Version = if ($versionMatch.Success) { "R" + ($versionMatch.Groups[1].Value - 1987) } else { "Unknown" }
                    Release = $versionMatch.Groups[1].Value
                }
            }
        }
    }
    
    return $found
}

function Get-AutoCADSupportPath {
    param([string]$AutoCADPath)
    
    # Tentar encontrar a pasta Support do AutoCAD
    $supportPaths = @()
    
    # Procurar em APPDATA
    $appdataPath = $env:APPDATA
    $autodeskPath = Join-Path $appdataPath "Autodesk"
    
    if (Test-Path $autodeskPath) {
        $acadFolders = Get-ChildItem $autodeskPath -Directory | Where-Object { $_.Name -match "AutoCAD" }
        foreach ($folder in $acadFolders) {
            $supportPath = Join-Path $folder.FullName "Support"
            if (-not (Test-Path $supportPath)) {
                # Tentar subpastas por idioma
                $subFolders = Get-ChildItem $folder.FullName -Directory -ErrorAction SilentlyContinue
                foreach ($sub in $subFolders) {
                    $langSupport = Join-Path $sub.FullName "Support"
                    if (Test-Path $langSupport) {
                        $supportPaths += $langSupport
                    }
                }
            }
            else {
                $supportPaths += $supportPath
            }
        }
    }
    
    return $supportPaths
}

function Install-EngenhariaCAD {
    Write-Log "Iniciando instalação do Engenharia CAD..." "Info"
    
    # 1. Criar pasta de instalação
    Write-Log "Criando pasta de instalação: $INSTALL_PATH" "Info"
    if (-not (Test-Path $INSTALL_PATH)) {
        New-Item -ItemType Directory -Path $INSTALL_PATH -Force | Out-Null
    }
    
    # 2. Criar pasta de comandos (drop folder)
    Write-Log "Criando pasta de comandos: $DROP_PATH" "Info"
    if (-not (Test-Path $DROP_PATH)) {
        New-Item -ItemType Directory -Path $DROP_PATH -Force | Out-Null
    }
    
    # 3. Copiar arquivos principais
    $filesToCopy = @(
        "forge_vigilante.lsp",
        "SINCRONIZADOR.ps1",
        "DETECTAR_AUTOCAD.ps1",
        "INICIAR_SINCRONIZADOR.bat"
    )
    
    foreach ($file in $filesToCopy) {
        $srcPath = Join-Path $SCRIPT_DIR $file
        $dstPath = Join-Path $INSTALL_PATH $file
        
        if (Test-Path $srcPath) {
            Copy-Item -Path $srcPath -Destination $dstPath -Force
            Write-Log "  Copiado: $file" "Success"
        }
        else {
            Write-Log "  Não encontrado: $file (pulando)" "Warning"
        }
    }
    
    # 4. Procurar instalações do AutoCAD
    $acadInstalls = Find-AutoCADInstallations
    
    if ($acadInstalls.Count -eq 0) {
        Write-Log "Nenhuma instalação do AutoCAD encontrada." "Warning"
        Write-Log "O Engenharia CAD funcionará, mas você precisará carregar manualmente o LISP." "Warning"
    }
    else {
        Write-Log "Encontrado(s) $($acadInstalls.Count) instalação(ões) do AutoCAD:" "Success"
        foreach ($acad in $acadInstalls) {
            Write-Log "  - AutoCAD $($acad.Release) em $($acad.Path)" "Info"
        }
        
        # 5. Instalar auto-load em cada instalação
        $acaddocSrc = Join-Path $SCRIPT_DIR "acaddoc.lsp"
        
        if (Test-Path $acaddocSrc) {
            foreach ($acad in $acadInstalls) {
                $supportPaths = Get-AutoCADSupportPath -AutoCADPath $acad.Path
                
                foreach ($supportPath in $supportPaths) {
                    $acaddocDst = Join-Path $supportPath "acaddoc.lsp"
                    
                    # Backup do arquivo existente
                    if (Test-Path $acaddocDst) {
                        $backupPath = "$acaddocDst.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
                        Copy-Item -Path $acaddocDst -Destination $backupPath -Force
                        Write-Log "  Backup criado: $backupPath" "Info"
                        
                        # Verificar se já tem nosso código
                        $existingContent = Get-Content $acaddocDst -Raw -ErrorAction SilentlyContinue
                        if ($existingContent -match "ENGENHARIA CAD") {
                            Write-Log "  Auto-load já configurado em: $supportPath" "Info"
                            continue
                        }
                        
                        # Adicionar ao final do arquivo existente
                        $newContent = Get-Content $acaddocSrc -Raw
                        Add-Content -Path $acaddocDst -Value "`n`n;;; === ENGENHARIA CAD AUTO-LOAD ===`n$newContent"
                        Write-Log "  Auto-load adicionado em: $supportPath" "Success"
                    }
                    else {
                        # Copiar arquivo novo
                        Copy-Item -Path $acaddocSrc -Destination $acaddocDst -Force
                        Write-Log "  Auto-load instalado em: $supportPath" "Success"
                    }
                }
            }
        }
        else {
            Write-Log "acaddoc.lsp não encontrado. Auto-load não configurado." "Warning"
        }
    }
    
    # 6. Criar atalho na área de trabalho
    Write-Log "Criando atalho na área de trabalho..." "Info"
    try {
        $desktopPath = [Environment]::GetFolderPath("Desktop")
        $shortcutPath = Join-Path $desktopPath "Engenharia CAD - Sincronizador.lnk"
        $targetPath = Join-Path $INSTALL_PATH "INICIAR_SINCRONIZADOR.bat"
        
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $targetPath
        $shortcut.WorkingDirectory = $INSTALL_PATH
        $shortcut.Description = "Iniciar Sincronizador Engenharia CAD"
        $shortcut.IconLocation = "shell32.dll,137"
        $shortcut.Save()
        
        Write-Log "Atalho criado na área de trabalho" "Success"
    }
    catch {
        Write-Log "Não foi possível criar atalho: $_" "Warning"
    }
    
    # 7. Testar conexão com o backend
    Write-Log "Testando conexão com o backend..." "Info"
    try {
        $testResult = Invoke-RestMethod -Uri "https://automacao-cad-backend.vercel.app/api/bridge/health" `
            -Method GET -TimeoutSec 10 -ErrorAction Stop
        Write-Log "Conexão com backend: OK" "Success"
    }
    catch {
        Write-Log "Backend não acessível (pode ser temporário): $_" "Warning"
    }
    
    Write-Log "Instalação concluída com sucesso!" "Success"
    
    return $true
}

function Uninstall-EngenhariaCAD {
    Write-Log "Desinstalando Engenharia CAD..." "Info"
    
    # 1. Remover auto-load dos AutoCADs
    $acadInstalls = Find-AutoCADInstallations
    foreach ($acad in $acadInstalls) {
        $supportPaths = Get-AutoCADSupportPath -AutoCADPath $acad.Path
        foreach ($supportPath in $supportPaths) {
            $acaddocPath = Join-Path $supportPath "acaddoc.lsp"
            if (Test-Path $acaddocPath) {
                $content = Get-Content $acaddocPath -Raw -ErrorAction SilentlyContinue
                if ($content -match "ENGENHARIA CAD") {
                    # Remover nosso código
                    $newContent = $content -replace "(?s);;; === ENGENHARIA CAD AUTO-LOAD ===.*$", ""
                    $newContent = $newContent.TrimEnd()
                    
                    if ($newContent.Length -lt 50) {
                        # Se sobrou muito pouco, provavelmente era só nosso arquivo
                        Remove-Item -Path $acaddocPath -Force -ErrorAction SilentlyContinue
                        Write-Log "  Removido: $acaddocPath" "Info"
                    }
                    else {
                        Set-Content -Path $acaddocPath -Value $newContent -Force
                        Write-Log "  Limpo: $acaddocPath" "Info"
                    }
                }
            }
        }
    }
    
    # 2. Remover atalho da área de trabalho
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "Engenharia CAD - Sincronizador.lnk"
    if (Test-Path $shortcutPath) {
        Remove-Item -Path $shortcutPath -Force
        Write-Log "Atalho removido" "Info"
    }
    
    # 3. Remover pasta de instalação
    if (Test-Path $INSTALL_PATH) {
        Remove-Item -Path $INSTALL_PATH -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Pasta de instalação removida: $INSTALL_PATH" "Info"
    }
    
    # Não remover a pasta de comandos por segurança (pode ter arquivos do usuário)
    Write-Log "A pasta $DROP_PATH foi mantida para preservar arquivos do usuário." "Info"
    
    Write-Log "Desinstalação concluída!" "Success"
}

function Show-PostInstallInfo {
    if ($Silent) { return }
    
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor $colors.Success
    Write-Host "║                    INSTALAÇÃO CONCLUÍDA!                              ║" -ForegroundColor $colors.Success
    Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor $colors.Success
    Write-Host ""
    Write-Host "  O que foi instalado:" -ForegroundColor $colors.Info
    Write-Host "    ✓ Arquivos do sistema em: C:\EngenhariaCAD" -ForegroundColor $colors.Success
    Write-Host "    ✓ Pasta de comandos: C:\AutoCAD_Drop" -ForegroundColor $colors.Success
    Write-Host "    ✓ Auto-load configurado no AutoCAD" -ForegroundColor $colors.Success
    Write-Host "    ✓ Atalho criado na área de trabalho" -ForegroundColor $colors.Success
    Write-Host ""
    Write-Host "  Próximos passos:" -ForegroundColor $colors.Info
    Write-Host "    1. Abra o AutoCAD - o sistema será carregado automaticamente" -ForegroundColor White
    Write-Host "    2. Execute o atalho 'Engenharia CAD - Sincronizador' na área de trabalho" -ForegroundColor White
    Write-Host "    3. Acesse https://automacao-cad-frontend.vercel.app e faça login" -ForegroundColor White
    Write-Host ""
    Write-Host "  Comandos do AutoCAD:" -ForegroundColor $colors.Info
    Write-Host "    FORGE_START  - Iniciar monitoramento" -ForegroundColor White
    Write-Host "    FORGE_STOP   - Parar monitoramento" -ForegroundColor White
    Write-Host "    FORGE_STATUS - Ver status" -ForegroundColor White
    Write-Host ""
    Write-Host "  Log de instalação salvo em: $LOG_FILE" -ForegroundColor $colors.Header
    Write-Host ""
}

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

try {
    Show-Banner
    
    # Verificar privilégios de administrador
    if (-not (Test-Admin)) {
        Write-Log "AVISO: Este script precisa ser executado como Administrador para configurar o AutoCAD." "Warning"
        Write-Log "Algumas funcionalidades podem não funcionar corretamente." "Warning"
        Write-Host ""
    }
    
    if ($Uninstall) {
        Uninstall-EngenhariaCAD
    }
    else {
        if (Install-EngenhariaCAD) {
            Show-PostInstallInfo
        }
    }
}
catch {
    Write-Log "ERRO FATAL: $_" "Error"
    Write-Log "Stack: $($_.ScriptStackTrace)" "Error"
}
finally {
    if (-not $Silent) {
        Write-Host ""
        Write-Host "Pressione qualquer tecla para continuar..." -ForegroundColor $colors.Header
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}
