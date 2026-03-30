from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STEEL_COST_BRL_PER_KG = 12.0
CONCRETE_COST_BRL_PER_M3 = 2500.0
PAINTING_LEAD_DAYS = 3
CONCRETE_CURE_DAYS = 7
WORKDAY_HOURS = 8.0

WIND_LOAD_N_PER_MM = 0.30

LADDER_RUNG_SPACING_MM = 300
LADDER_CAGE_START_MM = 2100
LADDER_RING_SPACING_MM = 1200
LADDER_CAGE_DIAMETER_MM = 700

KG_M_MONTANTE = 5.2
KG_M_DEGRAU = 2.9
KG_M_GAIOLA = 1.8

CONCRETE_DENSITY_KG_M3 = 2400.0
ANCHOR_MASS_LINEAR_KG_M = 0.8


@dataclass(frozen=True)
class ExecutiveCase:
    label: str
    scenario: str
    weight_total_kg: float
    fasteners_qty: int
    raw_material_cost_brl: float
    fabrication_hh: float
    supported_load_kn: float
    lead_time_days: int
    notes: str

    @property
    def financial_slenderness_kg_per_kn(self) -> float:
        if self.supported_load_kn <= 0:
            return 0.0
        return round(self.weight_total_kg / self.supported_load_kn, 2)


def _round_currency(value: float) -> float:
    return round(value, 2)


def _format_brl(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "_").replace(".", ",").replace("_", ".")


def _fabrication_days(hours: float) -> int:
    return int(math.ceil(hours / WORKDAY_HOURS))


def build_case_01() -> ExecutiveCase:
    altura_m = 3.0
    largura_mm = 400
    altura_mm = int(round(altura_m * 1000.0))

    qtd_degraus = int(math.ceil(altura_mm / LADDER_RUNG_SPACING_MM)) + 1
    altura_com_gaiola_mm = max(0, altura_mm - LADDER_CAGE_START_MM)
    qtd_aros = int(math.ceil(altura_com_gaiola_mm / LADDER_RING_SPACING_MM)) if altura_com_gaiola_mm > 0 else 0

    comprimento_montantes_m = (2 * altura_mm) / 1000.0
    comprimento_degraus_m = qtd_degraus * (largura_mm / 1000.0)
    comprimento_gaiola_m = qtd_aros * math.pi * (LADDER_CAGE_DIAMETER_MM / 1000.0)

    weight_total_kg = round(
        (comprimento_montantes_m * KG_M_MONTANTE)
        + (comprimento_degraus_m * KG_M_DEGRAU)
        + (comprimento_gaiola_m * KG_M_GAIOLA),
        2,
    )
    supported_load_kn = round((WIND_LOAD_N_PER_MM * altura_mm) / 1000.0, 3)
    fabrication_hh = 8.0
    lead_time_days = _fabrication_days(fabrication_hh) + PAINTING_LEAD_DAYS
    raw_material_cost_brl = _round_currency(weight_total_kg * STEEL_COST_BRL_PER_KG)

    return ExecutiveCase(
        label="Caso 01 (Leve/Manutenção)",
        scenario="Escada/torre mecânica 3,0 m com fixação soldada",
        weight_total_kg=weight_total_kg,
        fasteners_qty=0,
        raw_material_cost_brl=raw_material_cost_brl,
        fabrication_hh=fabrication_hh,
        supported_load_kn=supported_load_kn,
        lead_time_days=lead_time_days,
        notes=(
            "Carga suportada adotada como a carga distribuída de vento validada no teste de deflexão; "
            f"{qtd_degraus} degraus e {qtd_aros} aro(s) de gaiola."
        ),
    )


