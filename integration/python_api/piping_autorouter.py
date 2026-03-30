from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .base_generator import BasePetrobrasGenerator
from .compliance_loader import get_rule_param


def _distance_3d(a: dict[str, float], b: dict[str, float]) -> float:
    dx = float(b["x"] - a["x"])
    dy = float(b["y"] - a["y"])
    dz = float(b["z"] - a["z"])
    return (dx * dx + dy * dy + dz * dz) ** 0.5


class PipingAutoRouter(BasePetrobrasGenerator):
    disciplina = "piping"

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _route_points(self, ponto_a: dict[str, float], ponto_b: dict[str, float]) -> list[dict[str, float]]:
        # Traçado relâmpago ortogonal (A -> joelho 1 -> joelho 2 -> B).
        p1 = {"x": float(ponto_b["x"]), "y": float(ponto_a["y"]), "z": float(ponto_a["z"])}
        p2 = {"x": float(ponto_b["x"]), "y": float(ponto_b["y"]), "z": float(ponto_a["z"])}
        return [ponto_a, p1, p2, ponto_b]

    def generate(
        self,
        ponto_a: dict[str, float],
        ponto_b: dict[str, float],
        diametro_nominal_mm: float,
        material: str,
        schedule: str,
    ) -> dict[str, Any]:
        spacing_m = float(get_rule_param("N-1810", "routing.support_max_spacing_m", 3.0))
        clearance_mm = float(get_rule_param("N-1810", "routing.min_clearance_to_structure_mm", 150))

        points = self._route_points(ponto_a, ponto_b)
        segments = []
        total_len_m = 0.0
        for idx in range(len(points) - 1):
            seg_len_m = _distance_3d(points[idx], points[idx + 1]) / 1000.0
            total_len_m += seg_len_m
            segments.append(
                {
                    "id": f"SEG-{idx+1}",
                    "start": points[idx],
                    "end": points[idx + 1],
                    "length_m": round(seg_len_m, 3),
                }
            )

        support_count = max(2, int(total_len_m // spacing_m) + 1)
        supports = []
        support_pitch_m = total_len_m / max(1, support_count - 1)
        for i in range(support_count):
            supports.append(
                {
                    "id": f"SUP-{i+1}",
                    "type": "PIPE_SHOE",
                    "position_m": round(i * support_pitch_m, 3),
                    "norma": "N-1810",
                }
            )

        elbows_qty = max(0, len(points) - 2)
        bom = [
            {
                "item": "PIPE_STRAIGHT",
                "descricao": "Trecho total roteado automaticamente",
                "quantidade": 1,
                "comprimento_total_m": round(total_len_m, 3),
                "dn_mm": round(float(diametro_nominal_mm), 1),
                "material": material,
                "schedule": schedule,
            },
            {
                "item": "ELBOW_90",
                "descricao": "Curvas do auto-router",
                "quantidade": elbows_qty,
                "dn_mm": round(float(diametro_nominal_mm), 1),
                "material": material,
                "schedule": schedule,
            },
            {
                "item": "PIPE_SUPPORT",
                "descricao": "Suportes calculados por espaçamento de norma",
                "quantidade": support_count,
                "norma": "N-1810",
            },
        ]

        # Bounding boxes simplificados para detecção preliminar de interferência.
        components = [
            {
                "id": seg["id"],
                "origin": seg["start"],
                "size": {
                    "dx": abs(seg["end"]["x"] - seg["start"]["x"]) or float(diametro_nominal_mm),
                    "dy": abs(seg["end"]["y"] - seg["start"]["y"]) or float(diametro_nominal_mm),
                    "dz": abs(seg["end"]["z"] - seg["start"]["z"]) or float(diametro_nominal_mm),
                },
            }
            for seg in segments
        ]
        interference = self.detect_interferences(components, clearance_mm=clearance_mm)

        payload = {
            "header": {
                "modulo": "piping_autorouter_1_0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": f"PIPE-{uuid4().hex[:10]}",
                "normas": ["N-1810"],
            },
            "entrada": {
                "ponto_a": ponto_a,
                "ponto_b": ponto_b,
                "diametro_nominal_mm": diametro_nominal_mm,
                "material": material,
                "schedule": schedule,
            },
            "routing": {
                "points": points,
                "segments": segments,
                "comprimento_total_m": round(total_len_m, 3),
                "supports": supports,
            },
            "bom": bom,
            "interference": interference,
        }

        target_dir = self.output_dir / "piping"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"autorouter_{payload['header']['trace_id']}.json"
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "ok",
            "artifact": str(file_path),
            "payload": payload,
        }
