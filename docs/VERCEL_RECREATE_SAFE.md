# Recriar projeto na Vercel sem mexer no sistema atual

Este procedimento cria um projeto novo na Vercel em paralelo.
Nao apaga o projeto antigo, nao troca dominio e nao desfaz o sistema local.

## O que foi preparado no repositorio

- `api/index.py`: entrypoint da Vercel que reaproveita o `server.py` atual
- `vercel.json`: roteia todas as requisicoes para o backend FastAPI
- `requirements.txt`: dependencias minimas para o backend subir na Vercel

Esses arquivos sao aditivos. O backend local continua usando `server.py` como antes.

## Estrategia segura

1. Criar um projeto novo para o backend
2. Validar `/health` e `/docs`
3. So depois ajustar o frontend para apontar para o backend novo
4. So depois, se quiser, trocar dominio customizado

## Backend na Vercel

### Pelo painel

1. Criar um novo projeto na Vercel
2. Importar este repositorio
3. Root Directory: raiz do repositorio
4. Framework Preset: `Other`
5. Build Command: vazio
6. Output Directory: vazio
7. Deploy

### Variaveis minimas

- `JARVIS_SECRET`
- `APP_ENV=production`
- `ALLOW_DEMO_LOGIN=true`
- `SIMULATION_MODE=true`
- `LICENSE_FALLBACK_ENABLED=true`

Se usar licenciamento completo no deploy, incluir tambem:

- `ENG_AUTH_SECRET`
- `LICENSE_SECRET`

Se usar banco externo:

- `DATABASE_URL`

## Frontend na Vercel

Crie outro projeto separado:

1. Novo projeto na Vercel
2. Mesmo repositorio
3. Root Directory: `frontend`
4. Framework Preset: `Create React App`

Variaveis recomendadas:

- `REACT_APP_API_URL=https://SEU-BACKEND.vercel.app`
- `REACT_APP_SSE_URL=https://SEU-BACKEND.vercel.app`
- `REACT_APP_LICENSING_URL=https://SEU-BACKEND.vercel.app`

## Via CLI

Exemplo de fluxo seguro:

```powershell
vercel project add
vercel link --yes --project NOME_DO_BACKEND
vercel deploy
vercel deploy --prod
```

Depois repetir para o frontend dentro de `frontend/`.

## Automacao pronta (recomendado)

Para reduzir erro manual ao criar projetos novos, use o script:

```powershell
.\scripts\vercel_setup_and_deploy.ps1
```

Ele faz automaticamente:

1. Link do projeto backend na raiz do repositorio
2. Deploy backend (preview por padrao)
3. Captura da URL gerada do backend
4. Link do projeto frontend em `frontend/`
5. Atualizacao de `REACT_APP_API_URL`, `REACT_APP_SSE_URL`, `REACT_APP_LICENSING_URL`
6. Deploy frontend

Para deploy de producao:

```powershell
.\scripts\vercel_setup_and_deploy.ps1 -Prod
```

Para ja configurar as variaveis criticas do backend no mesmo comando:

```powershell
.\scripts\vercel_setup_and_deploy.ps1 -Prod `
	-JarvisSecret "SEU_SECRET_FORTE_32B+" `
	-EngAuthSecret "SEU_ENG_AUTH_SECRET" `
	-LicenseSecret "SEU_LICENSE_SECRET" `
	-DatabaseUrl "postgresql://user:pass@host:5432/db"
```

Se nao passar `-JarvisSecret`, o script nao sobrescreve esse valor e mantem o que ja estiver salvo no projeto da Vercel.

Opcional (quando usa time na Vercel):

```powershell
.\scripts\vercel_setup_and_deploy.ps1 -Scope "SEU_TIME"
```

## Checklist de validacao

- `GET /health`
- `GET /docs`
- login demo
- telas principais do frontend
- endpoints `/api/autocad/*` em modo simulacao

## Limite importante

Na Vercel, o backend serve bem para validar fluxo e UX.
O AutoCAD real nao roda dentro da Vercel; ele continua no computador do cliente,
via COM local ou via ponte com `forge_vigilante.lsp`.
