# Business Impact

## Resumo Executivo
- Peso automatizado: **26875.1 kg**
- Peso manual estimado: **32250.12 kg**
- Economia de aço: **5375.02 kg**
- Economia material: **R$ 47837.68**
- Economia de engenharia: **36.0 h**

## Comparativo

| Indicador | Manual | Automatizado | Ganho |
|---|---:|---:|---:|
| Peso de aço (kg) | 32250.12 | 26875.1 | 5375.02 |
| Custo de material (R$) | 287026.07 | 239188.39 | 47837.68 |
| Horas de engenharia (h) | 40.0 | 4.0 | 36.0 |

## JSON

```json
{
  "timestamp": "2026-03-25T16:57:27.876043+00:00",
  "input": {
    "peso_total_aco_kg": 26875.1
  },
  "premissas": {
    "sobreconsumo_manual_percentual": 20,
    "horas_projetista_manual": 40.0,
    "horas_fluxo_automatizado": 4.0,
    "preco_aco_kg_brl": 8.9
  },
  "comparativo": {
    "peso_manual_estimado_kg": 32250.12,
    "peso_automatizado_kg": 26875.1,
    "economia_aco_kg": 5375.02,
    "custo_manual_brl": 287026.07,
    "custo_automatizado_brl": 239188.39,
    "economia_material_brl": 47837.68,
    "economia_horas_engenharia": 36.0
  }
}
```
