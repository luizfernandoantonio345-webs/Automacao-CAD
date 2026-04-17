# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE VALIDAÇÃO DE ENGENHARIA — ASME B31.3, B16.5, AWS D1.1, ISO 128
# ═══════════════════════════════════════════════════════════════════════════════
"""
Valida as regras de negócio do módulo backend/engineering_validator.py
conforme as normas:
  - ASME B31.3 — Process Piping
  - ASME B16.5 — Pipe Flanges
  - AWS D1.1   — Structural Welding
  - ISO 128    — Technical Drawings
"""
import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))


from backend.engineering_validator import (
    EngineeringValidator,
    ASMEB31_3Validator,
    ASMEB16_5Validator,
    AWSD1_1Validator,
    ISO128Validator,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ASME B31.3 — TUBULAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

class TestASMEB31_3:
    """Casos de teste para ASME B31.3 Process Piping."""

    # ── Casos válidos ────────────────────────────────────────────────────────

    def test_standard_water_pipe_passes(self):
        """Tubulação DN100 Sch.40 para água a baixa pressão deve passar."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=114.3,   # DN100 OD
            thickness_mm=6.02,   # Sch.40
            pressure_bar=10.0,
            fluid="water",
            material_yield_mpa=250.0,
            temperature_c=25.0,
        )
        assert result.valid, f"Deveria ser válida: {result.errors}"
        assert result.norm == "ASME B31.3"
        assert "diameter_mm" in result.meta

    def test_thick_pipe_high_pressure_passes(self):
        """Tubo DN50 Sch.160 para vapor a alta pressão deve passar."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=60.3,    # DN50 OD
            thickness_mm=9.53,   # Sch.160
            pressure_bar=100.0,
            fluid="steam",
            temperature_c=300.0,
        )
        assert result.valid, f"Sch.160 deveria suportar 100 bar: {result.errors}"

    # ── Espessura insuficiente ───────────────────────────────────────────────

    def test_thin_wall_high_pressure_fails(self):
        """Tubo com parede fina (2mm) para pressão alta deve falhar."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=114.3,
            thickness_mm=2.0,    # Muito fina para 80 bar
            pressure_bar=80.0,
            fluid="gas",
        )
        assert not result.valid
        assert len(result.errors) > 0
        assert any("insuficiente" in e.lower() or "mínimo" in e.lower() for e in result.errors)

    def test_zero_thickness_fails(self):
        """Espessura zero deve gerar erro de validação."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=100.0,
            thickness_mm=0.0,
            pressure_bar=10.0,
        )
        assert not result.valid
        assert len(result.errors) > 0

    def test_zero_diameter_fails(self):
        """Diâmetro zero deve gerar erro."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=0,
            thickness_mm=5.0,
            pressure_bar=10.0,
        )
        assert not result.valid

    def test_negative_pressure_fails(self):
        """Pressão negativa deve ser rejeitada."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=100.0,
            thickness_mm=5.0,
            pressure_bar=-5.0,
        )
        assert not result.valid

    # ── Temperatura ──────────────────────────────────────────────────────────

    def test_high_temperature_warning(self):
        """Temperatura > 400°C deve gerar aviso."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=88.9,    # DN80
            thickness_mm=12.0,
            pressure_bar=20.0,
            temperature_c=420.0,
        )
        has_temp_warning = any("400" in w or "creep" in w.lower() for w in result.warnings)
        assert has_temp_warning, f"Deveria ter aviso de temperatura: {result.warnings}"

    def test_extreme_temperature_fails(self):
        """Temperatura > 482°C deve falhar (coeficiente Y inválido)."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=88.9,
            thickness_mm=20.0,
            pressure_bar=5.0,
            temperature_c=500.0,
        )
        assert not result.valid
        assert any("482" in e for e in result.errors)

    # ── Sugestão de Schedule ─────────────────────────────────────────────────

    def test_suggest_schedule_returns_options(self):
        """Sugestão de schedule deve retornar lista com pelo menos 1 opção."""
        result = ASMEB31_3Validator.suggest_schedule(
            diameter_mm=114.3,
            pressure_bar=50.0,
        )
        assert "suggested_schedules" in result
        assert len(result["suggested_schedules"]) >= 1
        assert "min_thickness_mm" in result
        assert result["min_thickness_mm"] > 0

    def test_suggest_schedule_high_pressure_returns_thick(self):
        """Alta pressão (30 bar) deve sugerir schedule pesado (Sch.80+)."""
        result = ASMEB31_3Validator.suggest_schedule(
            diameter_mm=114.3,
            pressure_bar=30.0,  # 30 bar é processável com Sch.80/160
        )
        schedules = [s["schedule"] for s in result["suggested_schedules"]]
        assert len(schedules) >= 1, f"Deveria sugerir pelo menos um schedule: {result}"
        # A 30 bar com DN100, schedules leves (Sch.5S, Sch.10S, Sch.STD) devem ser
        # insuficientes — apenas Sch.80 ou Sch.160 devem aparecer
        assert any("sch_80" in s or "sch_160" in s for s in schedules), \
            f"30 bar deveria sugerir sch_80 ou sch_160: {schedules}"

    # ── Meta informação ──────────────────────────────────────────────────────

    def test_meta_contains_required_fields(self):
        """Meta deve conter campos de rastreabilidade."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=114.3, thickness_mm=6.0, pressure_bar=10.0
        )
        required_meta = ["diameter_mm", "thickness_provided_mm", "pressure_bar"]
        for field in required_meta:
            assert field in result.meta, f"Campo {field} ausente no meta"

    # ── Integração via EngineeringValidator ──────────────────────────────────

    def test_engineering_validator_pipe_interface(self):
        """EngineeringValidator.validate_pipe_asme_b31_3 deve retornar dict."""
        result = EngineeringValidator.validate_pipe_asme_b31_3(
            diameter_mm=114.3, thickness_mm=6.0, pressure_bar=10.0
        )
        assert isinstance(result, dict)
        assert "valid" in result
        assert "norm" in result
        assert result["norm"] == "ASME B31.3"


# ═══════════════════════════════════════════════════════════════════════════════
# ASME B16.5 — FLANGES
# ═══════════════════════════════════════════════════════════════════════════════

class TestASMEB16_5:
    """Casos de teste para ASME B16.5 Pipe Flanges."""

    # ── Casos válidos ────────────────────────────────────────────────────────

    def test_class_150_low_pressure_valid(self):
        """Flange Classe 150 a 10 bar e 38°C deve ser válida."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=150,
            pressure_bar=10.0,
            temperature_c=38.0,
        )
        assert result.valid, f"Classe 150 deve suportar 10 bar: {result.errors}"

    def test_class_300_medium_pressure_valid(self):
        """Flange Classe 300 a 40 bar deve ser válida."""
        result = ASMEB16_5Validator.validate(
            size_inches=6.0,
            rating_class=300,
            pressure_bar=40.0,
            temperature_c=100.0,
        )
        assert result.valid, f"Classe 300 deve suportar 40 bar: {result.errors}"

    def test_class_600_high_pressure_valid(self):
        """Flange Classe 600 a 90 bar deve ser válida."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=600,
            pressure_bar=90.0,
            temperature_c=38.0,
        )
        assert result.valid, f"Classe 600 deve suportar 90 bar: {result.errors}"

    # ── Casos inválidos ──────────────────────────────────────────────────────

    def test_class_150_overpressure_fails(self):
        """Flange Classe 150 a 50 bar deve falhar."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=150,
            pressure_bar=50.0,
            temperature_c=38.0,
        )
        assert not result.valid
        assert len(result.errors) > 0
        assert any("excede" in e.lower() for e in result.errors)

    def test_invalid_class_fails(self):
        """Classe inválida (999) deve gerar erro."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=999,
            pressure_bar=10.0,
        )
        assert not result.valid
        assert any("inválida" in e.lower() or "999" in e for e in result.errors)

    def test_zero_size_fails(self):
        """Tamanho zero deve falhar."""
        result = ASMEB16_5Validator.validate(
            size_inches=0.0,
            rating_class=150,
            pressure_bar=10.0,
        )
        assert not result.valid

    def test_extreme_temperature_fails(self):
        """Temperatura > 538°C deve falhar."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=2500,
            pressure_bar=100.0,
            temperature_c=600.0,
        )
        assert not result.valid
        assert any("538" in e for e in result.errors)

    # ── Avisos ───────────────────────────────────────────────────────────────

    def test_near_limit_warning(self):
        """Pressão próxima ao limite (95%) deve gerar aviso."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=150,
            pressure_bar=18.5,  # ~95% de 19.6 bar
            temperature_c=38.0,
        )
        # Pode ser válido mas com aviso
        has_warning = len(result.warnings) > 0
        assert has_warning or not result.valid, "Deveria ter aviso em 95% do limite"

    def test_flat_face_high_class_warning(self):
        """Face plana (FF) com classe > 300 deve gerar aviso."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=600,
            pressure_bar=50.0,
            facing="FF",
        )
        has_ff_warning = any("ff" in w.lower() or "face plana" in w.lower() for w in result.warnings)
        assert has_ff_warning, f"Deveria avisar sobre FF em Classe 600: {result.warnings}"

    # ── Recomendação de upgrade ───────────────────────────────────────────────

    def test_overpressure_suggests_upgrade(self):
        """Flange fora de especificação deve recomendar classe maior."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0,
            rating_class=150,
            pressure_bar=30.0,  # Excede Classe 150
        )
        assert not result.valid
        has_recommendation = len(result.recommendations) > 0
        assert has_recommendation, "Deveria recomendar upgrade de classe"

    # ── Meta informação ──────────────────────────────────────────────────────

    def test_meta_contains_max_pressure(self):
        """Meta deve conter pressão máxima admissível."""
        result = ASMEB16_5Validator.validate(
            size_inches=4.0, rating_class=300, pressure_bar=20.0
        )
        assert "max_admissible_pressure_bar" in result.meta
        assert result.meta["max_admissible_pressure_bar"] > 0

    def test_engineering_validator_flange_interface(self):
        """EngineeringValidator.validate_flange_asme_b16_5 deve retornar dict."""
        result = EngineeringValidator.validate_flange_asme_b16_5(
            size_inches=4.0, rating_class=300, pressure_bar=20.0
        )
        assert isinstance(result, dict)
        assert result["norm"] == "ASME B16.5"


# ═══════════════════════════════════════════════════════════════════════════════
# AWS D1.1 — SOLDAGEM
# ═══════════════════════════════════════════════════════════════════════════════

class TestAWSD1_1:
    """Casos de teste para AWS D1.1 Structural Welding Code."""

    # ── Casos válidos ────────────────────────────────────────────────────────

    def test_standard_fillet_passes(self):
        """Filete 8mm em chapa 10mm deve ser válido."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=8 * 0.707,      # Garganta = leg × 0.707
            base_material_thickness_mm=10.0,
            electrode="E7018",
            weld_length_mm=200.0,
        )
        assert result.valid, f"Filete 8mm deveria ser válido: {result.errors}"
        assert result.norm == "AWS D1.1"

    def test_sufficient_strength_passes(self):
        """Solda com capacidade 2× a carga deve passar."""
        throat = 6.0  # mm
        length = 200.0  # mm
        # Capacidade ≈ 0.3 * 483 (E7018) * 6 * 200 / 1000 = 173 kN
        load_kn = 80.0  # Muito menos que a capacidade

        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=throat,
            base_material_thickness_mm=10.0,
            load_kn=load_kn,
            electrode="E7018",
            weld_length_mm=length,
        )
        assert result.valid, f"Deveria ser válido a 80 kN: {result.errors}"

    # ── Casos inválidos ──────────────────────────────────────────────────────

    def test_undersized_fillet_fails(self):
        """Filete muito pequeno para espessura de chapa deve falhar."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=1.5,   # Perna ≈ 2.1mm — insuficiente para chapa 20mm
            base_material_thickness_mm=20.0,
        )
        assert not result.valid
        assert any("insuficiente" in e.lower() or "mínimo" in e.lower() for e in result.errors)

    def test_overloaded_weld_fails(self):
        """Carga excessiva deve falhar."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=3.0,
            base_material_thickness_mm=8.0,
            load_kn=500.0,  # Muito mais que a capacidade
            weld_length_mm=100.0,
        )
        assert not result.valid
        assert any("excede" in e.lower() for e in result.errors)

    def test_zero_throat_fails(self):
        """Garganta zero deve falhar."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=0.0,
            base_material_thickness_mm=10.0,
        )
        assert not result.valid

    def test_zero_thickness_fails(self):
        """Espessura zero deve falhar."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=5.0,
            base_material_thickness_mm=0.0,
        )
        assert not result.valid

    # ── Avisos e recomendações ────────────────────────────────────────────────

    def test_high_utilization_warning(self):
        """Utilização > 85% deve gerar aviso."""
        throat = 4.0
        length = 100.0
        capacity = 0.3 * 483 * throat * length / 1000.0  # ≈ 58 kN
        load = capacity * 0.90  # 90% da capacidade

        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=throat,
            base_material_thickness_mm=8.0,
            load_kn=load,
            weld_length_mm=length,
        )
        has_high_util_warning = any(
            "85%" in w or "85" in w or "utilização" in w.lower() for w in result.warnings
        )
        assert has_high_util_warning, f"Deveria avisar alta utilização: {result.warnings}"

    def test_unknown_electrode_warns(self):
        """Eletrodo desconhecido deve gerar aviso."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=5.0,
            base_material_thickness_mm=10.0,
            electrode="E999XX",
        )
        has_electrode_warning = any("eletrodo" in w.lower() for w in result.warnings)
        assert has_electrode_warning, f"Eletrodo desconhecido deveria avisar: {result.warnings}"

    # ── Meta informação ──────────────────────────────────────────────────────

    def test_meta_contains_capacity(self):
        """Meta deve conter capacidade de solda."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=5.0,
            base_material_thickness_mm=10.0,
            weld_length_mm=150.0,
        )
        assert "weld_capacity_kn" in result.meta
        assert result.meta["weld_capacity_kn"] > 0

    def test_engineering_validator_weld_interface(self):
        """EngineeringValidator.validate_weld_aws_d1_1 deve retornar dict."""
        result = EngineeringValidator.validate_weld_aws_d1_1(
            throat_mm=5.0, base_material_thickness_mm=10.0
        )
        assert isinstance(result, dict)
        assert result["norm"] == "AWS D1.1"


