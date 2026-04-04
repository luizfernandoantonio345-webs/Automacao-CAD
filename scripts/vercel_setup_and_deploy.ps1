param(
    [string]$BackendProject,
    [string]$FrontendProject,
    [string]$Scope,
    [switch]$Prod,
    [string]$JarvisSecret,
    [string]$EngAuthSecret,
    [string]$LicenseSecret,
    [string]$DatabaseUrl,
    [ValidateSet("development", "production")]
    [string]$AppEnv = "production",
    [bool]$AllowDemoLogin = $true,
    [bool]$SimulationMode = $true,
    [bool]$LicenseFallbackEnabled = $true
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[vercel-deploy] $Message" -ForegroundColor Cyan
}

function Invoke-Vercel {
    param([string[]]$Arguments)
    Write-Host ("vercel " + ($Arguments -join " ")) -ForegroundColor DarkGray
    & vercel @Arguments
}

function Resolve-ProjectName {
    param(
        [string]$Provided,
        [string]$Prompt
    )

    if ($Provided -and $Provided.Trim().Length -gt 0) {
        return $Provided.Trim()
    }

    $value = Read-Host $Prompt
    if (-not $value -or $value.Trim().Length -eq 0) {
        throw "Nome do projeto nao informado."
    }

    return $value.Trim()
}

function Set-VercelEnvValue {
    param(
        [string]$Name,
        [string]$Value,
        [string]$Environment,
        [string]$Cwd,
        [string]$ScopeValue
    )

    $rmArgs = @("env", "rm", $Name, $Environment, "--yes", "--cwd", $Cwd)
    if ($ScopeValue) {
        $rmArgs += @("--scope", $ScopeValue)
    }

    try {
        Invoke-Vercel -Arguments $rmArgs | Out-Null
    }
    catch {
        # Ignore removal errors when variable does not exist.
    }

    $addArgs = @("env", "add", $Name, $Environment, "--cwd", $Cwd)
    if ($ScopeValue) {
        $addArgs += @("--scope", $ScopeValue)
    }

    $Value | & vercel @addArgs | Out-Null
}

function To-VercelBool {
    param([bool]$Value)
    if ($Value) {
        return "true"
    }
    return "false"
}

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    throw "CLI da Vercel nao encontrada. Instale com: npm i -g vercel"
}

$backend = Resolve-ProjectName -Provided $BackendProject -Prompt "Nome do projeto BACKEND na Vercel"
$frontend = Resolve-ProjectName -Provided $FrontendProject -Prompt "Nome do projeto FRONTEND na Vercel"

$commonArgs = @()
if ($Scope) {
    $commonArgs += @("--scope", $Scope)
}

Write-Step "Linkando backend na raiz do repositorio"
Invoke-Vercel -Arguments (@("link", "--yes", "--project", $backend, "--cwd", ".") + $commonArgs) | Out-Null

$backendVars = @{
    "APP_ENV"                  = $AppEnv
    "ALLOW_DEMO_LOGIN"         = (To-VercelBool -Value $AllowDemoLogin)
    "SIMULATION_MODE"          = (To-VercelBool -Value $SimulationMode)
    "LICENSE_FALLBACK_ENABLED" = (To-VercelBool -Value $LicenseFallbackEnabled)
}

if ($JarvisSecret -and $JarvisSecret.Trim().Length -gt 0) {
    $backendVars["JARVIS_SECRET"] = $JarvisSecret.Trim()
}
else {
    Write-Step "JARVIS_SECRET nao informado por parametro; mantendo valor ja configurado na Vercel"
}

if ($EngAuthSecret -and $EngAuthSecret.Trim().Length -gt 0) {
    $backendVars["ENG_AUTH_SECRET"] = $EngAuthSecret.Trim()
}

if ($LicenseSecret -and $LicenseSecret.Trim().Length -gt 0) {
    $backendVars["LICENSE_SECRET"] = $LicenseSecret.Trim()
}

if ($DatabaseUrl -and $DatabaseUrl.Trim().Length -gt 0) {
    $backendVars["DATABASE_URL"] = $DatabaseUrl.Trim()
}

Write-Step "Sincronizando variaveis de ambiente do backend"

$backendTargetEnvs = @("preview")
if ($Prod) {
    $backendTargetEnvs = @("production")
}

foreach ($backendEnv in $backendTargetEnvs) {
    foreach ($entry in $backendVars.GetEnumerator()) {
        Set-VercelEnvValue -Name $entry.Key -Value $entry.Value -Environment $backendEnv -Cwd "." -ScopeValue $Scope
    }
}

Write-Step "Fazendo deploy do backend"
$backendDeployArgs = @("deploy", "--yes", "--cwd", ".")
if ($Prod) {
    $backendDeployArgs += "--prod"
}
$backendDeployArgs += $commonArgs

$backendOutput = Invoke-Vercel -Arguments $backendDeployArgs | Out-String
$backendUrl = [regex]::Match($backendOutput, "https://[a-zA-Z0-9.-]+\.vercel\.app").Value
if (-not $backendUrl) {
    throw "Nao foi possivel extrair a URL do backend a partir da saida do deploy."
}

Write-Step "URL backend detectada: $backendUrl"

Write-Step "Linkando frontend (diretorio frontend)"
Invoke-Vercel -Arguments (@("link", "--yes", "--project", $frontend, "--cwd", "frontend") + $commonArgs) | Out-Null

Write-Step "Sincronizando variaveis de ambiente do frontend"
$frontendVars = @(
    "REACT_APP_API_URL",
    "REACT_APP_SSE_URL",
    "REACT_APP_LICENSING_URL"
)

$targetEnvs = @("preview")
if ($Prod) {
    $targetEnvs += "production"
}

foreach ($envName in $targetEnvs) {
    foreach ($varName in $frontendVars) {
        Set-VercelEnvValue -Name $varName -Value $backendUrl -Environment $envName -Cwd "frontend" -ScopeValue $Scope
    }
}

Write-Step "Fazendo deploy do frontend"
$frontendDeployArgs = @("deploy", "--yes", "--cwd", "frontend")
if ($Prod) {
    $frontendDeployArgs += "--prod"
}
$frontendDeployArgs += $commonArgs

$frontendOutput = Invoke-Vercel -Arguments $frontendDeployArgs | Out-String
$frontendUrl = [regex]::Match($frontendOutput, "https://[a-zA-Z0-9.-]+\.vercel\.app").Value

Write-Host ""
Write-Host "Backend URL : $backendUrl" -ForegroundColor Green
if ($frontendUrl) {
    Write-Host "Frontend URL: $frontendUrl" -ForegroundColor Green
}
else {
    Write-Host "Frontend URL: nao identificada na saida, verifique o log do deploy." -ForegroundColor Yellow
}
Write-Host "Concluido." -ForegroundColor Green
