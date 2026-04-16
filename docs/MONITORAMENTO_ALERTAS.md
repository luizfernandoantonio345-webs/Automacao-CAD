# 📊 Monitoramento e Alertas — Engenharia CAD

Este guia explica como configurar monitoramento e alertas para o sistema em produção.

## Endpoints de Health Check

| Endpoint             | Descrição                                            | Uso                     |
| -------------------- | ---------------------------------------------------- | ----------------------- |
| `/health`            | Status completo (banco, Redis, Celery, AutoCAD, LLM) | Monitoramento detalhado |
| `/healthz`           | Health check simples para load balancers             | Kubernetes, Vercel      |
| `/api/bridge/health` | Status de conexão do agente PowerShell               | Frontend polling        |

### Exemplo de Resposta `/health`

```json
{
  "status": "healthy",
  "database": true,
  "services": {
    "database": {
      "ok": true,
      "type": "postgresql",
      "ephemeral": false
    },
    "redis": {
      "ok": true,
      "configured": true
    },
    "llm": {
      "ok": true,
      "providers": {
        "openai": { "available": true },
        "anthropic": { "available": true }
      }
    }
  }
}
```

---

## Configuração de Alertas no Vercel

### Passo 1: Acessar Configurações

1. Vá para https://vercel.com/dashboard
2. Selecione o projeto `automacao-cad-backend`
3. Settings → Notifications

### Passo 2: Configurar Alertas de Deploy

| Evento               | Ação Recomendada        |
| -------------------- | ----------------------- |
| Deployment Failed    | ✅ Ativar email + Slack |
| Deployment Succeeded | ℹ️ Opcional             |
| Domain Expires Soon  | ✅ Ativar email         |

### Passo 3: Configurar Webhooks

Para alertas avançados, configure webhooks:

```json
{
  "url": "https://seu-servidor.com/webhooks/vercel",
  "events": ["deployment.created", "deployment.error", "deployment.ready"]
}
```

---

## Monitoramento Externo

### Opção 1: UptimeRobot (Grátis)

1. Crie conta em https://uptimerobot.com
2. Adicione monitor HTTP:
   - URL: `https://automacao-cad-backend.vercel.app/healthz`
   - Intervalo: 5 minutos
   - Timeout: 30 segundos
3. Configure alertas por email/Telegram/Slack

### Opção 2: Better Stack (Grátis até 10 monitores)

1. Crie conta em https://betterstack.com
2. Adicione heartbeat monitor
3. Configure alertas via PagerDuty, Slack, etc.

### Opção 3: Cronitor (Grátis até 5 monitores)

1. Crie conta em https://cronitor.io
2. Adicione monitor de uptime
3. Configure alertas

---

## Script de Monitoramento Local

Execute este script PowerShell para monitorar o sistema:

```powershell
# monitor_health.ps1
param(
    [int]$IntervalSeconds = 60,
    [string]$BackendUrl = "https://automacao-cad-backend.vercel.app"
)

$ErrorActionPreference = "SilentlyContinue"

function Test-Health {
    $response = Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec 10 -ErrorAction SilentlyContinue
    return $response
}

Write-Host "========================================="
Write-Host " ENGENHARIA CAD - MONITOR"
Write-Host "========================================="
Write-Host "Backend: $BackendUrl"
Write-Host "Intervalo: ${IntervalSeconds}s"
Write-Host ""

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $health = Test-Health

    if ($health.status -eq "healthy") {
        Write-Host "[$timestamp] ✅ HEALTHY - DB: $($health.services.database.type)" -ForegroundColor Green
    } elseif ($health.status -eq "degraded") {
        Write-Host "[$timestamp] ⚠️ DEGRADED" -ForegroundColor Yellow

        # Verificar serviços
        if (-not $health.services.database.ok) {
            Write-Host "  └─ ❌ Database: $($health.services.database.error)" -ForegroundColor Red
        }
        if (-not $health.services.redis.ok -and $health.services.redis.configured) {
            Write-Host "  └─ ❌ Redis: $($health.services.redis.error)" -ForegroundColor Red
        }
    } else {
        Write-Host "[$timestamp] ❌ OFFLINE ou ERRO" -ForegroundColor Red
    }

    Start-Sleep -Seconds $IntervalSeconds
}
```

**Uso:**

```powershell
.\monitor_health.ps1 -IntervalSeconds 30
```

---

## Alertas Automáticos via Telegram

### Configurar Bot Telegram

1. Crie um bot com @BotFather no Telegram
2. Obtenha o token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
3. Obtenha seu Chat ID (mensagem para @userinfobot)

### Script de Alerta

```powershell
# alert_telegram.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$BotToken,
    [Parameter(Mandatory=$true)]
    [string]$ChatId,
    [string]$BackendUrl = "https://automacao-cad-backend.vercel.app"
)

function Send-TelegramAlert {
    param([string]$Message)

    $url = "https://api.telegram.org/bot$BotToken/sendMessage"
    $body = @{
        chat_id = $ChatId
        text = $Message
        parse_mode = "Markdown"
    }
    Invoke-RestMethod -Uri $url -Method Post -Body $body | Out-Null
}

$lastStatus = "unknown"

while ($true) {
    try {
        $health = Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec 10
        $currentStatus = $health.status

        # Alertar se mudou de healthy para outro estado
        if ($lastStatus -eq "healthy" -and $currentStatus -ne "healthy") {
            Send-TelegramAlert "🔴 *ALERTA* - Engenharia CAD está $currentStatus`n`nVerifique: $BackendUrl/health"
        }

        # Alertar se voltou ao normal
        if ($lastStatus -ne "healthy" -and $currentStatus -eq "healthy") {
            Send-TelegramAlert "✅ *RECUPERADO* - Engenharia CAD voltou ao normal"
        }

        $lastStatus = $currentStatus
    } catch {
        if ($lastStatus -ne "offline") {
            Send-TelegramAlert "🔴 *ALERTA* - Engenharia CAD está OFFLINE`n`nEndpoint não responde"
            $lastStatus = "offline"
        }
    }

    Start-Sleep -Seconds 60
}
```

---

## Métricas Recomendadas

| Métrica                  | Threshold | Ação                 |
| ------------------------ | --------- | -------------------- |
| Response Time `/healthz` | > 2s      | Investigar latência  |
| Uptime                   | < 99.5%   | Investigar falhas    |
| Error Rate (5xx)         | > 1%      | Revisar logs         |
| Database Connection      | Falha     | Verificar PostgreSQL |
| Agent Heartbeat          | > 60s sem | Verificar PowerShell |

---

## Logs no Vercel

### Acessar Logs em Tempo Real

1. Vercel Dashboard → Projeto → Logs
2. Filtrar por:
   - Level: `error`, `warning`
   - Function: `api/index.py`
   - Time range: Last 24h

### Exportar Logs para Análise

```bash
# Via Vercel CLI
vercel logs automacao-cad-backend --follow
```

---

## Checklist de Monitoramento

- [ ] UptimeRobot configurado para `/healthz`
- [ ] Alertas de email no Vercel ativados
- [ ] Webhook para Slack/Discord configurado
- [ ] Script de monitoramento local testado
- [ ] Alertas Telegram configurados (opcional)
- [ ] Dashboard de métricas criado (opcional)

---

_Documento atualizado: Abril 2026_
