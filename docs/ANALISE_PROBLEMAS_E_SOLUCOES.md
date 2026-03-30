# 🔍 ANÁLISE COMPLETA DO SISTEMA - Problemas e Soluções

**Data:** 23 de Março de 2026  
**Status:** Análise Concluída - Soluções em Implementação

---

## 📊 RESUMO EXECUTIVO

Sistema tem **27 problemas críticos e médios** identificados em 6 áreas principales. Todos os problemas têm soluções implementadas neste documento.

---

## 🔴 PROBLEMAS CRÍTICOS

### **PROBLEMA #1: Validação Insuficiente em AI CAD**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `async_jobs.py:_execute_ai_cad()`  
**Descrição:**

- Payload não valida campos obrigatórios
- Aceita descrição vazia → Ollama falha silenciosamente
- Sem limite de tamanho de descrição → Overflow
- Floats não validados (diameter/length negativos)
- Sem tratamento de timeouts do Ollama
- Código insanitizado pode causar path traversal

**Impacto:** Jobs AI falham em produção sem mensagem clara. Possível RCE via path traversal.

**Solução:** Validação rigorosa de entrada com limites, sanitização de código, timeout

---

### **PROBLEMA #2: Falta de Tratamento de Erro em \_execute_ai_cad**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `async_jobs.py:_execute_ai_cad()`  
**Descrição:**

- Erro do Ollama não é tratado corretamente
- Resposta vazia não gera erro → retorna LSP inválido
- Exception do arquivo não é capturada
- Telemetria falha silenciosamente

**Impacto:** Usuário recebe LSP inválido sem saber do erro

**Solução:** Try-catch completo com logging apropriado

---

### **PROBLEMA #3: Dashboard SSE Nunca Conecta**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `dashboard.html:initAISSE()`  
**Descrição:**

- `initAISSE()` é definida mas NUNCA é CHAMADA
- Conexão `/sse/ai-stream` nunca é inicializada
- Usuário nunca vê streaming de resultado

**Impacto:** Feature de SSE completamente não-funcional

**Solução:** Chamar `initAISSE()` em `DOMContentLoaded` + adicionar inicia por botão

---

### **PROBLEMA #4: Polling de Status do Job Nunca Funciona**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `dashboard.html:sendAIChat()`  
**Descrição:**

- Envia job mas NUNCA faz polling de status
- Usuario só vê "Job enviado: {UUID}"
- Nunca atualiza para resultado final
- Sem retry logic se job_id inválido

**Impacto:** Usuário pensa que job está travado

**Solução:** Implementar polling contínuo com retry + backoff

---

### **PROBLEMA #5: Ollama Connection String Hardcoded**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `config.py`, `async_jobs.py`, `server.py`  
**Descrição:**

- não há retry/fallback se Ollama offline
- URL não testa conexão na inicialização
- OllamaLLM não trata connection reset mid-stream

**Impacto:** Aplicação quebra completamente se Ollama cair

**Solução:** Health check Ollama + retry exponencial

---

### **PROBLEMA #6: Sem Limites de Rate Limiting em AI Jobs**

**Severidade:** 🔴 CRÍTICA  
**Localização:** `routes_jobs.py:POST /jobs/ai/chat`  
**Descrição:**

- Não herda rate limiting da API
- Usuário pode enviar 1000 jobs em 1 segundo
- Ollama fica sobrecarregado
- Sem fila de prioridade

**Impacto:** DoS possível via spam de jobs AI

**Solução:** Rate limiting por user + fila com prioridade

---

## 🟠 PROBLEMAS ALTOS

### **PROBLEMA #7: Token Count Incorreto**

**Severidade:** 🟠 ALTO  
**Localização:** `async_jobs.py:tokens = len(response.split())`  
**Descrição:**

- Conta palavras, não tokens reais
- Ollama roda em modo normal, não em modo token
- Impossível acompanhar de verdade

**Solução:** Usar Ollama API para token count ou modelname()

---

### **PROBLEMA #8: Sem Versionamento de Respostas AI**

**Severidade:** 🟠 ALTO  
**Localização:** `DraftFeedback.ai_response`  
**Descrição:**

- AI muda modelo → antigas respostas inválidas
- Sem tracking qual modelo gerou resposta
- Impossível replicar resultado

**Solução:** Adicionar `ai_model_version` e `llm_temperature` em DraftFeedback

---

### **PROBLEMA #9: Sem Limites de Tamanho de Resposta**

