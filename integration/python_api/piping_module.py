from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _peso_tubo_kg_m(diametro_mm: float) -> float:
    tabela = {
        25: 1.7,
        50: 3.6,
        80: 6.0,
        100: 8.6,
        150: 15.0,
        200: 23.7,
    }
    diametros = sorted(tabela.keys())
    if diametro_mm <= diametros[0]:
        return tabela[diametros[0]]
    if diametro_mm >= diametros[-1]:
        return tabela[diametros[-1]]
    for i in range(len(diametros) - 1):
        d0, d1 = diametros[i], diametros[i + 1]
        if d0 <= diametro_mm <= d1:
            p0, p1 = tabela[d0], tabela[d1]
            fator = (diametro_mm - d0) / (d1 - d0)
            return round(p0 + (p1 - p0) * fator, 3)
    return 8.6


def gerar_bom_linha_reta_duas_curvas(
    comprimento_reto_m: float,
    diametro_nominal_mm: float,
    output_dir: Path,
    material: str = "ASTM A106 Gr.B",
    schedule: str = "STD",
) -> dict[str, Any]:
    if comprimento_reto_m <= 0:
        raise ValueError("comprimento_reto_m deve ser maior que zero")
    if diametro_nominal_mm <= 0:
        raise ValueError("diametro_nominal_mm deve ser maior que zero")

    peso_tubo = _peso_tubo_kg_m(diametro_nominal_mm)
    peso_trecho_reto = round(comprimento_reto_m * peso_tubo, 2)
    peso_curvas = round(2 * (peso_tubo * 0.45), 2)

    bom = [
        {
            "item": "PIPE_STRAIGHT",
            "descricao": "Tubo reto principal",
            "quantidade": 1,
            "comprimento_m": round(comprimento_reto_m, 3),
            "dn_mm": round(diametro_nominal_mm, 1),
            "material": material,
            "schedule": schedule,
            "massa_total_kg": peso_trecho_reto,
        },
        {
            "item": "ELBOW_90",
            "descricao": "Curva 90 graus raio longo",
            "quantidade": 2,
            "dn_mm": round(diametro_nominal_mm, 1),
            "material": material,
            "schedule": schedule,
            "massa_total_kg": peso_curvas,
        },
        {
            "item": "WELD_BUTT",
            "descricao": "Solda de topo para montagem do isométrico",
            "quantidade": 4,
            "massa_total_kg": 0.0,
        },
    ]

    output = {
        "header": {
            "modulo": "tubulacao_isometrico",
            "subtipo": "linha_reta_2_curvas",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versao": "0.1.0_BOOTSTRAP",
        },
        "entrada": {
            "comprimento_reto_m": round(comprimento_reto_m, 3),
            "diametro_nominal_mm": round(diametro_nominal_mm, 1),
            "material": material,
            "schedule": schedule,
        },
        "geometria_base": {
            "descricao": "Trecho reto com duas curvas de 90 graus",
            "pontos_3d": [
                {"x": 0, "y": 0, "z": 0},
                {"x": round(comprimento_reto_m * 1000, 2), "y": 0, "z": 0},
                {"x": round(comprimento_reto_m * 1000, 2), "y": 500, "z": 0},
                {"x": round(comprimento_reto_m * 1000, 2), "y": 500, "z": 500},
            ],
        },
        "bom": bom,
        "resumo": {
            "itens": len(bom),
            "peso_total_estimado_kg": round(sum(item["massa_total_kg"] for item in bom), 2),
            "isometrico_pronto": True,
        },
    }

    target_dir = output_dir / "piping"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / "bom_linha_reta_2_curvas.json"
    file_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "artifact": str(file_path),
        "payload": output,
    }