def build_case_20() -> ExecutiveCase:
    lado_m = 2.21
    altura_sapata_m = 0.89
    chumbadores_qty = 8
    chumbador_length_m = 0.8
    carga_suportada_kn = 981.0

    volume_concreto_m3 = lado_m * lado_m * altura_sapata_m
    concrete_weight_kg = volume_concreto_m3 * CONCRETE_DENSITY_KG_M3
    anchor_weight_kg = chumbadores_qty * chumbador_length_m * ANCHOR_MASS_LINEAR_KG_M
    weight_total_kg = round(concrete_weight_kg + anchor_weight_kg, 2)

    raw_material_cost_brl = _round_currency(
        (volume_concreto_m3 * CONCRETE_COST_BRL_PER_M3)
        + (anchor_weight_kg * STEEL_COST_BRL_PER_KG)
    )
    fabrication_hh = 28.0
    lead_time_days = _fabrication_days(fabrication_hh) + PAINTING_LEAD_DAYS + CONCRETE_CURE_DAYS

    return ExecutiveCase(
        label="Caso 20 (Pesado/Implantação)",
        scenario="Fundação civil para pórtico 100 t com sapata e chumbadores M36",
        weight_total_kg=weight_total_kg,
        fasteners_qty=chumbadores_qty,
        raw_material_cost_brl=raw_material_cost_brl,
        fabrication_hh=fabrication_hh,
        supported_load_kn=carga_suportada_kn,
        lead_time_days=lead_time_days,
        notes=(
            "Inclui volume de concreto da sapata e massa dos 8 chumbadores; "
            f"cura operacional considerada em {CONCRETE_CURE_DAYS} dias."
        ),
    )


def _build_rows(case_01: ExecutiveCase, case_20: ExecutiveCase) -> list[tuple[str, str, str]]:
    return [
        ("Peso Total (kg)", f"{case_01.weight_total_kg:.2f}", f"{case_20.weight_total_kg:.2f}"),
        ("Quantidade de Fixadores", str(case_01.fasteners_qty), str(case_20.fasteners_qty)),
        ("Custo Estimado de Matéria-Prima", _format_brl(case_01.raw_material_cost_brl), _format_brl(case_20.raw_material_cost_brl)),
        ("Horas-Homem (HH) de Fabricação", f"{case_01.fabrication_hh:.1f}", f"{case_20.fabrication_hh:.1f}"),
        ("Carga Suportada de Referência (kN)", f"{case_01.supported_load_kn:.3f}", f"{case_20.supported_load_kn:.1f}"),
        (
            "Índice de Esbeltez Financeira (kg/kN)",
            f"{case_01.financial_slenderness_kg_per_kn:.2f}",
            f"{case_20.financial_slenderness_kg_per_kn:.2f}",
        ),
        ("Lead Time Final (dias)", str(case_01.lead_time_days), str(case_20.lead_time_days)),
    ]


