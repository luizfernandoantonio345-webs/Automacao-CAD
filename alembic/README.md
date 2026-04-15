# Alembic Migrations — Engenharia CAD

Este diretório contém as migrations de banco de dados do projeto.

## Uso Básico

```bash
# Verificar status atual
alembic current

# Aplicar todas as migrations pendentes
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Criar nova migration
alembic revision -m "descrição da mudança"

# Ver histórico de migrations
alembic history
```

## Com PostgreSQL de Produção

```powershell
# Definir DATABASE_URL
$env:DATABASE_URL = "postgresql://user:pass@host/db?sslmode=require"

# Aplicar migrations
alembic upgrade head
```

## Migrations Existentes

| Versão | Descrição |
|--------|-----------|
| 001 | Schema inicial (users, projects, licenses, etc.) |
| 002 | Campos de IA (ai_fields) |

## Estrutura das Tabelas

- **users** — Usuários do sistema
- **projects** — Projetos CAD
- **quality_checks** — Verificações de qualidade
- **uploads** — Uploads de arquivos
- **licenses** — Licenças de software
- **audit_logs** — Logs de auditoria
- **notifications** — Notificações
- **user_sessions** — Sessões ativas
- **user_devices** — Dispositivos autorizados
