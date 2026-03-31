from __future__ import annotations

from pathlib import Path


class ExcelReader:
    """Le planilhas Excel e converte linhas em payloads compatveis com o core."""

    COLUMN_MAP = {
        "diametro": "diameter",
        "diameter": "diameter",
        "comprimento": "length",
        "length": "length",
        "empresa": "company",
        "company": "company",
        "nome_da_peca": "part_name",
        "nome_peca": "part_name",
        "part_name": "part_name",
        "codigo": "code",
        "code": "code",
        "fluido": "fluid",
        "fluid": "fluid",
        "temperatura_c": "temperature_c",
        "temperatura": "temperature_c",
        "temperature_c": "temperature_c",
        "pressao_operacao_bar": "operating_pressure_bar",
        "pressao_bar": "operating_pressure_bar",
        "operating_pressure_bar": "operating_pressure_bar",
    }

    def read(self, file_path: str | Path) -> list[dict]:
        import pandas as pd  # lazy import — pandas not required for non-Excel operations
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError("Apenas arquivos Excel .xlsx ou .xls sao suportados.")

        dataframe = pd.read_excel(path)
        dataframe = dataframe.rename(columns=self._normalize_columns)
        records = dataframe.to_dict(orient="records")
        if not records:
            raise ValueError("A planilha nao possui registros para processamento.")
        return records

    def _normalize_columns(self, column_name: str) -> str:
        normalized = str(column_name).strip().lower().replace(" ", "_")
        return self.COLUMN_MAP.get(normalized, normalized)
