# ENGENHARIA CAD v1.0 - GUIA DE IMPLEMENTAÇÃO

## 🎯 RESUMO EXECUTIVO

Este documento detalha a implementação **FASE 1 e FASE 2** do módulo de Interface Visual e Integração Backend da plataforma **Engenharia CAD v1.0**.

Todos os componentes foram desenvolvidos em **React + TypeScript + Electron** (frontend) e **FastAPI + Python** (backend), com suporte a temas claro/escuro, gerenciamento de contexto global e integração com refinarias.

---

## 📦 ARQUIVOS IMPLEMENTADOS

### **FRONTEND (React + TypeScript)**

#### 1. **Tema e Styling**
- **`src/styles/theme.ts`**
  - Definição de cores para modo claro e escuro
  - Cores CAD específicas (verde neon, amarelo, vermelho)
  - Exporta tipos e cores reutilizáveis

#### 2. **Contextos Globais**
- **`src/context/ThemeContext.tsx`**
  - Gerenciador de tema (light/dark)
  - Persistência em localStorage
  - Hook `useTheme()` para acesso em componentes
  
- **`src/context/GlobalContext.tsx`**
  - Gerenciador de refinaria selecionada
  - Persistência de configurações de projeto
  - Hook `useGlobal()` para acesso em componentes

#### 3. **Componentes Reutilizáveis**
- **`src/components/ThemeToggle.tsx`**
  - Botão Sol/Lua para alternar temas
  - Sensível a tema (cores dinâmicas)
  
- **`src/components/Loader.tsx`**
  - Spinner animado e mensagem de carregamento
  - Modo fullscreen ou inline
  - Cores sensíveis ao tema
  
- **`src/components/Sidebar.tsx`**
  - Navegação principal da aplicação
  - Links para Dashboard, GlobalSetup, CadConsole
  - Integração com ThemeToggle
  - Responsivo (collapsible em mobile)

#### 4. **Páginas Principais**
- **`src/pages/GlobalSetup.tsx`**
  - Tela de seleção de refinaria
  - Exibe normas, banco de dados de materiais, classe de pressão
  - Botão "SAVE & START NEW PROJECT" navega para Dashboard
  - Integra com backend via `GET /api/refineries`
  
- **`src/pages/CadConsole.tsx`**
  - Ponte de comando com AutoCAD
  - Painel de status CAD (conexão, database, pressão)
  - Painel de controle (barra de progresso, botões)
  - Log de comandos em tempo real
  - Simula injeção de LISP via `POST /api/cad/inject`

#### 5. **App Principal**
- **`src/App.tsx`** (ATUALIZADO)
  - Integra ThemeProvider e GlobalProvider
  - Roteamento com React Router (Dashboard, GlobalSetup, CadConsole)
  - Mantém autenticação e licenciamento existentes

---

### **BACKEND (FastAPI + Python)**

#### 1. **Dados de Refinarias**
- **`backend/database/refineries_data.json`**
  - Dados de 4 refinarias: REGAP, REPLAN, BRAAP, RECAP
  - Cada uma com: norms, material_database, pressure_class, tolerance
  - Suporta fácil extensão para mais refinarias

#### 2. **Serviço de Refinarias**
- **`engenharia_automacao/services/refinery_service.py`**
  - Singleton RefineryService para acesso aos dados
  - Métodos: `get_all_refineries()`, `get_refinery()`, `validate_refinery()`
  - Carregamento automático do JSON com fallback para dados padrão
  - Cache em memória para performance

#### 3. **Rotas CAD (API)**
- **`engenharia_automacao/app/routes_cad.py`**
  - `GET /api/refineries` - Lista todas as refinarias
  - `GET /api/refineries/{refinery_id}` - Detalhes de uma refinaria
  - `POST /api/cad/inject` - Injetar comando LISP no AutoCAD
  - `GET /api/cad/inject/{script_id}` - Status de injeção
  - `GET /api/cad/norms/{refinery_id}` - Normas aplicáveis
  - `GET /api/cad/materials/{refinery_id}` - Banco de dados de materiais

#### 4. **Servidor Principal**
- **`server.py`** (ATUALIZADO)
  - Adicionado import: `from engenharia_automacao.app.routes_cad import router as cad_router`
  - Adicionado: `app.include_router(cad_router)`
  - CORS já configurado para `http://localhost:3000`

---

## 🚀 COMO EXECUTAR

### **Pré-requisitos**
```bash
# Node.js e npm para o frontend
node --version  # v18+
npm --version   # v8+

# Python para o backend
python --version  # 3.9+
```

### **Setup Frontend**

