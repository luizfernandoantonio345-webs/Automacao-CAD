from __future__ import annotations

import csv
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .base_generator import BasePetrobrasGenerator
from .business_impact import gerar_business_impact
from .compliance_loader import get_rule_param, load_compliance_rules
from .piping_autorouter import PipingAutoRouter
from .worker_mecanica import processar_escada_marinheiro


PROFILE_CATALOG: list[dict[str, Any]] = [
    {
        "name": "W310x32.7",
        "kg_m": 32.7,
        "ix_mm4": 190_000_000.0,
        "area_mm2": 4166.0,
        "rx_mm": 213.0,
        "zx_mm3": 1_230_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "laminado",
        "classificacao": "perfil_laminado",
    },
    {
        "name": "W360x44",
        "kg_m": 44.0,
        "ix_mm4": 310_000_000.0,
        "area_mm2": 5605.0,
        "rx_mm": 235.0,
        "zx_mm3": 1_780_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "laminado",
        "classificacao": "perfil_laminado",
    },
    {
        "name": "W410x60",
        "kg_m": 60.0,
        "ix_mm4": 480_000_000.0,
        "area_mm2": 7643.0,
        "rx_mm": 251.0,
        "zx_mm3": 2_460_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "laminado",
        "classificacao": "perfil_laminado",
    },
    {
        "name": "VS500x79",
        "kg_m": 79.0,
        "ix_mm4": 980_000_000.0,
        "area_mm2": 10_064.0,
        "rx_mm": 312.0,
        "zx_mm3": 3_920_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "soldado",
        "classificacao": "perfil_soldado",
    },
    {
        "name": "VS600x101",
        "kg_m": 101.0,
        "ix_mm4": 1_420_000_000.0,
        "area_mm2": 12_866.0,
        "rx_mm": 332.0,
        "zx_mm3": 5_680_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "soldado",
        "classificacao": "perfil_soldado",
    },
    {
        "name": "VS650x140",
        "kg_m": 140.0,
        "ix_mm4": 1_980_000_000.0,
        "area_mm2": 17_834.0,
        "rx_mm": 347.0,
        "zx_mm3": 7_920_000.0,
        "material": "ASTM A572 Gr. 50",
        "fabrication": "soldado",
        "classificacao": "perfil_soldado",
    },
]

STANDARD_MATERIALS: dict[str, dict[str, Any]] = {
    "ASTM A36": {
        "familia": "aco_estrutural_laminado",
        "cost_brl_kg": 9.8,
        "density_kg_m3": 7850,
    },
    "ASTM A572 Gr. 50": {
        "familia": "aco_estrutural_soldado",
        "cost_brl_kg": 11.4,
        "density_kg_m3": 7850,
    },
    "ASTM A106 Gr.B": {
        "familia": "tubulacao",
        "cost_brl_kg": 13.6,
        "density_kg_m3": 7850,
    },
    "ASTM A325": {
        "familia": "parafusaria_estrutural",
        "cost_brl_kg": 18.0,
        "density_kg_m3": 7850,
    },
    "ASTM F1554 Gr.36": {
        "familia": "chumbador",
        "cost_brl_kg": 17.0,
        "density_kg_m3": 7850,
    },
    "E7018": {
        "familia": "consumivel_solda",
        "cost_brl_kg": 27.0,
        "density_kg_m3": 7800,
    },
    "Concreto C30": {
        "familia": "civil",
        "cost_brl_kg": 0.65,
        "density_kg_m3": 2400,
    },
}

