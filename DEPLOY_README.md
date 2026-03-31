# Engenharia CAD v1.0 Gold — Guia de Deploy e Startup

## Estrutura do Projeto (Árvore Final)

```
Engenharia CAD/
├── server.py                          # FastAPI principal (porta 8000)
├── main.py                            # Entry-point alternativo
├── ai_watchdog.py                     # IA de Baixo Nível (middleware invisível)
├── circuit_breaker.py                 # Circuit Breaker (Redis-backed, 3 estados)
├── dead_letter_queue.py               # Fila de mensagens mortas
├── celery_app.py                      # Instância Celery
├── celery_config.py                   # Configuração broker/backend
├── celery_tasks.py                    # Tasks assíncronas
├── gpu_support.py                     # Suporte GPU (detecção CUDA)
├── build_agente.py                    # Builder do agente local
├── forge_link_agent.py                # Agente Local (PC remoto)
├── docker-compose.yml                 # Stack: Redis + RabbitMQ + Workers
├── Dockerfile                         # Container principal
├── requirements.txt                   # Dependências Python
├── requirements-celery.txt            # Dependências Celery workers
├── start_Engenharia CAD.bat                 # Starter Windows (bat)
├── start_Engenharia CAD.ps1                 # Starter Windows (PowerShell)
├── final_check.py                     # ★ Script de verificação pré-demo
├── DEPLOY_README.md                   # ★ Este arquivo
│
├── backend/                           # ── BACKEND CORE ──
│   ├── __init__.py
│   ├── autocad_driver.py              # Driver Híbrido (COM + Ponte de Rede)
│   ├── routes_autocad.py              # 15+ endpoints REST /api/autocad/*
│   ├── routes_license.py              # Licenciamento + HWID
│   ├── hwid.py                        # Hardware ID fingerprinting
│   ├── forge_vigilante.lsp            # ★ Vigilante AutoLISP v2.0 (PC Cliente)
│   └── database/                      # SQLAlchemy + dados de licença
│
├── engenharia_automacao/              # ── MOTOR DE ENGENHARIA CAD ──
│   ├── __init__.py
│   ├── config.py                      # Configurações do motor
│   ├── main.py                        # Entry-point engenharia
│   ├── app/
│   │   ├── app.py                     # App engine
│   │   ├── auth.py                    # Autenticação
│   │   ├── routes_cad.py              # Rotas CAD (refinarias, normas, materiais)
│   │   ├── controllers/               # Controladores de domínio
│   │   └── ui/                        # Interface web do motor
│   ├── cad/                           # Lógica CAD específica
│   ├── core/                          # Core do motor
│   ├── services/                      # Serviços de negócio
│   └── data/                          # Dados do motor
│
├── frontend/                          # ── FRONTEND REACT ──
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── public/                        # Assets estáticos
│   ├── build/                         # Build de produção
│   └── src/
│       ├── App.tsx                    # Router principal + providers
│       ├── index.tsx                  # Entry-point React
│       ├── index.css
│       ├── pages/
│       │   ├── AutoCADControl.tsx     # ★ Controle AutoCAD (7 painéis, 15 endpoints)
│       │   ├── Dashboard.tsx          # Dashboard principal
│       │   ├── DataIngestion.tsx      # Ingestão de dados
│       │   ├── CadDashboard.tsx       # Dashboard CAD
│       │   ├── CadConsole.tsx         # Console CAD
│       │   ├── QualityGate.tsx        # Quality Gate
│       │   ├── FinalReport.tsx        # Relatório final
│       │   ├── GlobalSetup.tsx        # Setup global
│       │   └── Login.tsx              # Tela de login
│       ├── components/
│       │   ├── SidebarLayout.tsx      # Layout com sidebar
│       │   ├── Dashboard.tsx          # Componente dashboard
│       │   ├── License.tsx            # Componente licença
│       │   ├── Loader.tsx             # Spinner/loader
│       │   ├── Login.tsx              # Componente login
│       │   ├── Sidebar.tsx            # Sidebar standalone
│       │   └── ThemeToggle.tsx        # Alternador de tema
│       ├── context/
│       │   ├── GlobalContext.tsx       # Estado global
│       │   ├── ThemeContext.tsx        # Tema (dark/light)
│       │   └── ToastContext.tsx        # ★ Toast Notifications (circuit breaker)
│       ├── middleware/
│       │   ├── AIOrchestrator.ts      # Orquestrador IA (cache, anticipator)
│       │   ├── UIGuard.tsx            # Guard de UI
│       │   ├── useAIStatus.ts         # Hook de status IA
│       │   └── index.ts
│       ├── services/
│       │   └── api.ts                 # Axios + API_BASE_URL
│       ├── engine/                    # Motor de rendering
│       ├── renderer/                  # Renderer
│       └── styles/                    # Estilos
│
├── infrastructure/                    # ── INFRA / DEVOPS ──
│   ├── docker-compose-fase2.yml       # Stack fase 2
│   ├── docker-compose-fase3.yml       # Stack fase 3 (Loki + Promtail)
│   ├── docker-compose-fase4.yml       # Stack fase 4 (GPU)
│   ├── docker-compose-k8s.yml         # Stack Kubernetes
│   ├── Dockerfile.api                 # Container API
│   ├── Dockerfile.celery              # Container Worker
│   ├── Dockerfile.celery.gpu          # Container Worker GPU
│   ├── k8s-deployment.yml             # Deployment K8s
│   ├── prometheus.yml                 # Config Prometheus
│   ├── grafana_datasources.yml        # Datasources Grafana
│   ├── grafana_dashboards/            # Dashboards JSON
│   ├── loki-config.yml                # Config Loki
│   ├── promtail-config.yml            # Config Promtail
│   └── *.ps1 / *.sh                  # Scripts de setup
│
├── licensing_server/                  # ── SERVIDOR DE LICENÇAS ──
│   ├── app.py                         # Flask app (porta 5200)
│   └── data/                          # Dados de licenças
│
├── scripts/                           # ── SCRIPTS UTILITÁRIOS ──
│   ├── health_check.py                # Health check básico
│   ├── health_check_complete.py       # Health check completo
│   ├── generate_secrets.py            # Gerador de secrets
│   ├── kill_ports.py                  # Liberador de portas
│   ├── migrate_licenses.py            # Migração de licenças
│   ├── pid_mto_generator.py           # Gerador PID/MTO
│   ├── seed_project_corpus.py         # Seed de projetos
│   └── start_job_workers.py           # Starter de workers
│
├── data/                              # ── DADOS RUNTIME ──
│   ├── bootstrap_projects/            # Projetos base
│   ├── output/                        # Saída de processamento
│   └── telemetry/                     # Dados de telemetria
│
├── docs/                              # ── DOCUMENTAÇÃO ──
│   ├── AI_CAD_README.md
│   ├── QUICK_START.md
│   ├── SECURITY.md
│   ├── dashboard.html
│   └── ...                            # 20+ docs técnicos
│
├── alembic/                           # Migrações de banco
│   └── versions/
│
├── integration/                       # Testes de integração
│   └── python_api/
│
└── Z:/AutoCAD_Drop/                   # ── PASTA BRIDGE (rede) ──
    ├── job_*.lsp                      # Jobs gerados pelo servidor
    ├── job_*.done                     # Jobs processados
    └── forge_vigilante_update.lsp     # Atualização auto-update (se houver)
```