```bash
cd frontend

# Instalar dependências (primeira vez)
npm install

# Iniciar servidor React (porta 3000)
npm start

# Em outra aba - iniciar Electron
npm run electron
```

**Dependências instaladas automaticamente:**
- `react@18.0.0`
- `react-router-dom@6.15.0`
- `axios@1.5.0`
- `lucide-react@0.577.0` (ícones)
- `tailwindcss@3.4.19`

### **Setup Backend**

```bash
cd engenharia_automacao

# Criar ambiente virtual (se não existir)
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install fastapi uvicorn pydantic

# Exportar JARVIS_SECRET (importante para segurança)
export JARVIS_SECRET="sua_chave_super_secreta_aqui"

# Iniciar servidor (porta 8000)
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Nota:** Se estiver usando `python -m` em vez de `uvicorn`:
```bash
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### **URLs Importantes**

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | React App |
| Backend API | http://localhost:8000 | FastAPI Server |
| Docs API | http://localhost:8000/docs | Swagger UI |
| Refinarias | http://localhost:8000/api/refineries | JSON com todas as refinarias |

---

## 🎨 FLUXO DE USUÁRIO

### **1. Autenticação**
```
[Login Screen] 
  ↓ (username: tony, password: 123)
[Dashboard - com Theme Toggle]
```

### **2. Configuração de Projeto**
```
[Dashboard]
  ↓ Clica em "Configuração Global"
[GlobalSetup Page]
  ↓ Seleciona Refinaria (ex: REGAP)
  ↓ Visualiza normas e configs
  ↓ Clica "SAVE & START NEW PROJECT"
[Dashboard - com refinaria selecionada]
```

### **3. Execução CAD**
```
[Dashboard]
  ↓ Clica em "Console CAD"
[CadConsole Page]
  ↓ Vê status da conexão AutoCAD
  ↓ Clica "INJECT & DRAW"
  ↓ Simula injeção LISP
  ↓ Vê progresso e logs
```

### **4. Alternância de Tema**
```
[Em qualquer página]
  ↓ Sidebar → Clica em botão Sol/Lua
  ↓ Tema muda (light ↔ dark)
  ↓ Preferência salva em localStorage
```

---

## 🔌 ENDPOINTS API DISPONÍVEIS

### **Refinarias**
```bash
# Listar todas
curl http://localhost:8000/api/refineries

# Detalhes de uma
curl http://localhost:8000/api/refineries/REGAP

# Normas
curl http://localhost:8000/api/cad/norms/REGAP

# Banco de dados
curl http://localhost:8000/api/cad/materials/REGAP
```

### **Injeção CAD**
```bash
# Injeta comando LISP
curl -X POST http://localhost:8000/api/cad/inject \
  -H "Content-Type: application/json" \
  -d '{
    "refinery_id": "REGAP",
    "pressure_class": "150#",
    "norms": ["N-0058", "N-0076"],
    "drawing_type": "3D Piping Layout"
  }'

# Resultado:
# {
#   "script_id": "AUTO-abc123",
#   "refinery_id": "REGAP",
#   "timestamp": "2026-03-26T...",
#   "status": "PENDING",
#   "lisp_script": "..."
# }
```

---

## 🎯 FEATURES IMPLEMENTADOS

### **✅ COMPLETADOS**

1. **Sistema de Tema**
   - [x] Cores Light/Dark configuráveis
   - [x] Persistência em localStorage
   - [x] ThemeContext para consumo em componentes
   - [x] Cores CAD específicas (neon, gradient)

2. **GlobalContext**
   - [x] Armazenamento de refinaria selecionada
   - [x] Persistência de configurações
   - [x] Interface TypeScript com tipos

3. **Componentes**
   - [x] ThemeToggle (botão Sol/Lua)
   - [x] Loader com spinner animado
   - [x] Sidebar com navegação responsiva

4. **Páginas**
   - [x] GlobalSetup (seleção de refinaria)
   - [x] CadConsole (ponte de comando)
   - [x] Roteamento completo

5. **Backend**
   - [x] RefineryService singleton
   - [x] routes_cad com 6 endpoints
   - [x] Integração em server.py
   - [x] CORS configurado

### **⏳ PRÓXIMOS PASSOS (FASE 3)**

1. **Comunicação Real com AutoCAD**
   - [ ] Socket.io para conexão em tempo real
   - [ ] Geração real de LISP scripts
   - [ ] Feedback de progresso via SSE

2. **Banco de Dados**
   - [ ] Persistência de projetos
   - [ ] Histórico de injeções CAD
   - [ ] Audit trail

