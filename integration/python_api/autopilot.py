from __future__ import annotations

import json
import math
import re
from pathlib import Path
from uuid import uuid4

from integration.python_api.postgres_repositories import (
    MaterialModel,
    ProjectHistoryModel,
    create_database_engine,
    create_session_factory,
    init_database,
)


PROFILE_LIBRARY = [
    {"name": "W200x15", "ix": 1_840.0, "wx": 184.0, "mass_kg_m": 15.0},
    {"name": "W250x25", "ix": 4_080.0, "wx": 326.0, "mass_kg_m": 25.0},
    {"name": "W310x32", "ix": 7_250.0, "wx": 468.0, "mass_kg_m": 32.0},
    {"name": "W360x44", "ix": 12_900.0, "wx": 718.0, "mass_kg_m": 44.0},
    {"name": "W410x60", "ix": 20_200.0, "wx": 985.0, "mass_kg_m": 60.0},
]

DEFAULT_MATERIALS = [
    {"name": "Aço ASTM A36", "density": 7.85, "price_per_kg": 8.9, "cad_hatch": "ANSI31"},
    {"name": "Inox 316", "density": 8.0, "price_per_kg": 24.5, "cad_hatch": "AR-CONC"},
    {"name": "Aço SAE 1020", "density": 7.87, "price_per_kg": 9.8, "cad_hatch": "STEEL"},
]

PETROBRAS_APPROVED_MATERIALS = {
    "aço astm a36",
    "aco astm a36",
    "inox 316",
}


