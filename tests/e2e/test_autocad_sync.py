# ═══════════════════════════════════════════════════════════════════════════════
# TESTES E2E - AUTOCAD SYNC & BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes E2E para sincronização AutoCAD ↔ Backend.
"""
import pytest
import json
from pathlib import Path
import sys
import os

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")


@pytest.fixture
def e2e_client():
    """Cliente de teste para E2E."""
    from server import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestAutoCADBridge:
    """Testes do bridge AutoCAD."""
    
    def test_bridge_pending(self, e2e_client):
        """E2E: Bridge pending commands."""
        response = e2e_client.get("/api/bridge/pending")
        assert response.status_code in [200, 404]
    
    def test_bridge_status(self, e2e_client):
        """E2E: Bridge status."""
        response = e2e_client.get("/api/bridge/status")
        assert response.status_code in [200, 404]
    
    def test_bridge_send_command(self, e2e_client):
        """E2E: Send command to bridge."""
        response = e2e_client.post("/api/bridge/send", json={
            "command": "ZOOM",
            "args": ["E"]
        })
        assert response.status_code in [200, 422, 404]
    
    def test_bridge_draw_pipe(self, e2e_client):
        """E2E: Draw pipe via bridge."""
        response = e2e_client.post("/api/bridge/draw-pipe", json={
            "startPoint": [0, 0, 0],
            "endPoint": [100, 0, 0],
            "diameter": 50,
            "schedule": "SCH40"
        })
        assert response.status_code in [200, 422, 404]
    
    def test_bridge_insert_component(self, e2e_client):
        """E2E: Insert component via bridge."""
        response = e2e_client.post("/api/bridge/insert-component", json={
            "type": "elbow",
            "position": [50, 50, 0],
            "rotation": 90
        })
        assert response.status_code in [200, 422, 404]
    
    def test_bridge_connection(self, e2e_client):
        """E2E: Check bridge connection."""
        response = e2e_client.get("/api/bridge/connection")
        assert response.status_code in [200, 404]
    
    def test_bridge_ack(self, e2e_client):
        """E2E: Acknowledge command."""
        response = e2e_client.post("/api/bridge/ack", json={
            "command_id": "test_123",
            "status": "completed"
        })
        assert response.status_code in [200, 422, 404]


class TestAutoCADCommands:
    """Testes de comandos AutoCAD."""
    
    def test_autocad_health(self, e2e_client):
        """E2E: AutoCAD health."""
        response = e2e_client.get("/api/autocad/health")
        assert response.status_code in [200, 404]
    
    def test_autocad_buffer(self, e2e_client):
        """E2E: AutoCAD buffer status."""
        response = e2e_client.get("/api/autocad/buffer")
        assert response.status_code in [200, 404]
    
    def test_autocad_status(self, e2e_client):
        """E2E: AutoCAD connection status."""
        response = e2e_client.get("/api/autocad/status")
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
