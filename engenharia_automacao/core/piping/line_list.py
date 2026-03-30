from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LineListEntry:
    tag: str
    diameter_mm: float
    operating_pressure_bar: float
    hydrotest_pressure_bar: float
    pressure_class: str
    material: str
    flange_face: str
    selected_schedule: str


def build_line_list_entry(
    *,
    tag: str,
    diameter_mm: float,
    operating_pressure_bar: float,
    hydrotest_pressure_bar: float,
    pressure_class: str,
    material: str,
    flange_face: str,
    selected_schedule: str,
) -> LineListEntry:
    return LineListEntry(
        tag=tag,
        diameter_mm=round(diameter_mm, 2),
        operating_pressure_bar=round(operating_pressure_bar, 2),
        hydrotest_pressure_bar=round(hydrotest_pressure_bar, 2),
        pressure_class=pressure_class,
        material=material,
        flange_face=flange_face,
        selected_schedule=selected_schedule,
    )


def write_line_list_csv(entries: list[LineListEntry], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "Tag",
                "Diametro_mm",
                "Pressao_Operacao_bar",
                "Teste_Hidrostatico_bar",
                "Classe_Pressao",
                "Material",
                "Face_Flange",
                "Schedule",
            ]
        )
        for entry in entries:
            writer.writerow(
                [
                    entry.tag,
                    f"{entry.diameter_mm:.2f}",
                    f"{entry.operating_pressure_bar:.2f}",
                    f"{entry.hydrotest_pressure_bar:.2f}",
                    entry.pressure_class,
                    entry.material,
                    entry.flange_face,
                    entry.selected_schedule,
                ]
            )

    return path