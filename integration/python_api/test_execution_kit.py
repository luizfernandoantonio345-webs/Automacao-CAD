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
    temp_dir = Path("data/test_execution_kit") / uuid4().hex
    output_dir = temp_dir / "output"
    log_file = temp_dir / "engine.log"
    database_path = temp_dir / "execution_kit.db"
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


def test_export_execution_kit_generates_verified_package(client: TestClient) -> None:
    response = client.post(
        "/factory/export-execution-kit",
        json={
            "altura_torre_m": 8.0,
            "qtd_porticos": 50,
            "diametro_nominal_mm": 100.0,
            "ponto_succao": {"x": 1500.0, "y": 7600.0, "z": 0.0},
            "ponto_descarga": {"x": 23500.0, "y": 7600.0, "z": 6000.0},
            "stock_lengths_m": [6.0, 12.0],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["validation"]["clash_detection"]["total_after"] == 0
    assert payload["validation"]["clash_detection"]["ladder"]["relocated"] is True
    assert payload["validation"]["clash_detection"]["piping"]["relocated"] is True

    artifacts = payload["artifacts"]
    master_path = Path(artifacts["master_technical_spec"])
    drawing_json = Path(artifacts["drawing_json"])
    drawing_dxf = Path(artifacts["drawing_dxf"])
    bom_path = Path(artifacts["bom_completo"])
    reactions_path = Path(artifacts["reacoes_apoio"])

    assert master_path.exists()
    assert drawing_json.exists()
    assert drawing_dxf.exists()
    assert bom_path.exists()
    assert reactions_path.exists()

    master_payload = json.loads(master_path.read_text(encoding="utf-8"))
    assert master_payload["header"]["critical_execution_mode"] == "local-only"
    assert master_payload["disciplinas"]["estrutura"]["summary"]["qtd_porticos"] == 50
    assert master_payload["disciplinas"]["civil"]["reacoes_apoio"]
    assert master_payload["inventario_tecnico"]["plano_corte_otimizado"]["target_met"] is True
    assert master_payload["disciplinas"]["mecanica"]["escada"]["placement"]["relocated"] is True
    assert master_payload["disciplinas"]["tubulacao"]["routing"]["segments"]