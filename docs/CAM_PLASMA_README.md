# Módulo CAM - Corte Plasma CNC

## Visão Geral

O módulo CAM (Computer Aided Manufacturing) do Engenharia CAD fornece funcionalidades profissionais para geração de G-code otimizado para máquinas CNC de corte plasma.

## Características Principais

### 🎯 Funcionalidades

- **Import de Geometria**: Suporte a arquivos DXF e SVG
- **Configuração de Material**: Parâmetros pré-definidos para diversos materiais
- **Geração de Toolpath**: Caminhos de corte otimizados
- **G-code Profissional**: Compatível com Mach3, LinuxCNC, Plasma Edge
- **Preview Visual**: Visualização do corte antes da geração

### ⚙️ Otimizações Industriais

1. **Compensação de Kerf**
   - Ajuste automático do caminho considerando a largura do corte
   - Configurável por material e espessura

2. **Lead-in / Lead-out**
   - Entrada e saída suave do corte
   - Tipos: Arco (recomendado) ou Linear
   - Evita marcas na peça

3. **Sequenciamento Inteligente**
   - Cortes internos (furos) primeiro
   - Contornos externos por último
   - Minimiza deformação por calor

4. **Minimização de Deslocamento**
   - Algoritmo nearest-neighbor
   - Reduz tempo de máquina

5. **Controle de Altura (THC)**
   - Suporte a Torch Height Control
   - Tensão do arco configurável

## Estrutura de Arquivos

```
cam/
├── __init__.py              # Exports do módulo
├── geometry_parser.py       # Parser de DXF/SVG
├── toolpath_generator.py    # Gerador de toolpaths
├── gcode_generator.py       # Gerador de G-code
├── plasma_optimizer.py      # Otimizações de corte
└── routes.py                # API REST endpoints
```

## Materiais Suportados

| Material | Espessura | Amperagem | Velocidade | Kerf |
|----------|-----------|-----------|------------|------|
| Aço Carbono | 3mm | 30A | 3500 mm/min | 1.0mm |
| Aço Carbono | 6mm | 45A | 2000 mm/min | 1.5mm |
| Aço Carbono | 12mm | 80A | 900 mm/min | 2.0mm |
| Aço Inox | 6mm | 60A | 1600 mm/min | 1.8mm |
| Alumínio | 6mm | 65A | 2500 mm/min | 2.0mm |

## API Endpoints

### POST /api/cam/parse
Faz parse de um arquivo DXF ou SVG.

**Request**: `multipart/form-data` com campo `file`

**Response**:
```json
{
  "success": true,
  "geometry": {...},
  "stats": {
    "lines": 10,
    "circles": 2,
    "polylines": 5,
    "totalLength": 1234.5
  },
  "boundingBox": {
    "min": {"x": 0, "y": 0},
    "max": {"x": 500, "y": 300}
  }
}
```

### POST /api/cam/generate
Gera G-code a partir de geometria e configuração.

**Request**:
```json
{
  "geometry": {
    "lines": [...],
    "circles": [...],
    "polylines": [...]
  },
  "config": {
    "material": "mild_steel",
    "thickness": 6,
    "amperage": 45,
    "cuttingSpeed": 2000,
    "kerfWidth": 1.5,
    "leadInLength": 3.0,
    "leadOutLength": 2.0,
    "leadType": "arc",
    "thcEnabled": true
  }
}
```

**Response**:
```json
{
  "success": true,
  "code": "G21\nG90\n...",
  "stats": {
    "totalCuts": 5,
    "cuttingLength": 628.3,
    "rapidLength": 150.0,
    "estimatedTime": 180,
    "internalContours": 2,
    "externalContours": 3
  },
  "warnings": []
}
```

### GET /api/cam/materials
Lista materiais disponíveis com parâmetros recomendados.

## Fluxo de Uso

1. **Importar Desenho**
   - Acesse a tela "Controle CNC Plasma"
   - Faça upload de um arquivo DXF ou SVG

2. **Configurar Corte**
   - Selecione o material
   - Defina a espessura
   - Ajuste parâmetros avançados se necessário

3. **Gerar G-code**
   - Clique em "Gerar G-Code"
   - Visualize o preview e o código

4. **Baixar Arquivo**
   - Escolha o formato (.nc, .tap, .gcode)
   - Transfira para a máquina CNC via pen drive

## Compatibilidade

### Máquinas Suportadas
- Plasma Edge
- Hypertherm
- Mach3 / Mach4
- LinuxCNC
- UCCNC

### Formatos de Arquivo
- **Entrada**: DXF (AutoCAD), SVG
- **Saída**: .nc, .tap, .gcode

## Comandos G-code Utilizados

| Código | Descrição |
|--------|-----------|
| G00 | Movimento rápido (sem corte) |
| G01 | Movimento linear (corte) |
| G02 | Arco horário |
| G03 | Arco anti-horário |
| G04 | Pausa (pierce delay) |
| G17 | Plano XY |
| G21 | Unidades em milímetros |
| G54 | Sistema de coordenadas da peça |
| G90 | Coordenadas absolutas |
| M02 | Fim do programa |
| M03 | Ligar plasma |
| M05 | Desligar plasma |

## Dicas de Uso

### Para Melhor Qualidade de Corte

1. **Use lead-in em arco** para espessuras acima de 8mm
2. **Habilite THC** para materiais acima de 3mm
3. **Aumente o pierce delay** para materiais mais espessos
4. **Verifique a compensação de kerf** na tabela de corte da sua máquina

### Para Menor Tempo de Máquina

1. O sistema já otimiza a ordem de corte automaticamente
2. Agrupe peças similares no mesmo arquivo
3. Minimize espaço entre peças (respeitando o kerf)

## Suporte

Para dúvidas ou problemas:
- Verifique os warnings retornados pelo sistema
- Consulte a documentação da sua máquina CNC
- Entre em contato com o suporte técnico

---

**Versão**: 1.0.0  
**Desenvolvido por**: Engenharia CAD