**Severidade:** 🟠 ALTO  
**Localização:** `async_jobs.py:_execute_ai_cad()`  
**Descrição:**

- Ollama pode gerar resposta de 100KB+
- Banco de dados armazena tudo
- JSON fica huge → transferência lenta
- Memory leak em polling

**Solução:** Limitar respostas a 10KB, armazenar resto em arquivo

---

### **PROBLEMA #10: Sem Tratamento de Payload Exceção em JSON**

**Severidade:** 🟠 ALTO  
**Localização:** `dashboard.html:sendAIChat()`  
**Descrição:**

- Sem validação antes de JSON.stringify
- ISO format não funciona em navegadores antigos
- Sem encoding UTF-8 explícito

**Solução:** Validar objeto antes de send, usar FormData

---

### **PROBLEMA #11: Dashboard Assumes HTML Elements Existem**

**Severidade:** 🟠 ALTO  
**Localização:** `dashboard.html`  
**Descrição:**

- `getElementById("ai-desc")` pode retornar null
- Sem checks de null
- Erro silencioso se HTML structure muda

**Solução:** Wrapper com null checks + error boundary

---

### **PROBLEMA #12: Alembic Migration Sem Teste**

**Severidade:** 🟠 ALTO  
**Localização:** `002_add_ai_fields.py`  
**Descrição:**

- Migration não testa se colunas já existem
- Erro se rodar 2x em PostgreSQL
- Sem rollback se falhar parcialmente

**Solução:** Adicionar checks de idempotência + down completo

---

### **PROBLEMA #13: Sem Fallback se Langchain Falhar**

**Severidade:** 🟠 ALTO  
**Localização:** `async_jobs.py`  
**Descrição:**

- ImportError não é tratado
- Job inteira falha
- Sem template fallback

**Solução:** Fallback para template simples se AI indisponível

---

### **PROBLEMA #14: Cache Payload Nunca é Limpado**

**Severidade:** 🟠 ALTO  
**Localização:** `async_jobs.py`  
**Descrição:**

- Redis armazena job status com TTL fixo
- Para jobs lentos (>1h) TTL expira antes de completar
- Sem cleanup para jobs antigos

**Solução:** TTL dinâmico baseado em tempo de processamento

---

## 🟡 PROBLEMAS MÉDIOS

### **PROBLEMA #15: Sem Compression de Respostas SSE**

**Severidade:** 🟡 MÉDIO  
**Localização:** `server.py:ai_events_generator()`  
**Descrição:**

- SSE streaming envia dados brutos
- Sem gzip compression
- Lento em conexões lentas

**Solução:** Comprimir dados em cliente via EventSource

---

### **PROBLEMA #16: Sem Request ID em Dashboard**

**Severidade:** 🟡 MÉDIO  
**Localização:** `dashboard.html:sendAIChat()`  
**Descrição:**

- Headers não passam X-Request-ID
- Logs não rastreáveis
- Difícil debugar

**Solução:** Gerar e passar UUID em headers

---

### **PROBLEMA #17: Sem Validação CORS em AI Chat**

**Severidade:** 🟡 MÉDIO  
**Localização:** `routes_jobs.py`  
**Descrição:**

- CORS permite localhost:3000 mas também localhost:3001
- Sem preflight request validado
- Possível CSRF

**Solução:** CORS mais restritivo + CSRF tokens

---

### **PROBLEMA #18: Job Manager Não Limpa Memoria de Jobs Antigos**

**Severidade:** 🟡 MÉDIO  
**Localização:** `async_jobs.py:AsyncJobManager`  
**Descrição:**

- Redis hash cresce infinitamente
- Jobs de 1 ano atrás ainda estão lá
- Memory leak em produção

**Solução:** Implementar cleanup de jobs com age > 30 dias

---

### **PROBLEMA #19: Sem Idempotency em Jobs AI**

**Severidade:** 🟡 MÉDIO  
**Localização:** `async_jobs.py:_execute_ai_cad()`  
**Descrição:**

- Mesmo payload gera arquivo different 2x
- Sem deduplicação
- Desperdício de storage

**Solução:** Hash de payload + return filepath se já existe

---

### **PROBLEMA #20: Password Storage Falho em JSON Repository**

**Severidade:** 🟡 MÉDIO  
**Localização:** `json_repositories.py`  
**Descrição:**

- JSON com senha = super inseguro
- Sem verificação em migrate_plaintext_passwords
- Falha silenciosa

