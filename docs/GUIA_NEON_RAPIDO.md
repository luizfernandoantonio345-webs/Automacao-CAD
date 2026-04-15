# 🚀 Guia Rápido: Configurar PostgreSQL Neon

## Passo 1: Obter Connection String do Neon

### Se você JÁ TEM conta no Neon:
1. Acesse: https://console.neon.tech
2. Clique no seu projeto
3. Em **Connection Details**, copie a string completa

### Se você NÃO TEM conta:
1. Acesse: https://neon.tech
2. Clique **Sign Up** (use GitHub para login rápido)
3. Clique **Create Project**
   - Name: `engcad-prod`
   - Region: `South America (São Paulo)` ou mais próximo
4. Após criar, copie a **Connection String** que aparece

---

## Passo 2: Executar o Setup (escolha UMA opção)

### Opção A: Script Python (recomendado)
```powershell
cd "C:\Users\Sueli\Desktop\Automação CAD"
python scripts/complete_neon_setup.py "SUA_CONNECTION_STRING_AQUI"
```

### Opção B: Script PowerShell
```powershell
cd "C:\Users\Sueli\Desktop\Automação CAD"
.\scripts\setup_neon.ps1
# Cole a Connection String quando solicitado
```

### Opção C: Manual
```powershell
cd "C:\Users\Sueli\Desktop\Automação CAD"

# Definir variável de ambiente
$env:DATABASE_URL = "SUA_CONNECTION_STRING_AQUI"

# Testar conexão
python -c "import psycopg2; psycopg2.connect('$env:DATABASE_URL').close(); print('OK!')"

# Executar migrations
alembic upgrade head
```

---

## Passo 3: Configurar no Vercel

1. Acesse: https://vercel.com/dashboard
2. Selecione: **automacao-cad-backend**
3. Vá para: **Settings** → **Environment Variables**
4. Adicione:
   - **Key**: `DATABASE_URL`
   - **Value**: (sua connection string)
5. Marque: **Production** e **Preview**
6. Clique: **Save**
7. Vá para **Deployments** → clique no último → **Redeploy**

---

## Passo 4: Verificar

Acesse: https://automacao-cad-backend.vercel.app/health

Você deve ver:
```json
{
  "database": {
    "type": "postgresql",
    "healthy": true
  }
}
```

---

## 🎉 Pronto!

Seu banco de dados PostgreSQL está configurado. Os dados agora persistem mesmo após redeploys do Vercel!

---

## Problemas Comuns

### "psycopg2 not found"
```powershell
pip install psycopg2-binary
```

### "Connection refused"
- Verifique se a Connection String está correta
- Verifique se `?sslmode=require` está no final da URL

### "Permission denied"
- Verifique se o usuário da URL tem permissões no banco
