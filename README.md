# Engenharia CAD v1.0 Gold — Guia de Startup & Operação

> Plataforma híbrida de automação CAD industrial com Norma Petrobras N-58,
> controle direto de AutoCAD/GstarCAD via COM e ponte de rede AutoLISP.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend React (3000)                                              │
│  Electron Dashboard — Sidebar, Telemetria, Controles CAD            │
└────────────────┬────────────────────────────────────────────────────┘
                 │ HTTP / SSE
┌────────────────▼────────────────────────────────────────────────────┐
│  Servidor Central — FastAPI (8000)                                  │
│  server.py → rotas autocad, license, cad, ai_watchdog               │
├─────────────────────────────────────────────────────────────────────┤
│  Celery Workers (RabbitMQ 5672 + Redis 6379)                        │
│  celery_tasks.py → geração de projetos, IA, batch Excel             │
└────────────────┬────────────────────────────────────────────────────┘
                 │ COM direto OU Ponte de Rede (.lsp)
┌────────────────▼────────────────────────────────────────────────────┐
│  AutoCAD / GstarCAD  (PC local ou PC remoto via Vigilante)          │
│  forge_vigilante.lsp v2.0 — monitora pasta de rede e executa jobs   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Pré-requisitos

| Componente        | Versão mínima | Porta  |
|-------------------|---------------|--------|
| Python            | 3.10+         | —      |
| Node.js           | 18+           | —      |
| Docker + Compose  | 24+           | —      |
| Redis             | 7+            | 6379   |
| RabbitMQ          | 3.12+         | 5672   |
| AutoCAD ou GstarCAD | 2021+      | —      |

---

## 2. Instalação

### 2.1 Clone e ambiente Python

```powershell
cd "C:\Users\Sueli\Desktop\Automação CAD"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 Variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```env
JARVIS_SECRET=troque_por_uma_chave_forte_de_64_chars
RABBITMQ_USER=cad_user
RABBITMQ_PASS=troque_senha_rabbitmq
REDIS_PASS=troque_senha_redis
AUTOCAD_BRIDGE_PATH=C:/AutoCAD_Drop/
```

### 2.3 Instalar dependências do Frontend

```powershell
cd frontend
npm install
cd ..
```

---

## 3. Iniciar os Serviços

### Ordem obrigatória: Infrastructure → Backend → Frontend

### 3.1 Infrastructure (Redis + RabbitMQ)

```powershell
docker-compose up -d rabbitmq redis
```

Aguarde os health checks ficarem saudáveis:

```powershell
docker-compose ps
```

### 3.2 Backend — FastAPI (porta 8000)

```powershell
# Terminal 1 — Servidor principal
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Verifique: acesse `http://localhost:8000/system` — deve retornar JSON com cpu/ram/disk.

### 3.3 Worker Celery (processamento distribuído)

```powershell
# Terminal 2 — Worker Celery
celery -A celery_app worker --loglevel=info --concurrency=4 -Q cad_jobs,ai_cad,bulk_jobs,default
```

> **Nota:** Se não tiver RabbitMQ/Redis locais, o Celery opera em modo local
> automático (eager) para desenvolvimento.

### 3.4 Frontend React (porta 3000)

```powershell
# Terminal 3 — Frontend
cd frontend
npm start
```

Acesse: `http://localhost:3000`

---

## 4. Configurar a Ponte AutoCAD (Modo Bridge)

O Engenharia CAD opera em **dois modos**:

| Modo         | Quando usar                                   |
|--------------|-----------------------------------------------|
| **COM**      | AutoCAD roda na mesma máquina do servidor      |
| **Ponte**    | AutoCAD roda em outra máquina (rede)           |

### 4.1 Criar a pasta Bridge

```powershell
mkdir C:\AutoCAD_Drop
```

### 4.2 Configurar o caminho via API

```powershell
curl -X POST http://localhost:8000/api/autocad/config/bridge `
  -H "Content-Type: application/json" `
  -d '{"path": "C:/AutoCAD_Drop/"}'
```

---

## 5. Carregar o Vigilante no AutoCAD/GstarCAD

O script `forge_vigilante.lsp` v2.0 é o **agente no PC do AutoCAD** que monitora
a pasta Bridge e executa automaticamente os arquivos `.lsp` gerados pelo servidor.

