# ═══════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD - AUTO APPLOAD LISP (v3.0 Corrigido)
# Carrega automaticamente forge_vigilante.lsp no AutoCAD via COM
# ═══════════════════════════════════════════════════════════════════════════

[CmdletBinding()]
param(
    [switch]$Silent = $false,
    [string]$LspPath = "C:\EngenhariaCAD\forge_vigilante.lsp",
    [string]$DropPath = "C:\AutoCAD_Drop"
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

function Write-Status {
    param([string]$Msg, [string]$Color = 'Cyan')
    if (-not $Silent) {
        Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Msg" -ForegroundColor $Color
    }
}

function Test-CADRunning {
    $acad = Get-Process -Name "acad" -ErrorAction SilentlyContinue
    $gcad = Get-Process -Name "gcad" -ErrorAction SilentlyContinue
    return ($acad.Count -gt 0 -or $gcad.Count -gt 0)
}

function Get-CADApplication {
    # Tentar AutoCAD primeiro
    try {
        $app = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        return $app
    }
    catch { }
    
    # Tentar GstarCAD
    try {
        $app = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Gcad.Application")
        return $app
    }
    catch { }
    
    return $null
}

function Load-LSP {
    Write-Status "Aguardando AutoCAD estabilizar..."
    
    # Aguardar processo do CAD
    $timeout = 60
    while (-not (Test-CADRunning) -and $timeout -gt 0) {
        Start-Sleep -Seconds 2
        $timeout -= 2
        if (-not $Silent) { Write-Host "." -NoNewline }
    }
    if (-not $Silent) { Write-Host "" }
    
    if (-not (Test-CADRunning)) {
        Write-Status "AutoCAD nao iniciado em 60s" Red
        return $false
    }
    
    # Aguardar mais para COM estar pronto
    Start-Sleep -Seconds 5
    
    Write-Status "AutoCAD detectado - conectando via COM..."
    
    try {
        $com = Get-CADApplication
        
        if (-not $com) {
            Write-Status "Nao foi possivel conectar via COM" Yellow
            Write-Status "Execute manualmente: APPLOAD -> $LspPath" Yellow
            return $false
        }
        
        $com.Visible = $true
        $doc = $com.ActiveDocument
        
        if (-not $doc) {
            Write-Status "Nenhum documento ativo - criando novo..." Yellow
            $doc = $com.Documents.Add()
        }
        
        Write-Status "COM conectado - carregando LSP..."
        
        # Escapar path para LISP (usar / em vez de \)
        $lspPathEscaped = $LspPath.Replace("\", "/")
        
        # Carregar LSP diretamente via comando LISP
        $loadCmd = "(load `"$lspPathEscaped`") "
        $doc.SendCommand($loadCmd)
        Start-Sleep -Seconds 2
        
        # Iniciar vigilante
        $doc.SendCommand("(FORGE_START) ")
        Start-Sleep -Seconds 1
        
        Write-Status "LSP carregado e FORGE_START executado!" Green
        
        # Criar pasta drop se nao existe
        if (-not (Test-Path $DropPath)) {
            New-Item -ItemType Directory -Path $DropPath -Force | Out-Null
            Write-Status "Pasta $DropPath criada" Green
        }
        
        return $true
    }
    catch {
        Write-Status "Erro COM: $_" Red
        Write-Status "Execute manualmente no AutoCAD:" Yellow
        Write-Status "  Comando: (load `"$lspPathEscaped`")" Yellow
        Write-Status "  Depois: (FORGE_START)" Yellow
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

# Verificar se LSP existe
if (-not (Test-Path $LspPath)) {
    Write-Status "LSP nao encontrado: $LspPath" Red
    Write-Status "Execute primeiro: DETECTAR_AUTOCAD.ps1" Yellow
    exit 1
}

$result = Load-LSP

if ($result) {
    Write-Status "Setup completo! Sistema pronto para automacao." Green
    exit 0
}
else {
    Write-Status "Setup com avisos - verifique os logs acima." Yellow
    exit 0  # Nao falhar, pois pode ser carregado manualmente
}

