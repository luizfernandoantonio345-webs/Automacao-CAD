# ═══════════════════════════════════════════════════════════════════════════════
# CONFTEST - FIXTURES GLOBAIS PARA TESTES
# ═══════════════════════════════════════════════════════════════════════════════
"""
Fixtures compartilhadas para todos os testes.
"""
import os
import sys
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

# Adicionar raiz do projeto ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configurar variáveis de ambiente para teste
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE APLICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    """Cria instância da aplicação FastAPI para testes."""
    from server import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Cliente de teste HTTP para a API."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def async_client(app):
    """Cliente assíncrono para testar endpoints async."""
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE AUTENTICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_user():
    """Usuário padrão para testes."""
    return {
        "username": "testuser",
        "password": "TestPassword123!",
        "email": "test@example.com",
        "full_name": "Test User"
    }


@pytest.fixture
def admin_user():
    """Usuário admin para testes."""
    return {
        "username": "admin",
        "password": "AdminPassword123!",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": "admin"
    }


@pytest.fixture
def auth_token(client, test_user):
    """Token JWT válido para testes autenticados."""
    # Tentar registrar usuário (ignora se já existe)
    client.post("/api/auth/register", json=test_user)
    
    # Login
    response = client.post("/api/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    
    if response.status_code == 200:
        return response.json().get("access_token")
    
    # Fallback para demo token
    return "demo_test_token"


@pytest.fixture
def auth_headers(auth_token):
    """Headers com autenticação para requisições."""
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE DADOS DE TESTE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_dxf_content():
    """Conteúdo DXF simples para testes."""
    return """0
SECTION
2
ENTITIES
0
LINE
10
0.0
20
0.0
11
100.0
21
100.0
0
CIRCLE
10
50.0
20
50.0
40
25.0
0
ENDSEC
0
EOF
"""


@pytest.fixture
def sample_geometry():
    """Geometria de teste para CAM."""
    return {
        "type": "polygon",
        "points": [
            {"x": 0, "y": 0},
            {"x": 100, "y": 0},
            {"x": 100, "y": 100},
            {"x": 0, "y": 100}
        ],
        "closed": True
    }


@pytest.fixture
def sample_cutting_params():
    """Parâmetros de corte plasma para testes."""
    return {
        "material": "mild_steel",
        "thickness": 6.0,
        "amperage": 45,
        "feedRate": 2500,
        "pierceHeight": 5.0,
        "cutHeight": 1.5,
        "pierceDelay": 0.5
    }


@pytest.fixture
def sample_nesting_request():
    """Request de nesting para testes."""
    return {
        "pieces": [
            {
                "id": "piece_1",
                "name": "Flange",
                "geometry": {
                    "type": "circle",
                    "radius": 50
                },
                "quantity": 4
            },
            {
                "id": "piece_2", 
                "name": "Placa",
                "geometry": {
                    "type": "rectangle",
                    "width": 100,
                    "height": 200
                },
                "quantity": 2
            }
        ],
        "sheet": {
            "width": 1500,
            "height": 3000,
            "material": "mild_steel",
            "thickness": 6.0
        },
        "settings": {
            "spacing": 10,
            "margin": 20,
            "algorithm": "genetic"
        }
    }


@pytest.fixture
def sample_project():
    """Projeto de tubulação para testes."""
    return {
        "name": "Test Project",
        "description": "Projeto de teste para tubulação",
        "refinery_id": "REPLAN",
        "pipes": [
            {
                "tag": "2-HC-1234-A1A",
                "diameter": 2,
                "material": "A106",
                "schedule": "80",
                "fluid": "HC",
                "from_point": {"x": 0, "y": 0, "z": 0},
                "to_point": {"x": 1000, "y": 0, "z": 0}
            }
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE MOCK
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_autocad():
    """Mock do driver AutoCAD para testes sem AutoCAD instalado."""
    with patch("backend.autocad_driver.AutoCADDriver") as mock:
        driver = MagicMock()
        driver.connect.return_value = True
        driver.disconnect.return_value = True
        driver.draw_line.return_value = {"success": True}
        driver.draw_pipe.return_value = {"success": True}
        driver.insert_component.return_value = {"success": True}
        driver.save.return_value = {"success": True, "path": "/tmp/test.dwg"}
        mock.return_value = driver
        yield driver


@pytest.fixture
def mock_ai_engine():
    """Mock de engine de IA para testes rápidos."""
    with patch("ai_engines.router.AIEngineRouter") as mock:
        router = MagicMock()
        router.process.return_value = {
            "success": True,
            "engine": "test_engine",
            "result": {"analysis": "Mock analysis result"},
            "confidence": 0.95
        }
        mock.return_value = router
        yield router


@pytest.fixture
def mock_database():
    """Mock de banco de dados para testes isolados."""
    with patch("backend.database.db.get_db_connection") as mock:
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        conn.execute.return_value = cursor
        mock.return_value.__enter__ = MagicMock(return_value=conn)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield conn


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE ARQUIVOS TEMPORÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    """Diretório temporário para testes de arquivo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_dxf_file(temp_dir, sample_dxf_content):
    """Arquivo DXF temporário para testes."""
    dxf_path = temp_dir / "test.dxf"
    dxf_path.write_text(sample_dxf_content)
    return dxf_path


@pytest.fixture
def temp_gcode_file(temp_dir):
    """Arquivo G-Code temporário para testes."""
    gcode_path = temp_dir / "test.nc"
    gcode_content = """G90 G40 G49
G21
M06 T1
G0 X0 Y0
G1 Z-1.5 F2500
G1 X100 Y0
G1 X100 Y100
G1 X0 Y100
G1 X0 Y0
G0 Z5
M05
M30
"""
    gcode_path.write_text(gcode_content)
    return gcode_path


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Limpa dados de teste após cada teste."""
    yield
    # Cleanup executado após cada teste
    # Pode limpar arquivos temporários, caches, etc.


# ═══════════════════════════════════════════════════════════════════════════════
# MARKERS CUSTOMIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Configura markers customizados."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "autocad: marks tests requiring AutoCAD")
    config.addinivalue_line("markers", "gpu: marks tests requiring GPU")
