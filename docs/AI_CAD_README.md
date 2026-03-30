# Integração AI CAD no Engenharia CAD

## Overview

Integração completa de IA no Engenharia CAD usando Ollama + LangChain para gerar código LSP de AutoCAD automaticamente a partir de descrições naturais de peças.

## Arquitetura

```
┌─────────────┐
│ Dashboard   │
│ (HTML/JS)   │
└──────┬──────┘
       │ POST /jobs/ai/chat
       ▼
┌─────────────────┐     ┌─────────────┐
│ FastAPI Routes  │────▶│ Job Manager │
│ /jobs/ai/chat   │     │ (Redis)     │
└─────────────────┘     └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │ Worker Job  │
                        │ ai_cad type │
                        └──────┬──────┘
                               │
                        ┌──────▼──────────┐
                        │ Ollama LLM      │
                        │ (llama3.2:1b)   │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────┐
                        │ LSP File    │
                        │ (saved)     │
                        └─────────────┘
```

## Componentes Implementados

### 1. **config.py** - Configuração Ollama

```python
ollama_url: str = "http://localhost:11434"
llm_model: str = "llama3.2:1b"
max_tokens: int = 2048
```

### 2. **models.py** - Campos de Resposta AI

```python
class DraftFeedback:
    ai_response: Text
    tokens_used: Integer
```

### 3. **async_jobs.py** - Job Type: ai_cad

```python
def _execute_ai_cad(self, payload):
    # Gera LSP usando Ollama
    # Salva arquivo em output_dir
    # Retorna {lsp_path, tokens, ai_response}
```

### 4. **routes_jobs.py** - POST /jobs/ai/chat

```python
@router.post("/ai/chat")
async def submit_ai_chat_job(payload):
    return job_manager.submit_job("ai_cad", payload)
```

### 5. **dashboard.html** - Chat UI + SSE

- Interface gráfica para enviar prompts
- Streaming de resultados via SSE /sse/ai-stream
- Exibição em tempo real do LSP gerado

### 6. **Migration Alembic** - Versão 002

Adiciona colunas `ai_response` e `tokens_used` à tabela `draft_feedback`.

### 7. **Worker** - start_job_workers.py

```bash
python start_job_workers.py --job-types ai_cad
```

## Instalação

### 1. Dependências Python

```bash
pip install -r requirements.txt
```

Novas dependências adicionadas:

```
langchain-ollama==0.1.0
ollama==0.3.3
```

### 2. Ollama Local

```bash
# Download e instale Ollama em https://ollama.ai

# Puxe o modelo (primeira vez demora)
ollama pull llama3.2:1b

# Verifique se está rodando
curl http://localhost:11434/api/tags
```

### 3. Variáveis de Ambiente (.env)

```bash
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.2:1b
MAX_TOKENS=2048
REDIS_URL=redis://localhost:6379/0
JOBS_REDIS_URL=redis://localhost:6379/1
```

## Uso

### Teste Direto (curl)

```bash
curl -X POST http://127.0.0.1:8000/jobs/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "desc": "flange 4 furos",
    "diameter": 50,
    "length": 200,
    "details": "Material aço inox, furos M5",
    "code": "FLANGE-001",
    "company": "Engenharia Teste"
  }'
```

**Resposta:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "submitted"
}
```

### Consultar Status

```bash
curl http://127.0.0.1:8000/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Resposta (quando concluído):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "ai_cad",
  "status": "completed",
  "result": {
    "lsp_path": "/path/to/data/output/FLANGE-001_ai.lsp",
    "tokens": 1250,
    "ai_response": "(command \"._circle\" ...)..."
  }
}
```

### Dashboard Web

```
http://127.0.0.1:8000/dashboard.html
```

Painel com:

- Chat AI para gerar LSP
- Campos: Descrição, Diâmetro, Comprimento, Detalhes
- Visualização em tempo real da resposta
- Status do job

### Teste Automatizado

```bash
python test_ai_integration.py
```

Valida:

- ✓ Dependências instaladas
- ✓ Conectividade com servidor
- ✓ Submissão de job
- ✓ Monitoramento de status
- ✓ Arquivo LSP gerado

## Compatibilidade

### Redis vs SQLite

- **Com Redis:** Jobs processados assincrono em workers separados
- **Sem Redis:** Jobs executados sincronamente (mais lento)

### Banco de Dados

- **SQLite:** Padrão, funciona offline
- **PostgreSQL:** Production-ready com ai_response e tokens_used

## Prompt do AI

Template padrão (customize conforme necessário):

```
Gere código LSP AutoCAD para: {desc}
Parâmetros: Ø{diameter} x {length}mm, {details}
Output apenas código LSP válido.
```

### Exemplos de Entrada

- "eixo cônico 100x300mm com chanfro"
- "placa base 200x150mm com 6 furos"
- "cilindro hidráulico bore 80mm"

## Configuração Avançada

### Modelo Melhorado

Para melhor qualidade (mais lento, mais memória):

```bash
ollama pull llama2:7b
```

```env
LLM_MODEL=llama2:7b
MAX_TOKENS=4096
```

### Temperatura e Parâmetros

Modifique `langchain_ollama.OllamaLLM`:

```python
llm = OllamaLLM(
    model=CONFIG.llm_model,
    base_url=CONFIG.ollama_url,
    max_tokens=CONFIG.max_tokens,
    temperature=0.3,  # Mais determinístico
    top_p=0.9
)
```

## Troubleshooting

### Ollama não responde

```bash
# Verifique se está rodando
curl http://localhost:11434/api/tags

# Reinicie se necessário
ollama serve
```

### ImportError: langchain_ollama

```bash
pip install --upgrade langchain-ollama ollama
```

### Redis não disponível

System cairá em fallback sincronamente. Para desenvolvimento é ok.

### Arquivo LSP vazio

Verifique:

1. Modelo Ollama está respondendo
2. Descrição no payload
3. Memory do Ollama suficiente (1GB mínimo)

## Monitoramento

### Logs

```bash
tail -f data/engenharia_automacao.log
```

### Redis

```bash
redis-cli
> KEYS jobs:*
> LLEN jobs:ai_cad
```

### Status de Jobs

```bash
# Ver todos os jobs
curl http://127.0.0.1:8000/jobs/*

# Status específico
curl http://127.0.0.1:8000/jobs/{job_id}
```

## Performance

| Métrica        | Valor       |
| -------------- | ----------- |
| Modelo         | llama3.2:1b |
| Tempo Resposta | 5-15s       |
| Tokens Típicos | 500-2000    |
| Memória Ollama | 1-2 GB      |
| CPU            | 20-40%      |

## Próximos Passos

1. **Validação LSP:** Integrar verifier de sintaxe LSP
2. **Cache:** Armazenar respostas similares
3. **Fine-tuning:** Treinar modelo com exemplos específicos
4. **Rollback:** Fallback para templates se AI falhar
5. **Métricas:** Dashboard de qualidade das gerações

## Notas de Produção

- Ollama deve rodar em servidor dedicado ou container
- Configure rate-limiting para evitar abuse
- Implemente fila de prioridade para jobs críticos
- Monitore latência e qualidade do output
- Use modelo maior em produção
- Implemente versionamento de respostas AI

---

**Versão:** 1.0  
**Data:** 2026-03-23  
**Status:** ✓ Pronto para Teste
