# Como conectar o sistema ao computador que tem AutoCAD

Este sistema tem dois modos de integracao com o AutoCAD:

- `COM`: quando backend e AutoCAD rodam na mesma maquina Windows
- `Ponte`: quando o backend roda em outro lugar e o AutoCAD fica no PC do cliente

Para Vercel, o modo correto e `Ponte`.

## Cenário recomendado com Vercel

- Backend: Vercel
- Frontend: Vercel
- AutoCAD: computador do cliente
- Integracao com AutoCAD: pasta compartilhada + `backend/forge_vigilante.lsp`

## O que vai no PC com AutoCAD

1. AutoCAD ou GstarCAD instalado
2. Uma pasta local ou compartilhada para receber jobs `.lsp`
3. O arquivo `backend/forge_vigilante.lsp` carregado no AutoCAD

## Passo a passo

### 1. Criar a pasta bridge

Exemplos:

- `C:\AutoCAD_Drop\`
- `Z:\AutoCAD_Drop\`
- `\\SERVIDOR\AutoCAD_Drop\`

Se o backend estiver fora desse PC, a pasta precisa ser compartilhada com leitura e escrita.

### 2. Copiar o vigilante

Copie:

- `backend/forge_vigilante.lsp`

para uma pasta do PC que tem o AutoCAD, por exemplo:

- `C:\EngenhariaCAD\forge_vigilante.lsp`

### 3. Carregar no AutoCAD

1. Abrir o AutoCAD
2. Digitar `APPLOAD`
3. Carregar `forge_vigilante.lsp`
4. Opcional e recomendado: adicionar em Startup Suite para carregar sempre

### 4. Configurar o caminho monitorado

Dentro do AutoCAD:

1. Digitar `FORGE_PATH`
2. Informar a pasta bridge, por exemplo `Z:/AutoCAD_Drop/`
3. Digitar `FORGE_START`
4. Confirmar que o monitoramento ficou ativo

### 5. Apontar o backend para essa pasta

Se o backend estiver local:

```powershell
curl -X POST http://localhost:8000/api/autocad/config/bridge ^
  -H "Content-Type: application/json" ^
  -d "{\"path\":\"C:/AutoCAD_Drop/\"}"
```

Se o backend estiver publicado:

```powershell
curl -X POST https://SEU-BACKEND.vercel.app/api/autocad/config/bridge ^
  -H "Content-Type: application/json" ^
  -d "{\"path\":\"\\\\SERVIDOR\\AutoCAD_Drop\\\"}"
```

### 6. Ativar modo ponte

```powershell
curl -X POST https://SEU-BACKEND.vercel.app/api/autocad/config/mode ^
  -H "Content-Type: application/json" ^
  -d "{\"use_bridge\":true}"
```

## Como o fluxo funciona

1. O frontend envia a acao para o backend
2. O backend gera comandos AutoLISP
3. O backend grava um arquivo `.lsp` na pasta bridge
4. O `forge_vigilante.lsp` detecta esse arquivo
5. O AutoCAD executa o job

## O que nao muda

- O `server.py` continua sendo o backend principal
- O AutoCAD continua fora da Vercel
- O modo COM local continua disponivel para uso em Windows

## Observacoes praticas

- Vercel nao consegue acessar `C:\` do computador do cliente diretamente
- Para deploy remoto, a ponte precisa usar pasta compartilhada de rede acessivel pelo fluxo real de operacao
- Se voce quiser isolamento maior, existe tambem o `forge_link_agent.py`, que pode rodar como agente local no PC do AutoCAD

## Arquivos importantes

- `server.py`
- `backend/forge_vigilante.lsp`
- `backend/routes_autocad.py`
- `forge_link_agent.py`
