from __future__ import annotations

import time
from pathlib import Path

from integration.python_api.dependencies import CONFIG, get_api_logger


def execute_autocad_with_retry(result_path: Path) -> None:
    last_exc: Exception | None = None
    logger = get_api_logger()
    for attempt in range(1, CONFIG.max_autocad_retries + 1):
        try:
            from cad.autocad_executor import executar_no_autocad

            executar_no_autocad(str(result_path))
            return
        except Exception as exc:
            last_exc = exc
            logger.warning("Tentativa %d/%d falhou no AutoCAD: %s", attempt, CONFIG.max_autocad_retries, exc)
            time.sleep(0.5 * attempt)
    raise RuntimeError(f"Falha AutoCAD apos {CONFIG.max_autocad_retries} tentativa(s): {last_exc}")
