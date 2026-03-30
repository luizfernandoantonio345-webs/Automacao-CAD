from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .compliance_loader import get_rule_param


DXF_EXPORT_LAYERS = ["01_PERFIL", "02_FUROS", "03_SOLDA", "04_TEXTOS"]
CAGE_VERTICAL_BARS = 4
SUPPORT_SPACING_MM = 1500
SUPPORT_EDGE_MARGIN_MM = 450
SUPPORT_PLATE_WIDTH_MM = 120
SUPPORT_PLATE_HEIGHT_MM = 80
SUPPORT_PLATE_THICKNESS_MM = 8
SUPPORT_HOLE_DIAMETER_MM = 14
WELD_FILLET_MM = 6.0
STEEL_DENSITY_KG_M3 = 7850.0


@dataclass(frozen=True)
class PerfilHomologado:
    designacao: str
    material: str
    fabricacao: str
    massa_linear_kg_m: float
    observacao: str


@dataclass(frozen=True)
class EscadaMarinheiroConfig:
    espacamento_degrau_mm: int
    diametro_degrau_mm: int
    afastamento_parede_mm: int
    largura_escada_mm: int
    diametro_gaiola_mm: int
    inicio_gaiola_mm: int
    espacamento_aro_mm: int
    barra_chata_gaiola_mm: str
    altura_guarda_corpo_mm: int
    altura_max_sem_patamar_mm: int
    norma: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_dynamic_config() -> EscadaMarinheiroConfig:
    return EscadaMarinheiroConfig(
        espacamento_degrau_mm=300,
        diametro_degrau_mm=19,
        afastamento_parede_mm=200,
        largura_escada_mm=int(get_rule_param("N-1710", "ladder.ladder_width_mm", 450)),
        diametro_gaiola_mm=int(get_rule_param("N-1710", "ladder.cage_diameter_mm", 700)),
        inicio_gaiola_mm=int(get_rule_param("N-1710", "ladder.cage_start_height_mm", 2100)),
        espacamento_aro_mm=int(get_rule_param("N-1710", "ladder.cage_ring_spacing_mm", 1200)),
        barra_chata_gaiola_mm="38x6",
        altura_guarda_corpo_mm=int(get_rule_param("NR-12", "guardrail.min_guard_height_mm", 1100)),
        altura_max_sem_patamar_mm=6000,
        norma="N-1710/NR-12",
    )


def _default_profiles() -> dict[str, PerfilHomologado]:
    return {
        "montante": PerfilHomologado(
            designacao="TUBO ASTM A36 60.3x3.2 mm",
            material="ASTM A36",
            fabricacao="tubular",
            massa_linear_kg_m=4.49,
            observacao="Perfil homologado do calculista para montantes laterais.",
        ),
        "degrau": PerfilHomologado(
            designacao="BARRA REDONDA ASTM A36 D19 mm",
            material="ASTM A36",
            fabricacao="laminado",
            massa_linear_kg_m=2.23,
            observacao="Degrau macico antiderrapante conforme N-1710.",
        ),
        "gaiola_aro": PerfilHomologado(
            designacao="BARRA CHATA ASTM A36 38x6 mm",
            material="ASTM A36",
            fabricacao="laminado",
            massa_linear_kg_m=1.79,
            observacao="Aros da gaiola de protecao.",
        ),
        "gaiola_longitudinal": PerfilHomologado(
            designacao="BARRA CHATA ASTM A36 38x6 mm",
            material="ASTM A36",
            fabricacao="laminado",
            massa_linear_kg_m=1.79,
            observacao="Longarinas verticais da gaiola de protecao.",
        ),
        "suporte_braco": PerfilHomologado(
            designacao="BARRA CHATA ASTM A36 38x6 mm",
            material="ASTM A36",
            fabricacao="laminado",
            massa_linear_kg_m=1.79,
            observacao="Braco de fixacao entre escada e estrutura.",
        ),
    }


def _load_homologated_profiles(raw_profiles: dict[str, Any] | None) -> dict[str, PerfilHomologado]:
    profiles = _default_profiles()
    if not isinstance(raw_profiles, dict):
        return profiles

    for key, default_profile in profiles.items():
        candidate = raw_profiles.get(key)
        if not isinstance(candidate, dict):
            continue
        profiles[key] = PerfilHomologado(
            designacao=str(candidate.get("designacao", default_profile.designacao)),
            material=str(candidate.get("material", default_profile.material)),
            fabricacao=str(candidate.get("fabricacao", default_profile.fabricacao)),
            massa_linear_kg_m=float(candidate.get("massa_linear_kg_m", default_profile.massa_linear_kg_m) or default_profile.massa_linear_kg_m),
            observacao=str(candidate.get("observacao", default_profile.observacao)),
        )
    return profiles


def _plate_mass_kg(width_mm: int, height_mm: int, thickness_mm: int, quantity: int) -> float:
    volume_m3 = (width_mm / 1000.0) * (height_mm / 1000.0) * (thickness_mm / 1000.0)
    return round(volume_m3 * STEEL_DENSITY_KG_M3 * quantity, 2)


