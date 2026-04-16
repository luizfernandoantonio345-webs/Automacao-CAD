# 🔐 Segurança — Engenharia CAD

Este documento descreve as medidas de segurança implementadas no sistema.

## Headers de Segurança

### Frontend (automacao-cad-frontend.vercel.app)

| Header                    | Valor                                      | Proteção              |
| ------------------------- | ------------------------------------------ | --------------------- |
| `Content-Security-Policy` | Ver abaixo                                 | XSS, Code Injection   |
| `X-Content-Type-Options`  | `nosniff`                                  | MIME-type sniffing    |
| `X-Frame-Options`         | `DENY`                                     | Clickjacking          |
| `X-XSS-Protection`        | `1; mode=block`                            | XSS (legacy browsers) |
| `Referrer-Policy`         | `strict-origin-when-cross-origin`          | Vazamento de dados    |
| `Permissions-Policy`      | `camera=(), microphone=(), geolocation=()` | Acesso a recursos     |

### Content-Security-Policy (CSP) Detalhado

```
default-src 'self';
script-src 'self' 'wasm-unsafe-eval';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com data:;
img-src 'self' data: blob: https:;
connect-src 'self' https://automacao-cad-backend.vercel.app wss://automacao-cad-backend.vercel.app https://api.openai.com https://api.anthropic.com;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

| Diretiva                               | Significado                                         |
| -------------------------------------- | --------------------------------------------------- |
| `default-src 'self'`                   | Por padrão, só carrega recursos do próprio domínio  |
| `script-src 'self' 'wasm-unsafe-eval'` | Scripts apenas do domínio, permite WebAssembly      |
| `style-src 'self' 'unsafe-inline'`     | Estilos do domínio + inline (necessário para React) |
| `connect-src`                          | APIs permitidas para fetch/WebSocket                |
| `frame-ancestors 'none'`               | Não permite ser embutido em iframes                 |

### Backend (automacao-cad-backend.vercel.app)

| Header                   | Valor                                 | Proteção                 |
| ------------------------ | ------------------------------------- | ------------------------ |
| `X-Content-Type-Options` | `nosniff`                             | MIME-type sniffing       |
| `X-Frame-Options`        | `DENY`                                | Clickjacking             |
| `Cache-Control`          | `no-store, no-cache, must-revalidate` | Cache de dados sensíveis |

---

## Autenticação

### JWT (JSON Web Tokens)

- **Algoritmo**: HS256 (HMAC-SHA256)
- **Expiração**: 24 horas (access token)
- **Refresh**: 7 dias (refresh token)
- **Secret**: Variável de ambiente `JWT_SECRET` (mínimo 32 caracteres)

### Proteções Implementadas

| Proteção      | Status | Descrição                  |
| ------------- | ------ | -------------------------- |
| Rate Limiting | ✅     | 100 req/min por IP         |
| Brute Force   | ✅     | Bloqueio após 5 tentativas |
| CORS          | ✅     | Apenas origens permitidas  |
| HTTPS         | ✅     | Forçado via Vercel         |

---

## Senhas

### Política de Senhas

- **Mínimo**: 8 caracteres
- **Hashing**: bcrypt com salt (cost factor 12)
- **Validação**: zxcvbn para força da senha

### Armazenamento

```python
# Nunca armazenamos senhas em texto plano
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
```

---

## Banco de Dados

### PostgreSQL (Produção)

- **SSL**: Obrigatório (`sslmode=require`)
- **Conexões**: Pool limitado (max 20)
- **Credenciais**: Variáveis de ambiente, nunca no código

### SQLite (Desenvolvimento)

- **Localização**: `/data/engcad.db` ou `/tmp/engcad.db` (Vercel)
- **Permissões**: Arquivo local, não exposto publicamente

---

## Validação de Entrada

### Sanitização

```python
# Todas as entradas são sanitizadas
from markupsafe import escape

user_input = escape(request.form.get("name"))
```

### Validação de Tipos

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
```

---

## Proteção contra Ataques

### SQL Injection

```python
# ❌ NUNCA fazer isso
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# ✅ Sempre usar parâmetros
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

### XSS (Cross-Site Scripting)

- CSP bloqueia scripts inline
- React escapa automaticamente valores em JSX
- Headers `X-XSS-Protection` como fallback

### CSRF (Cross-Site Request Forgery)

- Tokens CSRF em formulários
- SameSite cookies (`Strict`)
- Verificação de Origin/Referer

---

## Logs e Auditoria

### O que é logado

| Evento             | Campos                                | Retenção |
| ------------------ | ------------------------------------- | -------- |
| Login              | user_id, ip, timestamp, success       | 90 dias  |
| Alteração de dados | user_id, entity, old_value, new_value | 1 ano    |
| Erros de segurança | ip, path, error_type                  | 30 dias  |

### O que NÃO é logado

- Senhas (nem hash)
- Tokens de acesso completos
- Dados de cartão de crédito

---

## Variáveis de Ambiente Sensíveis

| Variável            | Descrição               | Onde Definir    |
| ------------------- | ----------------------- | --------------- |
| `JWT_SECRET`        | Chave de assinatura JWT | Vercel Env Vars |
| `DATABASE_URL`      | Conexão PostgreSQL      | Vercel Env Vars |
| `OPENAI_API_KEY`    | API da OpenAI           | Vercel Env Vars |
| `ANTHROPIC_API_KEY` | API da Anthropic        | Vercel Env Vars |
| `STRIPE_SECRET_KEY` | Chave do Stripe         | Vercel Env Vars |

### Rotação de Secrets

Recomendado a cada 90 dias:

1. Gerar novo secret
2. Atualizar no Vercel
3. Fazer redeploy
4. Invalidar tokens antigos (forçar re-login)

---

## Checklist de Segurança

### Deploy

- [ ] Todas as variáveis de ambiente configuradas
- [ ] HTTPS forçado
- [ ] Headers de segurança ativos
- [ ] Logs de acesso habilitados

### Código

- [ ] Sem secrets hardcoded
- [ ] Inputs validados e sanitizados
- [ ] Queries parametrizadas
- [ ] Dependências atualizadas

### Monitoramento

- [ ] Alertas de erro configurados
- [ ] Rate limiting ativo
- [ ] Logs de auditoria funcionando

---

## Relatório de Vulnerabilidades

Se você encontrar uma vulnerabilidade de segurança, por favor:

1. **NÃO** divulgue publicamente
2. Envie email para: security@engenharia-cad.com.br
3. Inclua:
   - Descrição da vulnerabilidade
   - Passos para reproduzir
   - Impacto potencial

Responderemos em até 48 horas úteis.

---

_Documento atualizado: Abril 2026_
