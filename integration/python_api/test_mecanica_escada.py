from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENG_AUTH_SECRET", "test-secret")

from integration.python_api import app as api_module


@pytest.fixture
def client() -> TestClient:
    temp_dir = Path("data/test_mecanica_escada") / uuid4().hex
    output_dir = temp_dir / "output"
    log_file = temp_dir / "engine.log"
    database_path = temp_dir / "mecanica_escada.db"
    test_config = replace(
        api_module.CONFIG,
        data_dir=temp_dir,
        output_dir=output_dir,
        log_file=log_file,
        database_url=f"sqlite:///{database_path}",
    )
    api_module.app.dependency_overrides[api_module.get_app_config] = lambda: test_config
    api_module.app.dependency_overrides[api_module.get_output_dir] = lambda: output_dir
    api_module.app.dependency_overrides[api_module.get_log_file] = lambda: log_file
    test_client = TestClient(api_module.app)
    try:
        yield test_client
    finally:
        test_client.close()
        api_module.app.dependency_overrides.clear()
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_escada_marinheiro_exports_fabrication_artifacts(client: TestClient) -> None:
    response = client.post(
        "/mecanica/escada-marinheiro",
        json={
            "altura_torre_m": 8.0,
            "comprimento_barra_comercial_mm": 12000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"

    artifacts = payload["artifacts"]
    detail_json_path = Path(artifacts["detalhamento_json"])
    bom_csv_path = Path(artifacts["bom_csv"])
    cut_csv_path = Path(artifacts["cut_plan_csv"])
    dxf_script_path = Path(artifacts["dxf_script"])
    welding_notes_path = Path(artifacts["welding_notes_txt"])

    assert detail_json_path.exists()
    assert bom_csv_path.exists()
    assert cut_csv_path.exists()
    assert dxf_script_path.exists()
    assert welding_notes_path.exists()

    detail_payload = json.loads(detail_json_path.read_text(encoding="utf-8"))
    assert detail_payload["detalhamento"]["layers_exportacao_dxf"] == ["01_PERFIL", "02_FUROS", "03_SOLDA", "04_TEXTOS"]
    assert detail_payload["detalhamento"]["notas_soldagem"]["consumivel"] == "E7018"
    assert detail_payload["detalhamento"]["plano_corte"]["stock_length_mm"] == 12000

    dxf_script = dxf_script_path.read_text(encoding="utf-8")
    assert "01_PERFIL" in dxf_script
    assert "02_FUROS" in dxf_script
    assert "03_SOLDA" in dxf_script
    assert "04_TEXTOS" in dxf_script

    welding_notes = welding_notes_path.read_text(encoding="utf-8")
    assert "E7018" in welding_notes
    assert "SMAW" in welding_notes

    bom_csv = bom_csv_path.read_text(encoding="utf-8")
    assert "MONTANTE_LATERAL" in bom_csv
    assert "DEGRAU_ANTI_DERRAPANTE" in bom_csv

    cut_csv = cut_csv_path.read_text(encoding="utf-8")
    assert "batch_units" in cut_csv
    assert "barra_id" in cut_csv