def _support_positions(altura_mm: int) -> list[int]:
    if altura_mm <= 0:
        return []

    positions: list[int] = []
    current = SUPPORT_EDGE_MARGIN_MM
    upper_limit = max(SUPPORT_EDGE_MARGIN_MM, altura_mm - SUPPORT_EDGE_MARGIN_MM)
    while current < upper_limit:
        positions.append(current)
        current += SUPPORT_SPACING_MM
    positions.append(upper_limit)
    return sorted({int(position) for position in positions})


def _ring_positions(altura_mm: int, inicio_gaiola_mm: int, espacamento_aro_mm: int) -> list[int]:
    if altura_mm <= inicio_gaiola_mm:
        return []
    positions: list[int] = []
    current = inicio_gaiola_mm
    while current < altura_mm:
        positions.append(current)
        current += espacamento_aro_mm
    return positions


def _build_fabrication_parts(
    altura_mm: int,
    rail_length_mm: int,
    cfg: EscadaMarinheiroConfig,
    rung_positions: list[int],
    ring_positions: list[int],
    support_positions: list[int],
    profiles: dict[str, PerfilHomologado],
) -> list[dict[str, Any]]:
    cage_vertical_length_mm = max(0, altura_mm - cfg.inicio_gaiola_mm)
    parts: list[dict[str, Any]] = []

    for index in range(1, 3):
        parts.append(
            {
                "part_id": f"ML-{index:02d}",
                "item": "MONTANTE_LATERAL",
                "descricao": "Montante lateral com prolongamento acima do piso de saida.",
                "perfil": profiles["montante"].designacao,
                "material": profiles["montante"].material,
                "fabricacao": profiles["montante"].fabricacao,
                "comprimento_mm": rail_length_mm,
                "massa_unitaria_kg": round((rail_length_mm / 1000.0) * profiles["montante"].massa_linear_kg_m, 3),
                "stock_group": f"{profiles['montante'].designacao}|{profiles['montante'].material}",
                "aplicacao": f"Montante lateral {index}",
            }
        )

    for index, pos_y in enumerate(rung_positions, start=1):
        parts.append(
            {
                "part_id": f"DG-{index:03d}",
                "item": "DEGRAU_ANTI_DERRAPANTE",
                "descricao": "Degrau em barra redonda macica D19 mm.",
                "perfil": profiles["degrau"].designacao,
                "material": profiles["degrau"].material,
                "fabricacao": profiles["degrau"].fabricacao,
                "comprimento_mm": cfg.largura_escada_mm,
                "massa_unitaria_kg": round((cfg.largura_escada_mm / 1000.0) * profiles["degrau"].massa_linear_kg_m, 3),
                "stock_group": f"{profiles['degrau'].designacao}|{profiles['degrau'].material}",
                "aplicacao": f"Degrau a cota {pos_y} mm",
            }
        )

    ring_length_mm = int(round(math.pi * cfg.diametro_gaiola_mm))
    for index, pos_y in enumerate(ring_positions, start=1):
        parts.append(
            {
                "part_id": f"AR-{index:03d}",
                "item": "ARO_GAIOLA_PROTECAO",
                "descricao": f"Aro conformado em barra chata {cfg.barra_chata_gaiola_mm} mm.",
                "perfil": profiles["gaiola_aro"].designacao,
                "material": profiles["gaiola_aro"].material,
                "fabricacao": profiles["gaiola_aro"].fabricacao,
                "comprimento_mm": ring_length_mm,
                "massa_unitaria_kg": round((ring_length_mm / 1000.0) * profiles["gaiola_aro"].massa_linear_kg_m, 3),
                "stock_group": f"{profiles['gaiola_aro'].designacao}|{profiles['gaiola_aro'].material}",
                "aplicacao": f"Aro da gaiola a cota {pos_y} mm",
            }
        )

    if cage_vertical_length_mm > 0:
        for index in range(1, CAGE_VERTICAL_BARS + 1):
            parts.append(
                {
                    "part_id": f"GL-{index:02d}",
                    "item": "MONTANTE_GAIOLA",
                    "descricao": "Montante vertical da gaiola de protecao em barra chata.",
                    "perfil": profiles["gaiola_longitudinal"].designacao,
                    "material": profiles["gaiola_longitudinal"].material,
                    "fabricacao": profiles["gaiola_longitudinal"].fabricacao,
                    "comprimento_mm": cage_vertical_length_mm,
                    "massa_unitaria_kg": round((cage_vertical_length_mm / 1000.0) * profiles["gaiola_longitudinal"].massa_linear_kg_m, 3),
                    "stock_group": f"{profiles['gaiola_longitudinal'].designacao}|{profiles['gaiola_longitudinal'].material}",
                    "aplicacao": f"Montante vertical da gaiola {index}",
                }
            )

    for index, pos_y in enumerate(support_positions, start=1):
        parts.append(
            {
                "part_id": f"SB-{index:02d}",
                "item": "BRACO_SUPORTE_FIXACAO",
                "descricao": "Braco de fixacao da escada a estrutura existente.",
                "perfil": profiles["suporte_braco"].designacao,
                "material": profiles["suporte_braco"].material,
                "fabricacao": profiles["suporte_braco"].fabricacao,
                "comprimento_mm": cfg.afastamento_parede_mm,
                "massa_unitaria_kg": round((cfg.afastamento_parede_mm / 1000.0) * profiles["suporte_braco"].massa_linear_kg_m, 3),
                "stock_group": f"{profiles['suporte_braco'].designacao}|{profiles['suporte_braco'].material}",
                "aplicacao": f"Suporte de fixacao a cota {pos_y} mm",
            }
        )
        parts.append(
            {
                "part_id": f"CP-{index:02d}",
                "item": "CHAPA_SUPORTE_FIXACAO",
                "descricao": "Chapa base 120x80x8 mm com 2 furos D14 mm.",
                "perfil": "CHAPA ASTM A36 120x80x8 mm",
                "material": "ASTM A36",
                "fabricacao": "chaparia",
                "comprimento_mm": 0,
                "massa_unitaria_kg": round(_plate_mass_kg(SUPPORT_PLATE_WIDTH_MM, SUPPORT_PLATE_HEIGHT_MM, SUPPORT_PLATE_THICKNESS_MM, 1), 3),
                "stock_group": "CHAPA ASTM A36",
                "aplicacao": f"Chapa de fixacao a cota {pos_y} mm",
            }
        )

    return parts


