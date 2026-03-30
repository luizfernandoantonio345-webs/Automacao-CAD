from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engenharia_automacao.core.config import LSP_OUTPUT_DIR


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    """Configuracao central do sistema."""

    output_dir: Path = BASE_DIR / "data"
    lsp_output_dir: Path = BASE_DIR / "output"
    log_file: Path = BASE_DIR / "data" / "engenharia_automacao.log"
    layer_prefix: str = "ENG"
    stamp_text_height: float = 5.0


settings = Settings()