---

## Guia de Startup — Passo a Passo

### Pré-requisitos

| Componente       | Versão | Verificação                    |
| ---------------- | ------ | ------------------------------ |
| Python           | 3.10+  | `python --version`             |
| Node.js          | 18+    | `node --version`               |
| Docker Desktop   | 4.x+   | `docker --version`             |
| AutoCAD/GstarCAD | 2020+  | Instalado no PC Cliente (PC B) |

### PASSO 1 — Subir Infraestrutura (Redis + RabbitMQ)

```powershell
# Na raiz do projeto
cd "C:\Users\Sueli\Desktop\Automação CAD"

# Criar arquivo .env com secrets (OBRIGATÓRIO)
# Se ainda não existir:
python scripts/generate_secrets.py

# Subir containers Docker
docker-compose up -d redis rabbitmq

# Verificar que estão saudáveis
docker-compose ps
# Deve mostrar: cad-redis (healthy), cad-rabbitmq (healthy)
```

> **Sem Docker?** Redis e RabbitMQ podem rodar nativos no Windows.
> Redis: https://github.com/tporadowski/redis/releases
> RabbitMQ: https://www.rabbitmq.com/install-windows.html

### PASSO 2 — Subir o Backend (FastAPI)

```powershell
# Instalar dependências Python (primeira vez)
pip install -r requirements.txt

# Definir variáveis de ambiente
$env:JARVIS_SECRET = "<GERE_COM: python scripts/generate_secrets.py>"
$env:AUTOCAD_BRIDGE_PATH = "Z:\AutoCAD_Drop"   # ou caminho local
$env:REDIS_URL = "redis://:<SUA_SENHA_REDIS>@localhost:6379/1"

# Iniciar o servidor FastAPI (porta 8000)
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# ✓ Deve mostrar: Uvicorn running on http://0.0.0.0:8000
```