class AutopilotService:
    def __init__(self, database_url: str, output_dir: Path) -> None:
        self._ensure_database_parent(database_url)
        self.engine = create_database_engine(database_url)
        init_database(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self.output_dir = Path(output_dir)
        self.autopilot_dir = self.output_dir / "autopilot"
        self.autopilot_dir.mkdir(parents=True, exist_ok=True)
        self._seed_materials()

    def _seed_materials(self) -> None:
        with self.session_factory() as session:
            existing = {material.name.lower() for material in session.query(MaterialModel).all()}
            for item in DEFAULT_MATERIALS:
                if item["name"].lower() in existing:
                    continue
                session.add(MaterialModel(**item))
            session.commit()

    def _ensure_database_parent(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            return
        database_path = Path(database_url.replace("sqlite:///", "", 1))
        database_path.parent.mkdir(parents=True, exist_ok=True)

    def list_materials(self) -> list[dict]:
        with self.session_factory() as session:
            materials = session.query(MaterialModel).order_by(MaterialModel.name.asc()).all()
            return [
                {
                    "id": material.id,
                    "name": material.name,
                    "density": float(material.density),
                    "price_per_kg": float(material.price_per_kg),
                    "cad_hatch": material.cad_hatch or "",
                }
                for material in materials
            ]

    def execute(self, payload: dict) -> dict:
        with self.session_factory() as session:
            material = session.query(MaterialModel).filter(MaterialModel.id == payload["material_id"]).first()
            if material is None:
                raise ValueError("Material selecionado nao encontrado")

            span_m = float(payload["shed_width_m"])
            load_knm = float(payload["load_knm"])
            selected_profile, analysis = self._optimize_profile(span_m, load_knm)
            if selected_profile is None:
                raise ValueError("Nenhum perfil seguro encontrado para a combinacao de vao e carga")

            portal_count = max(2, math.ceil(float(payload["shed_length_m"]) / float(payload["bay_spacing_m"])) + 1)
            roof_rise_m = (float(payload["shed_width_m"]) / 2.0) * (float(payload["roof_slope_percent"]) / 100.0)
            beam_length_m = math.sqrt((float(payload["shed_width_m"]) / 2.0) ** 2 + roof_rise_m ** 2) * 2.0
            flange_allowance_m = portal_count * 4 * 0.35
            total_steel_length_m = portal_count * ((2.0 * float(payload["eave_height_m"])) + beam_length_m) + flange_allowance_m
            estimated_weight = round(total_steel_length_m * float(selected_profile["mass_kg_m"]), 2)
            estimated_cost = round(estimated_weight * float(material.price_per_kg), 2)

            compliance = self._build_compliance(material, analysis, payload, portal_count)
            cad_payload = self._build_cad_payload(payload, material, selected_profile, analysis, portal_count, roof_rise_m)

            safe_code = self._slugify(payload["code"])
            cad_payload_path = self.autopilot_dir / f"{safe_code}_cad_payload.json"
            report_path = self.autopilot_dir / f"{safe_code}_memorial.pdf"

            cad_payload_path.write_text(json.dumps(cad_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._write_pdf_report(
                report_path,
                title=f"Memorial SmartDesign - {payload['project_name']}",
                lines=self._build_report_lines(payload, material, selected_profile, analysis, compliance, estimated_weight, estimated_cost, cad_payload_path),
            )

            history = ProjectHistoryModel(
                id=str(uuid4()),
                code=str(payload["code"]),
                project_name=str(payload["project_name"]),
                company=str(payload["company"]),
                parameters_json=json.dumps(payload, ensure_ascii=False),
                estimated_weight=estimated_weight,
                estimated_cost=estimated_cost,
                compliance_status=compliance["status"],
                selected_profile=str(selected_profile["name"]),
                material_name=str(material.name),
                report_path=str(report_path),
                cad_payload_path=str(cad_payload_path),
            )
            session.add(history)
            session.commit()

        return {
            "project_id": history.id,
            "code": str(payload["code"]),
            "project_name": str(payload["project_name"]),
            "selected_profile": selected_profile,
            "analysis": analysis,
            "compliance": compliance,
            "estimated_weight": estimated_weight,
            "estimated_cost": estimated_cost,
            "portal_count": portal_count,
            "report_path": str(report_path),
            "cad_payload_path": str(cad_payload_path),
            "cad_bridge_event": "comando_cad",
            "cad_payload_preview": cad_payload["entidades"][:6],
        }

    def _seed_materials(self) -> None:
        with self.session_factory() as session:
            existing = {material.name.lower() for material in session.query(MaterialModel).all()}
            for item in DEFAULT_MATERIALS:
                if item["name"].lower() in existing:
                    continue
                session.add(MaterialModel(**item))
            session.commit()

    def _optimize_profile(self, span_m: float, load_knm: float) -> tuple[dict | None, dict | None]:
        for profile in sorted(PROFILE_LIBRARY, key=lambda item: item["mass_kg_m"]):
            analysis = self._analyze_structure(span_m, load_knm, profile)
            if analysis["safe"]:
                return profile, analysis
        if PROFILE_LIBRARY:
            fallback = PROFILE_LIBRARY[-1]
            return fallback, self._analyze_structure(span_m, load_knm, fallback)
        return None, None

    def _analyze_structure(self, span_m: float, load_knm: float, profile: dict) -> dict:
        elastic_modulus = 200_000.0
        fyk = 250.0
        span_mm = span_m * 1_000.0
        inertia_mm4 = float(profile["ix"]) * 10_000.0
        flecha_mm = (5.0 * (load_knm / 1_000.0) * (span_mm ** 4)) / (384.0 * elastic_modulus * inertia_mm4)
        limite_mm = span_mm / 250.0
        tensao_mpa = ((load_knm * (span_m ** 2) / 8.0) * 1_000_000.0) / (float(profile["wx"]) * 1_000.0)
        limite_tensao = fyk * 0.6
        safe = flecha_mm < limite_mm and tensao_mpa < limite_tensao
        return {
            "safe": safe,
            "deflection_mm": round(flecha_mm, 2),
            "deflection_limit_mm": round(limite_mm, 2),
            "stress_mpa": round(tensao_mpa, 2),
            "stress_limit_mpa": round(limite_tensao, 2),
            "utilization": f"{(tensao_mpa / limite_tensao) * 100.0:.1f}%",
            "status": "Estavel" if flecha_mm < limite_mm else "Critico",
        }

    def _build_compliance(self, material: MaterialModel, analysis: dict, payload: dict, portal_count: int) -> dict:
        checks = [
            {
                "rule": "Flecha maxima L/250",
                "status": "ok" if analysis["deflection_mm"] <= analysis["deflection_limit_mm"] else "alert",
                "detail": f"{analysis['deflection_mm']} mm / limite {analysis['deflection_limit_mm']} mm",
            },
            {
                "rule": "Tensao admissivel 60% do fyk",
                "status": "ok" if analysis["stress_mpa"] <= analysis["stress_limit_mpa"] else "alert",
                "detail": f"{analysis['stress_mpa']} MPa / limite {analysis['stress_limit_mpa']} MPa",
            },
            {
                "rule": "Material homologado Petrobras",
                "status": "ok" if material.name.strip().lower() in PETROBRAS_APPROVED_MATERIALS else "review",
                "detail": material.name,
            },
            {
                "rule": "Modulo repetitivo do galpao",
                "status": "ok" if portal_count >= 2 and float(payload["bay_spacing_m"]) > 0 else "review",
                "detail": f"{portal_count} porticos com espacamento de {payload['bay_spacing_m']} m",
            },
        ]
        approved = all(item["status"] == "ok" for item in checks)
        return {
            "status": "Aprovado Petrobras" if approved else "Revisao Petrobras",
            "checks": checks,
        }

    def _build_cad_payload(
        self,
        payload: dict,
        material: MaterialModel,
        profile: dict,
        analysis: dict,
        portal_count: int,
        roof_rise_m: float,
    ) -> dict:
        bay_spacing_mm = float(payload["bay_spacing_m"]) * 1_000.0
        width_mm = float(payload["shed_width_m"]) * 1_000.0
        height_mm = float(payload["eave_height_m"]) * 1_000.0
        roof_rise_mm = roof_rise_m * 1_000.0
        entities: list[dict] = []

        for index in range(portal_count):
            origin_x = index * bay_spacing_mm
            entities.extend(
                [
                    {
                        "tipo": "coluna",
                        "frame": index + 1,
                        "perfil": profile["name"],
                        "material": material.name,
                        "inicio": [origin_x, 0.0, 0.0],
                        "fim": [origin_x, height_mm, 0.0],
                    },
                    {
                        "tipo": "coluna",
                        "frame": index + 1,
                        "perfil": profile["name"],
                        "material": material.name,
                        "inicio": [origin_x + width_mm, 0.0, 0.0],
                        "fim": [origin_x + width_mm, height_mm, 0.0],
                    },
                    {
                        "tipo": "viga",
                        "frame": index + 1,
                        "perfil": profile["name"],
                        "material": material.name,
                        "inicio": [origin_x, height_mm, 0.0],
                        "meio": [origin_x + (width_mm / 2.0), height_mm + roof_rise_mm, 0.0],
                        "fim": [origin_x + width_mm, height_mm, 0.0],
                    },
                    {
                        "tipo": "flange",
                        "frame": index + 1,
                        "posicao": [origin_x, height_mm, 0.0],
                        "comprimento_mm": 350.0,
                        "hachura": material.cad_hatch or "ANSI31",
                    },
                    {
                        "tipo": "flange",
                        "frame": index + 1,
                        "posicao": [origin_x + width_mm, height_mm, 0.0],
                        "comprimento_mm": 350.0,
                        "hachura": material.cad_hatch or "ANSI31",
                    },
                    {
                        "tipo": "cota_alinhada",
                        "frame": index + 1,
                        "inicio": [origin_x, 0.0, 0.0],
                        "fim": [origin_x + width_mm, 0.0, 0.0],
                        "texto": f"Vao {payload['shed_width_m']} m",
                    },
                ]
            )

        return {
            "event": "executar_desenho",
            "project": {
                "project_name": payload["project_name"],
                "company": payload["company"],
                "code": payload["code"],
                "portal_count": portal_count,
                "material": material.name,
                "profile": profile["name"],
                "analysis": analysis,
            },
            "entidades": entities,
        }

    def _build_report_lines(
        self,
        payload: dict,
        material: MaterialModel,
        profile: dict,
        analysis: dict,
        compliance: dict,
        estimated_weight: float,
        estimated_cost: float,
        cad_payload_path: Path,
    ) -> list[str]:
        return [
            f"Projeto: {payload['project_name']}",
            f"Codigo: {payload['code']}",
            f"Empresa: {payload['company']}",
            f"Galpao: {payload['shed_width_m']} m x {payload['shed_length_m']} m",
            f"Pe direito: {payload['eave_height_m']} m | inclinacao: {payload['roof_slope_percent']}%",
            f"Carga de projeto: {payload['load_knm']} kN.m",
            f"Material: {material.name} | densidade {float(material.density):.2f} g/cm3 | R$ {float(material.price_per_kg):.2f}/kg",
            f"Perfil otimizado: {profile['name']} | massa linear {profile['mass_kg_m']} kg/m",
            f"Flecha: {analysis['deflection_mm']} mm / limite {analysis['deflection_limit_mm']} mm",
            f"Tensao: {analysis['stress_mpa']} MPa / limite {analysis['stress_limit_mpa']} MPa",
            f"Aproveitamento: {analysis['utilization']} | status: {analysis['status']}",
            f"Conformidade: {compliance['status']}",
            f"Peso estimado: {estimated_weight:.2f} kg",
            f"Custo estimado: R$ {estimated_cost:.2f}",
            f"Envelope CAD: {cad_payload_path}",
            "Fluxo preparado para ponte CAD externa no evento 'comando_cad'.",
        ]

    def _write_pdf_report(self, path: Path, title: str, lines: list[str]) -> None:
        def escape(value: str) -> str:
            return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        content_lines = ["BT", "/F1 16 Tf", "50 800 Td", f"({escape(title)}) Tj", "0 -28 Td", "/F1 10 Tf"]
        for line in lines[:40]:
            content_lines.append(f"({escape(str(line))}) Tj")
            content_lines.append("0 -14 Td")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")

        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)
        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
        )
        path.write_bytes(pdf)

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_")
        return normalized or "autopilot"