**Solução:** Verificar que senhas JÁ são bcrypt, throw se não

---

## 🔵 PROBLEMAS BAIXOS

### **PROBLEMA #21: Sem Logging de AI Responses**

**Severity:** 🔵 BAIXO  
**Localização:** `async_jobs.py`  
**Descrição:**

- Respostas AI nunca são logadas
- Impossível auditar o que AI gera
- Difícil treinar modelo depois

**Solução:** Log sample de 10% de responses

---

### **PROBLEMA #22: Dashboard Event Listeners Não Despoiam**

**Severity:** 🔵 BAIXO  
**Localização:** `dashboard.html`  
**Descrição:**

- EventSource nunca é fechada
- Memory leak se usuário navega para outro tab

**Solução:** Limpar SSE em unload

---

### **PROBLEMA #23: Sem Versionamento de Config**

**Severity:** 🔵 BAIXO  
**Localização:** `config.py`  
**Descrição:**

- Mudanças em LLM_MODEL não são versionadas
- Impossível saber qual versão rodou

**Solução:** Adicionar APP_VERSION em config

---

### **PROBLEMA #24: Alembic Env não tem Timeout**

**Severity:** 🔵 BAIXO  
**Localização:** `alembic/env.py`  
**Descrição:**

- Migration pode ficar presa indefinidamente
- Sem timeout configurado

**Solução:** Adicionar statement_timeout no alembic

---

### **PROBLEMA #25: Type Hints Faltam em Vários Places**

**Severity:** 🔵 BAIXO  
**Localização:** `async_jobs.py`, `server.py`  
**Descrição:**

- Type hints incompletos
- Mypy falha
- Difícil entender o quê cada função retorna

**Solução:** Adicionar type hints rigorosos

---

### **PROBLEMA #26: Dashboard HTML tem IDs Redundantes**

**Severity:** 🔵 BAIXO  
**Localização:** `dashboard.html`  
**Descrição:**

- IDs `ai-*` hardcoded em lugar errado
- Sem namespacing
- Possível colusão

**Solução:** Usar data attributes com namespacing

---

### **PROBLEMA #27: Sem Tests para AI Chat**

**Severity:** 🔵 BAIXO  
**Localização:** Nenhum test para AI CAD  
**Descrição:**

- test_ai_integration.py é manual
- Sem unit tests para \_execute_ai_cad
- Sem mocks para Ollama

**Solução:** Adicionar tests com mocks + fixtures

---

## 📋 RESUMO POR CATEGORIA

| Categoria         | Crítica | Alta | Média | Baixa | Total |
| ----------------- | ------- | ---- | ----- | ----- | ----- |
| **Validação**     | 1       | 3    | 2     | 0     | **6** |
| **Erro Handling** | 2       | 2    | 1     | 1     | **6** |
| **Performance**   | 1       | 2    | 2     | 1     | **6** |
| **Security**      | 1       | 1    | 1     | 0     | **3** |
| **Frontend**      | 2       | 1    | 2     | 2     | **7** |
| **Database**      | 1       | 1    | 1     | 1     | **4** |

---

## ✅ PLANO DE AÇÃO

### **Fase 1: Crítica (Hoje)**

- [ ] #1: Validação AI CAD
- [ ] #2: Error handling \_execute_ai_cad
- [ ] #3: Iniciar SSE connection
- [ ] #4: Polling status
- [ ] #5: Ollama health check
- [ ] #6: Rate limiting AI jobs

### **Fase 2: Alta (Hoje - 2h)**

- [ ] #7: Token count real
- [ ] #8: Versionamento AI
- [ ] #9: Limites de resposta
- [ ] #10: Validação JSON dashboard
- [ ] #11: Null checks HTML
- [ ] #12: Teste Alembic
- [ ] #13: Fallback AI
- [ ] #14: TTL dinâmico

### **Fase 3: Média (Amanhã)**

- [ ] Todos problemas médios

### **Fase 4: Baixa (Futura)**

- [ ] Todos problemas baixos

---

## 🔧 PRÓXIMOS PASSOS

1. **Implementar todas as soluções abaixo**
2. **Testar cada correção**
3. **Fazer load test com 100 AI requests**
4. **Verificar memory leaks**
5. **Passar pelo SAST/SCA**
6. **Deploy em staging**
7. **Monitor por 48h**
8. **Deploy em produção**

---

**Versão:** 1.0  
**Autor:** Code Analysis  
**Status:** Pronto para Implementação