### 5.1 Copiar o arquivo

Copie `backend/forge_vigilante.lsp` para uma pasta local no PC do AutoCAD:

```
C:\Engenharia CAD\forge_vigilante.lsp
```

### 5.2 Carregar no AutoCAD / GstarCAD

1. Abra o AutoCAD ou GstarCAD.
2. Digite **`APPLOAD`** na linha de comando (ou menu Ferramentas → Carregar Aplicativo).
3. Navegue até `C:\Engenharia CAD\forge_vigilante.lsp` e clique **"Carregar"**.
4. **Para carga automática em toda sessão:** clique no botão **"Conteúdo de Inicialização"**
   (canto inferior da janela APPLOAD) e adicione o arquivo lá.

### 5.3 Configurar a pasta monitorada (FORGE_PATH)

Na linha de comando do AutoCAD, digite:

```
FORGE_PATH
```

Informe o caminho da pasta Bridge (a mesma configurada no servidor):

```
C:\AutoCAD_Drop\
```

> Se for pasta de rede: `\\SERVIDOR\AutoCAD_Drop\` ou `Z:\AutoCAD_Drop\`

### 5.4 Iniciar o monitoramento

```
FORGE_START
```

O Vigilante exibirá:
```
[Engenharia CAD HH:MM:SS] Vigilante ATIVO — monitorando em background.
[Engenharia CAD HH:MM:SS] Intervalo: 1.5s
```

### Comandos do Vigilante

| Comando        | Descrição                              |
|----------------|----------------------------------------|
| `FORGE_START`  | Inicia o monitoramento da pasta        |
| `FORGE_STOP`   | Para o monitoramento                   |
| `FORGE_STATUS` | Exibe estado atual e estatísticas      |
| `FORGE_PATH`   | Altera a pasta monitorada              |

---

## 6. Verificação Pré-Deploy

Execute o script de validação para confirmar que tudo está operacional:

```powershell
python final_check.py --bridge-path "C:/AutoCAD_Drop/"
```

O script verifica: Redis, RabbitMQ, FastAPI, AutoCAD Driver, Bridge Path,
Frontend, Vigilante v2.0 e Layers N-58.

---

## 7. Endpoints Principais da API

| Método | Endpoint                      | Descrição                          |
|--------|-------------------------------|------------------------------------|
| POST   | `/login`                      | Autenticação (retorna JWT)         |
| GET    | `/system`                     | Métricas CPU/RAM/Disco             |
| GET    | `/ai/health`                  | Saúde da camada IA + Driver CAD    |
| POST   | `/api/autocad/connect`        | Conecta ao AutoCAD/GstarCAD        |
| POST   | `/api/autocad/draw-pipe`      | Desenha tubulação                  |
| POST   | `/api/autocad/draw-line`      | Desenha linha                      |
| POST   | `/api/autocad/insert-component`| Insere bloco (válvula, flange)    |
| POST   | `/api/autocad/add-text`       | Adiciona anotação                  |
| POST   | `/api/autocad/create-layers`  | Cria layers N-58 Petrobras         |
| POST   | `/api/autocad/batch-draw`     | Desenho em lote (IA)               |
| POST   | `/api/autocad/finalize`       | Gran Finale (Zoom + Regen)         |
| POST   | `/api/autocad/commit`         | Envia buffer para pasta Bridge     |
| POST   | `/api/autocad/config/bridge`  | Define pasta de rede               |
| POST   | `/api/autocad/config/mode`    | Alterna COM ↔ Ponte                |
| GET    | `/sse/system`                 | SSE métricas em tempo real         |
| GET    | `/sse/ai-stream`              | SSE respostas IA                   |

Documentação interativa: `http://localhost:8000/docs`

---

## 8. Layers Norma N-58 Petrobras

O sistema cria automaticamente os seguintes layers ao conectar:

