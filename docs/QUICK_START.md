# 🚀 ENGENHARIA CAD v1.0 - QUICK START

## Em 5 Minutos

### **Passo 1: Terminal 1 - Backend**
```powershell
cd "c:\Users\Sueli\Desktop\Automação CAD"
$env:JARVIS_SECRET="minha_chave_secreta_123"
python -m uvicorn server:app --reload --port 8000
```

### **Passo 2: Terminal 2 - Frontend**
```powershell
cd "c:\Users\Sueli\Desktop\Automação CAD\frontend"
npm start
```

### **Passo 3: Usar a Aplicação**
1. Abrir http://localhost:3000
2. Login: **tony** / **123**
3. Clique no ícone de Sol/Lua para alternar tema
4. Vá para "Configuração Global" no menu
5. Selecione uma refinaria (ex: REGAP)
6. Clique "SAVE & START NEW PROJECT"
7. Vá para "Console CAD"
8. Clique "INJECT & DRAW"

---

## 📁 Estrutura Criada

```
✅ src/styles/theme.ts                    - Temas light/dark
✅ src/context/ThemeContext.tsx           - Gerenciador de tema
✅ src/context/GlobalContext.tsx          - Gerenciador de refinaria
✅ src/components/ThemeToggle.tsx         - Botão Sol/Lua
✅ src/components/Loader.tsx              - Spinner de loading
✅ src/components/Sidebar.tsx             - Menu de navegação
✅ src/pages/GlobalSetup.tsx              - Seleção de refinaria
✅ src/pages/CadConsole.tsx               - Console CAD
✅ src/App.tsx                            - ATUALIZADO com rotas
✅ backend/database/refineries_data.json  - Dados de refinarias
✅ engenharia_automacao/services/refinery_service.py - Serviço
✅ engenharia_automacao/app/routes_cad.py - Rotas API
✅ server.py                              - ATUALIZADO com router
```

---

## 🎨 Temas Disponíveis

**Claro (Light):**
- Background: #F0F2F5
- Texto: #333333
- Azul Primário: #007BFF
- Verde Sucesso: #28A745

**Escuro (Dark):**
- Background: #1A1A1D
- Texto: #F0F0F0
- Azul Vibrante: #1E90FF
- Verde Neon: #32CD32

---

## 🔌 APIs Disponíveis

```
GET  http://localhost:8000/api/refineries
GET  http://localhost:8000/api/refineries/REGAP
POST http://localhost:8000/api/cad/inject
GET  http://localhost:8000/api/cad/norms/REGAP
GET  http://localhost:8000/api/cad/materials/REGAP
```

---

## ❓ Dúvidas Comuns

**P: Tema não está mudando?**
R: Verifique se clicou no botão Sol/Lua na Sidebar

**P: Refinarias não aparecem?**
R: Verificar se o backend está rodando em http://localhost:8000

**P: "Cannot find module"?**
R: Rodou `npm install` no frontend? E pip install no backend?

**P: Porta 8000 já está em uso?**
R: Mude para: `python -m uvicorn server:app --port 8001`

---

## 📚 Documentação Completa

- [ENGENHARIA_CAD_IMPLEMENTACAO_GUIA.md](./ENGENHARIA_CAD_IMPLEMENTACAO_GUIA.md) - Guia completo
- [VERIFICACAO_IMPLEMENTACAO.md](./VERIFICACAO_IMPLEMENTACAO.md) - Checklist de testes

---

## 🎯 Próximos Passos

1. Testar o fluxo completo
2. Integrar com AutoCAD real (FASE 3)
3. Adicionar banco de dados (FASE 4)
4. Deploy em produção

---

**Boa sorte! 🚀**
