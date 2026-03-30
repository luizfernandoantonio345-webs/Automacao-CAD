from __future__ import annotations

from engenharia_automacao.config import settings
from engenharia_automacao.core.engine.generator import ProjectGeometry, ProjectInput


class Generator:
    """Gera um script AutoLISP simples e executavel no AutoCAD."""

    def generate(self, payload: ProjectInput, geometry: ProjectGeometry) -> str:
        layer_name = self._sanitize_text(f"{settings.layer_prefix}_{payload.code}")
        company = self._escape_text(payload.company)
        part_name = self._escape_text(payload.part_name)
        code = self._escape_text(payload.code)

        tube_start = self._point(geometry.tube.start)
        tube_end = self._point(geometry.tube.end)
        flange_center = self._point(geometry.flange.center)
        curve_start = self._point(geometry.curve.start)
        curve_center = self._point(geometry.curve.center)
        curve_end = self._point(geometry.curve.end)

        stamp_x = geometry.curve.end[0] + 20.0
        stamp_y = -20.0

        lines = [
            "(defun c:DrawGeneratedPipe ()",
            f'  (setq layer_name "{layer_name}")',
            '  (command "_.-LAYER" "_Make" layer_name "")',
            '  (setvar "CLAYER" layer_name)',
            f'  (command "_.LINE" "{tube_start}" "{tube_end}" "")',
            f'  (command "_.CIRCLE" "{flange_center}" "{geometry.flange.radius}")',
            f'  (command "_.ARC" "{curve_start}" "{curve_center}" "{curve_end}")',
            f'  (command "_.TEXT" "{self._point((stamp_x, stamp_y))}" "{settings.stamp_text_height}" "0" "EMPRESA: {company}")',
            f'  (command "_.TEXT" "{self._point((stamp_x, stamp_y - 8.0))}" "{settings.stamp_text_height}" "0" "PECA: {part_name}")',
            f'  (command "_.TEXT" "{self._point((stamp_x, stamp_y - 16.0))}" "{settings.stamp_text_height}" "0" "CODIGO: {code}")',
            '  (princ "\\nProjeto gerado com sucesso.")',
            ")",
            '(princ "\\nComando carregado: DrawGeneratedPipe")',
        ]
        return "\n".join(lines) + "\n"

    def _point(self, point: tuple[float, float]) -> str:
        return f"{point[0]:.3f},{point[1]:.3f}"

    def _sanitize_text(self, value: str) -> str:
        return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)

    def _escape_text(self, value: str) -> str:
        """Escape text for safe use in LISP strings"""
        # Remove control characters and limit length
        sanitized = "".join(char for char in value if ord(char) >= 32)
        sanitized = sanitized[:120]  # Max length

        # Escape LISP special characters that could cause injection
        sanitized = sanitized.replace("\\", "\\\\")  # Escape backslashes first
        sanitized = sanitized.replace('"', '\\"')    # Escape quotes
        sanitized = sanitized.replace("(", "\\(")    # Escape parentheses
        sanitized = sanitized.replace(")", "\\)")    # Escape parentheses
        sanitized = sanitized.replace(";", "\\;")    # Escape semicolons

        return sanitized