| Layer            | Cor | Categoria      | Linetype   | Peso (mm) |
|------------------|-----|----------------|------------|-----------|
| PIPE-PROCESS     |  1  | Tubulação      | Continuous | 0.50      |
| PIPE-UTILITY     |  3  | Tubulação      | Continuous | 0.35      |
| PIPE-INSTRUMENT  |  6  | Instrumentação | DASHED     | 0.25      |
| EQUIP-VESSEL     |  4  | Equipamentos   | Continuous | 0.70      |
| EQUIP-PUMP       |  4  | Equipamentos   | Continuous | 0.50      |
| VALVE            |  6  | Instrumentação | Continuous | 0.50      |
| FLANGE           |  4  | Equipamentos   | Continuous | 0.35      |
| SUPPORT          |  8  | Civil          | CENTER     | 0.25      |
| ANNOTATION       |  7  | Texto/Cotas    | Continuous | 0.18      |
| DIMENSION        |  7  | Texto/Cotas    | Continuous | 0.18      |
| ISOMETRIC        | 150 | Isométrico     | Continuous | 0.25      |

---

## 9. Compatibilidade GstarCAD

O driver tenta **automaticamente** conectar nesta ordem:

1. `AutoCAD.Application` (Autodesk AutoCAD)
2. `Gcad.Application` (GstarCAD)
3. `GstarCAD.Application` (GstarCAD alternativo)

Se nenhum for encontrado via COM, o Modo Ponte (rede) funciona com **qualquer CAD**
que suporte AutoLISP.

---

## 10. Troubleshooting

| Problema                    | Solução                                        |
|-----------------------------|------------------------------------------------|
| Redis não conecta           | `docker-compose up -d redis`                   |
| RabbitMQ não conecta        | `docker-compose up -d rabbitmq`                |
| FastAPI não inicia          | Verificar `.env` e `pip install -r requirements.txt` |
| Vigilante não vê jobs       | Verificar FORGE_PATH aponta para mesma pasta   |
| COM Error no AutoCAD        | Fechar/abrir AutoCAD e tentar `POST /connect`  |
| "Módulo não encontrado"     | Ativar venv: `.\venv\Scripts\Activate.ps1`     |
| PC B não acessa API         | Verificar firewall (seção 11) e IP correto     |
| CORS blocked                | Verificar que CORS regex aceita o IP de origem |

---

## 11. Operação em Rede (PC A → PC B)

Cenário: **PC A** é o Servidor (FastAPI + Frontend) e **PC B** é o Cliente (AutoCAD/GstarCAD com Vigilante).

```
┌──────────────────────────┐         rede local         ┌──────────────────────────┐
│  PC A — SERVIDOR         │◄──────────────────────────►│  PC B — CLIENTE CAD      │
│  FastAPI :8000           │     HTTP + pasta Bridge     │  AutoCAD / GstarCAD      │
│  Frontend React :3000    │                             │  forge_vigilante.lsp     │
│  Redis / RabbitMQ        │                             │  Navegador (opcional)    │
└──────────────────────────┘                             └──────────────────────────┘
```

### 11.1 Descobrir o IP do PC A (Servidor)

No **PC A**, abra o PowerShell e execute:

```powershell
# Opção 1 — comando rápido
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' }).IPAddress

# Opção 2 — ipconfig tradicional
ipconfig | Select-String "IPv4"
```

Anote o IP (ex: `192.168.1.10`). Este é o IP que o PC B usará.

### 11.2 Iniciar o Backend para acesso em rede

No **PC A**, use o script `run_server.py` que já faz bind em `0.0.0.0`:

```powershell
# Terminal 1 — Backend (aceita conexões de qualquer IP da rede)
python run_server.py
```

O script exibirá automaticamente o IP local e a URL para o PC B.

Para modo desenvolvimento (apenas localhost):

```powershell
python run_server.py --dev
```

### 11.3 Iniciar o Frontend para acesso em rede

O React dev server precisa aceitar conexões externas. No **PC A**:

```powershell
# Terminal 2 — Frontend acessível pela rede
cd frontend
$env:HOST="0.0.0.0"; npm start
```

### 11.4 Acessar do PC B

No **PC B**, abra o navegador e acesse:

```
http://192.168.1.10:3000
```

> Substitua `192.168.1.10` pelo IP real do PC A.

O Frontend detecta automaticamente o hostname da URL e direciona as chamadas API
para `http://192.168.1.10:8000` — **não precisa configurar nada manualmente**.

### 11.5 Firewall do Windows — Abrir portas no PC A

Execute no **PowerShell como Administrador** no **PC A**:

```powershell
# Abrir porta 8000 (FastAPI Backend)
New-NetFirewallRule -DisplayName "Engenharia CAD API (8000)" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 `
  -Action Allow -Profile Private