### PASSO 3 — Subir Workers Celery (Opcional — para jobs assíncronos)

```powershell
# Em outro terminal:
$env:CELERY_BROKER_URL = "amqp://cad_user:<SUA_SENHA_RABBITMQ>@localhost:5672/cad_vhost"
$env:CELERY_RESULT_BACKEND = "redis://:<SUA_SENHA_REDIS>@localhost:6379/0"

celery -A celery_app worker --loglevel=info --concurrency=4 -n worker1@%h
```

### PASSO 4 — Subir o Frontend (React)

```powershell
# Em outro terminal:
cd frontend

# Instalar dependências (primeira vez)
npm install

# Iniciar em modo desenvolvimento (porta 3000)
npm start

# ✓ Abre automaticamente: http://localhost:3000
# Login: tony / 123
```

### PASSO 5 — Configurar o PC Cliente (PC B — REGAP)

Este é o computador que tem o AutoCAD instalado e recebe os comandos via pasta de rede.

#### 5a. Criar a pasta Bridge compartilhada

```
No PC B (ou servidor de arquivos):
1. Criar pasta:  Z:\AutoCAD_Drop\
2. Compartilhar com permissão de leitura/escrita para o servidor (PC A)
3. No PC A, mapear como unidade Z: (ou usar caminho UNC: \\SERVIDOR\AutoCAD_Drop)
```

#### 5b. Carregar o forge_vigilante.lsp v2.0 no AutoCAD

```
1. Copiar o arquivo:
   backend/forge_vigilante.lsp  →  C:\Engenharia CAD\forge_vigilante.lsp (no PC B)

2. Abrir o AutoCAD no PC B

3. Digitar na linha de comando:  APPLOAD  (Enter)

4. Navegar até C:\Engenharia CAD\forge_vigilante.lsp → clicar "Carregar"

5. Para carga AUTOMÁTICA em toda sessão:
   - No diálogo APPLOAD, clicar "Conteúdo de Inicialização" (canto inferior)
   - Adicionar forge_vigilante.lsp à lista

6. Na linha de comando do AutoCAD, digitar:
   FORGE_PATH   (Enter)
   → Digitar: Z:/AutoCAD_Drop/   (Enter)

   FORGE_START  (Enter)
   → Deve exibir: "[FORGE] Monitoramento ATIVO"

7. Verificar status:
   FORGE_STATUS (Enter)
   → Deve mostrar: Running = T, Jobs = 0 processados
```

> **Auto-Update v2.0:** O vigilante agora verifica automaticamente se existe
> `forge_vigilante_update.lsp` na pasta bridge. Se a versão for superior,
> ele se auto-atualiza sem intervenção manual.

