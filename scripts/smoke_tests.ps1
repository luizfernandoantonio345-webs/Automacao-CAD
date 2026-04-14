#!/usr/bin/env pwsh
# ═══════════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD — Post-Deploy Smoke Tests
# ═══════════════════════════════════════════════════════════════════════════════
# Validates that critical endpoints respond correctly after a Vercel deploy.
# Usage:
#   .\smoke_tests.ps1 -BackendUrl "https://automacao-cad-backend.vercel.app"
#   .\smoke_tests.ps1 -BackendUrl "https://automacao-cad-backend.vercel.app" -FrontendUrl "https://automacao-cad-frontend.vercel.app"
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$FrontendUrl
)

$ErrorActionPreference = "Continue"
$pass = 0
$fail = 0
$total = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body,
        [int[]]$ExpectedStatus = @(200),
        [string]$ContainsText
    )

    $script:total++
    Write-Host -NoNewline "  [$script:total] $Name ... "

    try {
        $params = @{
            Uri             = $Url
            Method          = $Method
            UseBasicParsing = $true
            TimeoutSec      = 15
            ErrorAction     = "Stop"
        }

        if ($Body) {
            $params["Body"] = ($Body | ConvertTo-Json -Compress)
            $params["ContentType"] = "application/json"
        }

        $response = Invoke-WebRequest @params

        if ($ExpectedStatus -contains $response.StatusCode) {
            if ($ContainsText -and $response.Content -notlike "*$ContainsText*") {
                Write-Host "FAIL (missing text: $ContainsText)" -ForegroundColor Red
                $script:fail++
                return
            }
            Write-Host "PASS ($($response.StatusCode))" -ForegroundColor Green
            $script:pass++
        }
        else {
            Write-Host "FAIL (got $($response.StatusCode), expected $($ExpectedStatus -join '/'))" -ForegroundColor Red
            $script:fail++
        }
    }
    catch {
        $statusCode = 0
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($ExpectedStatus -contains $statusCode) {
            Write-Host "PASS ($statusCode)" -ForegroundColor Green
            $script:pass++
        }
        else {
            Write-Host "FAIL ($_)" -ForegroundColor Red
            $script:fail++
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=== ENGENHARIA CAD — Smoke Tests ===" -ForegroundColor Cyan
Write-Host "Backend:  $BackendUrl" -ForegroundColor DarkGray
if ($FrontendUrl) { Write-Host "Frontend: $FrontendUrl" -ForegroundColor DarkGray }
Write-Host ""

# ── Backend Health ──
Write-Host "[Backend Health]" -ForegroundColor Yellow
Test-Endpoint -Name "Health check" -Url "$BackendUrl/health" -ContainsText "ok"
Test-Endpoint -Name "Healthz" -Url "$BackendUrl/healthz"

# ── Auth Endpoints ──
Write-Host "[Auth]" -ForegroundColor Yellow
Test-Endpoint -Name "Demo login" -Url "$BackendUrl/auth/demo" -Method "POST" -ExpectedStatus @(200, 429)
Test-Endpoint -Name "Register (validation)" -Url "$BackendUrl/auth/register" -Method "POST" `
    -Body @{ username = ""; password = ""; email = "" } `
    -ExpectedStatus @(400, 422, 429)

# ── Billing Endpoints ──
Write-Host "[Billing]" -ForegroundColor Yellow
Test-Endpoint -Name "Subscription status (nonexistent)" `
    -Url "$BackendUrl/api/billing/subscription/nonexistent@test.com" `
    -ExpectedStatus @(200)
Test-Endpoint -Name "Webhook (invalid payload)" `
    -Url "$BackendUrl/api/billing/webhooks/stripe" -Method "POST" `
    -ExpectedStatus @(400)
Test-Endpoint -Name "Checkout (no auth)" `
    -Url "$BackendUrl/api/billing/checkout" -Method "POST" `
    -Body @{ email = "test@test.com"; tier = "starter" } `
    -ExpectedStatus @(401)

# ── Public API ──
Write-Host "[Public API]" -ForegroundColor Yellow
Test-Endpoint -Name "AI status" -Url "$BackendUrl/api/ai/status" -ExpectedStatus @(200, 503)
Test-Endpoint -Name "CAM materials" -Url "$BackendUrl/api/cam/materials" -ExpectedStatus @(200, 503)
Test-Endpoint -Name "AutoCAD health" -Url "$BackendUrl/api/autocad/health" -ExpectedStatus @(200, 503)

# ── Frontend (if provided) ──
if ($FrontendUrl) {
    Write-Host "[Frontend]" -ForegroundColor Yellow
    Test-Endpoint -Name "Frontend loads" -Url "$FrontendUrl" -ExpectedStatus @(200) -ContainsText "html"
    Test-Endpoint -Name "Login page" -Url "$FrontendUrl/login" -ExpectedStatus @(200)
    Test-Endpoint -Name "Pricing page" -Url "$FrontendUrl/pricing" -ExpectedStatus @(200)
}

# ── Results ──
Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
Write-Host "  Passed: $pass/$total" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
if ($fail -gt 0) {
    Write-Host "  Failed: $fail/$total" -ForegroundColor Red
    Write-Host ""
    Write-Host "SMOKE TESTS FAILED — check the failures above." -ForegroundColor Red
    exit 1
}
else {
    Write-Host ""
    Write-Host "ALL SMOKE TESTS PASSED — deploy is healthy." -ForegroundColor Green
    exit 0
}
