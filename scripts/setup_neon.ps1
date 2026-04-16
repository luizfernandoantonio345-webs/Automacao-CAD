# =============================================================================
# CONFIGURAR POSTGRESQL NEON - Engenharia CAD
# =============================================================================
# 
# INSTRUÇÕES:
# 1. Copie a Connection String do Neon (formato: postgresql://user:pass@host/db)
# 2. Execute este script no PowerShell
# 3. Cole a Connection String quando solicitado
# 4. O script vai configurar tudo automaticamente!
#
# =============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$DatabaseUrl
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " CONFIGURAR POSTGRESQL NEON" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se está no diretório correto
$ProjectRoot = $PSScriptRoot
if (-not (Test-Path "$ProjectRoot\alembic.ini")) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
if (-not (Test-Path "$ProjectRoot\alembic.ini")) {
    Write-Host "ERRO: Execute este script no diretorio do projeto!" -ForegroundColor Red
    Write-Host "      Ou navegue para: C:\Users\Sueli\Desktop\Automacao CAD" -ForegroundColor Yellow
    exit 1
}

Set-Location $ProjectRoot
Write-Host "Diretorio: $ProjectRoot" -ForegroundColor Gray

# Solicitar Connection String se não fornecida
if (-not $DatabaseUrl) {
    Write-Host ""
    Write-Host "Cole a Connection String do Neon:" -ForegroundColor Yellow
    Write-Host "(Formato: postgresql://user:pass@host/db?sslmode=require)" -ForegroundColor Gray
    Write-Host ""
    $DatabaseUrl = Read-Host "DATABASE_URL"
}

# Validar formato
if (-not $DatabaseUrl.StartsWith("postgresql://") -and -not $DatabaseUrl.StartsWith("postgres://")) {
    Write-Host ""
    Write-Host "ERRO: URL invalida! Deve comecar com postgresql://" -ForegroundColor Red
    exit 1
}

# Normalizar URL (postgres:// -> postgresql://)
$DatabaseUrl = $DatabaseUrl -replace "^postgres://", "postgresql://"

# Garantir sslmode=require
if (-not $DatabaseUrl.Contains("sslmode=")) {
    if ($DatabaseUrl.Contains("?")) {
        $DatabaseUrl = "$DatabaseUrl&sslmode=require"
    }
    else {
        $DatabaseUrl = "$DatabaseUrl?sslmode=require"
    }
}

Write-Host ""
Write-Host "[OK] Connection String validada!" -ForegroundColor Green

# Definir variável de ambiente
$env:DATABASE_URL = $DatabaseUrl
Write-Host "[OK] DATABASE_URL definida" -ForegroundColor Green

# Ativar ambiente virtual
Write-Host ""
Write-Host "Ativando ambiente virtual..." -ForegroundColor Cyan
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
    Write-Host "[OK] Ambiente virtual ativado" -ForegroundColor Green
}
else {
    Write-Host "[!] Ambiente virtual nao encontrado, continuando..." -ForegroundColor Yellow
}

# Criar script Python temporário para testar conexão
$testScript = @'
import os
import sys
try:
    import psycopg2
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERRO: DATABASE_URL nao definida")
        sys.exit(1)
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    print(f"Conectado: {version[:60]}...")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"ERRO: {e}")
    sys.exit(1)
'@

$testScriptPath = "$env:TEMP\test_neon_connection.py"
$testScript | Out-File -FilePath $testScriptPath -Encoding UTF8

# Testar conexão
Write-Host ""
Write-Host "Testando conexao com PostgreSQL..." -ForegroundColor Cyan
$result = python $testScriptPath
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $result" -ForegroundColor Green
}
else {
    Write-Host "ERRO: Falha na conexao!" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifique:" -ForegroundColor Yellow
    Write-Host "  1. A Connection String esta correta?" -ForegroundColor Yellow
    Write-Host "  2. Voce esta conectado a internet?" -ForegroundColor Yellow
    Write-Host "  3. psycopg2 esta instalado? (pip install psycopg2-binary)" -ForegroundColor Yellow
    exit 1
}

# Executar migrations
Write-Host ""
Write-Host "Executando migrations do Alembic..." -ForegroundColor Cyan
try {
    alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Migrations concluidas!" -ForegroundColor Green
    }
    else {
        throw "Alembic retornou erro"
    }
}
catch {
    Write-Host "ERRO: Falha nas migrations!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Criar script Python para verificar tabelas
$verifyScript = @'
import os
import psycopg2
url = os.environ.get("DATABASE_URL", "")
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name
""")
tables = cur.fetchall()
print(f"Tabelas criadas: {len(tables)}")
for t in tables:
    print(f"  - {t[0]}")
conn.close()
'@

$verifyScriptPath = "$env:TEMP\verify_neon_tables.py"
$verifyScript | Out-File -FilePath $verifyScriptPath -Encoding UTF8

# Verificar tabelas criadas
Write-Host ""
Write-Host "Verificando tabelas criadas..." -ForegroundColor Cyan
python $verifyScriptPath

# Limpar arquivos temporários
Remove-Item $testScriptPath -ErrorAction SilentlyContinue
Remove-Item $verifyScriptPath -ErrorAction SilentlyContinue

# Instruções finais
Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host " CONFIGURACAO LOCAL CONCLUIDA!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proximo passo: Configurar no Vercel" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Acesse: https://vercel.com/dashboard" -ForegroundColor Cyan
Write-Host "2. Selecione: automacao-cad-backend" -ForegroundColor Cyan
Write-Host "3. Va para: Settings -> Environment Variables" -ForegroundColor Cyan
Write-Host "4. Adicione:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Key:   DATABASE_URL" -ForegroundColor White
Write-Host "   Value: (a URL que voce colou acima)" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Marque: Production e Preview" -ForegroundColor Cyan
Write-Host "6. Clique: Save" -ForegroundColor Cyan
Write-Host "7. Faca Redeploy do projeto" -ForegroundColor Cyan
Write-Host ""
Write-Host "Depois verifique em:" -ForegroundColor Yellow
Write-Host "https://automacao-cad-backend.vercel.app/health" -ForegroundColor White
Write-Host ""

# Copiar URL para clipboard
try {
    $DatabaseUrl | Set-Clipboard
    Write-Host "[OK] DATABASE_URL copiada para a area de transferencia!" -ForegroundColor Green
}
catch {
    # Ignorar erro de clipboard
}