### PASSO 6 — Executar Verificação Pré-Demo

```powershell
cd "C:\Users\Sueli\Desktop\Automação CAD"
python final_check.py
```

Deve mostrar todos os checks em **PASS**. Se algum falhar, seguir instruções na saída.

---

## Teste de Fogo Rápido

Após todos os serviços estarem rodando:

1. Abrir `http://localhost:3000` → Login (tony / 123)
2. Ir em **AutoCAD Control** na sidebar
3. Clicar **Conectar** → status deve mudar para "BRIDGE"
4. Clicar **Traçar Tubo** com valores padrão → Console mostra "OK"
5. Clicar **Commit Buffer → .lsp** → Arquivo aparece em `Z:\AutoCAD_Drop\`
6. No PC B (AutoCAD), o vigilante detecta e executa → tubo desenhado

---

## Portas do Sistema

| Serviço               | Porta | Acesso                                |
| --------------------- | ----- | ------------------------------------- |
| FastAPI (Backend)     | 8000  | http://localhost:8000/docs            |
| React (Frontend)      | 3000  | http://localhost:3000                 |
| Licensing Server      | 5200  | http://localhost:5200                 |
| Redis                 | 6379  | Interno                               |
| RabbitMQ (AMQP)       | 5672  | Interno                               |
| RabbitMQ (Management) | 15672 | http://localhost:15672                |
| Prometheus            | 9090  | http://localhost:9090 (se habilitado) |
| Grafana               | 3001  | http://localhost:3001 (se habilitado) |

---

## Revisão N-58 Petrobras — Conformidade de Layers

O sistema implementa o padrão de layers conforme Norma N-58 Petrobras:

| Layer             | ACI Color | Cor Visual | Linetype   | Lineweight | Status      |
| ----------------- | --------- | ---------- | ---------- | ---------- | ----------- |
| `PIPE-PROCESS`    | **1**     | Vermelho   | Continuous | 0.50mm     | ✅ Conforme |
| `PIPE-UTILITY`    | **3**     | Verde      | Continuous | 0.35mm     | ✅ Conforme |
| `PIPE-INSTRUMENT` | **5**     | Azul       | DASHED     | 0.25mm     | ✅ Conforme |
| `EQUIP-VESSEL`    | **2**     | Amarelo    | Continuous | 0.70mm     | ✅ Conforme |
| `EQUIP-PUMP`      | **2**     | Amarelo    | Continuous | 0.50mm     | ✅ Conforme |
| `VALVE`           | **6**     | Magenta    | Continuous | 0.50mm     | ✅ Conforme |
| `FLANGE`          | **4**     | Cyan       | Continuous | 0.35mm     | ✅ Conforme |
| `SUPPORT`         | **8**     | Cinza      | CENTER     | 0.25mm     | ✅ Conforme |
| `ANNOTATION`      | **7**     | Branco     | Continuous | 0.18mm     | ✅ Conforme |
| `DIMENSION`       | **7**     | Branco     | Continuous | 0.18mm     | ✅ Conforme |
| `ISOMETRIC`       | **150**   | Azul claro | Continuous | 0.25mm     | ✅ Conforme |

**Referência de cores ACI (AutoCAD Color Index):**

- 1 = Vermelho (Tubulação de Processo — maior destaque visual)
- 2 = Amarelo (Equipamentos — vasos e bombas)
- 3 = Verde (Utilidades — vapor, ar, água)
- 4 = Cyan (Flanges — conexões)
- 5 = Azul (Instrumentação — linhas tracejadas)
- 6 = Magenta (Válvulas — controle de fluxo)
- 7 = Branco (Anotações e cotas)
- 8 = Cinza (Suportes — elementos estruturais)
- 150 = Azul claro (Isométricos — vista auxiliar)

Todos os 11 layers são criados automaticamente no primeiro `connect()` de cada sessão
(Task 3 implementada em `autocad_driver.py`).

---

**Engenharia CAD v1.0 Gold — Pronto para Deploy**
