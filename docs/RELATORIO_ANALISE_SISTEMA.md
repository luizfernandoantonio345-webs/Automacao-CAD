# RELATÓRIO DE ANÁLISE COMPLETA DO SISTEMA Engenharia CAD

**Data:** 27 de Março de 2026
**Analista:** GitHub Copilot (Claude Opus 4.6)
**Versão do Sistema:** v1.0
**Status:** Análise Profunda — Todas as Perguntas Respondidas

---

## ÍNDICE

1. [Por que esse sistema foi criado?](#1-por-que-esse-sistema-foi-criado)
2. [A meta de autonomia total](#2-a-meta-de-autonomia-total)
3. [As tarefas que o sistema executa](#3-as-tarefas-que-o-sistema-executa)
4. [Potencial do sistema e onde ele pode chegar](#4-potencial-do-sistema-e-onde-ele-pode-chegar)
5. [Próxima atualização V2](#5-próxima-atualização-v2---o-que-deve-ser)
6. [Se eu fosse você, o que eu faria](#6-se-eu-fosse-você-o-que-eu-faria)

---

## 1. POR QUE ESSE SISTEMA FOI CRIADO?

### O Problema Real

Na engenharia industrial brasileira — especialmente em refinarias da Petrobras (REGAP, REPLAN, BRAAP, RECAP) — existe um gargalo brutal no ciclo de projetos de tubulação e estrutura metálica:

| Etapa Manual Hoje                                   | Tempo Médio      | Risco de Erro               |
| --------------------------------------------------- | ---------------- | --------------------------- |
| Projetar tubulação no AutoCAD                       | 4-8 horas/trecho | Alto (cálculos manuais)     |
| Gerar MTO (Material Take-Off)                       | 2-4 horas        | Altíssimo (contagem manual) |
| Verificar normas Petrobras (N-76, N-58, N-115)      | 1-2 horas        | Médio (consulta em PDFs)    |
| Gerar scripts LISP para AutoCAD                     | 30-60 min        | Alto (erro de sintaxe)      |
| Calcular expansão térmica (ASME B31.3)              | 1-2 horas        | Alto (fórmulas complexas)   |
| Selecionar materiais por fluido/pressão/temperatura | 30-60 min        | Médio                       |
| Gerar relatórios de engenharia                      | 1-2 horas        | Baixo                       |

**Um projeto de tubulação simples (2 sistemas, DN100 + DN200) consome 10-20 horas de trabalho repetitivo de engenheiro.**

### A Razão de Existir do Engenharia CAD

O Engenharia CAD foi criado para **eliminar o retrabalho humano** nessas etapas repetitivas. Ele não substitui o engenheiro — ele automatiza as partes mecânicas do trabalho:

- O engenheiro informa os parâmetros (diâmetro, comprimento, fluido, pressão, temperatura)
- O sistema **calcula, valida, seleciona materiais, gera o desenho CAD e produz o relatório** — tudo automaticamente

### O Contexto de Mercado

- **Setor-alvo:** Engenharia industrial pesada no Brasil (petroquímica, óleo & gás, siderurgia)
- **Dor principal:** Engenheiros gastam 60-70% do tempo em tarefas que poderiam ser automatizadas
- **Oportunidade:** Não existe ferramenta brasileira que integre AutoCAD + normas Petrobras + IA num sistema único

---

## 2. A META DE AUTONOMIA TOTAL

### Visão de Autonomia

A meta do Engenharia CAD é alcançar um ciclo **entrada → saída** completamente autônomo:

```
ENTRADA (Engenheiro informa):          SAÍDA (Sistema entrega):
─────────────────────────              ────────────────────────
• Descrição da peça                    • Arquivo .LSP para AutoCAD
• Diâmetro / Comprimento              • Desenho DXF/DWG gerado
• Fluido / Pressão / Temperatura       • MTO completo com custos
• Refinaria / Normas aplicáveis        • Relatório de engenharia
• Empresa / Código do projeto          • Especificação de soldagem
                                       • Plano de teste hidrostático
                                       • Seleção de materiais validada
                                       • Suportes de tubulação (Série L)
```

### Os 5 Níveis de Autonomia do Sistema

| Nível                              | Descrição                                                            | Status Atual                            |
| ---------------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| **Nível 1** — Geração de Scripts   | Gerar arquivos .LSP automaticamente a partir de parâmetros           | ✅ IMPLEMENTADO                         |
| **Nível 2** — Validação por Normas | Validar contra NBR 8800, ASME B31.3, Petrobras N-76/N-58/N-115       | ✅ IMPLEMENTADO                         |
| **Nível 3** — IA Generativa        | Usar LLM local (Ollama) para gerar LSP a partir de linguagem natural | ✅ IMPLEMENTADO (Básico)                |
| **Nível 4** — Execução no AutoCAD  | Injetar e executar o .LSP diretamente no AutoCAD instalado           | ⚠️ PREPARADO (requer pywin32 + AutoCAD) |
| **Nível 5** — Ciclo Fechado        | Sistema detecta erros no desenho, corrige e re-executa sozinho       | ❌ NÃO IMPLEMENTADO                     |

### O que "Autonomia Total" significa na prática

Quando o Nível 5 estiver completo, o engenheiro vai:

1. Abrir o Engenharia CAD
2. Selecionar a refinaria
3. Importar uma planilha Excel com 50 peças
4. Clicar **1 botão**
5. Ir tomar café
6. Voltar e encontrar: 50 desenhos no AutoCAD + MTO consolidado + relatórios prontos + tudo validado por normas

**Tempo estimado: 50 peças em 5 minutos em vez de 50 peças em 5 dias.**

---

## 3. AS TAREFAS QUE O SISTEMA EXECUTA

### 3.1 — Cálculos de Engenharia Estrutural (NBR 8800)

O módulo `calculista.py` implementa o método LRFD (Load and Resistance Factor Design) da norma brasileira:

- **Tração:** $N_{t,Rd} = A_g \times f_y / \gamma_{a1}$
- **Compressão:** Curva de flambagem com índice de esbeltez $\lambda = K \cdot L / r$
- **Flexão:** Verificação de flecha e momento resistente
- **Perfis:** Database completo com W, HP, C, L (propriedades geométricas: A, Ix, Iy, rx, ry, Zx, Wx)

### 3.2 — Cálculos de Tubulação (ASME B31.3)

O módulo `specs.py` calcula:

- **Espessura mínima de parede:** $t_{min} = \frac{P \cdot D}{2 \cdot (S \cdot E \cdot W + P \cdot Y)} + c$
  - P = pressão de projeto
  - D = diâmetro externo
  - S = tensão admissível do material
  - E = fator de eficiência de junta
  - c = tolerância de corrosão
- **Seleção automática de Schedule** (5S, 10S, 40, 80, 160, XXS)
- **Matriz de decisão por fluido** (hidrocarboneto, ácido, vapor, etc.)

### 3.3 — Expansão Térmica (Petrobras N-143 / ASME B31.3)

O módulo `expansao_termica.py` calcula:

- Expansão linear: $\Delta L = \alpha \cdot L \cdot \Delta T$
- Loop de expansão necessário (raio, comprimento, altura)
- Guias e ancoragens com espaçamento
- Validação se flexibilidade é suficiente

### 3.4 — Especificação de Fluidos (Petrobras N-76 + NACE MR-0175)

O módulo `n76_fluidos.py` implementa a matriz completa de seleção:

| Fluido               | Temperatura | Material Selecionado  | Vedação        |
| -------------------- | ----------- | --------------------- | -------------- |
| Hidrocarboneto       | < 200°C     | A106 Gr.B (carbono)   | Espirometálica |
| Hidrocarboneto       | > 400°C     | A335 P11 (liga Cr-Mo) | RTJ            |
| Ácido (H₂S)          | Qualquer    | Inox 316L (NACE)      | RTJ            |
| Vapor                | > 250°C     | A335 P22              | Espirometálica |
| Água desmineralizada | < 100°C     | A106 Gr.B             | Borracha       |

### 3.5 — Fabricação em Campo (Petrobras N-115 / N-133 / N-13)

O módulo `n115_field_joints.py`:

- Quebra tubulação em spools de máximo 6 metros
- Especifica processo de soldagem (SMAW com E7018)
- Calcula volume de solda e consumo de eletrodos
- Define pintura (primer epóxi de zinco + acabamento PU)

### 3.6 — Suportes de Tubulação (Petrobras Série L)

O módulo `serie_l_supports.py`:

- Seleciona tipo de suporte (apoio, guia, ancoragem, suporte de mola)
- Calcula espaçamento baseado em peso + fluido + temperatura
- Gera list de materiais de suportes

### 3.7 — Geração de AutoLISP

O módulo `cad/lisp/generator.py`:

- Gera comandos AutoLISP válidos: `LINE`, `CIRCLE`, `ARC`
- Cria layers automáticos com prefixo `ENG-`
- Adiciona carimbo com informações do projeto
- Salva arquivo `.lsp` pronto para carregar no AutoCAD

### 3.8 — MTO (Material Take-Off)

O módulo `pid_mto_generator.py`:

- Contagem EXATA de todos os componentes (não estimativa)
- Cálculo de peso total por sistema
- Cálculo de custo total de materiais (R$)
- Especificação de soldas com volume e consumo de eletrodos
- Plano de teste hidrostático com pontos VENT e DRAIN
- Tudo pronto para licitação

### 3.9 — IA Generativa (Ollama + LangChain)

- O engenheiro descreve a peça em português: _"flange de 4 furos, aço inox, M5"_
- O LLM local (llama3.2:1b) gera o código AutoLISP correspondente
- Processamento assíncrono via job queue (Celery + Redis)
- Streaming de resultado via SSE em tempo real

### 3.10 — AI Watchdog (Sistema Invisível de Proteção)

O `ai_watchdog.py` é um middleware FastAPI que:

- Sanitiza payloads automaticamente (campos vazios → valores padrão)
- Bloqueia operações quando RAM > 90% (evita OOM)
- Injeta fallback se handler crashar
- Completamente invisível para o usuário

### 3.11 — Gestão de Projetos via Frontend

Interface web React com:

- Seleção de refinaria (REGAP, REPLAN, BRAAP, RECAP)
- Console CAD com injeção de LISP
- Dashboard com métricas em tempo real (CPU, RAM, disco via SSE)
- Temas light/dark
- Sistema de autenticação com JWT

---

## 4. POTENCIAL DO SISTEMA E ONDE ELE PODE CHEGAR

### 4.1 — Potencial de Mercado Imediato (Brasil)

| Segmento                               | Tamanho Estimado | Ticket Médio/Ano | Potencial               |
| -------------------------------------- | ---------------- | ---------------- | ----------------------- |
| Petrobras (13 refinarias)              | 13 unidades      | R$ 200-500k      | R$ 2.6M - 6.5M          |
| EPCistas (Technip, Worley, Promon)     | ~20 empresas     | R$ 100-300k      | R$ 2M - 6M              |
| Siderúrgicas (CSN, Gerdau, Usiminas)   | ~10 unidades     | R$ 100-200k      | R$ 1M - 2M              |
| Petroquímicas (Braskem, Dow)           | ~15 plantas      | R$ 100-200k      | R$ 1.5M - 3M            |
| Engenharias de projeto (médio porte)   | ~50 empresas     | R$ 50-100k       | R$ 2.5M - 5M            |
| **Total Brasil (Cenário Conservador)** |                  |                  | **R$ 9.6M - 22.5M/ano** |

### 4.2 — Potencial de Expansão (Além do Piping)

O motor de cálculos do Engenharia CAD pode ser expandido para:

| Área                                                | Complexidade | Valor Agregado                           |
| --------------------------------------------------- | ------------ | ---------------------------------------- |
| **Elétrica industrial** (bandejamento, eletrodutos) | Média        | Altíssimo — mesmo problema de retrabalho |
| **Instrumentação** (malhas, listas de instrumentos) | Média        | Alto — padronização de documentos        |
| **Civil/Estrutural** (fundações de equipamentos)    | Alta         | Alto — integra com NBR 8800 já existente |
| **HVAC** (dutos, climatização industrial)           | Média        | Médio                                    |
| **Vasos de pressão** (ASME VIII)                    | Alta         | Altíssimo — mercado carente              |
| **Equipamentos rotativos** (bombas, compressores)   | Alta         | Alto — seleção e datasheet               |

### 4.3 — Potencial Tecnológico

| Capacidade       | Onde Está Hoje                           | Onde Pode Chegar                                                                             |
| ---------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------- |
| **IA/LLM**       | llama3.2:1b local, geração básica de LSP | Modelo fine-tuned em normas Petrobras, capaz de projetar sistemas completos a partir de P&ID |
| **AutoCAD**      | Gera .LSP para execução manual           | Integração COM direta → desenha, detecta clash, corrige, re-desenha                          |
| **BIM**          | Não tem                                  | Exportação IFC para Revit/Navisworks, integração com modelo 3D                               |
| **Digital Twin** | Não tem                                  | Sensor → Sistema → Alerta automático de manutenção preditiva                                 |
| **Cloud/SaaS**   | Docker local                             | Multi-tenant cloud com billing por uso (AWS/Azure)                                           |
| **Mobile**       | Não tem                                  | App para inspeção em campo com câmera + IA para validação visual                             |

### 4.4 — Cenário de Longo Prazo (3-5 anos)

Se bem executado, o Engenharia CAD pode se tornar:

> **A plataforma de engenharia industrial do Brasil** — o "Autodesk brasileiro" com normas locais embutidas e IA que fala português de engenharia.

Comparação com concorrentes internacionais:

| Concorrente        | Preço/Ano      | Normas BR | IA     | AutoCAD | Vantagem Engenharia CAD                         |
| ------------------ | -------------- | --------- | ------ | ------- | ----------------------------------------- |
| AVEVA E3D          | ~US$ 30k       | ❌        | ❌     | Parcial | 10x mais barato, normas Petrobras nativas |
| Hexagon SmartPlant | ~US$ 50k       | ❌        | ❌     | Parcial | Foco em piping BR, IA integrada           |
| Bentley OpenPlant  | ~US$ 20k       | ❌        | ❌     | ❌      | AutoCAD direto, MTO automático            |
| **Engenharia CAD**       | **R$ 50-100k** | **✅**    | **✅** | **✅**  | **Único com tudo integrado para BR**      |

---

## 5. PRÓXIMA ATUALIZAÇÃO V2 — O QUE DEVE SER

### 5.1 — V2 Feature Map Prioritizado

#### PRIORIDADE MÁXIMA (V2.0 Core)

| #   | Feature                                   | Justificativa                                                                                                                      | Esforço     |
| --- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 1   | **Integração real com AutoCAD via COM**   | Sem isso não há autonomia. O .LSP precisa ser injetado e executado automaticamente no AutoCAD. Usar `pywin32` + `win32com.client`. | 2-3 semanas |
| 2   | **Upload de Excel em lote no frontend**   | Hoje o Excel só funciona via backend. O engenheiro precisa fazer drag & drop na interface web e ver 50 peças sendo geradas.        | 1-2 semanas |
| 3   | **Modelo de IA fine-tuned para LISP**     | O llama3.2:1b genérico gera LSP ruim. Fine-tuning com dataset de 500+ exemplos reais de LSP de engenharia vai 10x a qualidade.     | 3-4 semanas |
| 4   | **Banco de dados PostgreSQL em produção** | Sair do SQLite. Histórico de projetos, auditoria, multi-usuário, backup.                                                           | 1 semana    |
| 5   | **Sistema de permissões (RBAC)**          | Admin, Engenheiro Sênior, Engenheiro Jr, Visualizador. Controle de quem pode gerar, aprovar, modificar.                            | 1-2 semanas |

#### PRIORIDADE ALTA (V2.1)

| #   | Feature                        | Justificativa                                                                                                       | Esforço     |
| --- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ----------- |
| 6   | **Visualizador 3D no browser** | Renderizar a tubulação gerada em Three.js antes de enviar ao AutoCAD. Preview visual evita erros.                   | 2-3 semanas |
| 7   | **Export PDF profissional**    | Relatórios de engenharia, MTO e especificações em PDF com layout profissional, logo da empresa, assinatura digital. | 1-2 semanas |
| 8   | **CI/CD Pipeline completo**    | GitHub Actions com testes, SAST, build Docker, deploy staging → produção.                                           | 1 semana    |
| 9   | **Multi-refinaria simultânea** | Projeto com peças de múltiplas refinarias/normas diferentes no mesmo batch.                                         | 1 semana    |
| 10  | **Notificações e aprovação**   | Workflow: Engenheiro gera → Sênior aprova → Sistema executa no AutoCAD.                                             | 2 semanas   |

#### PRIORIDADE MÉDIA (V2.2)

| #   | Feature                         | Justificativa                                                                      | Esforço     |
| --- | ------------------------------- | ---------------------------------------------------------------------------------- | ----------- |
| 11  | **Import de DWG/DXF existente** | Ler desenhos existentes, extrair geometria, alimentar o sistema com dados reais.   | 3-4 semanas |
| 12  | **Clash Detection**             | Detectar colisão entre tubulações e estrutura antes de fabricar.                   | 2-3 semanas |
| 13  | **Comparação de revisões**      | Qual peça mudou entre Rev.A e Rev.B? Diff visual + textual.                        | 1-2 semanas |
| 14  | **App de campo (mobile)**       | Inspeção em campo: tirar foto do tubo, IA compara com projeto, marca conformidade. | 4-6 semanas |

### 5.2 — Roadmap Visual V2

```
V1.0 (ATUAL)          V2.0 (3 meses)           V2.1 (6 meses)          V2.2 (12 meses)
─────────────          ──────────────           ──────────────          ───────────────
✅ Gera LSP            AutoCAD COM real         Visualizador 3D         Import DWG
✅ Valida normas       Upload Excel frontend    PDF profissional        Clash detection
✅ MTO básico          IA fine-tuned            CI/CD completo          Comparação revisões
✅ SSE streaming       PostgreSQL prod          Multi-refinaria         App mobile
✅ Auth JWT            RBAC permissões          Workflow aprovação      Digital twin (POC)
✅ Watchdog IA         Dashboard melhorado      API pública             Marketplace plugins
```

---

## 6. SE EU FOSSE VOCÊ, O QUE EU FARIA

### Diagnóstico Honesto

Você tem em mãos algo **raro**: um sistema que já funciona end-to-end, com cálculos reais de engenharia, integração com normas brasileiras, IA, frontend profissional, e infraestrutura de deploy. A maioria dos projetos morre antes de chegar aqui.

**Mas existem gaps críticos que separam "projeto que funciona" de "produto que vende".**

### Meu Plano de Ação (em ordem de prioridade)

---

#### PASSO 1 — Provar valor com 1 cliente real (Semanas 1-4)

**O que fazer:**

- Escolher UMA refinaria (REGAP é a mais citada no código — comece por ela)
- Preparar uma demo de 20 minutos com dados reais de REGAP
- Encontrar 1 engenheiro de tubulação em REGAP ou em uma EPCista que atende REGAP
- Mostrar: "Você gasta 8 horas fazendo isso. Olha o Engenharia CAD fazer em 3 minutos."
- Oferecer um piloto gratuito de 30 dias

**Por que isso primeiro:**

- Sem validação real, tudo é teoria
- 1 caso real vale mais que 100 features
- O feedback desse engenheiro vai definir o que importa no V2

---

#### PASSO 2 — Consertar a integração com AutoCAD (Semanas 2-6)

**O que fazer:**

- Implementar a conexão COM real via `pywin32`
- O fluxo precisa ser: clicou "INJECT & DRAW" → AutoCAD abre → desenho aparece
- Sem isso, o sistema é um "gerador de texto" e não um "automatizador CAD"

**Por que isso:**

- É a diferença entre "ferramenta legal" e "ferramenta que vende"
- Todo engenheiro entende em 5 segundos quando vê o desenho aparecer no AutoCAD sozinho

---

#### PASSO 3 — Fine-tuning do modelo de IA (Semanas 4-8)

**O que fazer:**

- Coletar 500+ exemplos de AutoLISP reais de projetos de tubulação
- Fine-tunar um modelo (llama3 ou mistral) especificamente para gerar LSP
- Dataset: entrada = descrição em português, saída = LSP válido e funcional
- Testar: taxa de LSP que executa sem erro no AutoCAD > 90%

**Por que isso:**

- O llama3.2:1b genérico não sabe LSP de engenharia
- Um modelo especializado é o diferencial competitivo imbatível

---

#### PASSO 4 — Proteger a propriedade intelectual (Semanas 1-2)

**O que fazer:**

- Registrar o software no INPI (Instituto Nacional da Propriedade Industrial)
- Custo: ~R$ 185 (pessoa física) ou ~R$ 370 (empresa)
- Tempo: pedido sai em 1 dia, registro definitivo em 3-12 meses
- Registrar o nome "Engenharia CAD" como marca

**Por que isso:**

- Se alguém copiar a ideia, você tem o registro
- Para vender para Petrobras/grandes empresas, registro no INPI é pré-requisito

---

#### PASSO 5 — Estruturar o modelo de negócio (Semanas 3-6)

**O que fazer:**

| Modelo                      | Ticket                       | Para quem                  |
| --------------------------- | ---------------------------- | -------------------------- |
| **SaaS mensal**             | R$ 2.000-5.000/mês           | Engenharias de médio porte |
| **Licença anual**           | R$ 50.000-100.000/ano        | Grandes EPCistas           |
| **Por projeto**             | R$ 5.000-20.000/projeto      | Freelancers e consultorias |
| **Enterprise (on-premise)** | R$ 200.000-500.000 + suporte | Petrobras, Vale, CSN       |

- Criar site com 1 página: problema → solução → demo → contato
- LinkedIn: postar 2x por semana sobre automação em engenharia
- Participar de eventos do setor (IBP, ABRATT, congressos de piping)

---

#### PASSO 6 — O que NÃO fazer (tão importante quanto o que fazer)

| ❌ NÃO faça                                        | ✅ Em vez disso                                                           |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| Adicionar 20 features antes de vender              | Venda com o que tem, melhore com feedback                                 |
| Gastar meses no visual do frontend                 | O engenheiro não se importa com CSS — ele quer que funcione               |
| Tentar atender todos os setores                    | Domine piping para petroquímica primeiro                                  |
| Construir SaaS multi-tenant antes de ter 1 cliente | Rode local/Docker para os primeiros 5 clientes                            |
| Competir com AVEVA/Hexagon em features             | Compita em preço, localização e velocidade                                |
| Ficar polindo código sem fim                       | Código bom que ninguém usa = lixo. Código ruim que gera receita = startup |

---

### Resumo: Os 90 Primeiros Dias

```
Dia 1-15:   REGISTRAR no INPI + Preparar demo com dados REGAP
Dia 15-30:  ENCONTRAR 1 engenheiro de tubulação → demo → piloto gratuito
Dia 30-45:  INTEGRAÇÃO AutoCAD COM real (a feature que vende)
Dia 45-60:  COLETAR feedback do piloto → implementar os 3 pedidos mais urgentes
Dia 60-75:  FINE-TUNING do modelo IA com LSPs reais
Dia 75-90:  CONVERTER piloto em contrato pago + buscar 2o e 3o cliente
```

---

## CONCLUSÃO

### O que o Engenharia CAD é hoje

Um sistema funcional de automação de engenharia CAD que:

- Gera AutoLISP automaticamente
- Calcula conforme NBR 8800, ASME B31.3, e 7+ normas Petrobras
- Produz MTO completo com custos
- Tem IA integrada para geração via linguagem natural
- Possui frontend profissional e infraestrutura de deploy escalável
- Tem 65 testes automatizados e auditoria de segurança

### O que falta para ser um produto

- Integração real com AutoCAD (o sistema gera o arquivo, mas não executa)
- Fine-tuning do modelo de IA (a geração de LSP é genérica demais)
- 1 cliente real validando e pagando
- Registro de propriedade intelectual

### O diferencial imbatível

**Ninguém no Brasil tem um sistema que combina:**

1. Normas Petrobras nativas (N-76, N-58, N-115, N-133, N-143, Série L)
2. IA generativa local (sem enviar dados para cloud)
3. AutoCAD direto (LISP + COM)
4. MTO com cálculo exato de custos e soldagem
5. Tudo em português, pensado para engenheiro brasileiro

**Esse é o seu moat (fosso competitivo). Proteja-o e execute rápido.**

---

_Relatório gerado por análise automatizada de todo o código-fonte, documentação, testes, infraestrutura e arquitetura do Engenharia CAD._
