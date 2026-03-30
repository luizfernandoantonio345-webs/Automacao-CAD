from __future__ import annotations

import math
import re

from engenharia_automacao.core.engine.generator import ProjectInput
from engenharia_automacao.core.piping.specs import select_piping_specification


class ValidationError(ValueError):
    """Erro levantado quando a entrada nao atende as regras do sistema."""


class Validator:
    """Valida e normaliza os dados recebidos pela aplicacao."""

    MAX_DIAMETER = 1_000_000.0
    MAX_LENGTH = 10_000_000.0
    MAX_TEXT_LENGTH = 120
    SAFE_TEXT_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

    def validate(self, payload: dict) -> ProjectInput:
        diameter = self._read_positive_number(payload, "diameter", max_value=self.MAX_DIAMETER)
        length = self._read_positive_number(payload, "length", max_value=self.MAX_LENGTH)
        company = self._read_text(payload, "company")
        part_name = self._read_text(payload, "part_name")
        code = self._read_text(payload, "code")
        fluid = self._read_optional_text(payload, "fluid", default="Agua")
        temperature_c = self._read_number_with_bounds(
            payload,
            "temperature_c",
            default=25.0,
            min_value=-100.0,
            max_value=700.0,
        )
        operating_pressure_bar = self._read_number_with_bounds(
            payload,
            "operating_pressure_bar",
            default=10.0,
            min_value=0.1,
            max_value=500.0,
        )

        spec = select_piping_specification(
            fluid=fluid,
            temperature_c=temperature_c,
            operating_pressure_bar=operating_pressure_bar,
            diameter_mm=diameter,
        )

        return ProjectInput(
            diameter=diameter,
            length=length,
            company=company,
            part_name=part_name,
            code=code,
            fluid=fluid,
            temperature_c=temperature_c,
            operating_pressure_bar=operating_pressure_bar,
            pressure_class=spec.pressure_class,
            material=spec.material,
            flange_face=spec.flange_face,
            corrosion_allowance_mm=spec.corrosion_allowance_mm,
            required_wall_thickness_mm=spec.required_wall_thickness_mm,
            selected_schedule=spec.selected_schedule,
            selected_wall_thickness_mm=spec.selected_wall_thickness_mm,
            hydrotest_pressure_bar=spec.hydrotest_pressure_bar,
        )

    def _read_positive_number(self, payload: dict, field: str, max_value: float) -> float:
        if field not in payload:
            raise ValidationError(f"Campo obrigatorio ausente: {field}.")
        try:
            value = float(payload[field])
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Campo invalido para {field}.") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValidationError(f"O campo {field} deve ser maior que zero.")
        if value > max_value:
            raise ValidationError(f"O campo {field} excede o limite suportado ({max_value:g}).")
        return value

    def _read_text(self, payload: dict, field: str) -> str:
        value = str(payload.get(field, "")).strip()
        if not value:
            raise ValidationError(f"Campo obrigatorio ausente: {field}.")
        if len(value) > self.MAX_TEXT_LENGTH:
            raise ValidationError(f"O campo {field} excede {self.MAX_TEXT_LENGTH} caracteres.")
        sanitized = self.SAFE_TEXT_PATTERN.sub("", value)
        if not sanitized:
            raise ValidationError(f"Campo invalido para {field}.")
        return sanitized

    def _read_optional_text(self, payload: dict, field: str, default: str) -> str:
        raw_value = payload.get(field, default)
        value = str(raw_value).strip() if raw_value is not None else default
        if not value:
            value = default
        if len(value) > self.MAX_TEXT_LENGTH:
            raise ValidationError(f"O campo {field} excede {self.MAX_TEXT_LENGTH} caracteres.")
        sanitized = self.SAFE_TEXT_PATTERN.sub("", value)
        if not sanitized:
            raise ValidationError(f"Campo invalido para {field}.")
        return sanitized

    def _read_number_with_bounds(
        self,
        payload: dict,
        field: str,
        default: float,
        min_value: float,
        max_value: float,
    ) -> float:
        raw_value = payload.get(field, default)
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Campo invalido para {field}.") from exc
        if not math.isfinite(value) or value < min_value or value > max_value:
            raise ValidationError(
                f"O campo {field} deve estar entre {min_value:g} e {max_value:g}."
            )
        return value
