from __future__ import annotations

import logging
from pathlib import Path
import re

from engenharia_automacao.cad.autocad_executor import executar_no_autocad
from engenharia_automacao.cad.lisp.generator import Generator as LispGenerator
from engenharia_automacao.config import settings
from engenharia_automacao.core.config import AUTO_EXECUTE, LSP_OUTPUT_DIR
from engenharia_automacao.core.engine.generator import Generator
from engenharia_automacao.core.integrations.excel_reader import ExcelReader
from engenharia_automacao.core.piping.line_list import build_line_list_entry, write_line_list_csv
from engenharia_automacao.core.validations.validator import Validator


class ProjectService:
    """Orquestra o fluxo de validacao, geometria e geracao CAD."""

    def __init__(
        self,
        validator: Validator | None = None,
        geometry_generator: Generator | None = None,
        cad_generator: LispGenerator | None = None,
        excel_reader: ExcelReader | None = None,
    ) -> None:
        self.validator = validator or Validator()
        self.geometry_generator = geometry_generator or Generator()
        self.cad_generator = cad_generator or LispGenerator()
        self.excel_reader = excel_reader or ExcelReader()
        self.logger = _build_logger()

    def generate_project(
        self,
        payload: dict,
        output_path: str | Path,
        execute_in_autocad: bool | None = None,
    ) -> Path:
        self.logger.info("Iniciando geracao para o codigo informado.")
        project_input = self.validator.validate(payload)
        geometry = self.geometry_generator.generate(project_input)
        lisp_code = self.cad_generator.generate(project_input, geometry)
        line_list_entry = build_line_list_entry(
            tag=project_input.code,
            diameter_mm=project_input.diameter,
            operating_pressure_bar=project_input.operating_pressure_bar,
            hydrotest_pressure_bar=project_input.hydrotest_pressure_bar,
            pressure_class=project_input.pressure_class,
            material=project_input.material,
            flange_face=project_input.flange_face,
            selected_schedule=project_input.selected_schedule,
        )

        final_path = self._resolve_output_path(output_path, project_input.code)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(lisp_code, encoding="utf-8")
        self.logger.info("Arquivo LISP gerado em %s", final_path)

        line_list_path = final_path.with_name(f"{final_path.stem}_line_list.csv")
        write_line_list_csv([line_list_entry], line_list_path)
        self.logger.info("Line list gerada em %s", line_list_path)

        should_execute = AUTO_EXECUTE if execute_in_autocad is None else execute_in_autocad
        if should_execute:
            self.logger.info("Execucao no AutoCAD habilitada: %s", final_path)
            try:
                executar_no_autocad(str(final_path))
                self.logger.info("AutoCAD executado para %s", final_path)
            except Exception as exc:
                self.logger.error("Falha na execucao AutoCAD para %s: %s", final_path, exc, exc_info=True)

        return final_path

    def generate_projects_from_excel(
        self,
        excel_path: str | Path,
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        target_dir = Path(output_dir) if output_dir else LSP_OUTPUT_DIR
        self.logger.info("Iniciando processamento em lote do Excel: %s", excel_path)
        rows = self.excel_reader.read(excel_path)

        generated_files: list[Path] = []
        line_list_entries = []
        for index, row in enumerate(rows, start=1):
            try:
                self.logger.info("Processando linha %d de %d: %s", index, len(rows), row)
                generated = self.generate_project(row, target_dir)
                generated_files.append(generated)

                project_input = self.validator.validate(row)
                line_list_entries.append(
                    build_line_list_entry(
                        tag=project_input.code,
                        diameter_mm=project_input.diameter,
                        operating_pressure_bar=project_input.operating_pressure_bar,
                        hydrotest_pressure_bar=project_input.hydrotest_pressure_bar,
                        pressure_class=project_input.pressure_class,
                        material=project_input.material,
                        flange_face=project_input.flange_face,
                        selected_schedule=project_input.selected_schedule,
                    )
                )
                self.logger.info("Linha %d processada com sucesso", index)
            except Exception as exc:
                self.logger.error("Falha ao processar linha %d: %s", index, exc, exc_info=True)
                continue

        if line_list_entries:
            consolidated_line_list = target_dir / "line_list.csv"
            write_line_list_csv(line_list_entries, consolidated_line_list)
            self.logger.info("Line list consolidada gerada em %s", consolidated_line_list)

        self.logger.info("Processamento em lote concluido: %d arquivo(s) gerado(s)", len(generated_files))
        return generated_files

    def _resolve_output_path(self, output_path: str | Path, code: str) -> Path:
        path = Path(output_path)
        if path.suffix.lower() == ".lsp":
            return path
        safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", code).strip("_") or "projeto"
        return path / f"{safe_code}.lsp"


def run(payload: dict, output_path: str | Path) -> Path:
    """Executa o fluxo principal para geracao de um arquivo LISP."""
    return ProjectService().generate_project(payload, output_path)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("engenharia_automacao")
    if logger.handlers:
        return logger

    from engenharia_automacao.core.config import LOG_LEVEL

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(settings.log_file, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    return logger
