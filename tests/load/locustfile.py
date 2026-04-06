# ═══════════════════════════════════════════════════════════════════════════════
# LOAD TESTING COM LOCUST - AUTOMAÇÃO CAD
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes de carga para validar performance do sistema em produção.

Executar:
    pip install locust
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Acesse: http://localhost:8089 para iniciar o teste
"""
from locust import HttpUser, task, between, events
import json
import random
import time


class CamUser(HttpUser):
    """Usuário simulado para operações CAM."""
    
    wait_time = between(1, 3)  # Espera 1-3 segundos entre requisições
    
    def on_start(self):
        """Setup inicial - login."""
        # Tentar login demo
        response = self.client.post("/auth/demo")
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}
    
    @task(10)
    def health_check(self):
        """Verificação de saúde (alta frequência)."""
        self.client.get("/health")
    
    @task(5)
    def system_metrics(self):
        """Métricas do sistema."""
        self.client.get("/system")
    
    @task(3)
    def get_materials(self):
        """Listar materiais disponíveis."""
        self.client.get("/api/cam/materials")
    
    @task(2)
    def get_library_pieces(self):
        """Listar peças da biblioteca."""
        self.client.get("/api/cam/library/pieces")
    
    @task(2)
    def parse_simple_dxf(self):
        """Parse de DXF simples."""
        dxf_content = """0
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
ENDSEC
0
EOF"""
        
        self.client.post("/api/cam/parse", json={
            "content": dxf_content,
            "filename": f"test_{random.randint(1000, 9999)}.dxf",
            "fileType": "dxf"
        })
    
    @task(2)
    def validate_geometry(self):
        """Validar geometria."""
        geometry = {
            "entities": [
                {"type": "line", "start": [0, 0], "end": [100, 0]},
                {"type": "line", "start": [100, 0], "end": [100, 100]},
                {"type": "line", "start": [100, 100], "end": [0, 100]},
                {"type": "line", "start": [0, 100], "end": [0, 0]},
            ]
        }
        
        self.client.post("/api/cam/validate", json={"geometry": geometry})
    
    @task(1)
    def generate_gcode(self):
        """Gerar G-code (operação pesada)."""
        geometry = {
            "entities": [
                {"type": "line", "start": [0, 0], "end": [100, 0]},
                {"type": "line", "start": [100, 0], "end": [100, 100]},
            ]
        }
        
        parameters = {
            "material": "mild_steel",
            "thickness_mm": 6.0,
            "amperage": 45,
            "cutting_speed_mm_min": 2500
        }
        
        self.client.post("/api/cam/generate", json={
            "geometry": geometry,
            "parameters": parameters,
            "outputFormat": "hypertherm"
        })
    
    @task(1)
    def run_nesting(self):
        """Executar nesting (operação pesada)."""
        pieces = [
            {"name": "Square", "geometry": {"type": "rectangle", "width": 100, "height": 100}, "quantity": 3},
        ]
        
        sheet = {
            "width_mm": 1500,
            "height_mm": 3000,
            "material": "mild_steel",
            "thickness_mm": 6.0
        }
        
        self.client.post("/api/cam/nesting/run", json={
            "pieces": pieces,
            "sheet": sheet,
            "options": {"spacing_mm": 10}
        })


class DashboardUser(HttpUser):
    """Usuário de dashboard (visualização)."""
    
    wait_time = between(2, 5)
    
    @task(5)
    def view_dashboard_kpis(self):
        """Visualizar KPIs do dashboard."""
        self.client.get("/api/dashboard/kpis")
    
    @task(3)
    def view_dashboard_metrics(self):
        """Visualizar métricas."""
        self.client.get("/api/dashboard/metrics")
    
    @task(2)
    def view_jobs(self):
        """Visualizar jobs."""
        self.client.get("/api/cam/jobs")
    
    @task(1)
    def view_ai_status(self):
        """Status dos engines de IA."""
        self.client.get("/api/ai/status")


class APIUser(HttpUser):
    """Usuário API genérico."""
    
    wait_time = between(1, 2)
    
    @task(10)
    def root(self):
        """Endpoint raiz."""
        self.client.get("/")
    
    @task(5)
    def openapi(self):
        """OpenAPI spec."""
        self.client.get("/openapi.json")
    
    @task(3)
    def docs(self):
        """Documentação."""
        self.client.get("/docs")


class HeavyUser(HttpUser):
    """Usuário pesado (stress test)."""
    
    wait_time = between(0.5, 1)  # Mais rápido
    
    @task(1)
    def concurrent_requests(self):
        """Múltiplas requisições concorrentes."""
        for _ in range(5):
            self.client.get("/health")
    
    @task(1)
    def large_geometry(self):
        """Geometria grande."""
        entities = []
        for i in range(50):
            entities.append({
                "type": "line",
                "start": [i * 10, 0],
                "end": [i * 10 + 5, 100]
            })
        
        self.client.post("/api/cam/validate", json={
            "geometry": {"entities": entities}
        })


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTOS E MÉTRICAS CUSTOMIZADAS
# ═══════════════════════════════════════════════════════════════════════════════

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Executado ao iniciar o teste."""
    print("=" * 60)
    print("LOAD TEST INICIADO - Automação CAD")
    print(f"Target: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Executado ao finalizar o teste."""
    print("=" * 60)
    print("LOAD TEST FINALIZADO")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Log de cada requisição."""
    if response_time > 1000:  # Mais de 1 segundo
        print(f"⚠️ SLOW REQUEST: {name} - {response_time}ms")


# ═══════════════════════════════════════════════════════════════════════════════
# CENÁRIOS DE TESTE
# ═══════════════════════════════════════════════════════════════════════════════

class MixedWorkload(HttpUser):
    """Carga mista realista."""
    
    wait_time = between(1, 5)
    
    tasks = {
        CamUser.health_check: 10,
        CamUser.get_materials: 3,
        CamUser.validate_geometry: 2,
        DashboardUser.view_dashboard_kpis: 5,
    }


if __name__ == "__main__":
    import os
    os.system("locust -f tests/load/locustfile.py --host=http://localhost:8000")
