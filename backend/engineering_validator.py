"""
═══════════════════════════════════════════════════════════════════════════════
  Módulo de Validação de Engenharia — Normas Técnicas
═══════════════════════════════════════════════════════════════════════════════

Implementa validações segundo as normas:
  - ASME B31.3 — Process Piping (tubulação industrial)
  - ASME B16.5 — Pipe Flanges and Flanged Fittings (flanges)
  - AWS D1.1    — Structural Welding Code — Steel (soldagem)
  - ISO 128     — Technical drawings — General principles of presentation

Uso:
    from backend.engineering_validator import EngineeringValidator

    result = EngineeringValidator.validate_pipe_asme_b31_3(
        diameter_mm=100, thickness_mm=6, pressure_bar=15, fluid="water"
    )
    if not result["valid"]:
        print(result["errors"])
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── Tipos de resultado ──────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid: bool
    norm: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "norm": self.norm,
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendations": self.recommendations,
            "meta": self.meta,
        }


# ═══════════════════════════════════════════════════════════════════════════
# ASME B31.3 — TUBULAÇÃO DE PROCESSO
# ═══════════════════════════════════════════════════════════════════════════

# Diâmetros Nominais de Tubos (DN → OD em mm) — Tabela ASME B36.10
_PIPE_DN_TO_OD_MM = {
    15: 21.3, 20: 26.7, 25: 33.4, 32: 42.2, 40: 48.3, 50: 60.3,
    65: 73.0, 80: 88.9, 100: 114.3, 125: 141.3, 150: 168.3,
    200: 219.1, 250: 273.1, 300: 323.9, 350: 355.6, 400: 406.4,
    450: 457.2, 500: 508.0, 600: 609.6,
}

# Fluidos e fatores de segurança (ASME B31.3 Tabela A-1 simplificado)
_FLUID_SAFETY_FACTOR = {
    "water": 1.0, "steam": 1.2, "gas": 1.5,
    "corrosive": 1.8, "toxic": 2.0, "unknown": 1.5,
}

# Espessuras mínimas de parede por schedule (mm, para DN50-DN150)
_MIN_WALL_THICKNESS_MM = {
    "sch_5s": 1.65, "sch_10s": 2.11, "sch_std": 3.91,
    "sch_40": 3.91, "sch_80": 5.54, "sch_160": 9.53,
}


class ASMEB31_3Validator:
    """Validador ASME B31.3 — Process Piping."""

    NORM = "ASME B31.3"

    @classmethod
    def validate(
        cls,
        diameter_mm: float,
        thickness_mm: float,
        pressure_bar: float,
        fluid: str = "unknown",
        material_yield_mpa: float = 250.0,
        temperature_c: float = 25.0,
    ) -> ValidationResult:
        """
        Valida tubulação segundo ASME B31.3.

        Fórmula de espessura mínima (Eq. 304.1.2):
            t_min = (P * D) / (2 * (S * E + P * Y))
        onde:
            P  = pressão interna (MPa)
            D  = diâmetro externo (mm)
            S  = tensão admissível (MPa) — geralmente material_yield / 3
            E  = fator de junta = 1.0 (tubos sem costura)
            Y  = coeficiente de temperatura = 0.4 (temp < 482°C)
        """
        result = ValidationResult(valid=True, norm=cls.NORM)

        # ── Validação de entrada ─────────────────────────────────────────────
        if diameter_mm <= 0:
            result.errors.append("Diâmetro deve ser maior que zero.")
            result.valid = False
            return result

        if thickness_mm <= 0:
            result.errors.append("Espessura de parede deve ser maior que zero.")
            result.valid = False
            return result

        if pressure_bar < 0:
            result.errors.append("Pressão não pode ser negativa.")
            result.valid = False
            return result

        # ── Conversões ───────────────────────────────────────────────────────
        pressure_mpa = pressure_bar * 0.1
        allowable_stress_mpa = material_yield_mpa / 3.0  # Fator de segurança 3:1
        E = 1.0   # Junta sem costura
        Y = 0.4   # Temperatura < 482°C

        # ── Espessura mínima requerida ────────────────────────────────────────
        if (2 * (allowable_stress_mpa * E + pressure_mpa * Y)) > 0:
            t_min = (pressure_mpa * diameter_mm) / (
                2 * (allowable_stress_mpa * E + pressure_mpa * Y)
            )
        else:
            t_min = 0.0

        # Adiciona allowance de corrosão (c = 1.5mm por padrão para água)
        corrosion_allowance = 1.5 if fluid in ("water", "steam") else 3.0
        t_required = t_min + corrosion_allowance

        result.meta.update({
            "diameter_mm": diameter_mm,
            "thickness_provided_mm": thickness_mm,
            "thickness_min_required_mm": round(t_required, 2),
            "pressure_bar": pressure_bar,
            "pressure_mpa": round(pressure_mpa, 3),
            "allowable_stress_mpa": round(allowable_stress_mpa, 1),
            "fluid": fluid,
        })

        # ── Verificações ─────────────────────────────────────────────────────
        if thickness_mm < t_required:
            result.errors.append(
                f"Espessura {thickness_mm}mm INSUFICIENTE. "
                f"Mínimo requerido pela ASME B31.3: {t_required:.2f}mm "
                f"(inclui corrosão de {corrosion_allowance}mm)."
            )
            result.valid = False
        elif thickness_mm < t_required * 1.1:
            result.warnings.append(
                f"Espessura {thickness_mm}mm está próxima do limite. "
                f"Mínimo: {t_required:.2f}mm. Recomenda-se margem de 10%."
            )

        if temperature_c > 400:
            result.warnings.append(
                f"Temperatura {temperature_c}°C acima de 400°C — verificar "
                "creep e degradação de material conforme ASME B31.3 Apêndice F."
            )

        if temperature_c > 482:
            result.errors.append(
                f"Temperatura {temperature_c}°C excede limite de 482°C para "
                "coeficiente Y=0.4. Recalcular com Y de alta temperatura."
            )
            result.valid = False

        if pressure_bar > 690:
            result.warnings.append(
                f"Pressão {pressure_bar} bar (> 690 bar) — aplicável a "
                "Category M fluid service (ASME B31.3 Capítulo IX)."
            )

        # ── Recomendações ────────────────────────────────────────────────────
        safety_factor = cls._get_safety_factor(fluid)
        if safety_factor > 1.0:
            result.recommendations.append(
                f"Fluido '{fluid}' requer fator de segurança adicional {safety_factor}x. "
                "Considerar schedule maior."
            )

        if diameter_mm < 21.3:
            result.recommendations.append(
                "Diâmetro abaixo de DN15 (OD 21.3mm). "
                "Verificar aplicabilidade da ASME B31.3 (pode ser B31.1)."
            )

        return result

    @classmethod
    def _get_safety_factor(cls, fluid: str) -> float:
        return _FLUID_SAFETY_FACTOR.get(fluid.lower(), 1.5)

    @classmethod
    def suggest_schedule(
        cls,
        diameter_mm: float,
        pressure_bar: float,
        material_yield_mpa: float = 250.0,
    ) -> Dict[str, Any]:
        """Sugere schedule de tubo baseado na pressão e diâmetro."""
        result = cls.validate(
            diameter_mm=diameter_mm,
            thickness_mm=999,  # Passa validação de espessura
            pressure_bar=pressure_bar,
            material_yield_mpa=material_yield_mpa,
        )
        t_min = result.meta.get("thickness_min_required_mm", 0)

        suggestions = []
        for sched, t in sorted(_MIN_WALL_THICKNESS_MM.items(), key=lambda x: x[1]):
            if t >= t_min:
                suggestions.append({"schedule": sched, "thickness_mm": t})

        return {
            "diameter_mm": diameter_mm,
            "pressure_bar": pressure_bar,
            "min_thickness_mm": round(t_min, 2),
            "suggested_schedules": suggestions[:3],
        }


# ═══════════════════════════════════════════════════════════════════════════
# ASME B16.5 — FLANGES E CONEXÕES
# ═══════════════════════════════════════════════════════════════════════════

# Pressão máxima admissível por Classe e Temperatura (bar)
# Tabela 2-1.1 — Grupo 1.1 (A105/A516-70, Aço Carbono)
_B165_PRESSURE_RATING = {
    # Classe: {temperatura_máxima_C: pressão_max_bar}
    150:  {38: 19.6, 100: 17.7, 150: 15.8, 200: 13.8, 250: 12.1, 300: 10.2},
    300:  {38: 51.1, 100: 46.6, 150: 45.1, 200: 43.8, 250: 39.8, 300: 35.3},
    600:  {38: 102.1, 100: 93.2, 150: 90.2, 200: 87.5, 250: 79.6, 300: 70.7},
    900:  {38: 153.2, 100: 139.8, 150: 135.3, 200: 131.3, 250: 119.4, 300: 106.1},
    1500: {38: 255.3, 100: 233.0, 150: 225.5, 200: 218.8, 250: 199.0, 300: 176.8},
    2500: {38: 425.6, 100: 388.4, 150: 375.9, 200: 364.7, 250: 331.7, 300: 294.7},
}

# Diâmetros nominais disponíveis por Classe ASME B16.5
_B165_VALID_SIZES = [
    0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24
]

_B165_VALID_CLASSES = [150, 300, 600, 900, 1500, 2500]


class ASMEB16_5Validator:
    """Validador ASME B16.5 — Pipe Flanges and Flanged Fittings."""

    NORM = "ASME B16.5"

    @classmethod
    def validate(
        cls,
        size_inches: float,
        rating_class: int,
        pressure_bar: float,
        temperature_c: float = 38.0,
        facing: str = "RF",
    ) -> ValidationResult:
        """
        Valida flange conforme ASME B16.5.

        Args:
            size_inches:   Diâmetro nominal (polegadas) ex: 4.0 para 4"
            rating_class:  Classe do flange: 150, 300, 600, 900, 1500, 2500
            pressure_bar:  Pressão de operação (bar)
            temperature_c: Temperatura de operação (°C)
            facing:        Tipo de face: RF (Raised Face), FF (Flat Face), RTJ
        """
        result = ValidationResult(valid=True, norm=cls.NORM)

        # ── Validação de entrada ─────────────────────────────────────────────
        if size_inches <= 0:
            result.errors.append("Tamanho nominal deve ser positivo.")
            result.valid = False
            return result

        if rating_class not in _B165_VALID_CLASSES:
            result.errors.append(
                f"Classe {rating_class} inválida. "
                f"Classes disponíveis: {_B165_VALID_CLASSES}"
            )
            result.valid = False
            return result

        if pressure_bar < 0:
            result.errors.append("Pressão não pode ser negativa.")
            result.valid = False
            return result

        # ── Verifica tamanho nominal ──────────────────────────────────────────
        closest_size = min(_B165_VALID_SIZES, key=lambda s: abs(s - size_inches))
        if abs(closest_size - size_inches) > 0.01:
            result.warnings.append(
                f"Tamanho {size_inches}\" não é nominal padrão ASME B16.5. "
                f"Mais próximo: {closest_size}\""
            )

        # ── Pressão máxima admissível ─────────────────────────────────────────
        class_ratings = _B165_PRESSURE_RATING.get(rating_class, {})

        # Encontra pressão para temperatura (interpolação linear simples)
        max_pressure = cls._interpolate_pressure(class_ratings, temperature_c)

        result.meta.update({
            "size_inches": size_inches,
            "rating_class": rating_class,
            "operating_pressure_bar": pressure_bar,
            "max_admissible_pressure_bar": round(max_pressure, 1),
            "temperature_c": temperature_c,
            "facing": facing,
        })

        if pressure_bar > max_pressure:
            result.errors.append(
                f"Pressão {pressure_bar:.1f} bar EXCEDE o limite admissível "
                f"{max_pressure:.1f} bar para Classe {rating_class} a {temperature_c}°C "
                f"(ASME B16.5 Tabela 2-1.1)."
            )
            result.valid = False
        elif pressure_bar > max_pressure * 0.9:
            result.warnings.append(
                f"Pressão {pressure_bar:.1f} bar está acima de 90% do limite "
                f"({max_pressure:.1f} bar). Considerar classe superior."
            )

        # ── Recomendações por tipo de face ────────────────────────────────────
        if facing == "FF" and rating_class > 300:
            result.warnings.append(
                "Face Plana (FF) com classe > 300 pode causar vazamento. "
                "Recomendado usar Raised Face (RF) ou RTJ."
            )

        if temperature_c > 538:
            result.errors.append(
                f"Temperatura {temperature_c}°C excede 538°C (limite ASME B16.5 para aço carbono)."
            )
            result.valid = False

        # ── Sugestão de upgrade ────────────────────────────────────────────────
        if not result.valid:
            for cls_upgrade in sorted(_B165_VALID_CLASSES):
                if cls_upgrade <= rating_class:
                    continue
                max_p_upgrade = cls._interpolate_pressure(
                    _B165_PRESSURE_RATING[cls_upgrade], temperature_c
                )
                if pressure_bar <= max_p_upgrade:
                    result.recommendations.append(
                        f"Usar Classe {cls_upgrade} que suporta até {max_p_upgrade:.1f} bar "
                        f"a {temperature_c}°C."
                    )
                    break

        return result

    @classmethod
    def _interpolate_pressure(cls, ratings: Dict[int, float], temp: float) -> float:
        """Interpolação linear entre pontos de temperatura da tabela B16.5."""
        if not ratings:
            return 0.0
        temps = sorted(ratings.keys())
        if temp <= temps[0]:
            return ratings[temps[0]]
        if temp >= temps[-1]:
            return ratings[temps[-1]] * 0.8  # Redução conservadora extrapolada

        for i in range(len(temps) - 1):
            t1, t2 = temps[i], temps[i + 1]
            if t1 <= temp <= t2:
                p1, p2 = ratings[t1], ratings[t2]
                ratio = (temp - t1) / (t2 - t1)
                return p1 + ratio * (p2 - p1)
        return ratings[temps[0]]


# ═══════════════════════════════════════════════════════════════════════════
# AWS D1.1 — CÓDIGO DE SOLDAGEM ESTRUTURAL
# ═══════════════════════════════════════════════════════════════════════════

# Tamanhos mínimos de solda de filete por espessura do material (mm)
# AWS D1.1 Tabela 6.1
_AWS_MIN_FILLET_SIZE = [
    (6.4, 3.0),    # t ≤ 6.4mm → min 3mm
    (12.7, 5.0),   # 6.4 < t ≤ 12.7mm → min 5mm
    (19.1, 6.0),   # 12.7 < t ≤ 19.1mm → min 6mm
    (float("inf"), 8.0),  # t > 19.1mm → min 8mm
]

# Resistência de eletrodos AWS (MPa)
_ELECTRODE_STRENGTH_MPA = {
    "E6010": 413, "E6011": 413, "E6013": 413,
    "E7018": 483, "E7016": 483, "E7015": 483,
    "E8018": 552, "E9018": 621, "E11018": 758,
    "ER70S-6": 483, "ER70S-3": 483, "ER80S-D2": 552,
}

_AWS_VALID_WELD_TYPES = ["fillet", "groove", "plug", "slot", "stud"]


class AWSD1_1Validator:
    """Validador AWS D1.1 — Structural Welding Code — Steel."""

    NORM = "AWS D1.1"

    @classmethod
    def validate_fillet_weld(
        cls,
        throat_mm: float,
        base_material_thickness_mm: float,
        load_kn: float = 0.0,
        electrode: str = "E7018",
        weld_length_mm: float = 100.0,
        joint_type: str = "fillet",
    ) -> ValidationResult:
        """
        Valida solda de filete conforme AWS D1.1.

        Args:
            throat_mm:                    Garganta efetiva (mm)
            base_material_thickness_mm:   Espessura do metal base (mm)
            load_kn:                      Carga aplicada (kN), 0 = sem verificação de carga
            electrode:                    Classificação do eletrodo AWS
            weld_length_mm:               Comprimento da solda (mm)
            joint_type:                   Tipo de junta
        """
        result = ValidationResult(valid=True, norm=cls.NORM)

        # ── Validação de entrada ─────────────────────────────────────────────
        if throat_mm <= 0:
            result.errors.append("Garganta da solda deve ser maior que zero.")
            result.valid = False
            return result

        if base_material_thickness_mm <= 0:
            result.errors.append("Espessura do metal base deve ser maior que zero.")
            result.valid = False
            return result

        if joint_type not in _AWS_VALID_WELD_TYPES:
            result.warnings.append(
                f"Tipo de junta '{joint_type}' não reconhecido. "
                f"Válidos: {_AWS_VALID_WELD_TYPES}"
            )

        # ── Tamanho mínimo de filete ──────────────────────────────────────────
        min_fillet = cls._get_min_fillet(base_material_thickness_mm)

        # Para filete: leg size ≈ throat / 0.707
        leg_size = throat_mm / 0.707

        result.meta.update({
            "throat_mm": throat_mm,
            "leg_size_mm": round(leg_size, 2),
            "min_fillet_leg_mm": min_fillet,
            "base_thickness_mm": base_material_thickness_mm,
            "electrode": electrode,
            "weld_length_mm": weld_length_mm,
        })

        if leg_size < min_fillet:
            result.errors.append(
                f"Perna de filete {leg_size:.1f}mm INSUFICIENTE para espessura {base_material_thickness_mm}mm. "
                f"Mínimo AWS D1.1 Tabela 6.1: {min_fillet}mm."
            )
            result.valid = False

        # ── Tamanho máximo de filete ──────────────────────────────────────────
        max_fillet = base_material_thickness_mm - 1.5  # AWS D1.1 2.4.3
        if base_material_thickness_mm < 6.4:
            max_fillet = base_material_thickness_mm  # Chapa fina

        if leg_size > max_fillet and base_material_thickness_mm > 6.4:
            result.warnings.append(
                f"Perna de filete {leg_size:.1f}mm excede máximo recomendado "
                f"{max_fillet:.1f}mm (base - 1.5mm)."
            )

        # ── Resistência do eletrodo ───────────────────────────────────────────
        electrode_fuw = _ELECTRODE_STRENGTH_MPA.get(electrode.upper())
        if electrode_fuw is None:
            result.warnings.append(
                f"Eletrodo '{electrode}' não na tabela AWS. Verificar manualmente."
            )
            electrode_fuw = 483  # Default E7018

        # Tensão admissível AWS D1.1 Tabela 2.3 (cisalhamento = 0.3 * Fuw)
        allowable_shear_mpa = 0.3 * electrode_fuw

        # Resistência de solda por unidade de comprimento
        weld_unit_strength_n_per_mm = allowable_shear_mpa * throat_mm
        total_capacity_kn = weld_unit_strength_n_per_mm * weld_length_mm / 1000.0

        result.meta["weld_capacity_kn"] = round(total_capacity_kn, 1)
        result.meta["allowable_shear_mpa"] = round(allowable_shear_mpa, 1)

        if load_kn > 0:
            if load_kn > total_capacity_kn:
                result.errors.append(
                    f"Carga {load_kn}kN EXCEDE capacidade da solda {total_capacity_kn:.1f}kN "
                    f"(eletrodo {electrode}, garganta {throat_mm}mm, L={weld_length_mm}mm)."
                )
                result.valid = False
            elif load_kn > total_capacity_kn * 0.85:
                result.warnings.append(
                    f"Utilização {(load_kn/total_capacity_kn*100):.0f}% — "
                    "Acima de 85%. Aumentar garganta ou comprimento."
                )
            else:
                result.recommendations.append(
                    f"Utilização {(load_kn/total_capacity_kn*100):.0f}% da capacidade."
                )

        # ── Recomendações gerais ─────────────────────────────────────────────
        if electrode_fuw < 483 and base_material_thickness_mm > 12:
            result.recommendations.append(
                f"Para espessura > 12mm, considerar eletrodo E7018 ou superior "
                "(baixo hidrogênio)."
            )

        return result

    @classmethod
    def _get_min_fillet(cls, thickness_mm: float) -> float:
        """Retorna tamanho mínimo de filete conforme AWS D1.1 Tabela 6.1."""
        for t_max, min_size in _AWS_MIN_FILLET_SIZE:
            if thickness_mm <= t_max:
                return min_size
        return 8.0


# ═══════════════════════════════════════════════════════════════════════════
# ISO 128 — DESENHO TÉCNICO
# ═══════════════════════════════════════════════════════════════════════════

# Espessuras de linha ISO 128-24 (mm)
_ISO128_LINE_WIDTHS = [0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0]

# Escalas preferenciais ISO 5455
_ISO_PREFERRED_SCALES = {
    "reduction": [1/2, 1/5, 1/10, 1/20, 1/50, 1/100, 1/200, 1/500, 1/1000],
    "enlargement": [2/1, 5/1, 10/1, 20/1, 50/1],
    "full": [1/1],
}

# Formatos de papel ISO 216
_ISO216_FORMATS = {
    "A0": (841, 1189), "A1": (594, 841), "A2": (420, 594),
    "A3": (297, 420), "A4": (210, 297), "A5": (148, 210),
}


class ISO128Validator:
    """Validador ISO 128 — Technical Drawings — General Principles."""

    NORM = "ISO 128"

    @classmethod
    def validate_line_width(cls, width_mm: float) -> ValidationResult:
        """Valida espessura de linha conforme ISO 128-24."""
        result = ValidationResult(valid=True, norm=cls.NORM)

        closest = min(_ISO128_LINE_WIDTHS, key=lambda w: abs(w - width_mm))

        if abs(closest - width_mm) > 0.001:
            result.warnings.append(
                f"Espessura {width_mm}mm não é padrão ISO 128-24. "
                f"Mais próxima: {closest}mm. "
                f"Valores padrão: {_ISO128_LINE_WIDTHS}"
            )
        else:
            result.recommendations.append(f"Espessura {width_mm}mm está na tabela ISO 128-24.")

        result.meta["closest_standard_mm"] = closest
        return result

    @classmethod
    def validate_scale(cls, numerator: float, denominator: float) -> ValidationResult:
        """Valida escala de desenho conforme ISO 5455."""
        result = ValidationResult(valid=True, norm=f"{cls.NORM} / ISO 5455")
        scale = numerator / denominator if denominator != 0 else 0

        all_preferred = (
            _ISO_PREFERRED_SCALES["reduction"]
            + _ISO_PREFERRED_SCALES["enlargement"]
            + _ISO_PREFERRED_SCALES["full"]
        )

        closest = min(all_preferred, key=lambda s: abs(s - scale))

        if abs(closest - scale) > 0.001:
            result.warnings.append(
                f"Escala {numerator}:{denominator} não é preferencial ISO 5455. "
                f"Escala mais próxima: {cls._format_scale(closest)}"
            )
        else:
            result.recommendations.append(
                f"Escala {numerator}:{denominator} é preferencial ISO 5455."
            )

        result.meta["scale_ratio"] = scale
        return result

    @classmethod
    def validate_paper_format(
        cls,
        width_mm: float,
        height_mm: float,
        tolerance_mm: float = 2.0
    ) -> ValidationResult:
        """Valida formato de papel conforme ISO 216."""
        result = ValidationResult(valid=True, norm=f"{cls.NORM} / ISO 216")

        dims = (min(width_mm, height_mm), max(width_mm, height_mm))

        matched = None
        for fmt, (w, h) in _ISO216_FORMATS.items():
            if abs(dims[0] - w) <= tolerance_mm and abs(dims[1] - h) <= tolerance_mm:
                matched = fmt
                break

        if matched:
            result.recommendations.append(f"Formato reconhecido: {matched} ({dims[0]}×{dims[1]}mm)")
            result.meta["format"] = matched
        else:
            result.warnings.append(
                f"Formato {width_mm}×{height_mm}mm não reconhecido como padrão ISO 216. "
                f"Formatos disponíveis: {list(_ISO216_FORMATS.keys())}"
            )
            result.meta["format"] = "custom"

        return result

    @classmethod
    def _format_scale(cls, ratio: float) -> str:
        if ratio >= 1:
            return f"{int(ratio)}:1"
        return f"1:{int(round(1/ratio))}"


# ═══════════════════════════════════════════════════════════════════════════
# VALIDADOR UNIFICADO
# ═══════════════════════════════════════════════════════════════════════════

class EngineeringValidator:
    """Ponto de entrada unificado para todas as validações de engenharia."""

    @staticmethod
    def validate_pipe_asme_b31_3(
        diameter_mm: float,
        thickness_mm: float,
        pressure_bar: float,
        fluid: str = "unknown",
        material_yield_mpa: float = 250.0,
        temperature_c: float = 25.0,
    ) -> Dict[str, Any]:
        return ASMEB31_3Validator.validate(
            diameter_mm, thickness_mm, pressure_bar, fluid,
            material_yield_mpa, temperature_c
        ).to_dict()

    @staticmethod
    def suggest_pipe_schedule(
        diameter_mm: float,
        pressure_bar: float,
        material_yield_mpa: float = 250.0,
    ) -> Dict[str, Any]:
        return ASMEB31_3Validator.suggest_schedule(diameter_mm, pressure_bar, material_yield_mpa)

    @staticmethod
    def validate_flange_asme_b16_5(
        size_inches: float,
        rating_class: int,
        pressure_bar: float,
        temperature_c: float = 38.0,
        facing: str = "RF",
    ) -> Dict[str, Any]:
        return ASMEB16_5Validator.validate(
            size_inches, rating_class, pressure_bar, temperature_c, facing
        ).to_dict()

    @staticmethod
    def validate_weld_aws_d1_1(
        throat_mm: float,
        base_material_thickness_mm: float,
        load_kn: float = 0.0,
        electrode: str = "E7018",
        weld_length_mm: float = 100.0,
    ) -> Dict[str, Any]:
        return AWSD1_1Validator.validate_fillet_weld(
            throat_mm, base_material_thickness_mm, load_kn, electrode, weld_length_mm
        ).to_dict()

    @staticmethod
    def validate_drawing_line_width(width_mm: float) -> Dict[str, Any]:
        return ISO128Validator.validate_line_width(width_mm).to_dict()

    @staticmethod
    def validate_drawing_scale(numerator: float, denominator: float) -> Dict[str, Any]:
        return ISO128Validator.validate_scale(numerator, denominator).to_dict()