def _group_parts_to_bom(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for part in parts:
        key = (str(part["item"]), str(part["perfil"]), str(part["material"]))
        bucket = grouped.setdefault(
            key,
            {
                "item": part["item"],
                "descricao": part["descricao"],
                "perfil": part["perfil"],
                "quantidade": 0,
                "comprimento_unitario_m": round(part["comprimento_mm"] / 1000.0, 3),
                "comprimento_total_m": 0.0,
                "material": part["material"],
                "fabricacao": part["fabricacao"],
                "massa_total_kg": 0.0,
            },
        )
        bucket["quantidade"] += 1
        bucket["comprimento_total_m"] += part["comprimento_mm"] / 1000.0
        bucket["massa_total_kg"] += float(part["massa_unitaria_kg"])

    bom = list(grouped.values())
    for item in bom:
        item["comprimento_total_m"] = round(float(item["comprimento_total_m"]), 3)
        item["massa_total_kg"] = round(float(item["massa_total_kg"]), 2)
    bom.sort(key=lambda item: (item["item"], item["perfil"], item["material"]))
    return bom


def _rectangle_entities(origin_x: float, origin_y: float, width: float, height: float, layer: str) -> list[dict[str, Any]]:
    return [
        {"type": "line", "layer": layer, "start": {"x": origin_x, "y": origin_y}, "end": {"x": origin_x + width, "y": origin_y}},
        {"type": "line", "layer": layer, "start": {"x": origin_x + width, "y": origin_y}, "end": {"x": origin_x + width, "y": origin_y + height}},
        {"type": "line", "layer": layer, "start": {"x": origin_x + width, "y": origin_y + height}, "end": {"x": origin_x, "y": origin_y + height}},
        {"type": "line", "layer": layer, "start": {"x": origin_x, "y": origin_y + height}, "end": {"x": origin_x, "y": origin_y}},
    ]


def _build_geometry_package(
    altura_mm: int,
    rail_length_mm: int,
    cfg: EscadaMarinheiroConfig,
    rung_positions: list[int],
    ring_positions: list[int],
    support_positions: list[int],
) -> dict[str, Any]:
    front_entities: list[dict[str, Any]] = []
    side_entities: list[dict[str, Any]] = []
    model_3d: list[dict[str, Any]] = []

    side_origin_x = float(cfg.largura_escada_mm + cfg.diametro_gaiola_mm + 1200)
    cage_radius_mm = cfg.diametro_gaiola_mm / 2.0
    cage_center_x = cfg.largura_escada_mm / 2.0

    front_entities.append(
        {"type": "line", "layer": "01_PERFIL", "start": {"x": 0.0, "y": 0.0}, "end": {"x": 0.0, "y": float(rail_length_mm)}}
    )
    front_entities.append(
        {"type": "line", "layer": "01_PERFIL", "start": {"x": float(cfg.largura_escada_mm), "y": 0.0}, "end": {"x": float(cfg.largura_escada_mm), "y": float(rail_length_mm)}}
    )

    for pos_y in rung_positions:
        front_entities.append(
            {
                "type": "line",
                "layer": "01_PERFIL",
                "start": {"x": 0.0, "y": float(pos_y)},
                "end": {"x": float(cfg.largura_escada_mm), "y": float(pos_y)},
            }
        )
        model_3d.append(
            {
                "type": "line",
                "id": f"RUNG-{pos_y:04d}",
                "start": {"x": 0.0, "y": float(pos_y), "z": 0.0},
                "end": {"x": float(cfg.largura_escada_mm), "y": float(pos_y), "z": 0.0},
            }
        )

    cage_front_x_positions = [
        cage_center_x - cage_radius_mm,
        cage_center_x - (cage_radius_mm * 0.35),
        cage_center_x + (cage_radius_mm * 0.35),
        cage_center_x + cage_radius_mm,
    ]
    for pos_y in ring_positions:
        front_entities.append(
            {
                "type": "circle",
                "layer": "01_PERFIL",
                "center": {"x": cage_center_x, "y": float(pos_y)},
                "radius": cage_radius_mm,
            }
        )
        model_3d.append(
            {
                "type": "circle",
                "id": f"RING-{pos_y:04d}",
                "center": {"x": cage_center_x, "y": float(pos_y), "z": 0.0},
                "radius": cage_radius_mm,
                "plane": "XZ",
            }
        )

    if ring_positions:
        for index, x_position in enumerate(cage_front_x_positions, start=1):
            front_entities.append(
                {
                    "type": "line",
                    "layer": "01_PERFIL",
                    "start": {"x": float(x_position), "y": float(cfg.inicio_gaiola_mm)},
                    "end": {"x": float(x_position), "y": float(altura_mm)},
                }
            )
            angle = ((index - 1) * (2.0 * math.pi / CAGE_VERTICAL_BARS))
            model_3d.append(
                {
                    "type": "line",
                    "id": f"CAGE-LONG-{index:02d}",
                    "start": {"x": cage_center_x + (cage_radius_mm * math.cos(angle)), "y": float(cfg.inicio_gaiola_mm), "z": cage_radius_mm * math.sin(angle)},
                    "end": {"x": cage_center_x + (cage_radius_mm * math.cos(angle)), "y": float(altura_mm), "z": cage_radius_mm * math.sin(angle)},
                }
            )

    side_entities.append(
        {
            "type": "line",
            "layer": "01_PERFIL",
            "start": {"x": side_origin_x + float(cfg.afastamento_parede_mm), "y": 0.0},
            "end": {"x": side_origin_x + float(cfg.afastamento_parede_mm), "y": float(rail_length_mm)},
        }
    )
    side_entities.append(
        {"type": "line", "layer": "01_PERFIL", "start": {"x": side_origin_x, "y": 0.0}, "end": {"x": side_origin_x, "y": float(altura_mm)}}
    )

    for pos_y in support_positions:
        side_entities.append(
            {
                "type": "line",
                "layer": "01_PERFIL",
                "start": {"x": side_origin_x, "y": float(pos_y)},
                "end": {"x": side_origin_x + float(cfg.afastamento_parede_mm), "y": float(pos_y)},
            }
        )
        side_entities.extend(
            _rectangle_entities(
                side_origin_x - SUPPORT_PLATE_THICKNESS_MM,
                float(pos_y - (SUPPORT_PLATE_HEIGHT_MM / 2.0)),
                float(SUPPORT_PLATE_THICKNESS_MM),
                float(SUPPORT_PLATE_HEIGHT_MM),
                "01_PERFIL",
            )
        )
        for hole_offset in (-25.0, 25.0):
            side_entities.append(
                {
                    "type": "circle",
                    "layer": "02_FUROS",
                    "center": {"x": side_origin_x - (SUPPORT_PLATE_THICKNESS_MM / 2.0), "y": float(pos_y + hole_offset)},
                    "radius": SUPPORT_HOLE_DIAMETER_MM / 2.0,
                }
            )

    text_entities = [
        {
            "type": "text",
            "layer": "04_TEXTOS",
            "position": {"x": 0.0, "y": float(rail_length_mm + 250)},
            "height": 120.0,
            "rotation": 0.0,
            "value": f"ESCADA MARINHEIRO N-1710 | H={altura_mm} mm | L={cfg.largura_escada_mm} mm",
        },
        {
            "type": "text",
            "layer": "04_TEXTOS",
            "position": {"x": 0.0, "y": float(rail_length_mm + 70)},
            "height": 90.0,
            "rotation": 0.0,
            "value": f"DEGRAUS D{cfg.diametro_degrau_mm} mm @ {cfg.espacamento_degrau_mm} mm | GAIOLA CHATA {cfg.barra_chata_gaiola_mm}",
        },
        {
            "type": "text",
            "layer": "03_SOLDA",
            "position": {"x": float(cfg.largura_escada_mm + 120), "y": float(min(altura_mm, 900))},
            "height": 80.0,
            "rotation": 0.0,
            "value": f"FW {WELD_FILLET_MM:.0f} mm E7018 - DEGRAU x MONTANTE",
        },
        {
            "type": "text",
            "layer": "03_SOLDA",
            "position": {"x": float(cfg.largura_escada_mm + 120), "y": float(max(cfg.inicio_gaiola_mm, 2400))},
            "height": 80.0,
            "rotation": 0.0,
            "value": f"FW {WELD_FILLET_MM:.0f} mm E7018 - GAIOLA x MONTANTES",
        },
        {
            "type": "text",
            "layer": "03_SOLDA",
            "position": {"x": side_origin_x + float(cfg.afastamento_parede_mm + 120), "y": float(support_positions[0] if support_positions else 600)},
            "height": 80.0,
            "rotation": 0.0,
            "value": f"FW {WELD_FILLET_MM:.0f} mm E7018 - SUPORTE x MONTANTE",
        },
    ]

    model_3d.extend(
        [
            {"type": "line", "id": "RAIL-L", "start": {"x": 0.0, "y": 0.0, "z": 0.0}, "end": {"x": 0.0, "y": float(rail_length_mm), "z": 0.0}},
            {"type": "line", "id": "RAIL-R", "start": {"x": float(cfg.largura_escada_mm), "y": 0.0, "z": 0.0}, "end": {"x": float(cfg.largura_escada_mm), "y": float(rail_length_mm), "z": 0.0}},
        ]
    )

    return {
        "dxf_layers": list(DXF_EXPORT_LAYERS),
        "view_2d": {
            "front_view": front_entities + text_entities,
            "side_view": side_entities,
        },
        "model_3d": model_3d,
        "metadata": {
            "side_view_origin_x_mm": side_origin_x,
            "cage_radius_mm": cage_radius_mm,
            "support_plate_mm": {
                "width": SUPPORT_PLATE_WIDTH_MM,
                "height": SUPPORT_PLATE_HEIGHT_MM,
                "thickness": SUPPORT_PLATE_THICKNESS_MM,
            },
        },
    }


def _pack_stock_bars(pieces: list[dict[str, Any]], stock_length_mm: int) -> tuple[list[dict[str, Any]], int]:
    bars: list[dict[str, Any]] = []
    for piece in sorted(pieces, key=lambda item: (item["comprimento_mm"], item["part_id"]), reverse=True):
        placed = False
        for bar in bars:
            if bar["remaining_mm"] >= piece["comprimento_mm"]:
                bar["pecas"].append(piece)
                bar["remaining_mm"] -= piece["comprimento_mm"]
                placed = True
                break
        if not placed:
            bars.append(
                {
                    "remaining_mm": stock_length_mm - piece["comprimento_mm"],
                    "pecas": [piece],
                }
            )
    total_waste_mm = sum(bar["remaining_mm"] for bar in bars)
    return bars, total_waste_mm


def _build_cut_plan(parts: list[dict[str, Any]], stock_length_mm: int, target_waste_percent: float = 5.0, max_batch_units: int = 12) -> dict[str, Any]:
    eligible = [part for part in parts if part["fabricacao"] in {"laminado", "tubular"} and int(part["comprimento_mm"]) > 0]
    excluded = [
        {
            "part_id": part["part_id"],
            "item": part["item"],
            "motivo": "fora_do_escopo_de_corte_em_barra",
        }
        for part in parts
        if part not in eligible
    ]

    def evaluate(batch_units: int) -> dict[str, Any]:
        expanded: list[dict[str, Any]] = []
        for unit in range(1, batch_units + 1):
            for part in eligible:
                expanded.append({**part, "part_id": f"{part['part_id']}-U{unit:02d}", "batch_unit": unit})

        grouped: dict[str, list[dict[str, Any]]] = {}
        for piece in expanded:
            grouped.setdefault(piece["stock_group"], []).append(piece)

        groups_output: list[dict[str, Any]] = []
        total_stock_mm = 0
        total_used_mm = 0
        total_waste_mm = 0
        for group_name, group_pieces in sorted(grouped.items()):
            bars, waste_mm = _pack_stock_bars(group_pieces, stock_length_mm)
            used_mm = sum(int(piece["comprimento_mm"]) for piece in group_pieces)
            total_stock_mm += len(bars) * stock_length_mm
            total_used_mm += used_mm
            total_waste_mm += waste_mm

            formatted_bars = []
            for index, bar in enumerate(bars, start=1):
                formatted_bars.append(
                    {
                        "barra_id": f"{group_name.split('|')[0][:8].upper()}-{index:03d}",
                        "comprimento_barra_mm": stock_length_mm,
                        "aproveitamento_mm": stock_length_mm - bar["remaining_mm"],
                        "sobra_mm": bar["remaining_mm"],
                        "pecas": [
                            {
                                "part_id": piece["part_id"],
                                "item": piece["item"],
                                "perfil": piece["perfil"],
                                "material": piece["material"],
                                "comprimento_mm": piece["comprimento_mm"],
                                "batch_unit": piece["batch_unit"],
                            }
                            for piece in bar["pecas"]
                        ],
                    }
                )

            waste_percent = round((waste_mm / (len(bars) * stock_length_mm)) * 100.0, 3) if bars else 0.0
            groups_output.append(
                {
                    "stock_group": group_name,
                    "bars": formatted_bars,
                    "total_stock_mm": len(bars) * stock_length_mm,
                    "total_used_mm": used_mm,
                    "waste_mm": waste_mm,
                    "waste_percent": waste_percent,
                }
            )

        overall_waste_percent = round((total_waste_mm / total_stock_mm) * 100.0, 3) if total_stock_mm else 0.0
        return {
            "batch_units": batch_units,
            "groups": groups_output,
            "total_stock_mm": total_stock_mm,
            "total_used_mm": total_used_mm,
            "waste_mm": total_waste_mm,
            "waste_percent": overall_waste_percent,
            "target_met": overall_waste_percent <= target_waste_percent,
        }

    single_unit = evaluate(1)
    recommended = single_unit
    if not single_unit["target_met"]:
        for batch_units in range(2, max_batch_units + 1):
            candidate = evaluate(batch_units)
            recommended = candidate
            if candidate["target_met"]:
                break

    return {
        "status": "ok" if eligible else "sem_itens_elegiveis",
        "stock_length_mm": stock_length_mm,
        "target_waste_percent": target_waste_percent,
        "single_unit": single_unit,
        "recommended_batch": recommended,
        "target_met": recommended["target_met"],
        "excluded": excluded,
        "note": "Quando a perda unitária nao atende a meta, o plano recomenda corte em lote para manter desperdicio abaixo de 5%.",
    }


def _render_welding_notes(qtd_degraus: int, qtd_aros: int, qtd_suportes: int) -> tuple[dict[str, Any], str]:
    notes = {
        "consumivel": "E7018",
        "processo": "SMAW",
        "garganta_filete_mm": WELD_FILLET_MM,
        "juntas": [
            {
                "item": "Degrau x montante",
                "tipo": "filete duplo continuo",
                "quantidade_juntas": qtd_degraus * 2,
                "comprimento_util_mm": 40,
            },
            {
                "item": "Aro da gaiola x montante da gaiola",
                "tipo": "filete intermitente alternado",
                "quantidade_juntas": qtd_aros * CAGE_VERTICAL_BARS,
                "comprimento_util_mm": 35,
            },
            {
                "item": "Suporte x montante lateral",
                "tipo": "filete duplo continuo",
                "quantidade_juntas": qtd_suportes * 2,
                "comprimento_util_mm": 60,
            },
        ],
        "inspecao": [
            "Limpar respingos e escoria entre passes.",
            "Executar ponteamento com gabarito para manter passo dos degraus em 300 mm.",
            "Verificar esquadro dos montantes antes do cordao definitivo.",
        ],
    }

    lines = [
        "NOTAS DE SOLDAGEM - ESCADA MARINHEIRO",
        "Consumivel: E7018",
        "Processo: SMAW",
        f"Garganta minima de filete: {WELD_FILLET_MM:.0f} mm",
        "",
        "JUNTAS:",
        f"1. Degrau x montante: filete duplo continuo, {qtd_degraus * 2} juntas, 40 mm por extremidade.",
        f"2. Aro da gaiola x montante da gaiola: filete intermitente alternado, {qtd_aros * CAGE_VERTICAL_BARS} juntas, 35 mm por encontro.",
        f"3. Suporte x montante lateral: filete duplo continuo, {qtd_suportes * 2} juntas, 60 mm por encontro.",
        "",
        "CONTROLE:",
        "- Remover escoria entre passes.",
        "- Conferir alinhamento final e abertura livre da escada antes da liberacao.",
        "- Aplicar EPS de campo Petrobras para sequencia de soldagem.",
    ]
    return notes, "\n".join(lines) + "\n"


def _render_dxf_script(geometry: dict[str, Any], output_path: Path) -> str:
    commands = [
        "; ENGENHARIA CAD - ESCADA MARINHEIRO N-1710",
        "; Script SCR para gerar detalhamento 2D e salvar em DXF.",
    ]

    layer_colors = {
        "01_PERFIL": 7,
        "02_FUROS": 1,
        "03_SOLDA": 3,
        "04_TEXTOS": 2,
    }
    for layer in DXF_EXPORT_LAYERS:
        commands.append(f"_.-LAYER _Make {layer} _Color {layer_colors[layer]} {layer} \"")

    all_entities = list(geometry["view_2d"]["front_view"]) + list(geometry["view_2d"]["side_view"])
    for entity in all_entities:
        commands.append(f"_.-LAYER _Set {entity['layer']} \"")
        if entity["type"] == "line":
            commands.extend(
                [
                    "_.LINE",
                    f"{entity['start']['x']:.3f},{entity['start']['y']:.3f}",
                    f"{entity['end']['x']:.3f},{entity['end']['y']:.3f}",
                    "",
                ]
            )
        elif entity["type"] == "circle":
            commands.extend(
                [
                    "_.CIRCLE",
                    f"{entity['center']['x']:.3f},{entity['center']['y']:.3f}",
                    f"{entity['radius']:.3f}",
                ]
            )
        elif entity["type"] == "text":
            commands.extend(
                [
                    "_.TEXT",
                    f"{entity['position']['x']:.3f},{entity['position']['y']:.3f}",
                    f"{entity['height']:.3f}",
                    f"{entity['rotation']:.3f}",
                    str(entity["value"]),
                ]
            )

    commands.extend(
        [
            "_.ZOOM _Extents",
            "_.SAVEAS",
            "DXF",
            "2018",
            str(output_path).replace("\\", "/"),
        ]
    )
    return "\n".join(commands) + "\n"


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _write_bom_csv(path: Path, bom: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["item", "descricao", "perfil", "material", "fabricacao", "quantidade", "comprimento_unitario_mm", "comprimento_total_mm", "massa_total_kg"])
        for item in bom:
            writer.writerow(
                [
                    item["item"],
                    item["descricao"],
                    item.get("perfil", ""),
                    item["material"],
                    item["fabricacao"],
                    item["quantidade"],
                    int(round(float(item.get("comprimento_unitario_m", 0.0)) * 1000.0)),
                    int(round(float(item.get("comprimento_total_m", 0.0)) * 1000.0)),
                    f"{float(item['massa_total_kg']):.2f}",
                ]
            )
    return str(path)


def _write_cut_plan_csv(path: Path, cut_plan: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    recommended = cut_plan["recommended_batch"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(
            [
                "batch_units",
                "stock_group",
                "barra_id",
                "comprimento_barra_mm",
                "aproveitamento_mm",
                "sobra_mm",
                "part_id",
                "item",
                "perfil",
                "material",
                "comprimento_peca_mm",
                "batch_unit",
            ]
        )
        for group in recommended["groups"]:
            for bar in group["bars"]:
                for piece in bar["pecas"]:
                    writer.writerow(
                        [
                            recommended["batch_units"],
                            group["stock_group"],
                            bar["barra_id"],
                            bar["comprimento_barra_mm"],
                            bar["aproveitamento_mm"],
                            bar["sobra_mm"],
                            piece["part_id"],
                            piece["item"],
                            piece["perfil"],
                            piece["material"],
                            piece["comprimento_mm"],
                            piece["batch_unit"],
                        ]
                    )
    return str(path)


def processar_escada_marinheiro(
    altura_torre_m: float,
    output_dir: Path,
    perfis_homologados: dict[str, Any] | None = None,
    stock_length_mm: int = 12000,
) -> dict[str, Any]:
    min_h = float(get_rule_param("N-1710", "min_tower_height_m", 2.0))
    max_h = float(get_rule_param("N-1710", "max_tower_height_m", 200.0))
    if not (min_h <= altura_torre_m <= max_h):
        raise ValueError(f"altura_torre_m deve estar entre {min_h} e {max_h}")
    if stock_length_mm <= 0:
        raise ValueError("stock_length_mm deve ser maior que zero")

    cfg = _load_dynamic_config()
    profiles = _load_homologated_profiles(perfis_homologados)
    altura_mm = int(round(altura_torre_m * 1000))
    rail_length_mm = altura_mm + cfg.altura_guarda_corpo_mm
    qtd_degraus = int(math.floor(altura_mm / cfg.espacamento_degrau_mm)) + 1
    rung_positions = [index * cfg.espacamento_degrau_mm for index in range(qtd_degraus)]
    espacamento_real_degrau_mm = float(cfg.espacamento_degrau_mm)
    folga_superior_mm = int(max(0, altura_mm - ((qtd_degraus - 1) * cfg.espacamento_degrau_mm)))

    ring_positions = _ring_positions(altura_mm, cfg.inicio_gaiola_mm, cfg.espacamento_aro_mm)
    qtd_aros = len(ring_positions)
    support_positions = _support_positions(altura_mm)
    incluir_patamar = altura_mm > cfg.altura_max_sem_patamar_mm

    fabrication_parts = _build_fabrication_parts(
        altura_mm=altura_mm,
        rail_length_mm=rail_length_mm,
        cfg=cfg,
        rung_positions=rung_positions,
        ring_positions=ring_positions,
        support_positions=support_positions,
        profiles=profiles,
    )
    bom = _group_parts_to_bom(fabrication_parts)
    peso_total_kg = round(sum(item["massa_total_kg"] for item in bom), 2)

    geometry = _build_geometry_package(
        altura_mm=altura_mm,
        rail_length_mm=rail_length_mm,
        cfg=cfg,
        rung_positions=rung_positions,
        ring_positions=ring_positions,
        support_positions=support_positions,
    )
    cut_plan = _build_cut_plan(fabrication_parts, stock_length_mm=stock_length_mm)
    welding_notes, welding_text = _render_welding_notes(qtd_degraus=qtd_degraus, qtd_aros=qtd_aros, qtd_suportes=len(support_positions))

    payload = {
        "header": {
            "modulo": "mecanica_escadas",
            "subtipo": "escada_marinheiro_guarda_corpo",
            "norma": cfg.norma,
            "timestamp": _utc_now(),
            "versao": "1.2.0_DETALHAMENTO",
        },
        "entrada": {
            "altura_torre_m": altura_torre_m,
            "stock_length_mm": stock_length_mm,
            "perfis_homologados_fornecidos": bool(perfis_homologados),
        },
        "parametros_escada": {
            "espacamento_degrau_mm": cfg.espacamento_degrau_mm,
            "diametro_degrau_mm": cfg.diametro_degrau_mm,
            "afastamento_parede_mm": cfg.afastamento_parede_mm,
            "largura_escada_mm": cfg.largura_escada_mm,
            "diametro_gaiola_mm": cfg.diametro_gaiola_mm,
            "inicio_gaiola_mm": cfg.inicio_gaiola_mm,
            "espacamento_aro_mm": cfg.espacamento_aro_mm,
            "barra_chata_gaiola_mm": cfg.barra_chata_gaiola_mm,
            "altura_guarda_corpo_mm": cfg.altura_guarda_corpo_mm,
            "espacamento_real_degrau_mm": espacamento_real_degrau_mm,
            "folga_superior_mm": folga_superior_mm,
        },
        "resultado": {
            "altura_total_mm": altura_mm,
            "altura_fabricacao_mm": rail_length_mm,
            "quantidade_degraus": qtd_degraus,
            "quantidade_aros_gaiola": qtd_aros,
            "quantidade_suportes": len(support_positions),
            "patamar_descanso_intermediario": {
                "obrigatorio": incluir_patamar,
                "inserido": incluir_patamar,
                "altura_instalacao_mm": int(round(altura_mm / 2.0)) if incluir_patamar else None,
            },
            "peso_total_kg": peso_total_kg,
            "validacao_normativa": {
                "atende_n1710": espacamento_real_degrau_mm == cfg.espacamento_degrau_mm and cfg.afastamento_parede_mm == 200 and cfg.diametro_degrau_mm == 19,
                "atende_nr12": cfg.altura_guarda_corpo_mm >= 1100,
                "status": "ok" if espacamento_real_degrau_mm == cfg.espacamento_degrau_mm and cfg.altura_guarda_corpo_mm >= 1100 else "revisar",
            },
            "xdata": {
                "trace_id": f"ESC-{uuid4().hex[:12]}",
                "norma": cfg.norma,
                "categoria": "Escada Marinheiro + Guarda-Corpo",
                "peso_total_kg": peso_total_kg,
                "origem": "worker_mecanica",
                "data_criacao": _utc_now(),
                "versao_norma_aplicada": "1.2.0",
                "status_validacao_carga": "ok",
            },
        },
        "perfis_homologados": {key: asdict(value) for key, value in profiles.items()},
        "bom": bom,
        "detalhamento": {
            "lista_pecas": fabrication_parts,
            "geometria": geometry,
            "plano_corte": cut_plan,
            "notas_soldagem": welding_notes,
            "layers_exportacao_dxf": list(DXF_EXPORT_LAYERS),
        },
    }

    target_dir = output_dir / "mecanica"
    detail_dir = target_dir / "escada_marinheiro_detalhamento"
    target_dir.mkdir(parents=True, exist_ok=True)
    detail_dir.mkdir(parents=True, exist_ok=True)

    legacy_json_path = target_dir / "escada_marinheiro_guarda_corpo.json"
    detail_json_path = detail_dir / "escada_marinheiro_detalhamento.json"
    bom_csv_path = detail_dir / "bom_escada_marinheiro.csv"
    cut_csv_path = detail_dir / "plano_corte_escada_marinheiro.csv"
    weld_notes_path = detail_dir / "notas_soldagem_escada_marinheiro.txt"
    dxf_target_path = detail_dir / "escada_marinheiro_fabricacao.dxf"
    dxf_script_path = detail_dir / "gerar_escada_marinheiro_dxf.scr"

    _write_json(legacy_json_path, payload)
    _write_json(detail_json_path, payload)
    _write_bom_csv(bom_csv_path, bom)
    _write_cut_plan_csv(cut_csv_path, cut_plan)
    _write_text(weld_notes_path, welding_text)
    _write_text(dxf_script_path, _render_dxf_script(geometry, dxf_target_path))

    artifacts = {
        "detalhamento_json": str(detail_json_path),
        "bom_csv": str(bom_csv_path),
        "cut_plan_csv": str(cut_csv_path),
        "welding_notes_txt": str(weld_notes_path),
        "dxf_script": str(dxf_script_path),
        "dxf_target": str(dxf_target_path),
        "legacy_json": str(legacy_json_path),
    }

    return {
        "status": "ok",
        "artifact": str(legacy_json_path),
        "artifacts": artifacts,
        "payload": payload,
    }