# Abrir porta 3000 (Frontend React)
New-NetFirewallRule -DisplayName "Engenharia CAD Frontend (3000)" `
  -Direction Inbound -Protocol TCP -LocalPort 3000 `
  -Action Allow -Profile Private
```

> **Profile Private** limita o acesso à rede privada. Para redes de domínio corporativo,
> adicione `-Profile Domain` ou use `-Profile Private,Domain`.

Para verificar se as regras foram criadas:

```powershell
Get-NetFirewallRule -DisplayName "Engenharia CAD*" | Format-Table DisplayName, Enabled, Direction
```

Para remover as regras depois:

```powershell
Remove-NetFirewallRule -DisplayName "Engenharia CAD API (8000)"
Remove-NetFirewallRule -DisplayName "Engenharia CAD Frontend (3000)"
```

---

## 12. Ponte de Rede — Caminhos UNC (PC A ↔ PC B)

Quando o AutoCAD roda no **PC B** e o servidor roda no **PC A**, a pasta Bridge
deve ser compartilhada na rede.

### 12.1 Criar e compartilhar a pasta no PC A

No **PC A**, execute como Administrador:

```powershell
# Criar pasta
mkdir C:\Engenharia CAD_Bridge

# Compartilhar na rede com permissão total
New-SmbShare -Name "Engenharia CAD_Bridge" -Path "C:\Engenharia CAD_Bridge" `
  -FullAccess "Everyone" -Description "Engenharia CAD Bridge Folder"
```

### 12.2 Permissões obrigatórias

O Vigilante (`forge_vigilante.lsp`) precisa de **Controle Total** na pasta
compartilhada porque ele:

1. **Lê** os arquivos `job_*.lsp` gerados pelo servidor
2. **Executa** o conteúdo LISP no AutoCAD
3. **Renomeia** o arquivo para `.done` após execução (ou **deleta** se renomear falhar)

Se as permissões estiverem incorretas, o Vigilante executará o mesmo job
repetidamente (loop infinito).

**Configurar permissões NTFS:**

```powershell
# No PC A — dar Controle Total na pasta para Everyone (rede privada)
$acl = Get-Acl "C:\Engenharia CAD_Bridge"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "Everyone", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl "C:\Engenharia CAD_Bridge" $acl
```

> **Segurança:** Em ambiente corporativo, substitua `Everyone` pelo grupo
> ou usuário específico do PC B (ex: `DOMINIO\usuario_pcb`).

### 12.3 Configurar o FORGE_PATH com caminho UNC no PC B

No **PC B**, dentro do AutoCAD, configure o Vigilante com o caminho UNC:

```
FORGE_PATH
```

Informe o caminho **UNC** (usando o IP ou nome do PC A):

```
\\192.168.1.10\Engenharia CAD_Bridge\
```

Formatos válidos:

| Formato | Exemplo |
|---------|---------|
| UNC com IP | `\\192.168.1.10\Engenharia CAD_Bridge\` |
| UNC com hostname | `\\PC-A\Engenharia CAD_Bridge\` |
| Drive mapeado | `Z:\Engenharia CAD_Bridge\` (após `net use Z: \\192.168.1.10\Engenharia CAD_Bridge`) |

> **Atenção:** No AutoLISP, use barras normais no FORGE_PATH: `//192.168.1.10/Engenharia CAD_Bridge/`
> O Vigilante aceita ambos os formatos (`\\` e `//`).

### 12.4 Configurar o Bridge Path no servidor (PC A)

No PC A, informe ao servidor o caminho **local** da mesma pasta:

```powershell
curl -X POST http://localhost:8000/api/autocad/config/bridge `
  -H "Content-Type: application/json" `
  -d '{"path": "C:/Engenharia CAD_Bridge/"}'
```

Ou via variável de ambiente no `.env`:

```env
AUTOCAD_BRIDGE_PATH=C:/Engenharia CAD_Bridge/
```

### 12.5 Verificação rápida da ponte

```powershell
# No PC A — verificar se a pasta está compartilhada
Get-SmbShare -Name "Engenharia CAD_Bridge"

# No PC B — verificar se consegue acessar
Test-Path "\\192.168.1.10\Engenharia CAD_Bridge"
```

---

## Licença

Projeto proprietário — Engenharia CAD v1.0 Gold.
Outputs em `data/output/`
