from __future__ import annotations

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
    temp_dir = Path("data/test_quality_gate") / uuid4().hex
    output_dir = temp_dir / "output"
    log_file = temp_dir / "quality_gate.log"
    database_path = temp_dir / "quality_gate.db"
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


def _payload() -> dict:
    return {
        "altura_torre_m": 8.0,
        "qtd_porticos": 50,
        "diametro_nominal_mm": 100.0,
        "ponto_succao": {"x": 1500.0, "y": 7600.0, "z": 0.0},
        "ponto_descarga": {"x": 23500.0, "y": 7600.0, "z": 6000.0},
        "stock_lengths_m": [6.0, 12.0],
    }


def test_generate_data_book_creates_zip_and_regap_audit(client: TestClient) -> None:
    response = client.post("/factory/data-book/generate", json=_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["regap_audit"]["status"] == "ok"

    zip_path = Path(payload["data_book"]["zip_path"])
    assert zip_path.exists()


def test_quality_gate_returns_final_decision_and_technical_solution(client: TestClient) -> None:
    response = client.post("/factory/quality-gate/final", json={**_payload(), "max_clash_resolution_iterations": 12})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["final_gate"]["status"] in {"approved", "rejected"}
    assert isinstance(payload["technical_solution"], list)
    assert len(payload["technical_solution"]) >= 1
    assert payload["regap_audit"]["status"] == "ok"
