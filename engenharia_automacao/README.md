# Engenharia Automacao

Sistema de engenharia automatizada com interface desktop, validacao central, leitura de Excel e geracao AutoLISP.

## Fases implementadas

- `CORE`: validacao, modelos, geracao de geometria e servico central.
- `CAD`: emissao de comandos `LINE`, `CIRCLE` e `ARC`, com layer e carimbo automaticos.
- `UI`: dois modos de uso, `Manual` e `Excel`, com separacao entre interface e controller.
- `QA`: testes unitarios e fluxo de lote por planilha.

## Fluxo

`UI -> Controller -> CORE -> CAD -> arquivo .lsp`

Qualquer erro de validacao interrompe a execucao.

## Arquivos principais

- `config.py`: configuracao central.
- `core/main.py`: servico principal e logging.
- `core/integrations/excel_reader.py`: leitura de Excel com `pandas`.
- `cad/lisp/generator.py`: emissao do AutoLISP.
- `app/ui/main_window.py`: interface desktop.
- `app/controllers/project_controller.py`: controle entre UI e core.

## Como executar

### Backend Python (real)
1. `cd integration/python_api`
2. `pip install -r requirements.txt`
3. `python app.py`

### Licensing server
1. `cd licensing_server`
2. `pip install fastapi uvicorn`
3. `uvicorn app:app --reload --host 0.0.0.0 --port 5200`

### Frontend Electron + React
1. `cd frontend`
2. `npm install`
3. `npm start` (apenas React)
4. `npm run electron` (React + Electron)

### Build unificado
`build_all.bat`

## Endpoints usados
- POST `http://localhost:8000/login`
- POST `http://localhost:8000/generate`
- POST `http://localhost:8000/excel`
- GET  `http://localhost:8000/history`
- GET  `http://localhost:8000/logs`
- GET  `http://localhost:8000/health`

## Colunas esperadas no Excel

- `diametro`
- `comprimento`
- `empresa`
- `nome_da_peca`
- `codigo`

## Como testar

Execute `python -m pytest engenharia_automacao/tests`

## Execucao AutoCAD e configuracoes

- Ajuste `core/config.py`:
  - `AUTO_EXECUTE = True` para disparar AutoCAD automatico (requer `pywin32` e AutoCAD instalado)
  - `USE_LOGIN = True` para modo seguro com controle de licenca
  - `LSP_OUTPUT_DIR` para salvar .lsp em pasta de saida
  - `LOG_LEVEL` para nivel de log

- Se `AUTO_EXECUTE` estiver habilitado, o sistema fara:
  - abrir ou conectar ao AutoCAD
  - carregar o arquivo .lsp
  - executar comando `DrawGeneratedPipe`

## Simulacao de uso

Execute `python engenharia_automacao/simulate_usage.py` para rodar 5 projetos aleatorios e testar pipeline completo.
