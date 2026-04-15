# 📦 Engenharia CAD - Guia de Instalação

## Requisitos do Sistema

### Computador do Cliente
- **Sistema Operacional**: Windows 10 ou 11 (64-bit)
- **PowerShell**: 5.1 ou superior (incluso no Windows 10+)
- **CAD Software** (um dos seguintes):
  - AutoCAD 2020, 2021, 2022, 2023, 2024, 2025 ou 2026
  - AutoCAD LT 2023 ou 2024
  - GstarCAD 2022, 2023 ou 2024
  - ZWCAD 2023 ou 2024
  - BricsCAD V23 ou V24
- **Conexão com Internet**: Necessária para comunicação com o servidor

### Servidor (já configurado)
- Backend: https://automacao-cad-backend.vercel.app
- Frontend: https://automacao-cad-frontend.vercel.app

---

## Instalação Passo a Passo

### Passo 1: Download do Instalador

1. Acesse: https://automacao-cad-frontend.vercel.app
2. Faça login com sua conta
3. Vá para **Configurações** → **AutoCAD Agent**
4. Clique em **"Baixar Instalador"**
5. Salve o arquivo `Engenharia_CAD_Instalador.zip`

Ou baixe diretamente:
```
https://automacao-cad-backend.vercel.app/api/download/sincronizador
```

### Passo 2: Extrair Arquivos

1. Localize o arquivo `Engenharia_CAD_Instalador.zip`
2. Clique com botão direito → **"Extrair Tudo..."**
3. Escolha um local (ex: `C:\Downloads\Engenharia_CAD_Instalador`)
4. Clique em **"Extrair"**

### Passo 3: Executar Instalador

1. Abra a pasta extraída
2. Clique com **botão direito** em `INSTALAR.bat`
3. Selecione **"Executar como administrador"**
4. Se aparecer aviso do SmartScreen, clique em **"Mais informações"** → **"Executar assim mesmo"**
5. Aguarde a instalação completar

### Passo 4: Verificar Instalação

O instalador criará:
- 📁 `C:\EngenhariaCAD\` - Arquivos do sistema
- 📁 `C:\AutoCAD_Drop\` - Pasta de comandos
- 🔗 Atalho na área de trabalho: "Engenharia CAD - Sincronizador"

---

## Uso Diário

### Iniciar o Sistema

1. **Método 1 (Recomendado)**: Clique duplo no atalho "Engenharia CAD - Sincronizador" na área de trabalho
2. **Método 2**: Execute `C:\EngenhariaCAD\INICIAR_SINCRONIZADOR.bat`

### No AutoCAD

Ao abrir o AutoCAD, o sistema será carregado automaticamente. Você verá:

```
╔═══════════════════════════════════════════════════════════════╗
║           ENGENHARIA CAD - FORGE VIGILANTE v2.0               ║
╠═══════════════════════════════════════════════════════════════╣
║  Sistema carregado com sucesso!                               ║
║                                                               ║
║  Comandos disponíveis:                                        ║
║    FORGE_START  - Iniciar monitoramento                       ║
║    FORGE_STOP   - Parar monitoramento                         ║
║    FORGE_STATUS - Ver status atual                            ║
║                                                               ║
║  Iniciando automaticamente em 3 segundos...                   ║
╚═══════════════════════════════════════════════════════════════╝
```

### Comandos do AutoCAD

| Comando | Descrição |
|---------|-----------|
| `FORGE_START` | Inicia o monitoramento da pasta de comandos |
| `FORGE_STOP` | Para o monitoramento |
| `FORGE_STATUS` | Mostra estatísticas (jobs processados, falhas, etc.) |
| `FORGE_PATH` | Altera a pasta monitorada |

### No Sincronizador

O sincronizador mostrará:

```
+-----------------------------------------------------------------------+
| STATUS: [OK] CONECTADO    Uptime: 00:05:30                            |
| CAD: AutoCAD 2024         Comandos: 3                                 |
+-----------------------------------------------------------------------+
```

---

## Troubleshooting

### Problema: "Bridge indisponível" no Sincronizador

**Causas possíveis:**
1. Sem conexão com internet
2. Backend temporariamente offline
3. Firewall bloqueando conexão

**Soluções:**
1. Verifique sua conexão com internet
2. Aguarde alguns minutos e tente novamente
3. Adicione exceção no firewall para PowerShell

### Problema: AutoCAD não carrega o sistema automaticamente

**Soluções:**
1. Verifique se o arquivo existe: `C:\EngenhariaCAD\forge_vigilante.lsp`
2. No AutoCAD, digite `APPLOAD` e carregue manualmente o arquivo
3. Re-execute o instalador como administrador

### Problema: Comandos não são executados no AutoCAD

**Verificações:**
1. O Sincronizador está rodando e mostrando "CONECTADO"?
2. No AutoCAD, digite `FORGE_STATUS` - está "Monitorando"?
3. A pasta `C:\AutoCAD_Drop` existe?

**Solução:**
1. No AutoCAD, digite `FORGE_START`
2. Verifique se há arquivos `.lsp` na pasta `C:\AutoCAD_Drop`

### Problema: "Acesso negado" ao instalar

**Solução:**
1. Feche o AutoCAD
2. Clique com botão direito em `INSTALAR.bat`
3. Selecione "Executar como administrador"

---

## Desinstalação

### Via Instalador
1. Abra PowerShell como administrador
2. Execute:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\EngenhariaCAD\INSTALAR.ps1" -Uninstall
```

### Manual
1. Delete a pasta `C:\EngenhariaCAD`
2. Delete o atalho da área de trabalho
3. (Opcional) Delete `C:\AutoCAD_Drop`

---

## Arquivos do Sistema

| Arquivo | Local | Descrição |
|---------|-------|-----------|
| `forge_vigilante.lsp` | `C:\EngenhariaCAD\` | Plugin AutoLISP principal |
| `SINCRONIZADOR.ps1` | `C:\EngenhariaCAD\` | Script de sincronização |
| `acaddoc.lsp` | `%APPDATA%\Autodesk\AutoCAD...\Support\` | Auto-load |
| `engcad_install.log` | `%USERPROFILE%\` | Log de instalação |

---

## Suporte

- **Site**: https://automacao-cad-frontend.vercel.app
- **Documentação**: https://automacao-cad-frontend.vercel.app/docs
- **Email**: suporte@engenhariacad.com

---

*Versão do documento: 2.0 | Atualizado: Abril 2026*
