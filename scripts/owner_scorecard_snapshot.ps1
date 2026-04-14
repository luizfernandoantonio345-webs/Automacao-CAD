param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$OutputDir = "docs/reports"
)

$ErrorActionPreference = "Stop"

Write-Host "Generating owner scorecard snapshot from backend endpoints..."

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$outFile = Join-Path $OutputDir "owner_scorecard_snapshot_$timestamp.md"

function Try-GetJson {
    param(
        [string]$Url
    )
    try {
        return Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 15
    }
    catch {
        Write-Warning "Failed endpoint: $Url"
        return $null
    }
}

$health = Try-GetJson "$BaseUrl/health"
$analyticsDashboard = Try-GetJson "$BaseUrl/api/analytics/dashboard"
$analyticsKpis = Try-GetJson "$BaseUrl/api/analytics/kpis"
$performance = Try-GetJson "$BaseUrl/api/analytics/performance"

$lines = @()
$lines += "# Owner Scorecard Snapshot"
$lines += ""
$lines += "Generated at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
$lines += "Base URL: $BaseUrl"
$lines += ""
$lines += "## Platform Health"

if ($health) {
    $lines += "- Overall status: $($health.status)"
    if ($health.services) {
        $lines += "- Database OK: $($health.services.database.ok)"
        $lines += "- Redis OK: $($health.services.redis.ok)"
        $lines += "- Celery OK: $($health.services.celery.ok)"
        $lines += "- LLM OK: $($health.services.llm.ok)"
        $lines += "- AutoCAD OK: $($health.services.autocad.ok)"
    }
}
else {
    $lines += "- Health endpoint unavailable"
}

$lines += ""
$lines += "## Analytics KPIs"

if ($analyticsKpis -and $analyticsKpis.kpis) {
    foreach ($prop in $analyticsKpis.kpis.PSObject.Properties) {
        $kpiName = $prop.Name
        $kpi = $prop.Value
        if ($kpi.current_value -ne $null) {
            $lines += "- ${kpiName}: $($kpi.current_value) $($kpi.unit)"
        }
        else {
            $lines += "- ${kpiName}: available"
        }
    }
}
else {
    $lines += "- KPI endpoint unavailable"
}

$lines += ""
$lines += "## Performance"

if ($performance) {
    foreach ($prop in $performance.PSObject.Properties) {
        $lines += "- $($prop.Name): $($prop.Value)"
    }
}
else {
    $lines += "- Performance endpoint unavailable"
}

$lines += ""
$lines += "## Dashboard Summary"

if ($analyticsDashboard) {
    if ($analyticsDashboard.system_health) {
        $lines += "- System health object present"
    }
    if ($analyticsDashboard.ai_performance) {
        $lines += "- AI performance object present"
    }
    if ($analyticsDashboard.kpis) {
        $lines += "- KPI dictionary present"
    }
}
else {
    $lines += "- Dashboard endpoint unavailable"
}

$lines | Set-Content -Path $outFile -Encoding UTF8

Write-Host "Snapshot generated: $outFile"
Write-Host "Done."
