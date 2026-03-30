from __future__ import annotations

from pathlib import Path

from engenharia_automacao.core.main import ProjectService
from engenharia_automacao.core.validations.validator import ValidationError


class ProjectController:
    """Intermedia a UI e o servico central sem duplicar regras de negocio."""

    def __init__(self, service: ProjectService | None = None) -> None:
        self.service = service or ProjectService()

    def generate_manual(self, payload: dict, output_file: str | Path) -> Path:
        return self.service.generate_project(payload, output_file)

    def generate_from_excel(
        self,
        excel_file: str | Path,
        output_dir: str | Path,
    ) -> list[Path]:
        return self.service.generate_projects_from_excel(excel_file, output_dir)


__all__ = ["ProjectController", "ValidationError"]
