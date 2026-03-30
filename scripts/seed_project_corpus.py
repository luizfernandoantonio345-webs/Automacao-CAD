from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING_ROOT = ROOT / "engenharia_automacao"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from engenharia_automacao.core.main import ProjectService
from integration.python_api.telemetry import ProjectTelemetryStore


PARTS = ["Tubo", "Curva", "Tee", "Flange", "Reducer", "Valve"]
COMPANIES = [
    "Atlas Engenharia",
    "Engenharia CAD Labs",
    "Norte Tubulacoes",
    "Sul Processos",
    "Montreal Plantas",
    "Omega Piping",
]


def build_payload(index: int) -> dict:
    part = PARTS[index % len(PARTS)]
    company = COMPANIES[index % len(COMPANIES)]
    diameter = 50 + (index % 40) * 12.5
    length = 120 + (index % 55) * 35
    return {
        "diameter": diameter,
        "length": length,
        "company": company,
        "part_name": part,
        "code": f"AUTO-{index:04d}",
    }


def main(total: int = 1200) -> int:
    output_dir = ROOT / "data" / "bootstrap_projects"
    telemetry = ProjectTelemetryStore(ROOT / "data" / "telemetry")
    service = ProjectService()

    output_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for index in range(1, total + 1):
        payload = build_payload(index)
        result = service.generate_project(payload, output_dir, execute_in_autocad=False)
        telemetry.record_event(payload, source="seed.bootstrap", result_path=str(result))
        created += 1

    stats = telemetry.rebuild_stats()
    print(f"Projetos gerados: {created}")
    print(f"Diretorio: {output_dir}")
    print(f"Eventos: {telemetry.events_file}")
    print(f"Stats: {telemetry.stats_file}")
    print(f"Total acumulado em telemetria: {stats['total_projects']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