DRAWING_LAYERS = [
    "0",
    "ESTR_PORTICOS",
    "ESTR_LIGACOES",
    "ESTR_COTAS",
    "MEC_ESCADAS",
    "PIPING",
    "CIVIL_BASE",
    "ANOTACOES",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_up(value: float, step: int = 5) -> int:
    return int(math.ceil(value / step) * step)


def _norma_metadata() -> dict[str, Any]:
    rules = load_compliance_rules()
    metadata = rules.get("metadata", {}) if isinstance(rules, dict) else {}
    return {
        "source": metadata.get("source", "Petrobras + NR"),
        "version": metadata.get("version", "1.0.0"),
        "updated_at": metadata.get("updated_at", "n/a"),
    }


def _build_xdata(categoria: str, origem: str, status_validacao_carga: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    norma_meta = _norma_metadata()
    payload = {
        "trace_id": f"SD-{categoria[:3].upper()}-{uuid4().hex[:10]}",
        "categoria": categoria,
        "origem": origem,
        "data_criacao": _utc_now(),
        "versao_norma_aplicada": norma_meta["version"],
        "status_validacao_carga": status_validacao_carga,
    }
    if extra:
        payload.update(extra)
    return payload


def _validate_material(material: str) -> None:
    if material not in STANDARD_MATERIALS:
        raise ValueError(f"Material fora da padronização REGAP: {material}")


def _weld_spec(thickness_mm: float) -> dict[str, Any]:
    garganta = round(max(5.0, min(12.0, 0.7 * float(thickness_mm))), 1)
    passes = 1 if thickness_mm <= 8 else 2 if thickness_mm <= 16 else 3
    return {
        "consumivel": "E7018",
        "processo": "SMAW",
        "garganta_mm": garganta,
        "passes_minimos": passes,
        "observacao": "Aplicar preparo e sequência conforme EPS de campo Petrobras.",
    }


def _beam_deflection_mm(distributed_load_kn_m: float, span_m: float, inertia_mm4: float, modulus_mpa: float = 200_000.0) -> float:
    load_n_mm = float(distributed_load_kn_m)
    span_mm = float(span_m) * 1000.0
    return round((5.0 * load_n_mm * (span_mm ** 4)) / (384.0 * modulus_mpa * float(inertia_mm4)), 3)


def _next_astm_a572_profile(current_name: str) -> dict[str, Any] | None:
    a572_profiles = [item for item in PROFILE_CATALOG if str(item.get("material")) == "ASTM A572 Gr. 50"]
    for idx, item in enumerate(a572_profiles):
        if item["name"] == current_name:
            return a572_profiles[idx + 1] if idx + 1 < len(a572_profiles) else None
    return a572_profiles[0] if a572_profiles else None


def _evaluate_elu(
    profile: dict[str, Any],
    span_m: float,
    height_m: float,
    wind_load_kn: float,
    gravity_kn: float,
    deflection_limit_mm: float,
) -> dict[str, Any]:
    e_mpa = 200_000.0
    fy_mpa = 345.0
    phi_c = 0.9
    phi_b = 0.9
    k_factor = float(get_rule_param("NBR-8800", "structural.k_factor", 1.0))

    line_load_kn_m = (gravity_kn + (0.35 * wind_load_kn)) / span_m
    estimated_deflection_mm = _beam_deflection_mm(line_load_kn_m, span_m, profile["ix_mm4"])
    moment_kn_m = round(wind_load_kn * (height_m / 2.0), 3)
    axial_kn = round((gravity_kn / 2.0) + (0.10 * wind_load_kn), 3)

    klr = (k_factor * height_m * 1000.0) / float(profile["rx_mm"])
    fe_mpa = (math.pi ** 2 * e_mpa) / (klr ** 2) if klr > 0 else float("inf")
    inelastic_limit = 4.71 * math.sqrt(e_mpa / fy_mpa)
    if klr <= inelastic_limit:
        fcr_mpa = (0.658 ** (fy_mpa / fe_mpa)) * fy_mpa
    else:
        fcr_mpa = 0.877 * fe_mpa

    pn_kn = (phi_c * fcr_mpa * float(profile["area_mm2"])) / 1000.0
    md_kn_m = (phi_b * fy_mpa * float(profile["zx_mm3"])) / 1_000_000.0

    eta_n = axial_kn / pn_kn if pn_kn > 0 else 99.0
    eta_m = moment_kn_m / md_kn_m if md_kn_m > 0 else 99.0
    eta = max(eta_n, eta_m, eta_n + eta_m)
    status = "PASS" if eta <= 1.0 and estimated_deflection_mm <= deflection_limit_mm else "FAIL"

    return {
        "carga_linear_kn_m": round(line_load_kn_m, 3),
        "flecha_calculada_mm": estimated_deflection_mm,
        "flecha_limite_mm": deflection_limit_mm,
        "flecha_adotada_mm": min(estimated_deflection_mm, deflection_limit_mm),
        "status_flecha": "ok" if estimated_deflection_mm <= deflection_limit_mm else "limitado_em_L250",
        "elu": {
            "k_factor": round(k_factor, 3),
            "esbeltez_l_r": round(klr, 3),
            "flambagem": {
                "fe_mpa": round(fe_mpa, 3),
                "fcr_mpa": round(fcr_mpa, 3),
                "pn_kn": round(pn_kn, 3),
            },
            "momento_resistente": {
                "md_kn_m": round(md_kn_m, 3),
            },
            "solicitacao": {
                "nsd_kn": round(axial_kn, 3),
                "msd_kn_m": round(moment_kn_m, 3),
            },
            "taxa_utilizacao_eta": round(eta, 4),
            "taxa_utilizacao_componentes": {
                "eta_n": round(eta_n, 4),
                "eta_m": round(eta_m, 4),
                "eta_interacao": round(eta_n + eta_m, 4),
            },
            "status": status,
            "formulas": {
                "esbeltez": "L/r = (K*L)/r",
                "flambagem": "Fe = pi^2*E/(KL/r)^2; Fcr conforme NBR 8800",
                "momento_resistente": "Md = phi_b*fy*Zx",
                "utilizacao": "eta = max(Nsd/Pn, Msd/Md, Nsd/Pn + Msd/Md)",
            },
        },
    }


def _select_profile_for_portico(span_m: float, height_m: float, wind_load_kn: float) -> dict[str, Any]:
    deflection_limit_mm = round((span_m * 1000.0) / float(get_rule_param("NBR-8800", "structural.max_deflection_ratio", 250)), 3)

    selected: dict[str, Any] | None = None
    for profile in PROFILE_CATALOG:
        weight_kg = profile["kg_m"] * ((2.0 * height_m) + span_m)
        gravity_kn = (weight_kg * 9.81) / 1000.0
        elu_check = _evaluate_elu(profile, span_m, height_m, wind_load_kn, gravity_kn, deflection_limit_mm)
        candidate = {
            **profile,
            "peso_total_estimado_kg": round(weight_kg, 2),
            "carga_gravitacional_kn": round(gravity_kn, 3),
            **elu_check,
            "redimensionamento_auto": {"aplicado": False, "motivo": None, "perfil_origem": profile["name"]},
        }
        if candidate["elu"]["status"] == "PASS":
            selected = candidate
            break

    if selected is None:
        profile = PROFILE_CATALOG[-1]
        weight_kg = profile["kg_m"] * ((2.0 * height_m) + span_m)
        gravity_kn = (weight_kg * 9.81) / 1000.0
        selected = {
            **profile,
            "peso_total_estimado_kg": round(weight_kg, 2),
            "carga_gravitacional_kn": round(gravity_kn, 3),
            **_evaluate_elu(profile, span_m, height_m, wind_load_kn, gravity_kn, deflection_limit_mm),
            "redimensionamento_auto": {"aplicado": False, "motivo": "limite_catalogo", "perfil_origem": profile["name"]},
        }

    while selected["elu"]["taxa_utilizacao_eta"] > 0.85:
        next_profile = _next_astm_a572_profile(selected["name"])
        if not next_profile or next_profile["name"] == selected["name"]:
            break
        weight_kg = next_profile["kg_m"] * ((2.0 * height_m) + span_m)
        gravity_kn = (weight_kg * 9.81) / 1000.0
        selected = {
            **next_profile,
            "peso_total_estimado_kg": round(weight_kg, 2),
            "carga_gravitacional_kn": round(gravity_kn, 3),
            **_evaluate_elu(next_profile, span_m, height_m, wind_load_kn, gravity_kn, deflection_limit_mm),
            "redimensionamento_auto": {
                "aplicado": True,
                "motivo": "regra_ouro_eta_maior_085",
                "perfil_origem": selected["name"],
            },
        }

    return selected


def _design_base_plate(vertical_kn: float, horizontal_kn: float, moment_kn_m: float) -> dict[str, Any]:
    _validate_material("ASTM A36")
    _validate_material("ASTM F1554 Gr.36")
    allowable_bearing_mpa = 8.0
    required_area_mm2 = max((vertical_kn * 1000.0) / allowable_bearing_mpa, 160_000.0)
    side_mm = _round_up(math.sqrt(required_area_mm2), 25)
    thickness_mm = _round_up(20.0 + (moment_kn_m / 12.0), 2)
    anchor_diameter_mm = 24 if moment_kn_m <= 120.0 and horizontal_kn <= 35.0 else 30
    anchor_qty = 4 if anchor_diameter_mm == 24 else 8
    weld = _weld_spec(thickness_mm)
    plate_mass_kg = round(((side_mm / 1000.0) ** 2) * (thickness_mm / 1000.0) * STANDARD_MATERIALS["ASTM A36"]["density_kg_m3"], 2)
    anchor_length_m = 0.75 if anchor_diameter_mm == 24 else 0.9
    anchor_mass_kg = round(anchor_qty * anchor_length_m * (anchor_diameter_mm / 1000.0) ** 2 * math.pi / 4.0 * STANDARD_MATERIALS["ASTM F1554 Gr.36"]["density_kg_m3"], 2)
    anchor_area_mm2 = math.pi * (anchor_diameter_mm ** 2) / 4.0
    fy_anchor_mpa = 250.0
    phi_anchor = 0.75
    anchor_capacity_kn = (phi_anchor * fy_anchor_mpa * anchor_area_mm2) / 1000.0
    active_anchors = max(2, anchor_qty // 2)
    lever_arm_m = max((side_mm / 1000.0) * 0.8, 0.1)
    anchor_tension_kn = (moment_kn_m / (active_anchors * lever_arm_m)) + (horizontal_kn / anchor_qty)
    eta_anchor = anchor_tension_kn / anchor_capacity_kn if anchor_capacity_kn > 0 else 99.0

    return {
        "placa_base": {
            "material": "ASTM A36",
            "dimensoes_mm": {"largura": side_mm, "comprimento": side_mm, "espessura": thickness_mm},
            "massa_total_kg": plate_mass_kg,
        },
        "chumbadores": {
            "material": "ASTM F1554 Gr.36",
            "quantidade": anchor_qty,
            "diametro_mm": anchor_diameter_mm,
            "comprimento_m": anchor_length_m,
            "massa_total_kg": anchor_mass_kg,
        },
        "solda": weld,
        "criterios": {
            "pressao_admissivel_base_mpa": allowable_bearing_mpa,
            "carga_vertical_kn": round(vertical_kn, 3),
            "carga_horizontal_kn": round(horizontal_kn, 3),
            "momento_base_kn_m": round(moment_kn_m, 3),
        },
        "verificacao_chumbadores": {
            "formulas": {
                "tracao_solicitante": "N_t,sd = Msd/(n_ativo*z) + Hsd/n_total",
                "resistencia": "N_t,Rd = phi*fy*A",
                "utilizacao": "eta = N_t,sd/N_t,Rd",
            },
            "nt_sd_kn": round(anchor_tension_kn, 3),
            "nt_rd_kn": round(anchor_capacity_kn, 3),
            "taxa_utilizacao_eta": round(eta_anchor, 4),
            "status": "PASS" if eta_anchor <= 1.0 else "FAIL",
        },
    }


def _connection_detail(profile: dict[str, Any]) -> dict[str, Any]:
    _validate_material("ASTM A36")
    _validate_material("ASTM A325")
    plate_thickness_mm = 16 if profile["fabrication"] == "soldado" else 12
    bolt_diameter_mm = int(get_rule_param("NBR-8800", "connections.default_bolt_diameter_mm", 20))
    bolts_qty = 6 if profile["fabrication"] == "soldado" else 4
    edge_distance_mm = int(get_rule_param("NBR-8800", "connections.min_edge_distance_mm", 35))
    gauge_mm = int(get_rule_param("NBR-8800", "connections.default_gauge_mm", 70))
    weld = _weld_spec(plate_thickness_mm)
    plate_height_mm = 280 if profile["fabrication"] == "soldado" else 220
    plate_width_mm = 180 if profile["fabrication"] == "soldado" else 160
    plate_mass_kg = round((plate_height_mm / 1000.0) * (plate_width_mm / 1000.0) * (plate_thickness_mm / 1000.0) * STANDARD_MATERIALS["ASTM A36"]["density_kg_m3"], 2)
    bolt_mass_kg = round(bolts_qty * 0.65, 2)
    return {
        "chapa_ligacao": {
            "material": "ASTM A36",
            "dimensoes_mm": {
                "altura": plate_height_mm,
                "largura": plate_width_mm,
                "espessura": plate_thickness_mm,
            },
            "massa_total_kg": plate_mass_kg,
        },
        "parafusos": {
            "material": "ASTM A325",
            "quantidade": bolts_qty,
            "diametro_mm": bolt_diameter_mm,
            "distancia_borda_mm": edge_distance_mm,
            "gabarito_mm": gauge_mm,
            "massa_total_kg": bolt_mass_kg,
        },
        "solda": weld,
    }


def _build_portico_geometry(index: int, span_mm: float, height_mm: float, spacing_mm: float) -> dict[str, Any]:
    z = index * spacing_mm
    return {
        "left_column": {
            "id": f"P-{index + 1:03d}-COL-L",
            "start": {"x": 0.0, "y": 0.0, "z": z},
            "end": {"x": 0.0, "y": height_mm, "z": z},
        },
        "right_column": {
            "id": f"P-{index + 1:03d}-COL-R",
            "start": {"x": span_mm, "y": 0.0, "z": z},
            "end": {"x": span_mm, "y": height_mm, "z": z},
        },
        "beam": {
            "id": f"P-{index + 1:03d}-VIGA",
            "start": {"x": 0.0, "y": height_mm, "z": z},
            "end": {"x": span_mm, "y": height_mm, "z": z},
        },
    }


def _generate_porticos(qtd_porticos: int) -> dict[str, Any]:
    span_m = 25.0
    height_m = 8.0
    spacing_m = 6.0
    span_mm = span_m * 1000.0
    height_mm = height_m * 1000.0
    spacing_mm = spacing_m * 1000.0

    wind_speed = float(get_rule_param("REGAP", "wind.basic_speed_m_s", 38.0))
    wind_pressure_kpa = round((0.613 * (wind_speed ** 2)) / 1000.0, 3)
    drag_coeff = float(get_rule_param("REGAP", "wind.drag_coefficient", 1.3))
    exposed_area_m2 = span_m * height_m * float(get_rule_param("REGAP", "wind.structural_projection_factor", 0.18))
    wind_load_kn = round(wind_pressure_kpa * exposed_area_m2 * drag_coeff, 3)

    porticos: list[dict[str, Any]] = []
    beam_components: list[dict[str, Any]] = []
    support_reactions: list[dict[str, Any]] = []
    civil_design: list[dict[str, Any]] = []
    bom: list[dict[str, Any]] = []

    for index in range(qtd_porticos):
        selected_profile = _select_profile_for_portico(span_m, height_m, wind_load_kn)
        _validate_material(selected_profile["material"])
        geometry = _build_portico_geometry(index, span_mm, height_mm, spacing_mm)
        moment_kn_m = round(wind_load_kn * (height_m / 2.0), 3)
        vertical_reaction_kn = round(selected_profile["carga_gravitacional_kn"] / 2.0, 3)
        horizontal_reaction_kn = round(wind_load_kn / 2.0, 3)
        base_plate = _design_base_plate(vertical_reaction_kn, horizontal_reaction_kn, moment_kn_m)
        connection = _connection_detail(selected_profile)

        portico_id = f"P-{index + 1:03d}"
        status_validacao = "ok" if selected_profile["elu"]["status"] == "PASS" else "falha_elu"
        xdata = _build_xdata(
            categoria="PORTICO_COMPLETO",
            origem="generate_full_unit_project",
            status_validacao_carga=status_validacao,
            extra={
                "perfil": selected_profile["name"],
                "material": selected_profile["material"],
                "peso_estimado_kg": selected_profile["peso_total_estimado_kg"],
                "eta": selected_profile["elu"]["taxa_utilizacao_eta"],
            },
        )

        beam_components.append(
            {
                "id": geometry["beam"]["id"],
                "origin": {"x": 0.0, "y": height_mm - 450.0, "z": (index * spacing_mm) - 150.0},
                "size": {"dx": span_mm, "dy": 450.0, "dz": 300.0},
            }
        )

        support_reactions.append(
            {
                "portico_id": portico_id,
                "apoio_esquerdo": {
                    "fx_kn": 0.0,
                    "fy_kn": horizontal_reaction_kn,
                    "fz_kn": vertical_reaction_kn,
                    "mz_kn_m": moment_kn_m,
                },
                "apoio_direito": {
                    "fx_kn": 0.0,
                    "fy_kn": horizontal_reaction_kn,
                    "fz_kn": vertical_reaction_kn,
                    "mz_kn_m": moment_kn_m,
                },
                "xdata": _build_xdata(
                    categoria="REACAO_APOIO",
                    origem=portico_id,
                    status_validacao_carga="ok",
                ),
            }
        )

        civil_design.append(
            {
                "portico_id": portico_id,
                "placa_base": base_plate["placa_base"],
                "chumbadores": base_plate["chumbadores"],
                "solda": base_plate["solda"],
                "criterios": base_plate["criterios"],
                "verificacao_chumbadores": base_plate["verificacao_chumbadores"],
                "xdata": _build_xdata(
                    categoria="CIVIL_BASE",
                    origem=portico_id,
                    status_validacao_carga="ok",
                ),
            }
        )

        porticos.append(
            {
                "id": portico_id,
                "tipo": "PORTICO_COMPLETO",
                "coordenadas": {"x": 0.0, "y": 0.0, "z": index * spacing_mm},
                "dimensoes": {"vao_mm": span_mm, "altura_mm": height_mm, "espacamento_mm": spacing_mm},
                "perfil": {
                    "designacao": selected_profile["name"],
                    "material": selected_profile["material"],
                    "fabricacao": selected_profile["fabrication"],
                    "peso_kg_m": selected_profile["kg_m"],
                },
                "analise": {
                    "vento": {
                        "local": "Betim/MG - REGAP",
                        "velocidade_basica_m_s": wind_speed,
                        "pressao_dinamica_kpa": wind_pressure_kpa,
                        "carga_total_kn": wind_load_kn,
                    },
                    "flecha": {
                        "criterio": "L/250",
                        "limite_mm": selected_profile["flecha_limite_mm"],
                        "calculada_mm": selected_profile["flecha_calculada_mm"],
                        "adotada_mm": selected_profile["flecha_adotada_mm"],
                        "status": selected_profile["status_flecha"],
                    },
                    "verificacao_elu": selected_profile["elu"],
                    "redimensionamento_auto": selected_profile["redimensionamento_auto"],
                    "reacoes_apoio": support_reactions[-1],
                },
                "ligacao_viga_pilar": connection,
                "geometria": geometry,
                "xdata": xdata,
            }
        )

        bom.extend(
            [
                {
                    "disciplina": "estrutura",
                    "item": "PORTICO_COLUNA",
                    "descricao": "Coluna principal do pórtico",
                    "quantidade": 2,
                    "comprimento_unitario_m": height_m,
                    "comprimento_total_m": round(2.0 * height_m, 3),
                    "material": selected_profile["material"],
                    "fabricacao": selected_profile["fabrication"],
                    "massa_total_kg": round(2.0 * height_m * selected_profile["kg_m"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "estrutura",
                    "item": "PORTICO_VIGA",
                    "descricao": "Viga principal do pórtico",
                    "quantidade": 1,
                    "comprimento_unitario_m": span_m,
                    "comprimento_total_m": round(span_m, 3),
                    "material": selected_profile["material"],
                    "fabricacao": selected_profile["fabrication"],
                    "massa_total_kg": round(span_m * selected_profile["kg_m"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "estrutura",
                    "item": "CHAPA_LIGACAO",
                    "descricao": "Chapa de ligação nó viga-pilar",
                    "quantidade": 2,
                    "material": connection["chapa_ligacao"]["material"],
                    "fabricacao": "calandrada",
                    "massa_total_kg": round(2.0 * connection["chapa_ligacao"]["massa_total_kg"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "estrutura",
                    "item": "PARAFUSO_ESTRUTURAL",
                    "descricao": "Parafuso ASTM A325 das ligações",
                    "quantidade": 2 * connection["parafusos"]["quantidade"],
                    "material": connection["parafusos"]["material"],
                    "fabricacao": "industrializado",
                    "massa_total_kg": round(2.0 * connection["parafusos"]["massa_total_kg"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "civil",
                    "item": "PLACA_BASE",
                    "descricao": "Placa de base para apoio do pórtico",
                    "quantidade": 2,
                    "material": base_plate["placa_base"]["material"],
                    "fabricacao": "chaparia",
                    "massa_total_kg": round(2.0 * base_plate["placa_base"]["massa_total_kg"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "civil",
                    "item": "CHUMBADOR",
                    "descricao": "Chumbador de fundação",
                    "quantidade": 2 * base_plate["chumbadores"]["quantidade"],
                    "material": base_plate["chumbadores"]["material"],
                    "fabricacao": "industrializado",
                    "massa_total_kg": round(2.0 * base_plate["chumbadores"]["massa_total_kg"], 2),
                    "portico_id": portico_id,
                },
                {
                    "disciplina": "soldagem",
                    "item": "CONSUMIVEL_SOLDA",
                    "descricao": "Consumível de solda de fabricação e montagem",
                    "quantidade": 1,
                    "material": "E7018",
                    "fabricacao": "consumivel",
                    "massa_total_kg": round(3.2 + (0.012 * selected_profile["peso_total_estimado_kg"]), 2),
                    "portico_id": portico_id,
                },
            ]
        )

    return {
        "porticos": porticos,
        "beam_components": beam_components,
        "support_reactions": support_reactions,
        "civil_design": civil_design,
        "bom": bom,
        "summary": {
            "qtd_porticos": qtd_porticos,
            "peso_total_aco_kg": round(sum(item["perfil"]["peso_kg_m"] * (2.0 * height_m + span_m) for item in porticos), 2),
            "flecha_maxima_mm": round(max(item["analise"]["flecha"]["adotada_mm"] for item in porticos), 3),
            "flecha_limite_mm": round((span_m * 1000.0) / float(get_rule_param("NBR-8800", "structural.max_deflection_ratio", 250)), 3),
            "local_vento": "Betim/MG - REGAP",
            "velocidade_vento_m_s": wind_speed,
        },
    }


def _build_accessory_component(component_id: str, origin: dict[str, float], size: dict[str, float]) -> dict[str, Any]:
    return {"id": component_id, "origin": origin, "size": size}


def _detect_clashes(accessory_components: list[dict[str, Any]], beam_components: list[dict[str, Any]], clearance_mm: float) -> list[dict[str, Any]]:
    clashes: list[dict[str, Any]] = []
    for accessory in accessory_components:
        accessory_bbox = BasePetrobrasGenerator.compute_bounding_box(accessory["origin"], accessory["size"])
        for beam in beam_components:
            beam_bbox = BasePetrobrasGenerator.compute_bounding_box(beam["origin"], beam["size"])
            if BasePetrobrasGenerator._aabb_intersects(accessory_bbox, beam_bbox, clearance_mm=clearance_mm):
                clashes.append(
                    {
                        "accessory_id": accessory["id"],
                        "beam_id": beam["id"],
                        "accessory_bbox": accessory_bbox.to_dict(),
                        "beam_bbox": beam_bbox.to_dict(),
                    }
                )
    return clashes


def _resolve_vertical_accessory_clash(
    component_id: str,
    origin: dict[str, float],
    size: dict[str, float],
    beam_components: list[dict[str, Any]],
    clearance_mm: float,
    shift_axis: str,
    shift_step_mm: float,
    max_iterations: int,
) -> dict[str, Any]:
    component = _build_accessory_component(component_id, dict(origin), dict(size))
    before = _detect_clashes([component], beam_components, clearance_mm)
    iterations = 0

    while iterations < max_iterations and before:
        component["origin"][shift_axis] = float(component["origin"].get(shift_axis, 0.0)) + shift_step_mm
        iterations += 1
        before = _detect_clashes([component], beam_components, clearance_mm)

    return {
        "component": component,
        "clashes": before,
        "iterations": iterations,
        "resolved": len(before) == 0,
    }


def _build_piping_components(route_points: list[dict[str, float]], diameter_mm: float) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]
        components.append(
            {
                "id": f"PIPE-SEG-{index + 1}",
                "origin": {
                    "x": min(float(start["x"]), float(end["x"])),
                    "y": min(float(start["y"]), float(end["y"])),
                    "z": min(float(start["z"]), float(end["z"])),
                },
                "size": {
                    "dx": abs(float(end["x"]) - float(start["x"])) or diameter_mm,
                    "dy": abs(float(end["y"]) - float(start["y"])) or diameter_mm,
                    "dz": abs(float(end["z"]) - float(start["z"])) or diameter_mm,
                },
            }
        )
    return components


def _flatten_bom_item(item: dict[str, Any], origem: str) -> dict[str, Any]:
    material = str(item.get("material", "ASTM A36"))
    _validate_material(material)
    mass = round(float(item.get("massa_total_kg", 0.0) or 0.0), 2)
    unit_cost = STANDARD_MATERIALS[material]["cost_brl_kg"]
    return {
        **item,
        "origem": origem,
        "massa_total_kg": mass,
        "custo_total_brl": round(mass * unit_cost, 2),
        "material": material,
    }


def _aggregate_bom(items: list[dict[str, Any]]) -> dict[str, Any]:
    aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in items:
        key = (str(item.get("disciplina", "geral")), str(item.get("item", "SEM_ITEM")), str(item.get("material", "SEM_MATERIAL")))
        bucket = aggregated.setdefault(
            key,
            {
                "disciplina": item.get("disciplina", "geral"),
                "item": item.get("item", "SEM_ITEM"),
                "descricao": item.get("descricao", ""),
                "material": item.get("material", "SEM_MATERIAL"),
                "fabricacao": item.get("fabricacao", "n/a"),
                "quantidade": 0.0,
                "comprimento_total_m": 0.0,
                "massa_total_kg": 0.0,
                "custo_total_brl": 0.0,
            },
        )
        bucket["quantidade"] += float(item.get("quantidade", 0.0) or 0.0)
        bucket["comprimento_total_m"] += float(item.get("comprimento_total_m", 0.0) or 0.0)
        bucket["massa_total_kg"] += float(item.get("massa_total_kg", 0.0) or 0.0)
        bucket["custo_total_brl"] += float(item.get("custo_total_brl", 0.0) or 0.0)

    linhas = []
    for value in aggregated.values():
        value["quantidade"] = round(value["quantidade"], 3)
        value["comprimento_total_m"] = round(value["comprimento_total_m"], 3)
        value["massa_total_kg"] = round(value["massa_total_kg"], 2)
        value["custo_total_brl"] = round(value["custo_total_brl"], 2)
        linhas.append(value)
    linhas.sort(key=lambda item: (item["disciplina"], item["item"], item["material"]))
    return {
        "linhas": linhas,
        "resumo": {
            "itens": len(linhas),
            "massa_total_kg": round(sum(item["massa_total_kg"] for item in linhas), 2),
            "custo_total_brl": round(sum(item["custo_total_brl"] for item in linhas), 2),
        },
    }


def _optimize_cut_plan(items: list[dict[str, Any]], stock_lengths_m: list[float]) -> dict[str, Any]:
    eligible_pieces: list[dict[str, Any]] = []
    stock_options = sorted({round(float(value), 3) for value in stock_lengths_m if float(value) > 0})
    if not stock_options:
        stock_options = [6.0, 12.0]

    excluded: list[dict[str, Any]] = []
    for item in items:
        fabrication = str(item.get("fabricacao", ""))
        unit_length = float(item.get("comprimento_unitario_m", 0.0) or 0.0)
        qty = int(float(item.get("quantidade", 0.0) or 0.0))
        if fabrication not in {"laminado", "tubular"} or unit_length <= 0.0 or qty <= 0:
            excluded.append(
                {
                    "item": item.get("item"),
                    "motivo": "fora_do_escopo_de_barra_padrao",
                    "fabricacao": fabrication,
                }
            )
            continue
        if unit_length > max(stock_options):
            excluded.append(
                {
                    "item": item.get("item"),
                    "motivo": "comprimento_superior_a_barra_comercial",
                    "fabricacao": fabrication,
                }
            )
            continue
        for _ in range(qty):
            eligible_pieces.append(
                {
                    "item": item.get("item"),
                    "material": item.get("material"),
                    "length_m": unit_length,
                }
            )

    if not eligible_pieces:
        return {
            "status": "sem_itens_elegiveis",
            "waste_percent": 0.0,
            "bars": [],
            "excluded": excluded,
        }

    def pack(stock_length: float) -> dict[str, Any]:
        bars: list[dict[str, Any]] = []
        for piece in sorted(eligible_pieces, key=lambda item: item["length_m"], reverse=True):
            placed = False
            for bar in bars:
                if bar["remaining_m"] + 1e-6 >= piece["length_m"]:
                    bar["pieces"].append(piece)
                    bar["remaining_m"] = round(bar["remaining_m"] - piece["length_m"], 3)
                    placed = True
                    break
            if not placed:
                bars.append(
                    {
                        "stock_length_m": stock_length,
                        "remaining_m": round(stock_length - piece["length_m"], 3),
                        "pieces": [piece],
                    }
                )

        total_stock = round(sum(bar["stock_length_m"] for bar in bars), 3)
        total_used = round(sum(piece["length_m"] for piece in eligible_pieces), 3)
        waste = round(total_stock - total_used, 3)
        waste_percent = round((waste / total_stock) * 100.0, 3) if total_stock else 0.0
        return {
            "stock_length_m": stock_length,
            "bars": bars,
            "total_stock_m": total_stock,
            "total_used_m": total_used,
            "waste_m": waste,
            "waste_percent": waste_percent,
        }

    best = min((pack(option) for option in stock_options), key=lambda item: (item["waste_percent"], item["waste_m"]))
    formatted_bars = []
    for index, bar in enumerate(best["bars"], start=1):
        formatted_bars.append(
            {
                "barra_id": f"BAR-{index:03d}",
                "comprimento_comercial_m": bar["stock_length_m"],
                "aproveitamento_m": round(bar["stock_length_m"] - bar["remaining_m"], 3),
                "sobra_m": bar["remaining_m"],
                "pecas": [
                    {
                        "item": piece["item"],
                        "material": piece["material"],
                        "comprimento_m": piece["length_m"],
                    }
                    for piece in bar["pieces"]
                ],
            }
        )
    return {
        "status": "ok",
        "stock_length_m": best["stock_length_m"],
        "waste_percent": best["waste_percent"],
        "waste_m": best["waste_m"],
        "bars": formatted_bars,
        "excluded": excluded,
        "target_met": best["waste_percent"] < 3.0,
    }


def _render_field_memorial(project_data: dict[str, Any]) -> str:
    summary = project_data["disciplinas"]["estrutura"]["summary"]
    clash = project_data["validation"]["clash_detection"]
    bom_summary = project_data["inventario_tecnico"]["resumo"]
    beams = project_data["disciplinas"]["estrutura"]["porticos"]
    anchors = project_data["disciplinas"]["civil"]["dimensionamento_bases"]

    lines = [
        "# Memorial Tecnico Executivo - Pacote Executivo",
        "",
        f"- Data UTC: {project_data['header']['generated_at']}",
        "- Local: REGAP - Betim/MG",
        "- Modo de calculo critico: 100% local",
        "- Normas: NBR 8800, NR-12, N-1710, N-1810, N-13",
        "",
        "## 1. Estrutura",
        f"- Quantidade de porticos: {summary['qtd_porticos']}",
        f"- Flecha maxima adotada: {summary['flecha_maxima_mm']} mm",
        f"- Limite normativo: {summary['flecha_limite_mm']} mm (L/250)",
        f"- Vento adotado: {summary['velocidade_vento_m_s']} m/s em Betim/MG",
        "",
        "## 2. Interferencias",
        f"- Conflitos iniciais detectados: {clash['total_before']}",
        f"- Conflitos resolvidos apos deslocamento: {clash['total_after']}",
        f"- Escada deslocada: {clash['ladder']['relocated']}",
        f"- Tubulacao deslocada: {clash['piping']['relocated']}",
        "",
        "## 3. Verificacao de Estabilidade",
        "",
        "Formulas aplicadas (NBR 8800 - ELU):",
        "- Esbeltez: L/r = (K*L)/r",
        "- Flambagem: Fe = pi^2*E/(KL/r)^2 e Fcr conforme regime de flambagem",
        "- Momento resistente: Md = phi_b*fy*Zx",
        "- Taxa de utilizacao: eta = max(Nsd/Pn, Msd/Md, Nsd/Pn + Msd/Md)",
        "",
        "### 3.1 Resultado por Viga",
        "| Viga | Perfil | L/r | K | Md (kN.m) | Eta | Resultado |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for portico in beams:
        elu = portico["analise"]["verificacao_elu"]
        linha = (
            f"| {portico['geometria']['beam']['id']} | {portico['perfil']['designacao']} | "
            f"{elu['esbeltez_l_r']:.3f} | {elu['k_factor']:.3f} | {elu['momento_resistente']['md_kn_m']:.3f} | "
            f"{elu['taxa_utilizacao_eta']:.4f} | {elu['status']} |"
        )
        lines.append(linha)

    lines.extend(
        [
            "",
            "### 3.2 Resultado por Chumbador",
            "| Base | Grupo de chumbadores | Nt,sd (kN) | Nt,Rd (kN) | Eta | Resultado |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for base in anchors:
        check = base["verificacao_chumbadores"]
        lines.append(
            f"| {base['portico_id']} | {base['chumbadores']['quantidade']}x D{base['chumbadores']['diametro_mm']} | "
            f"{check['nt_sd_kn']:.3f} | {check['nt_rd_kn']:.3f} | {check['taxa_utilizacao_eta']:.4f} | {check['status']} |"
        )

    lines.extend(
        [
            "",
            "## 4. Civil",
            "- Reacoes de apoio exportadas para dimensionamento de placa de base e chumbadores.",
            "- Chumbadores validados por razao solicitacao/resistencia em ELU.",
            "",
            "## 5. Fabricacao",
            f"- Massa total inventariada: {bom_summary['massa_total_kg']} kg",
            f"- Custo total estimado: R$ {bom_summary['custo_total_brl']}",
            f"- Plano de corte alvo < 3%: {project_data['inventario_tecnico']['plano_corte_otimizado']['target_met']}",
            "",
            "## 6. Pintura e Preparacao de Superficie",
            "- Esquema Petrobras N-13: Pintura de manutencao.",
            "- Preparacao de superficie: jateamento ao metal quase branco Sa 2 1/2.",
            "",
            "## 7. Observacoes",
            "- Projeto executivo emitido com layers Petrobras, vistas, cortes, notas tecnicas e XData de rastreabilidade.",
            "- Consumivel de solda especificado como E7018 com garganta definida por espessura de chapa.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _regap_seal_payload() -> dict[str, Any]:
    return {
        "selo": "REGAP-CONFORME",
        "unit": "REGAP",
        "cidade": "Betim",
        "estado": "MG",
        "timestamp_utc": _utc_now(),
    }


def _regap_seal_line() -> str:
    return "SELO DE CONFORMIDADE: REGAP-CONFORME | UNIDADE: REGAP BETIM/MG"


def _render_isometric_report(project_data: dict[str, Any]) -> dict[str, Any]:
    piping = project_data["disciplinas"]["tubulacao"]
    routing = piping["routing"]
    return {
        "header": {
            "documento": "isometrico_tubulacao",
            "seal": _regap_seal_payload(),
            "normas": ["N-1810", "ASME B31.3"],
        },
        "entrada": piping["entrada"],
        "routing": {
            "points": routing.get("points", []),
            "segments": routing.get("segments", []),
            "supports": routing.get("supports", []),
            "distance_total_m": routing.get("distance_total_m", 0.0),
        },
        "xdata": piping.get("xdata", {}),
    }


def _write_mto_csv(path: Path, bom: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        writer.writerow(["SELO_REGAP", "DISCIPLINA", "ITEM", "DESCRICAO", "MATERIAL", "FABRICACAO", "QUANTIDADE", "COMPRIMENTO_TOTAL_M", "MASSA_TOTAL_KG", "CUSTO_TOTAL_BRL"])
        for item in bom.get("linhas", []):
            writer.writerow(
                [
                    "REGAP-CONFORME",
                    item.get("disciplina", ""),
                    item.get("item", ""),
                    item.get("descricao", ""),
                    item.get("material", ""),
                    item.get("fabricacao", ""),
                    item.get("quantidade", 0),
                    item.get("comprimento_total_m", 0.0),
                    item.get("massa_total_kg", 0.0),
                    item.get("custo_total_brl", 0.0),
                ]
            )
    return str(path)


def _render_painting_plan(project_data: dict[str, Any]) -> str:
    resumo = project_data["inventario_tecnico"]["resumo"]
    lines = [
        "# Plano de Pintura - Petrobras N-13",
        "",
        _regap_seal_line(),
        "",
        "## Escopo",
        "- Preparacao de superficie conforme Petrobras N-13.",
        "- Sistema primer epoxi rico em zinco + acabamento poliuretano alifatico.",
        "- Consumivel de solda de referencia: E7018 (juntas estruturais e suportes).",
        "",
        "## Base de Quantitativos",
        f"- Massa total inventariada: {resumo['massa_total_kg']} kg",
        f"- Custo total estimado: R$ {resumo['custo_total_brl']}",
        "",
        "## Critico de Campo",
        "- Validar pontos de contato com tubulacao apos montagem para evitar sombra de pintura.",
        "- Garantir cura entre demaos em conformidade com ficha tecnica do fabricante.",
        "- Registrar inspecao visual e medicao de espessura seca por lote.",
    ]
    return "\n".join(lines) + "\n"


def build_data_book_zip(export_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    artifacts = export_manifest.get("artifacts", {})
    required_map = {
        "memorial": artifacts.get("memorial_md") or artifacts.get("memorial_txt"),
        "isometricos": artifacts.get("isometrico_json"),
        "mto": artifacts.get("mto_csv"),
        "plano_pintura": artifacts.get("plano_pintura_md"),
    }

    missing = [name for name, path in required_map.items() if not path or not Path(path).exists()]
    if missing:
        raise ValueError(f"Documentos obrigatorios ausentes para Data-Book: {', '.join(missing)}")

    data_book_dir = output_dir / "execution_kit" / "data_book"
    data_book_dir.mkdir(parents=True, exist_ok=True)
    zip_path = data_book_dir / "REGAP_DataBook.zip"

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for doc_name, doc_path in required_map.items():
            src = Path(str(doc_path))
            zip_file.write(src, arcname=f"{doc_name}/{src.name}")

    return {
        "zip_path": str(zip_path),
        "documents": {name: str(path) for name, path in required_map.items()},
        "seal": _regap_seal_payload(),
    }


def audit_regap_conformity(export_manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = export_manifest.get("artifacts", {})
    checks: list[dict[str, Any]] = [
        {
            "documento": "memorial",
            "path": artifacts.get("memorial_md") or artifacts.get("memorial_txt"),
            "required_token": "REGAP",
        },
        {
            "documento": "isometricos",
            "path": artifacts.get("isometrico_json"),
            "required_token": "REGAP-CONFORME",
        },
        {
            "documento": "mto",
            "path": artifacts.get("mto_csv"),
            "required_token": "REGAP-CONFORME",
        },
        {
            "documento": "plano_pintura",
            "path": artifacts.get("plano_pintura_md"),
            "required_token": "REGAP-CONFORME",
        },
    ]

    report: list[dict[str, Any]] = []
    for check in checks:
        doc_path = check["path"]
        exists = bool(doc_path) and Path(str(doc_path)).exists()
        has_token = False
        if exists:
            try:
                text = Path(str(doc_path)).read_text(encoding="utf-8", errors="ignore")
                has_token = str(check["required_token"]) in text
            except Exception:
                has_token = False
        report.append(
            {
                "documento": check["documento"],
                "path": doc_path,
                "exists": exists,
                "token_required": check["required_token"],
                "token_found": has_token,
                "status": "ok" if exists and has_token else "nao_conforme",
            }
        )

    ok_count = len([item for item in report if item["status"] == "ok"])
    return {
        "status": "ok" if ok_count == len(report) else "nao_conforme",
        "total": len(report),
        "conformes": ok_count,
        "nao_conformes": len(report) - ok_count,
        "detalhes": report,
    }


def _default_cut_angles(item_name: str) -> tuple[float, float]:
    if "PIPE" in item_name:
        return (37.5, 37.5)
    if "VIGA" in item_name:
        return (45.0, 45.0)
    return (90.0, 90.0)


def _render_master_cut_plan_txt(project_data: dict[str, Any]) -> str:
    detailed_items = project_data["inventario_tecnico"].get("itens_detalhados", [])
    lines = [
        "PLANO DE CORTE MASTER - CHAO DE FABRICA",
        "item;material;quantidade;comprimento_unitario_m;angulo_inicio_graus;angulo_fim_graus;peso_unitario_kg;cubagem_unitaria_m3;cubagem_total_m3",
    ]

    for item in detailed_items:
        item_name = str(item.get("item", "SEM_ITEM"))
        material = str(item.get("material", "ASTM A36"))
        density = float(STANDARD_MATERIALS.get(material, STANDARD_MATERIALS["ASTM A36"])["density_kg_m3"])
        qty = max(float(item.get("quantidade", 0.0) or 0.0), 0.0)
        if qty <= 0.0:
            continue

        total_mass_kg = float(item.get("massa_total_kg", 0.0) or 0.0)
        unit_weight_kg = total_mass_kg / qty
        unit_length_m = float(item.get("comprimento_unitario_m", 0.0) or 0.0)
        if unit_length_m > 0.0 and density > 0.0:
            area_m2 = (unit_weight_kg / unit_length_m) / density
            unit_volume_m3 = area_m2 * unit_length_m
        else:
            unit_volume_m3 = unit_weight_kg / density if density > 0.0 else 0.0

        total_volume_m3 = unit_volume_m3 * qty
        angle_start, angle_end = _default_cut_angles(item_name)

        lines.append(
            ";".join(
                [
                    item_name,
                    material,
                    f"{qty:.0f}",
                    f"{unit_length_m:.3f}",
                    f"{angle_start:.1f}",
                    f"{angle_end:.1f}",
                    f"{unit_weight_kg:.3f}",
                    f"{unit_volume_m3:.6f}",
                    f"{total_volume_m3:.6f}",
                ]
            )
        )

    return "\n".join(lines) + "\n"


def _render_dxf(project_data: dict[str, Any]) -> str:
    entities: list[str] = []

    def add_line(layer: str, start: dict[str, float], end: dict[str, float], xdata: dict[str, Any]) -> None:
        entities.extend(
            [
                "0", "LINE",
                "8", layer,
                "10", str(start["x"]),
                "20", str(start["y"]),
                "30", str(start["z"]),
                "11", str(end["x"]),
                "21", str(end["y"]),
                "31", str(end["z"]),
                "1001", "SMARTDESIGN",
                "1000", json.dumps(xdata, ensure_ascii=True),
            ]
        )

    for portico in project_data["disciplinas"]["estrutura"]["porticos"]:
        add_line("ESTR_PORTICOS", portico["geometria"]["left_column"]["start"], portico["geometria"]["left_column"]["end"], portico["xdata"])
        add_line("ESTR_PORTICOS", portico["geometria"]["right_column"]["start"], portico["geometria"]["right_column"]["end"], portico["xdata"])
        add_line("ESTR_PORTICOS", portico["geometria"]["beam"]["start"], portico["geometria"]["beam"]["end"], portico["xdata"])

    ladder = project_data["disciplinas"]["mecanica"]["escada"]
    ladder_origin = ladder["placement"]["origin"]
    ladder_height = ladder["geometry"]["altura_total_mm"]
    add_line(
        "MEC_ESCADAS",
        ladder_origin,
        {"x": ladder_origin["x"], "y": ladder_origin["y"] + ladder_height, "z": ladder_origin["z"]},
        ladder["xdata"],
    )

    for segment in project_data["disciplinas"]["tubulacao"]["routing"]["segments"]:
        add_line("PIPING", segment["start"], segment["end"], project_data["disciplinas"]["tubulacao"]["xdata"])

    return "\n".join(
        [
            "0", "SECTION",
            "2", "HEADER",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "TABLES",
            "0", "TABLE",
            "2", "APPID",
            "70", "1",
            "0", "APPID",
            "2", "SMARTDESIGN",
            "70", "0",
            "0", "ENDTAB",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "ENTITIES",
            *entities,
            "0", "ENDSEC",
            "0", "EOF",
        ]
    )


def export_execution_kit(project_data: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    root = output_dir / "execution_kit"
    drawings_dir = root / "desenhos"
    procurement_dir = root / "compras"
    calculations_dir = root / "calculos"
    reports_dir = root / "relatorios"
    civil_dir = root / "civil"

    drawing_json_path = _write_json(drawings_dir / "smartdesign_execution_package.json", project_data["drawing_package"])
    drawing_dxf_path = _write_text(drawings_dir / "smartdesign_execution_package.dxf", _render_dxf(project_data))
    master_path = _write_json(root / "master_technical_spec.json", project_data)
    bom_path = _write_json(procurement_dir / "bom_completo.json", project_data["inventario_tecnico"])
    cut_plan_path = _write_json(procurement_dir / "plano_corte_otimizado.json", project_data["inventario_tecnico"]["plano_corte_otimizado"])
    cut_plan_master_txt = _write_text(procurement_dir / "plano_de_corte_master.txt", _render_master_cut_plan_txt(project_data))
    support_path = _write_json(civil_dir / "reacoes_apoio_porticos.json", {"reacoes": project_data["disciplinas"]["civil"]["reacoes_apoio"]})
    civil_path = _write_json(civil_dir / "dimensionamento_base_e_chumbadores.json", {"bases": project_data["disciplinas"]["civil"]["dimensionamento_bases"]})

    memorial_content = _render_field_memorial(project_data)
    memorial_sealed = f"{_regap_seal_line()}\n\n{memorial_content}"
    memorial_md = _write_text(calculations_dir / "memorial_calculo_simplificado.md", memorial_sealed)
    memorial_txt = _write_text(calculations_dir / "memorial_calculo_simplificado.txt", memorial_sealed)

    isometric_payload = _render_isometric_report(project_data)
    isometric_json_path = _write_json(reports_dir / "isometrico_tubulacao_regap.json", isometric_payload)
    mto_csv_path = _write_mto_csv(procurement_dir / "mto_regap.csv", project_data["inventario_tecnico"])
    painting_plan_md = _write_text(reports_dir / "plano_pintura_n13.md", _render_painting_plan(project_data))

    memorial_pdf_path: str | None = None
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        pdf_target = calculations_dir / "memorial_calculo_simplificado.pdf"
        c = canvas.Canvas(str(pdf_target), pagesize=A4)
        y = 800
        for line in memorial_content.splitlines():
            c.drawString(36, y, line[:120])
            y -= 14
            if y < 40:
                c.showPage()
                y = 800
        c.save()
        memorial_pdf_path = str(pdf_target)
    except Exception:
        memorial_pdf_path = None

    roi_json = project_data["artifacts"]["roi_json"]
    roi_md = project_data["artifacts"]["roi_markdown"]

    export_manifest = {
        "status": "ok",
        "root_dir": str(root),
        "artifacts": {
            "drawing_json": drawing_json_path,
            "drawing_dxf": drawing_dxf_path,
            "master_technical_spec": master_path,
            "bom_completo": bom_path,
            "plano_corte_otimizado": cut_plan_path,
            "plano_de_corte_master_txt": cut_plan_master_txt,
            "reacoes_apoio": support_path,
            "dimensionamento_base": civil_path,
            "memorial_md": memorial_md,
            "memorial_txt": memorial_txt,
            "memorial_pdf": memorial_pdf_path,
            "roi_json": roi_json,
            "roi_markdown": roi_md,
            "isometrico_json": isometric_json_path,
            "mto_csv": mto_csv_path,
            "plano_pintura_md": painting_plan_md,
        },
    }

    export_manifest["data_book"] = build_data_book_zip(export_manifest, output_dir)
    export_manifest["regap_audit"] = audit_regap_conformity(export_manifest)

    _write_json(root / "export_manifest.json", export_manifest)
    return export_manifest


def generate_full_unit_project(
    output_dir: Path,
    altura_torre_m: float,
    qtd_porticos: int = 50,
    ponto_succao: dict[str, float] | None = None,
    ponto_descarga: dict[str, float] | None = None,
    diametro_nominal_mm: float = 100.0,
    stock_lengths_m: list[float] | None = None,
) -> dict[str, Any]:
    if qtd_porticos <= 0:
        raise ValueError("qtd_porticos deve ser maior que zero")
    if diametro_nominal_mm <= 0.0:
        raise ValueError("diametro_nominal_mm deve ser maior que zero")

    output_dir.mkdir(parents=True, exist_ok=True)
    stock_lengths = stock_lengths_m or [6.0, 12.0]
    clearance_mm = float(get_rule_param("N-1810", "routing.min_clearance_to_structure_mm", 150.0))

    porticos_package = _generate_porticos(qtd_porticos)
    escada = processar_escada_marinheiro(altura_torre_m, output_dir)
    ladder_payload = escada["payload"]
    ladder_result = ladder_payload["resultado"]
    ladder_params = ladder_payload["parametros_escada"]

    ladder_origin = {"x": 800.0, "y": 0.0, "z": 0.0}
    ladder_size = {
        "dx": float(ladder_params["diametro_gaiola_mm"]),
        "dy": float(ladder_result["altura_total_mm"]),
        "dz": float(ladder_params["diametro_gaiola_mm"]),
    }
    ladder_initial_clashes = _detect_clashes(
        [_build_accessory_component("ESCADA", ladder_origin, ladder_size)],
        porticos_package["beam_components"],
        clearance_mm,
    )
    ladder_resolution = _resolve_vertical_accessory_clash(
        component_id="ESCADA",
        origin=ladder_origin,
        size=ladder_size,
        beam_components=porticos_package["beam_components"],
        clearance_mm=clearance_mm,
        shift_axis="z",
        shift_step_mm=900.0,
        max_iterations=12,
    )

    ponto_a = ponto_succao or {"x": 1500.0, "y": 7600.0, "z": 0.0}
    ponto_b = ponto_descarga or {"x": 23_500.0, "y": 7600.0, "z": 6000.0}
    router_engine = PipingAutoRouter(output_dir)
    route_points = router_engine._route_points(dict(ponto_a), dict(ponto_b))
    piping_initial_clashes = _detect_clashes(_build_piping_components(route_points, diametro_nominal_mm), porticos_package["beam_components"], clearance_mm)
    piping_shift_count = 0
    while piping_initial_clashes and piping_shift_count < 12:
        ponto_a = {**ponto_a, "y": float(ponto_a["y"]) - 600.0}
        ponto_b = {**ponto_b, "y": float(ponto_b["y"]) - 600.0}
        route_points = router_engine._route_points(dict(ponto_a), dict(ponto_b))
        piping_initial_clashes = _detect_clashes(_build_piping_components(route_points, diametro_nominal_mm), porticos_package["beam_components"], clearance_mm)
        piping_shift_count += 1

    piping = router_engine.generate(
        ponto_a=dict(ponto_a),
        ponto_b=dict(ponto_b),
        diametro_nominal_mm=diametro_nominal_mm,
        material=str(get_rule_param("N-1810", "materials.default_pipe_material", "ASTM A106 Gr.B")),
        schedule=str(get_rule_param("N-1810", "materials.default_schedule", "STD")),
    )
    piping_payload = piping["payload"]
    piping_material = str(piping_payload["entrada"]["material"])
    _validate_material(piping_material)

    structure_bom = [_flatten_bom_item(item, "estrutura_core") for item in porticos_package["bom"]]
    ladder_bom = []
    for item in ladder_payload["bom"]:
        converted = {
            "disciplina": "mecanica",
            "item": item["item"],
            "descricao": item["descricao"],
            "quantidade": item.get("quantidade", 0),
            "comprimento_total_m": item.get("comprimento_total_m", 0.0),
            "comprimento_unitario_m": round(float(item.get("comprimento_total_m", 0.0)) / max(float(item.get("quantidade", 1) or 1), 1.0), 3),
            "material": str(item.get("material", "ASTM A36")),
            "fabricacao": str(item.get("fabricacao", "tubular")),
            "massa_total_kg": item.get("massa_total_kg", 0.0),
        }
        ladder_bom.append(_flatten_bom_item(converted, "escada_marinheiro"))

    piping_bom = []
    for item in piping_payload["bom"]:
        converted = {
            "disciplina": "tubulacao",
            "item": item["item"],
            "descricao": item["descricao"],
            "quantidade": item.get("quantidade", 0),
            "comprimento_total_m": item.get("comprimento_total_m", item.get("comprimento_m", 0.0)),
            "material": str(item.get("material", piping_material)),
            "fabricacao": "tubular" if item["item"] == "PIPE_STRAIGHT" else "industrializado",
            "massa_total_kg": item.get("massa_total_kg", 0.0),
        }
        if converted["item"] == "PIPE_STRAIGHT":
            converted["comprimento_unitario_m"] = round(min(float(converted["comprimento_total_m"] or 0.0), max(stock_lengths)), 3)
            converted["quantidade"] = max(1, int(math.ceil(float(converted["comprimento_total_m"] or 0.0) / max(stock_lengths))))
        piping_bom.append(_flatten_bom_item(converted, "piping_autorouter"))

    all_bom_items = structure_bom + ladder_bom + piping_bom
    aggregated_bom = _aggregate_bom(all_bom_items)
    cut_plan = _optimize_cut_plan(ladder_bom + piping_bom, stock_lengths)
    aggregated_bom["plano_corte_otimizado"] = cut_plan
    aggregated_bom["itens_detalhados"] = all_bom_items

    roi = gerar_business_impact(float(aggregated_bom["resumo"]["massa_total_kg"]), output_dir / "reports")

    ladder_xdata = _build_xdata(
        categoria="ESCADA_MARINHEIRO",
        origem="generate_full_unit_project",
        status_validacao_carga="ok" if ladder_resolution["resolved"] else "pendente_revisao",
        extra={
            "norma": ladder_payload["header"]["norma"],
            "peso_total_kg": ladder_result["peso_total_kg"],
        },
    )
    piping_xdata = _build_xdata(
        categoria="TUBULACAO",
        origem="generate_full_unit_project",
        status_validacao_carga="ok",
        extra={
            "material": piping_material,
            "schedule": piping_payload["entrada"]["schedule"],
        },
    )

    drawing_package = {
        "header": {
            "project": "SMARTDESIGN_CORE_EXECUTION_PACKAGE",
            "generated_at": _utc_now(),
            "zero_real": str(get_rule_param("REGAP", "drafting.zero_real_label", "Zero Real")),
            "layers": list(get_rule_param("REGAP", "drafting.layers", DRAWING_LAYERS)),
        },
        "objects": {
            "porticos": porticos_package["porticos"],
            "escada": {
                "id": "ESCADA-01",
                "placement": {"origin": ladder_resolution["component"]["origin"], "relocated": ladder_resolution["iterations"] > 0},
                "geometry": {
                    "altura_total_mm": ladder_result["altura_total_mm"],
                    "largura_mm": ladder_params["largura_escada_mm"],
                    "diametro_gaiola_mm": ladder_params["diametro_gaiola_mm"],
                },
                "xdata": ladder_xdata,
            },
            "tubulacao": {
                "routing": piping_payload["routing"],
                "xdata": piping_xdata,
            },
        },
        "detalhamento": {
            "vistas": list(get_rule_param("REGAP", "drafting.required_views", ["planta_baixa", "vista_frontal", "vista_lateral", "corte_a", "corte_b"])),
            "cotas": {
                "lineares": [
                    {"id": "COTA-VAO", "valor_mm": 25_000.0, "referencia": "Zero Real"},
                    {"id": "COTA-ALTURA", "valor_mm": 8_000.0, "referencia": "Zero Real"},
                    {"id": "COTA-ESCADA", "valor_mm": ladder_result["altura_total_mm"], "referencia": "Zero Real"},
                ],
                "niveis": [
                    {"id": "NIV-000", "elevacao_mm": 0.0, "label": "Zero Real"},
                    {"id": "NIV-BEAM", "elevacao_mm": 8_000.0, "label": "+8.000"},
                ],
            },
            "ligacoes": [portico["ligacao_viga_pilar"] for portico in porticos_package["porticos"][:2]],
            "notas_tecnicas": list(get_rule_param("REGAP", "drafting.default_notes", [])),
            "data_book": {
                "aco_estrutural": ["ASTM A36", "ASTM A572 Gr. 50"],
                "consumivel_solda": "E7018",
                "pintura": "Petrobras N-13",
            },
        },
    }

    project_data = {
        "header": {
            "project": "SMARTDESIGN_CORE_CONSOLIDADO",
            "generated_at": _utc_now(),
            "critical_execution_mode": "local-only",
            "cloud_dependency_for_critical_path": False,
            "normas_aplicadas": ["NBR 8800", "NR-12", "N-1710", "N-1810", "N-13"],
            "norma_metadata": _norma_metadata(),
        },
        "disciplinas": {
            "estrutura": {
                "porticos": porticos_package["porticos"],
                "summary": porticos_package["summary"],
            },
            "mecanica": {
                "escada": {
                    "artifact": escada["artifact"],
                    "placement": {
                        "origin": ladder_resolution["component"]["origin"],
                        "relocated": ladder_resolution["iterations"] > 0,
                        "shift_z_mm": round(float(ladder_resolution["component"]["origin"]["z"]) - float(ladder_origin["z"]), 3),
                    },
                    "geometry": {
                        "altura_total_mm": ladder_result["altura_total_mm"],
                        "largura_escada_mm": ladder_params["largura_escada_mm"],
                        "diametro_gaiola_mm": ladder_params["diametro_gaiola_mm"],
                        "quantidade_degraus": ladder_result["quantidade_degraus"],
                    },
                    "resultado": ladder_result,
                    "xdata": ladder_xdata,
                },
            },
            "tubulacao": {
                "artifact": piping["artifact"],
                "routing": piping_payload["routing"],
                "entrada": piping_payload["entrada"],
                "xdata": piping_xdata,
            },
            "civil": {
                "reacoes_apoio": porticos_package["support_reactions"],
                "dimensionamento_bases": porticos_package["civil_design"],
            },
        },
        "validation": {
            "materials_dictionary": {"allowed": sorted(STANDARD_MATERIALS.keys())},
            "clash_detection": {
                "prioridade": "estrutura",
                "clearance_mm": clearance_mm,
                "ladder": {
                    "before": ladder_initial_clashes,
                    "after": _detect_clashes([ladder_resolution["component"]], porticos_package["beam_components"], clearance_mm),
                    "relocated": ladder_resolution["iterations"] > 0,
                },
                "piping": {
                    "before": _detect_clashes(_build_piping_components(router_engine._route_points({"x": 1500.0, "y": 7600.0, "z": 0.0}, {"x": 23_500.0, "y": 7600.0, "z": 6000.0}), diametro_nominal_mm), porticos_package["beam_components"], clearance_mm),
                    "after": _detect_clashes(_build_piping_components(piping_payload["routing"]["points"], diametro_nominal_mm), porticos_package["beam_components"], clearance_mm),
                    "relocated": piping_shift_count > 0,
                },
                "total_before": len(ladder_initial_clashes) + len(_detect_clashes(_build_piping_components(router_engine._route_points({"x": 1500.0, "y": 7600.0, "z": 0.0}, {"x": 23_500.0, "y": 7600.0, "z": 6000.0}), diametro_nominal_mm), porticos_package["beam_components"], clearance_mm)),
                "total_after": len(_detect_clashes([ladder_resolution["component"]], porticos_package["beam_components"], clearance_mm)) + len(_detect_clashes(_build_piping_components(piping_payload["routing"]["points"], diametro_nominal_mm), porticos_package["beam_components"], clearance_mm)),
            },
            "verificacao_estabilidade": {
                "vigas": [
                    {
                        "id": portico["geometria"]["beam"]["id"],
                        "perfil": portico["perfil"]["designacao"],
                        "eta": portico["analise"]["verificacao_elu"]["taxa_utilizacao_eta"],
                        "resultado": portico["analise"]["verificacao_elu"]["status"],
                    }
                    for portico in porticos_package["porticos"]
                ],
                "chumbadores": [
                    {
                        "id": base["portico_id"],
                        "eta": base["verificacao_chumbadores"]["taxa_utilizacao_eta"],
                        "resultado": base["verificacao_chumbadores"]["status"],
                    }
                    for base in porticos_package["civil_design"]
                ],
            },
        },
        "inventario_tecnico": aggregated_bom,
        "drawing_package": drawing_package,
        "artifacts": {
            "roi_json": roi["json_artifact"],
            "roi_markdown": roi["markdown_artifact"],
        },
    }

    master_path = output_dir / "master_technical_spec.json"
    master_path.write_text(json.dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8")
    project_data["artifacts"]["master_technical_spec"] = str(master_path)
    return project_data