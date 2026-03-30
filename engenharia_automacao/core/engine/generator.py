from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectInput:
    """Estrutura consolidada dos dados de entrada do projeto."""

    diameter: float
    length: float
    company: str
    part_name: str
    code: str
    fluid: str = "Agua"
    temperature_c: float = 25.0
    operating_pressure_bar: float = 10.0
    pressure_class: str = "ASME 150"
    material: str = "ASTM A106 Gr.B"
    flange_face: str = "RF"
    corrosion_allowance_mm: float = 3.0
    required_wall_thickness_mm: float = 3.0
    selected_schedule: str = "SCH 40"
    selected_wall_thickness_mm: float = 3.91
    hydrotest_pressure_bar: float = 15.0


@dataclass(frozen=True)
class LineGeometry:
    """Representa o tubo como uma linha 2D."""

    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True)
class CircleGeometry:
    """Representa a flange como um circulo 2D."""

    center: tuple[float, float]
    radius: float


@dataclass(frozen=True)
class ArcGeometry:
    """Representa a curva como um arco definido por tres pontos."""

    start: tuple[float, float]
    center: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True)
class ProjectGeometry:
    """Agrupa a geometria gerada para o projeto."""

    tube: LineGeometry
    flange: CircleGeometry
    curve: ArcGeometry


class Generator:
    """Converte os dados validados em geometria base para o desenho."""

    def generate(self, payload: ProjectInput) -> ProjectGeometry:
        radius = payload.diameter / 2.0
        tube = LineGeometry(start=(0.0, 0.0), end=(payload.length, 0.0))
        flange = CircleGeometry(center=(0.0, 0.0), radius=radius)
        curve = ArcGeometry(
            start=(payload.length, 0.0),
            center=(payload.length, payload.diameter),
            end=(payload.length + payload.diameter, payload.diameter),
        )
        return ProjectGeometry(tube=tube, flange=flange, curve=curve)
