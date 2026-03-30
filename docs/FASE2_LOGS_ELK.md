# ====================================================================
# FASE 2: Logs Estruturados + ELK Stack
# Guia para adicionar observabilidade avançada
# ====================================================================

## 🎯 O Que Foi Implementado

### ✓ Logging Estruturado JSON
- Logs em formato JSON para busca e análise
- Campos estruturados: timestamp, level, task_id, job_type, duration
- Arquivos: `/app/logs/celery.log` e `/app/logs/celery_structured.log`

### ✓ Loki + Promtail
- **Loki**: Agregador de logs distribuído (como ELK mas mais leve)
- **Promtail**: Agente que coleta logs dos containers e envia para Loki
- Busca de logs em tempo real via Grafana

### ✓ Elasticsearch + Kibana (Básico)
- **Elasticsearch**: Busca full-text de logs
- **Kibana**: Dashboard para visualizar logs
- Integração com logs estruturados

## 🚀 Como Usar

### 1. Atualizar Docker Compose
```bash
# Merge docker-compose-fase2.yml com docker-compose.yml
# Ou usar docker-compose -f docker-compose.yml -f docker-compose-fase2.yml up -d
```

### 2. Iniciar Serviços
```bash
docker-compose -f docker-compose.yml -f docker-compose-fase2.yml up -d
```

### 3. Acessar Dashboards

| Serviço | URL | Função |
|---------|-----|--------|
| **Loki** | http://localhost:3100 | API de logs |
| **Kibana** | http://localhost:5601 | Dashboard logs |
| **Grafana** | http://localhost:3000 | Logs via Loki |

### 4. Configurar Kibana
1. Acesse http://localhost:5601
2. Vá em "Management" → "Index Patterns"
3. Crie pattern: `celery-*`
4. Configure timestamp field

### 5. Adicionar Loki no Grafana
1. Acesse http://localhost:3000
2. "Configuration" → "Data Sources" → "Add data source"
3. Escolher "Loki", URL: http://loki:3100
4. Salvar e testar

### 6. Explorar Logs
- **Grafana Explore**: Selecione Loki datasource
- Query: `{job="cad_workers"}` para ver logs dos workers
- Query: `{container="cad-worker-1"}` para container específico

## 📊 Benefícios

- ✅ **Busca avançada**: Encontre logs por task_id, job_type, nível
- ✅ **Correlação**: Ligue logs com métricas Prometheus
- ✅ **Alertas**: Configure alertas em logs (ex: muitos erros)
- ✅ **Debugging**: Trace execução completa de tasks
- ✅ **Auditoria**: Logs imutáveis para compliance

## 🔧 Arquivos Criados

- `docker-compose-fase2.yml` - Serviços ELK
- `loki-config.yml` - Config Loki
- `promtail-config.yml` - Config Promtail
- Logs estruturados em `celery_config.py` e `celery_tasks.py`

## 📈 Próximas Fases

- **Fase 3**: Circuit Breaker + Dead Letter Queue
- **Fase 4**: GPU Support (CUDA)
- **Fase 5**: Kubernetes (EKS)

**Fase 2 completa! Sistema agora com observabilidade enterprise.** 🚀