3. **Validação e Qualidade**
   - [ ] QualityGate page
   - [ ] Clash detection
   - [ ] Relatórios em PDF/Excel

4. **Performance**
   - [ ] Caching de refinarias
   - [ ] Rate limiting aprimorado
   - [ ] Compressão de assets

---

## 🐛 TROUBLESHOOTING

### **Problema: "Cannot find module"**
```bash
# Solução: Node_modules ou venv não instalados
cd frontend && npm install
cd ../engenharia_automacao && pip install -r requirements.txt
```

### **Problema: CORS Error**
```bash
# Solução: Servidor backend não rodando
# Verificar se está em http://localhost:8000
# Se necessário, adicionar mais origins em server.py:
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "seu_host_aqui"]
```

### **Problema: Refinarias JSON não encontrado**
```bash
# Solução: RefineryService não encontra arquivo
# Verificar caminho em engenharia_automacao/services/refinery_service.py
# Ou usar dados padrão que estão hardcoded
```

### **Problema: Tema não persiste**
```bash
# Solução: localStorage vazio ou desabilitado
# Verificar console do navegador
# localStorage.getItem('theme-preference') deve retornar 'light' ou 'dark'
```

---

## 📊 ESTRUTURA DE DADOS

### **RefineryConfig**
```typescript
interface RefineryConfig {
  name: string;                              // "REGAP Gabriel Passos"
  location: string;                          // "Betim, MG"
  norms: string[];                           // ["N-0058", "N-0076"]
  material_database: string;                 // "SINCOR_REGAP_V2.3.5"
  default_pressure_class: string;            // "150#"
  clash_detection_tolerance_mm: number;      // 5
}
```

### **CadInjectRequest**
```python
class CadInjectRequest(BaseModel):
    refinery_id: str                        # "REGAP"
    pressure_class: str                     # "150#"
    norms: List[str]                        # ["N-0058"]
    drawing_type: str = "3D Piping Layout" # tipo de desenho
    additional_params: Optional[dict] = None
```

### **CadInjectResponse**
```python
class CadInjectResponse(BaseModel):
    script_id: str                          # "AUTO-abc123"
    refinery_id: str                        # "REGAP"
    timestamp: str                          # ISO timestamp
    status: str                             # "PENDING" | "COMPLETED"
    lisp_script: Optional[str]             # Script LISP gerado
```

---

## 📝 NOTAS IMPORTANTES

1. **Segurança**
   - Sempre definir `JARVIS_SECRET` em .env
   - CORS está limitado a localhost:3000
   - JWT token com 1 hora de validade

2. **Performance**
   - RefineryService é singleton (cache)
   - localStorage para persistência local
   - Sem banco de dados (FASE 3)

3. **Escalabilidade**
   - Adicionar novas refinarias: editar `refineries_data.json`
   - Adicionar novos endpoints: `routes_cad.py`
   - Novo tema: extend `src/styles/theme.ts`

4. **TypeScript**
   - Todos os componentes com tipos completos
   - Interfaces em `src/context/` e respostas API
   - Zero `any` types

---

## 🎓 EXEMPLOS DE USO

### **Acessar tema em componente**
```typescript
import { useTheme } from '../context/ThemeContext';

function MeuComponente() {
  const { isDark, theme, toggleTheme } = useTheme();
  
  return (
    <div style={{ backgroundColor: theme.background }}>
      <button onClick={toggleTheme}>
        {isDark ? 'Modo Claro' : 'Modo Escuro'}
      </button>
    </div>
  );
}
```

### **Acessar refinaria global**
```typescript
import { useGlobal } from '../context/GlobalContext';

function MeuComponente() {
  const { selectedRefinery, refineryConfig } = useGlobal();
  
  if (!selectedRefinery) {
    return <p>Selecione uma refinaria primeiro</p>;
  }
  
  return <p>Refinaria: {refineryConfig?.name}</p>;
}
```

### **Chamar API de refinarias**
```typescript
import axios from 'axios';

async function carregarRefinarias() {
  const response = await axios.get('http://localhost:8000/api/refineries');
  console.log(response.data); // { "REGAP": {...}, "REPLAN": {...} }
}
```

---

## 📞 SUPORTE

Para dúvidas ou problemas:
1. Verificar console do navegador (F12)
2. Verificar logs do servidor FastAPI
3. Revisar os arquivos de rota API
4. Validar estrutura JSON em `refineries_data.json`

---

**Status:** ✅ FASE 1 e FASE 2 CONCLUÍDAS
**Versão:** 1.0 BETA
**Data:** 26/03/2026
