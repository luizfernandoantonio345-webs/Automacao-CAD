# Engenharia CAD v5.0 🚀

Plataforma de automação CAD industrial com integração direta com AutoCAD/GstarCAD, utilizando Python, FastAPI e controle via AutoLISP.

## 🔥 Principais funcionalidades

- Automação de desenhos CAD
- Integração com AutoCAD/GstarCAD via COM
- Execução remota via ponte de rede (AutoLISP)
- Geração de projetos em lote com suporte a IA
- Dashboard web com monitoramento em tempo real

## 🛠 Tecnologias utilizadas

- Python (FastAPI)
- React / Electron
- Redis + RabbitMQ
- Celery (processamento assíncrono)
- AutoLISP (integração CAD)
- Docker

## 🌐 Demonstração

👉 https://automacao-cad-frontend.vercel.app/

## 🧠 Arquitetura

Sistema distribuído com:

- Frontend (React)
- Backend (FastAPI)
- Workers assíncronos (Celery)
- Integração CAD local/remota

---

## 📌 Sobre o projeto

Projeto desenvolvido com foco em automação industrial e integração de sistemas CAD, aplicando conceitos de backend, arquitetura distribuída e comunicação entre serviços.

---

## 📖 Documentação técnica completa

### Agente de Conexão AutoCAD

O sistema utiliza um agente local que roda na máquina do usuário para estabelecer comunicação bidirecional entre o frontend web e o AutoCAD/GstarCAD instalado.

#### Arquivos do Agente

| Arquivo                     | Localização                    | Função                           |
| --------------------------- | ------------------------------ | -------------------------------- |
| `install-agent.bat`         | GitHub → Download              | Instalador automatizado          |
| `SINCRONIZADOR.ps1`         | `%USERPROFILE%\EngCAD-Agente\` | Ponte de comunicação com backend |
| `DETECTAR_AUTOCAD.ps1`      | `%USERPROFILE%\EngCAD-Agente\` | Detecta CAD instalado            |
| `INICIAR_SINCRONIZADOR.bat` | `%USERPROFILE%\EngCAD-Agente\` | Atalho para iniciar agente       |

#### Fluxo de Instalação

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Usuário clica "Instalar Agente" no site                     │
│     ↓                                                           │
│  2. Navegador baixa install-agent-autocad.bat                   │
│     ↓                                                           │
│  3. Usuário executa o .bat (duplo clique)                       │
│     ↓                                                           │
│  4. Script cria pasta %USERPROFILE%\EngCAD-Agente               │
│     ↓                                                           │
│  5. Downloads: SINCRONIZADOR.ps1, DETECTAR_AUTOCAD.ps1          │
│     ↓                                                           │
│  6. Testa conexão com backend (health check)                    │
│     ↓                                                           │
│  7. Inicia SINCRONIZADOR.ps1 em loop permanente                 │
│     ↓                                                           │
│  8. Dashboard mostra status: 🟢 CONECTADO                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Tratamento de Erros

O instalador foi projetado para NUNCA fechar silenciosamente:

| Erro                            | Como é tratado                       |
| ------------------------------- | ------------------------------------ |
| PowerShell ausente              | Mensagem clara + aguarda 60s         |
| Download falhou                 | Try/catch com erro detalhado         |
| Backend offline                 | Modo local ativado, retry automático |
| CAD não detectado               | Continua monitorando                 |
| `C:\AutoCAD_Drop` sem permissão | Usa `%USERPROFILE%\AutoCAD_Drop`     |
| SmartScreen bloqueia            | Instruções no dialog do site         |

#### Pasta de Comandos (Drop Folder)

O agente monitora uma pasta onde arquivos `.lsp` são depositados para execução:

```
Primário:   C:\AutoCAD_Drop\
Fallback:   %USERPROFILE%\AutoCAD_Drop\
```

O AutoCAD (com `forge_vigilante.lsp` carregado) monitora esta pasta e executa automaticamente os comandos LISP enviados pelo backend.

#### Comunicação Backend ↔ Agente

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │ ──────▶ │   Backend    │ ──────▶ │   Agente     │
│   (React)    │         │   (FastAPI)  │         │   (PS1)      │
└──────────────┘         └──────────────┘         └──────────────┘
                              │                        │
                              │  POST /api/bridge/     │
                              │  connection            │
                              │◀─────────────────────▶│
                              │                        │
                              │  GET /api/bridge/      │
                              │  pending               │
                              │◀─────────────────────▶│
                              │                        │
                              │  POST /api/bridge/     │
                              │  ack/{id}              │
                              │◀─────────────────────▶│
```

#### Endpoints do Bridge

| Método | Endpoint                 | Descrição                |
| ------ | ------------------------ | ------------------------ |
| POST   | `/api/bridge/connection` | Heartbeat do agente      |
| GET    | `/api/bridge/pending`    | Busca comandos pendentes |
| POST   | `/api/bridge/ack/{id}`   | Confirma execução        |

#### Reiniciar o Agente

Para reiniciar manualmente:

```powershell
# Opção 1: Via atalho
%USERPROFILE%\EngCAD-Agente\INICIAR_SINCRONIZADOR.bat

# Opção 2: Direto no PowerShell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\EngCAD-Agente\SINCRONIZADOR.ps1"
```

#### Logs e Diagnóstico

O agente exibe um dashboard em tempo real no terminal:

```
┌─────────────────────────────────────────────────────────────────────┐
│ STATUS: 🟢 CONECTADO          Uptime: 00:15:32                      │
│ CAD: AutoCAD 2024             Comandos: 5                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### URLs de Produção

| Serviço      | URL                                             |
| ------------ | ----------------------------------------------- |
| Frontend     | https://automacao-cad-frontend.vercel.app       |
| Backend      | https://automacao-cad-backend.vercel.app        |
| Health Check | https://automacao-cad-backend.vercel.app/health |

---

### Estrutura do Projeto

```
Automacao-CAD/
├── AutoCAD_Cliente/          # Scripts do agente local
│   ├── install-agent.bat     # Instalador
│   ├── SINCRONIZADOR.ps1     # Ponte de comunicação
│   ├── DETECTAR_AUTOCAD.ps1  # Detector de CAD
│   └── INICIAR_SINCRONIZADOR.bat
├── backend/                  # Módulos Python do backend
├── frontend/                 # App React
├── api/                      # Serverless functions (Vercel)
├── server.py                 # Servidor FastAPI principal
└── requirements.txt          # Dependências Python
```

---

## 📜 Licença

Projeto proprietário — Engenharia CAD v5.0 Gold.
