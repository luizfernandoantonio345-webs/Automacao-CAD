from __future__ import annotations

from dataclasses import dataclass

from .n76_fluidos import obter_spec_fluido


@dataclass(frozen=True)
class PipingSpecification:
    pressure_class: str
    material: str
    flange_face: str
    corrosion_allowance_mm: float
    required_wall_thickness_mm: float
    selected_schedule: str
    selected_wall_thickness_mm: float
    hydrotest_pressure_bar: float


CORROSION_ALLOWANCE_MM = 3.0  # Padrao REGAP

# Tabela simplificada de espessura por schedule [mm] para diametros nominais [mm].
# Referencia operacional para selecao rapida de especificacao.
SCHEDULE_TABLE_MM: dict[int, dict[str, float]] = {
    25: {"SCH 40": 3.38, "SCH 80": 4.55, "SCH 160": 6.35},
    50: {"SCH 40": 3.91, "SCH 80": 5.54, "SCH 160": 8.74},
    80: {"SCH 40": 5.49, "SCH 80": 7.62, "SCH 160": 11.13},
    100: {"SCH 40": 6.02, "SCH 80": 8.56, "SCH 160": 13.49},
    150: {"SCH 40": 7.11, "SCH 80": 10.97, "SCH 160": 18.26},
    200: {"SCH 40": 8.18, "SCH 80": 12.70, "SCH 160": 23.01},
    250: {"SCH 40": 9.27, "SCH 80": 15.09, "SCH 160": 28.58},
    300: {"SCH 40": 10.31, "SCH 80": 17.48, "SCH 160": 33.32},
}

ALLOWABLE_STRESS_MPA: dict[str, tuple[float, float]] = {
    # (S_ambiente, S_alta_temp) para uso simplificado em B31.3
    "ASTM A106 Gr.B": (138.0, 120.0),
    "ASTM A335 P11": (165.0, 140.0),
}


def select_piping_specification(
    fluid: str,
    temperature_c: float,
    operating_pressure_bar: float,
    diameter_mm: float,
) -> PipingSpecification:
    material, flange_face = _select_material_and_flange(fluid, temperature_c)
    pressure_class = _select_pressure_class(operating_pressure_bar, temperature_c)

    required_wall = calculate_required_wall_thickness_mm(
        pressure_bar=operating_pressure_bar,
        outside_diameter_mm=diameter_mm,
        material=material,
        temperature_c=temperature_c,
        corrosion_allowance_mm=CORROSION_ALLOWANCE_MM,
    )
    selected_schedule, selected_thickness = select_schedule(required_wall, diameter_mm)
    hydrotest_pressure = calculate_hydrotest_pressure_bar(
        operating_pressure_bar=operating_pressure_bar,
        material=material,
        temperature_c=temperature_c,
    )

    return PipingSpecification(
        pressure_class=pressure_class,
        material=material,
        flange_face=flange_face,
        corrosion_allowance_mm=CORROSION_ALLOWANCE_MM,
        required_wall_thickness_mm=required_wall,
        selected_schedule=selected_schedule,
        selected_wall_thickness_mm=selected_thickness,
        hydrotest_pressure_bar=hydrotest_pressure,
    )


def calculate_required_wall_thickness_mm(
    pressure_bar: float,
    outside_diameter_mm: float,
    material: str,
    temperature_c: float,
    corrosion_allowance_mm: float,
) -> float:
    """Calcula espessura minima pela forma simplificada da ASME B31.3 e soma corrosao."""
    pressure_mpa = pressure_bar * 0.1
    allowable_stress = _allowable_stress(material, temperature_c)

    e_factor = 1.0
    w_factor = 1.0
    y_factor = 0.4

    denominator = 2.0 * (allowable_stress * e_factor * w_factor + pressure_mpa * y_factor)
    if denominator <= 0:
        raise ValueError("Nao foi possivel calcular a espessura minima da tubulacao.")

    pressure_thickness = (pressure_mpa * outside_diameter_mm) / denominator
    total_thickness = pressure_thickness + corrosion_allowance_mm
    return round(total_thickness, 2)


def select_schedule(required_wall_thickness_mm: float, diameter_mm: float) -> tuple[str, float]:
    nominal = _nearest_nominal_diameter(diameter_mm)
    schedule_map = SCHEDULE_TABLE_MM[nominal]

    for schedule, thickness in schedule_map.items():
        if thickness >= required_wall_thickness_mm:
            return schedule, thickness

    # Caso extremo: retorna o schedule mais robusto da tabela.
    fallback_schedule, fallback_thickness = list(schedule_map.items())[-1]
    return fallback_schedule, fallback_thickness


def calculate_hydrotest_pressure_bar(
    operating_pressure_bar: float,
    material: str,
    temperature_c: float,
) -> float:
    """Teste hidrostático por prática de B31.3: 1.5x pressão de operação ajustada por tensão admissível."""
    ambient_stress = _allowable_stress(material, 38.0)
    design_stress = _allowable_stress(material, temperature_c)
    stress_ratio = ambient_stress / max(design_stress, 1.0)
    correction = min(1.25, max(1.0, stress_ratio))
    return round(1.5 * operating_pressure_bar * correction, 2)


def _select_material_and_flange(fluid: str, temperature_c: float) -> tuple[str, str]:
    # Prioriza matriz N-76 (REGAP/Petrobras) quando o fluido for reconhecido.
    try:
        spec_fluido = obter_spec_fluido(fluid, temperatura_c=temperature_c)
        return spec_fluido.material, spec_fluido.face_flange
    except ValueError:
        pass

    normalized = fluid.strip().lower()
    if normalized == "hidrocarboneto" and temperature_c > 200.0:
        return "ASTM A335 P11", "RTJ"
    return "ASTM A106 Gr.B", "RF"


def _select_pressure_class(operating_pressure_bar: float, temperature_c: float) -> str:
    # Regras específicas solicitadas: "Vapor de Baixa" e "Água Ácida"
    # são tratadas via N-76 em _select_material_and_flange; aqui mantemos
    # a lógica de classe por pressão/temperatura.
    if operating_pressure_bar <= 20.0 and temperature_c <= 200.0:
        return "ASME 150"
    if operating_pressure_bar <= 50.0 and temperature_c <= 400.0:
        return "ASME 300"
    if operating_pressure_bar <= 100.0:
        return "ASME 600"
    return "ASME 900"


def _allowable_stress(material: str, temperature_c: float) -> float:
    ambient_stress, high_temp_stress = ALLOWABLE_STRESS_MPA.get(material, ALLOWABLE_STRESS_MPA["ASTM A106 Gr.B"])
    if temperature_c <= 200.0:
        return ambient_stress
    return high_temp_stress


def _nearest_nominal_diameter(diameter_mm: float) -> int:
    return min(SCHEDULE_TABLE_MM, key=lambda nominal: abs(nominal - diameter_mm))
