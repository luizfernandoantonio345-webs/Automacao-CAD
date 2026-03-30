# Deploy de Teste na Vercel

Este projeto deve ser testado na Vercel em dois apps separados:

1. Backend FastAPI
2. Frontend React

## 1. Backend

- Criar um projeto novo na Vercel apontando para a raiz do repositório
- Framework preset: `Other`
- Build Command: vazio
- Output Directory: vazio

Arquivos usados:

- `api/index.py`
- `vercel.json`

Variáveis de ambiente mínimas:

- `JARVIS_SECRET`
- `ENG_AUTH_SECRET`
- `LICENSE_SECRET`
- `APP_ENV=production`
- `ALLOW_DEMO_LOGIN=true`
- `SIMULATION_MODE=true`
- `LICENSE_FALLBACK_ENABLED=true`

Observações:

- O backend sobe em modo de teste sem COM local no Linux
- A parte AutoCAD real continua no computador do cliente via agente local

## 2. Frontend

- Criar outro projeto na Vercel
- Definir `frontend` como Root Directory
- Framework preset: `Create React App`

Variáveis de ambiente recomendadas:

- `REACT_APP_API_URL=https://SEU-BACKEND.vercel.app`
- `REACT_APP_SSE_URL=https://SEU-BACKEND.vercel.app`
- `REACT_APP_LICENSING_URL=https://SEU-BACKEND.vercel.app`

## 3. O que validar no teste

- Abrir frontend publicado
- Fazer login demo
- Navegar entre as telas principais
- Confirmar resposta de `/health`
- Confirmar resposta de `/docs`
- Validar chamadas de `/api/autocad/*` em modo simulação

## 4. Limitação importante

Na Vercel, este teste serve para validar fluxo do produto e UX.
O serviço final de produção deve migrar para VPS.
