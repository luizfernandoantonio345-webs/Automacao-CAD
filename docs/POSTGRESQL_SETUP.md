# 🗄️ Configuração de PostgreSQL para Produção

Este guia explica como migrar de SQLite para PostgreSQL no Engenharia CAD.

## Por que PostgreSQL?

| Característica | SQLite | PostgreSQL |
|----------------|--------|------------|
| Escalabilidade | 1 usuário | Milhares |
| Persistência em Vercel | ❌ Efêmero | ✅ Permanente |
| Conexões simultâneas | Limitado | Ilimitado |
| Backups automáticos | ❌ Manual | ✅ Automático |
| Replicação | ❌ Não | ✅ Sim |

## Opções de Provedores PostgreSQL

### 1. Neon (RECOMENDADO)
- **Tier Grátis**: 512MB, 3GB transfer, auto-scaling
- **Prós**: Serverless, branching, cold-start rápido
- **Site**: https://neon.tech

### 2. Supabase
- **Tier Grátis**: 500MB, 2GB transfer
- **Prós**: Dashboard completo, auth integrado
- **Site**: https://supabase.com

### 3. Railway
- **Tier Grátis**: $5/mês de crédito
- **Prós**: Deploy fácil, integração GitHub
- **Site**: https://railway.app

### 4. ElephantSQL
- **Tier Grátis**: 20MB (muito limitado)
- **Prós**: Simples
- **Site**: https://elephantsql.com

---

## Configuração Passo a Passo

### 1. Criar Banco no Neon

1. Acesse https://neon.tech
2. Crie uma conta (pode usar GitHub)
3. Crie um novo projeto "engenharia-cad"
4. Copie a Connection String:
   ```
   postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```

### 2. Configurar Variáveis de Ambiente no Vercel

1. Acesse https://vercel.com
2. Vá para seu projeto `automacao-cad-backend`
3. Settings → Environment Variables
4. Adicione:

| Name | Value | Environment |
|------|-------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@host/db?sslmode=require` | Production, Preview |
| `ALLOW_EPHEMERAL_DB` | `false` | Production |

### 3. Executar Migrations

```bash
# Localmente com a DATABASE_URL de produção
export DATABASE_URL="postgresql://..."

# Executar Alembic
cd /path/to/Automacao-CAD
.venv/Scripts/activate  # Windows
alembic upgrade head
```

Ou via script Python:
```python
import os
os.environ["DATABASE_URL"] = "postgresql://..."

from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

### 4. Verificar Conexão

```bash
# Testar conexão
curl https://automacao-cad-backend.vercel.app/health

# Deve retornar:
{
  "status": "healthy",
  "database": "postgresql",
  "ephemeral": false
}
```

---

## Configuração do alembic.ini

Atualize `alembic.ini` para usar DATABASE_URL:

```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .

# Usar variável de ambiente
sqlalchemy.url = env:DATABASE_URL
```

---

## Script de Migração Automática

Execute este script para migrar dados do SQLite para PostgreSQL:

```powershell
# migrate_to_postgres.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$PostgresUrl
)

$env:DATABASE_URL = $PostgresUrl

# Verificar conexão
Write-Host "Verificando conexão com PostgreSQL..."
python -c "
import os
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Conexão OK!')
conn.close()
"

# Executar migrations
Write-Host "Executando migrations..."
alembic upgrade head

Write-Host "Migração concluída!"
```

---

## Backup e Restauração

### Backup via pg_dump
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Restauração
```bash
psql $DATABASE_URL < backup_20260415.sql
```

### Backup Automático no Neon
O Neon faz backups automáticos a cada hora. Para restaurar:
1. Vá para o dashboard Neon
2. Selecione o projeto
3. Clique em "Branches"
4. Use "Restore" para voltar a um ponto anterior

---

## Troubleshooting

### Erro: "relation does not exist"
```bash
# Recriar tabelas
alembic downgrade base
alembic upgrade head
```

### Erro: "connection refused"
- Verifique se o IP está na whitelist do banco
- Verifique se `?sslmode=require` está na URL

### Erro: "too many connections"
- O Neon free tier tem limite de 100 conexões
- Use connection pooling (já implementado)

---

## Checklist de Migração

- [ ] Criar conta no Neon/Supabase
- [ ] Criar projeto de banco de dados
- [ ] Copiar connection string
- [ ] Adicionar DATABASE_URL no Vercel
- [ ] Remover ALLOW_EPHEMERAL_DB do Vercel
- [ ] Fazer redeploy do backend
- [ ] Executar migrations (alembic upgrade head)
- [ ] Criar usuário admin/teste
- [ ] Verificar endpoints funcionando
- [ ] Configurar backup automático

---

*Documento atualizado: Abril 2026*