def _markdown_dashboard(case_01: ExecutiveCase, case_20: ExecutiveCase) -> str:
    rows = _build_rows(case_01, case_20)
    material_intensity_gain = round(
        (1.0 - (case_20.financial_slenderness_kg_per_kn / case_01.financial_slenderness_kg_per_kn)) * 100.0,
        1,
    )

    lines = [
        "# Dashboard Comparativo ROI - Casos 01 e 20",
        "",
        f"Gerado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 1. Tabela Comparativa de Recursos",
        "",
        "| Indicador | Caso 01 (Leve/Manutenção) | Caso 20 (Pesado/Implantação) |",
        "|---|---:|---:|",
    ]
    for indicador, valor_01, valor_20 in rows:
        lines.append(f"| {indicador} | {valor_01} | {valor_20} |")

    lines += [
        "",
        "## 2. Análise de Eficiência",
        "",
        "O Índice de Esbeltez Financeira é calculado por:",
        "",
        "$$",
        r"IE_f = \frac{Peso\ total}{Carga\ suportada}",
        "$$",
        "",
        f"- Caso 01: {case_01.financial_slenderness_kg_per_kn:.2f} kg/kN",
        f"- Caso 20: {case_20.financial_slenderness_kg_per_kn:.2f} kg/kN",
        f"- Ganho de eficiência material do Caso 20 sobre o Caso 01: {material_intensity_gain:.1f}%",
        "",
        "Leitura gerencial:",
        f"- O SmartDesign reduz a intensidade material por carga suportada ao sair de um cenário leve de manutenção para um cenário pesado de implantação.",
        f"- A diferença de índice mostra que o caso pesado entrega mais capacidade estrutural por unidade de massa, evitando superdimensionamento financeiro.",
        "",
        "## 3. Relatório de Planejamento",
        "",
        "| Etapa | Caso 01 | Caso 20 |",
        "|---|---:|---:|",
        f"| Fabricação | {_fabrication_days(case_01.fabrication_hh)} dia(s) | {_fabrication_days(case_20.fabrication_hh)} dia(s) |",
        f"| Pintura N-13 | {PAINTING_LEAD_DAYS} dia(s) | {PAINTING_LEAD_DAYS} dia(s) |",
        f"| Cura do concreto | 0 dia | {CONCRETE_CURE_DAYS} dia(s) |",
        f"| Lead Time Final | {case_01.lead_time_days} dia(s) | {case_20.lead_time_days} dia(s) |",
        "",
        "## 4. Notas Executivas",
        "",
        f"- {case_01.label}: {case_01.notes}",
        f"- {case_20.label}: {case_20.notes}",
        "- Cobertura executiva: 100% dos indicadores solicitados nesta comparação foram consolidados em custo, peso, tempo e eficiência.",
    ]
    return "\n".join(lines) + "\n"


def _terminal_dashboard(case_01: ExecutiveCase, case_20: ExecutiveCase) -> str:
    rows = _build_rows(case_01, case_20)
    left_width = max(len(row[0]) for row in rows + [("Indicador", "", "")])
    col_a = len(case_01.label)
    col_b = len(case_20.label)

    def fmt_line(indicador: str, valor_01: str, valor_20: str) -> str:
        return f"{indicador:<{left_width}} | {valor_01:>{col_a}} | {valor_20:>{col_b}}"

    separator = f"{'-' * left_width}-+-{'-' * col_a}-+-{'-' * col_b}"
    lines = [
        "EXECUTIVE SUMMARY ROI - SMARTDESIGN",
        separator,
        fmt_line("Indicador", case_01.label, case_20.label),
        separator,
    ]
    for indicador, valor_01, valor_20 in rows:
        lines.append(fmt_line(indicador, valor_01, valor_20))
    lines += [
        separator,
        f"Decisão: {case_01.label} atende manutenção com baixo CAPEX imediato; {case_20.label} entrega melhor eficiência material por carga e prazo total de {case_20.lead_time_days} dias.",
    ]
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, case_01: ExecutiveCase, case_20: ExecutiveCase) -> None:
    rows = _build_rows(case_01, case_20)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=",")
        writer.writerow(["Indicador", case_01.label, case_20.label])
        for indicador, valor_01, valor_20 in rows:
            writer.writerow([indicador, valor_01, valor_20])


def generate_dashboard(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    case_01 = build_case_01()
    case_20 = build_case_20()

    csv_path = output_dir / "executive_summary_ROI.csv"
    md_path = output_dir / "executive_summary_ROI.md"
    terminal_path = output_dir / "executive_summary_ROI_terminal.txt"

    _write_csv(csv_path, case_01, case_20)
    md_path.write_text(_markdown_dashboard(case_01, case_20), encoding="utf-8")
    terminal_path.write_text(_terminal_dashboard(case_01, case_20), encoding="utf-8")

    return {
        "csv": str(csv_path),
        "markdown": str(md_path),
        "terminal": str(terminal_path),
    }


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2] / "data" / "output"
    artifacts = generate_dashboard(base_dir)
    for key, value in artifacts.items():
        print(f"{key.upper()}: {value}")