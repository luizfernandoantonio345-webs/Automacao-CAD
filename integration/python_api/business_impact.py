from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def gerar_business_impact(peso_total_aco_kg: float, output_dir: Path) -> dict[str, Any]:
    if peso_total_aco_kg <= 0:
        raise ValueError("peso_total_aco_kg deve ser maior que zero")

    # Premissas solicitadas: manual usa 20% mais aço e consome 40h.
    peso_manual_kg = round(peso_total_aco_kg * 1.20, 2)
    economia_aco_kg = round(peso_manual_kg - peso_total_aco_kg, 2)

    horas_manual = 40.0
    horas_automacao = 4.0
    economia_horas = round(horas_manual - horas_automacao, 2)

    preco_aco_kg_brl = 8.90
    custo_manual_brl = round(peso_manual_kg * preco_aco_kg_brl, 2)
    custo_automacao_brl = round(peso_total_aco_kg * preco_aco_kg_brl, 2)
    economia_material_brl = round(custo_manual_brl - custo_automacao_brl, 2)

    resumo = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": {"peso_total_aco_kg": round(peso_total_aco_kg, 2)},
        "premissas": {
            "sobreconsumo_manual_percentual": 20,
            "horas_projetista_manual": horas_manual,
            "horas_fluxo_automatizado": horas_automacao,
            "preco_aco_kg_brl": preco_aco_kg_brl,
        },
        "comparativo": {
            "peso_manual_estimado_kg": peso_manual_kg,
            "peso_automatizado_kg": round(peso_total_aco_kg, 2),
            "economia_aco_kg": economia_aco_kg,
            "custo_manual_brl": custo_manual_brl,
            "custo_automatizado_brl": custo_automacao_brl,
            "economia_material_brl": economia_material_brl,
            "economia_horas_engenharia": economia_horas,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "business_impact.json"
    md_path = output_dir / "business_impact.md"

    json_path.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    md_content = (
        "# Business Impact\n\n"
        "## Resumo Executivo\n"
        f"- Peso automatizado: **{resumo['comparativo']['peso_automatizado_kg']} kg**\n"
        f"- Peso manual estimado: **{resumo['comparativo']['peso_manual_estimado_kg']} kg**\n"
        f"- Economia de aço: **{resumo['comparativo']['economia_aco_kg']} kg**\n"
        f"- Economia material: **R$ {resumo['comparativo']['economia_material_brl']}**\n"
        f"- Economia de engenharia: **{resumo['comparativo']['economia_horas_engenharia']} h**\n\n"
        "## Comparativo\n\n"
        "| Indicador | Manual | Automatizado | Ganho |\n"
        "|---|---:|---:|---:|\n"
        f"| Peso de aço (kg) | {resumo['comparativo']['peso_manual_estimado_kg']} | {resumo['comparativo']['peso_automatizado_kg']} | {resumo['comparativo']['economia_aco_kg']} |\n"
        f"| Custo de material (R$) | {resumo['comparativo']['custo_manual_brl']} | {resumo['comparativo']['custo_automatizado_brl']} | {resumo['comparativo']['economia_material_brl']} |\n"
        f"| Horas de engenharia (h) | {horas_manual} | {horas_automacao} | {resumo['comparativo']['economia_horas_engenharia']} |\n\n"
        "## JSON\n\n"
        "```json\n"
        f"{json.dumps(resumo, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )
    md_path.write_text(md_content, encoding="utf-8")

    return {
        "status": "ok",
        "json_artifact": str(json_path),
        "markdown_artifact": str(md_path),
        "report": resumo,
    }