# ═══════════════════════════════════════════════════════════════════════════════
# ISO 128 — DESENHO TÉCNICO
# ═══════════════════════════════════════════════════════════════════════════════

class TestISO128:
    """Casos de teste para ISO 128 Technical Drawings."""

    def test_standard_line_width_accepted(self):
        """Espessura 0.5mm (ISO 128-24) deve ser reconhecida."""
        result = ISO128Validator.validate_line_width(0.5)
        assert result.valid
        assert result.meta["closest_standard_mm"] == 0.5

    def test_nonstandard_line_width_warns(self):
        """Espessura 0.4mm não é padrão ISO — deve gerar aviso."""
        result = ISO128Validator.validate_line_width(0.4)
        assert len(result.warnings) > 0
        assert any("0.4" in w or "padrão" in w.lower() for w in result.warnings)

    def test_preferred_scale_accepted(self):
        """Escala 1:10 é preferencial ISO 5455."""
        result = ISO128Validator.validate_scale(1, 10)
        has_preferred = any("preferencial" in r.lower() for r in result.recommendations)
        assert has_preferred, f"1:10 deve ser preferencial: {result.recommendations}"

    def test_nonpreferred_scale_warns(self):
        """Escala 1:7 não é preferencial ISO 5455."""
        result = ISO128Validator.validate_scale(1, 7)
        has_warning = len(result.warnings) > 0
        assert has_warning

    def test_a4_paper_recognized(self):
        """Formato A4 (210×297mm) deve ser reconhecido."""
        result = ISO128Validator.validate_paper_format(210, 297)
        assert result.meta.get("format") == "A4"

    def test_a3_paper_recognized(self):
        """Formato A3 (297×420mm) deve ser reconhecido."""
        result = ISO128Validator.validate_paper_format(297, 420)
        assert result.meta.get("format") == "A3"

    def test_custom_paper_warns(self):
        """Formato não padrão deve gerar aviso."""
        result = ISO128Validator.validate_paper_format(250, 350)
        has_warning = len(result.warnings) > 0 or result.meta.get("format") == "custom"
        assert has_warning

    def test_engineering_validator_line_width_interface(self):
        """EngineeringValidator.validate_drawing_line_width deve retornar dict."""
        result = EngineeringValidator.validate_drawing_line_width(0.5)
        assert isinstance(result, dict)
        assert "valid" in result

    def test_engineering_validator_scale_interface(self):
        """EngineeringValidator.validate_drawing_scale deve retornar dict."""
        result = EngineeringValidator.validate_drawing_scale(1, 100)
        assert isinstance(result, dict)
        assert "valid" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE BORDA — ENTRADA EXTREMA
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Casos extremos que não devem causar exceções."""

    def test_very_large_diameter(self):
        """Diâmetro muito grande (1000mm) não deve quebrar."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=1000.0,
            thickness_mm=20.0,
            pressure_bar=10.0,
        )
        assert isinstance(result.valid, bool)

    def test_very_high_pressure(self):
        """Pressão extrema (1000 bar) deve ser processada."""
        result = ASMEB31_3Validator.validate(
            diameter_mm=114.3,
            thickness_mm=50.0,
            pressure_bar=1000.0,
        )
        assert isinstance(result.valid, bool)

    def test_float_size_flange(self):
        """Flange com tamanho fracionário não deve quebrar."""
        result = ASMEB16_5Validator.validate(
            size_inches=1.5,
            rating_class=300,
            pressure_bar=20.0,
        )
        assert isinstance(result.valid, bool)

    def test_very_long_weld(self):
        """Solda muito longa (5000mm) deve processar."""
        result = AWSD1_1Validator.validate_fillet_weld(
            throat_mm=5.0,
            base_material_thickness_mm=10.0,
            load_kn=100.0,
            weld_length_mm=5000.0,
        )
        assert isinstance(result.valid, bool)
        assert result.meta.get("weld_capacity_kn", 0) > 0

    def test_all_validators_return_dict(self):
        """Todos os validadores via EngineeringValidator devem retornar dict."""
        validations = [
            EngineeringValidator.validate_pipe_asme_b31_3(100, 5, 10),
            EngineeringValidator.validate_flange_asme_b16_5(4.0, 300, 20.0),
            EngineeringValidator.validate_weld_aws_d1_1(5.0, 10.0),
            EngineeringValidator.validate_drawing_line_width(0.5),
            EngineeringValidator.validate_drawing_scale(1, 10),
        ]
        for v in validations:
            assert isinstance(v, dict), f"Retornou {type(v)}, esperado dict"
            assert "valid" in v
            assert "norm" in v
            assert "errors" in v
            assert "warnings" in v
