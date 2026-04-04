# 🗄️ Configuração de Banco de Dados - Produção

## ⚠️ IMPORTANTE: SQLite vs PostgreSQL

**Em ambiente Vercel, SQLite é EFÊMERO!**

- Dados são armazenados em `/tmp/engcad.db`
- O diretório `/tmp` é limpo entre deploys e cold starts
- **NÃO USE SQLite em produção no Vercel**

---

## 🐘 Configurando PostgreSQL para Produção

### Opção 1: Vercel Postgres (Recomendado)

1. **Na Dashboard do Vercel:**
   - Vá em Storage → Create Database → Postgres
   - Selecione a região mais próxima
   - A variável `POSTGRES_URL` será configurada automaticamente

2. **Renomear variável:**

   ```bash
   # No painel de variáveis do projeto Vercel, adicione:
   DATABASE_URL = $POSTGRES_URL
   ```

3. **Executar migrations:**
   ```bash
   # Localmente com a URL de produção
   export DATABASE_URL="postgres://..."
   alembic upgrade head
   ```

### Opção 2: Supabase (Gratuito até 500MB)

1. **Criar projeto em:** https://supabase.com

2. **Copiar Connection String:**
   - Settings → Database → Connection String → URI

3. **Configurar no Vercel:**
   ```
   DATABASE_URL=postgres://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   ```

### Opção 3: Neon (Serverless Postgres)

1. **Criar conta em:** https://neon.tech

2. **Criar projeto e copiar connection string**

3. **Configurar no Vercel:**
   ```
   DATABASE_URL=postgres://[USER]:[PASSWORD]@[HOST]/[DATABASE]?sslmode=require
   ```

### Opção 4: Railway

1. **Criar projeto em:** https://railway.app

2. **Adicionar PostgreSQL plugin**

3. **Copiar `DATABASE_URL` para o Vercel**

---

## 🔧 Executando Migrations

### Desenvolvimento (SQLite)

```bash
cd "Automação CAD"
alembic upgrade head
```

### Produção (PostgreSQL)

```bash
# Defina a URL de produção
export DATABASE_URL="postgres://user:password@host:5432/database"

# Execute as migrations
alembic upgrade head

# Verificar status
alembic current
```

---

## 📋 Variáveis de Ambiente

| Variável         | Descrição                 | Exemplo                             |
| ---------------- | ------------------------- | ----------------------------------- |
| `DATABASE_URL`   | URL de conexão PostgreSQL | `postgres://user:pass@host:5432/db` |
| `ENGCAD_DB_PATH` | Caminho SQLite (dev)      | `./data/engcad.db`                  |

---

## 🧪 Testando Conexão

```python
# No Python
from backend.database.config import check_database_health

result = check_database_health()
print(result)
# {'engine': 'postgresql', 'is_ephemeral': False, 'connected': True, ...}
```

```bash
# Via API
curl https://your-app.vercel.app/health
```

---

## 📊 Schema do Banco

O schema completo está em:

- `alembic/versions/001_initial_schema.py`

### Tabelas Principais

| Tabela           | Descrição                 |
| ---------------- | ------------------------- |
| `users`          | Usuários e autenticação   |
| `projects`       | Projetos de engenharia    |
| `quality_checks` | Verificações de qualidade |
| `uploads`        | Arquivos enviados         |
| `licenses`       | Licenças de software      |
| `audit_logs`     | Trilha de auditoria       |
| `notifications`  | Sistema de notificações   |
| `cam_jobs`       | Trabalhos de corte CNC    |
| `cam_pieces`     | Biblioteca de peças       |

---

## 🚀 Checklist de Deploy

- [ ] Criar banco PostgreSQL (Vercel, Supabase, Neon, etc.)
- [ ] Configurar `DATABASE_URL` no Vercel
- [ ] Executar `alembic upgrade head` com URL de produção
- [ ] Verificar conexão via `/health`
- [ ] Testar autenticação
- [ ] Verificar logs de erro

---

## 🔒 Segurança

1. **Nunca commite DATABASE_URL no código**
2. **Use SSL em produção:** `?sslmode=require`
3. **Rotacione senhas periodicamente**
4. **Configure backups automáticos**
5. **Monitore com alertas de conexão**
