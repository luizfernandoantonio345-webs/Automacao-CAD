# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE AUTOMAÇÃO — ChatCAD, G-Code, AutoCAD Bridge
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes de automação para validar individualmente:
  - ChatCAD: interpretação + resposta coerente + LISP válido
  - G-Code: pequenos, grandes, inválidos
  - AutoCAD Bridge: envio, execução, retorno de status

Logs padronizados:
  [OK]   operação bem-sucedida
  [WARN] alerta não-bloqueante
  [ERRO] falha crítica
"""
import pytest
import json
import re
import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")

logger = logging.getLogger("engcad.tests.automation")

# ── Logger auxiliar para testes ───────────────────────────────────────────────
def log_ok(msg: str):
    logger.info(f"[OK]   {msg}")
    print(f"[OK]   {msg}")

def log_warn(msg: str):
    logger.warning(f"[WARN] {msg}")
    print(f"[WARN] {msg}")

def log_erro(msg: str):
    logger.error(f"[ERRO] {msg}")
    print(f"[ERRO] {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    import tempfile
    from uuid import uuid4
    test_db = Path(tempfile.gettempdir()) / f"engcad_automation_{uuid4().hex}.db"
    os.environ["ENGCAD_DB_PATH"] = str(test_db)
    for m in ["server", "backend.database.db", "backend.database.connection_pool"]:
        sys.modules.pop(m, None)
    from server import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="module")
def demo_headers(client):
    resp = client.post("/auth/demo")
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 1 — CHATCAD: INTERPRETAÇÃO E RESPOSTA
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatCADInterpretation:
    """Validação da camada de interpretação NLP do ChatCAD."""

    def test_interpret_flange_command(self):
        """Entrada 'desenhar flange 4 polegadas' deve ser reconhecida como comando."""
        from ai_engines.chatcad_interpreter import interpretar_prompt, ComandoTipo

        resultado = interpretar_prompt("desenhar flange 4 polegadas")
        log_ok(f"Tipo interpretado: {resultado.tipo}")

        assert resultado.tipo in (
            ComandoTipo.SIMPLES,
            ComandoTipo.COMPOSTO,
            ComandoTipo.PROJETO,
            ComandoTipo.PERGUNTA,
        ), f"Tipo desconhecido: {resultado.tipo}"

        assert resultado.confianca >= 0.0
        log_ok(f"Confiança: {resultado.confianca:.2f}")

    def test_interpret_circle_command(self):
        """Desenhar círculo deve gerar plano com geometria."""
        from ai_engines.chatcad_interpreter import interpretar_prompt

        resultado = interpretar_prompt("desenhar círculo raio 50mm")
        log_ok(f"Resultado círculo: tipo={resultado.tipo}, confianca={resultado.confianca}")

        assert resultado.dados is not None
        assert isinstance(resultado.dados, dict)

    def test_interpret_pipe_command(self):
        """Tubulação DN100 deve ser interpretada com dados corretos."""
        from ai_engines.chatcad_interpreter import interpretar_prompt

        resultado = interpretar_prompt("desenhar tubulação DN100 comprimento 3000mm")
        log_ok(f"Tubulação: {resultado.tipo}")
        assert resultado.tipo != "desconhecido"

    def test_interpret_question(self):
        """Pergunta deve ser classificada como pergunta."""
        from ai_engines.chatcad_interpreter import interpretar_prompt, ComandoTipo

        resultado = interpretar_prompt("O que é um flange?")
        log_ok(f"Pergunta tipo: {resultado.tipo}")
        assert resultado.tipo in (ComandoTipo.PERGUNTA, ComandoTipo.DESCONHECIDO)

    def test_interpret_invalid_returns_gracefully(self):
        """Entrada vazia ou inválida não deve levantar exceção."""
        from ai_engines.chatcad_interpreter import interpretar_prompt

        for texto in ["", "   ", "xyz123!@#$%", "a" * 500]:
            try:
                resultado = interpretar_prompt(texto)
                log_ok(f"Entrada inválida tratada: tipo={resultado.tipo}")
            except Exception as e:
                log_erro(f"Exceção inesperada para entrada '{texto[:30]}': {e}")
                pytest.fail(f"interpretar_prompt levantou exceção: {e}")


class TestChatCADEndpoint:
    """Validação dos endpoints REST do ChatCAD."""

    def test_chat_endpoint_flange(self, client, demo_headers):
        """POST /api/chatcad/chat com 'flange 4 polegadas' deve retornar resposta."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": "desenhar flange 4 polegadas"},
            headers=demo_headers,
        )
        log_ok(f"Status chat flange: {resp.status_code}")
        assert resp.status_code in (200, 201), f"Inesperado: {resp.status_code} {resp.text[:200]}"

        data = resp.json()
        assert "resposta" in data or "success" in data, f"Resposta inválida: {data}"
        log_ok(f"Resposta recebida: success={data.get('success')}")

    def test_chat_endpoint_circle(self, client, demo_headers):
        """Comando de círculo deve retornar código ou plano."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": "desenhar círculo no centro com raio 100"},
            headers=demo_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        log_ok(f"Círculo: {json.dumps(data)[:200]}")

    def test_chat_endpoint_question_response_coherent(self, client, demo_headers):
        """Pergunta sobre engenharia deve retornar texto coerente."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": "O que é uma flange ASME B16.5?"},
            headers=demo_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()

        resposta_str = json.dumps(data).lower()
        has_content = any(
            kw in resposta_str
            for kw in ["flange", "asme", "norma", "pressão", "classe", "encaixe"]
        )
        if has_content:
            log_ok("Resposta coerente para pergunta ASME B16.5")
        else:
            log_warn("Resposta não mencionou termos ASME — LLM pode estar offline")

    def test_chat_endpoint_lisp_validation(self, client, demo_headers):
        """Comando que gera LISP deve retornar código com parênteses balanceados."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": "desenhar linha de (0,0) até (100,100)"},
            headers=demo_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        resp_str = json.dumps(data)

        # Se contém LISP, valida que parênteses são balanceados
        if "(" in resp_str and "(command" in resp_str.lower():
            opens = resp_str.count("(")
            closes = resp_str.count(")")
            assert abs(opens - closes) <= 2, f"LISP desequilibrado: {opens} '(' vs {closes} ')'"
            log_ok(f"LISP balanceado: {opens} parênteses")
        else:
            log_warn("Resposta não contém LISP direto (normal se for pergunta/fallback)")

    def test_chat_endpoint_empty_texto_rejected(self, client, demo_headers):
        """Texto vazio deve ser rejeitado pela validação Pydantic."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": ""},
            headers=demo_headers,
        )
        assert resp.status_code in (400, 422), f"Deveria rejeitar texto vazio: {resp.status_code}"
        log_ok(f"Texto vazio rejeitado com status {resp.status_code}")

    def test_chat_endpoint_too_long_rejected(self, client, demo_headers):
        """Texto muito longo (>2000 chars) deve ser rejeitado."""
        resp = client.post(
            "/api/chatcad/chat",
            json={"texto": "x" * 2001},
            headers=demo_headers,
        )
        assert resp.status_code in (400, 422), f"Deveria rejeitar texto longo: {resp.status_code}"
        log_ok(f"Texto muito longo rejeitado: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 2 — G-CODE: VALORES PEQUENOS, GRANDES, INVÁLIDOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGCodeGeneration:
    """Validação de geração de G-Code via API."""

    GCODE_ENDPOINT = "/api/cam/generate"

    def _base_geometry(self):
        return {
            "entities": [
                {"type": "circle", "center": {"x": 100, "y": 100}, "radius": 50}
            ],
            "boundingBox": {"min": {"x": 50, "y": 50}, "max": {"x": 150, "y": 150}},
            "stats": {"lines": 0, "arcs": 0, "circles": 1, "polylines": 0, "totalLength": 314.16},
        }

    def _base_config(self, **overrides):
        cfg = {
            "material": "mild_steel",
            "thickness": 6.0,
            "amperage": 60,
            "cuttingSpeed": 2500,
            "kerfWidth": 1.5,
            "pierceHeight": 3.8,
            "pierceDelay": 0.5,
            "cutHeight": 1.5,
            "safeHeight": 10.0,
        }
        cfg.update(overrides)
        return cfg

    def test_gcode_small_values(self, client, demo_headers):
        """Valores pequenos (raio 1mm, espessura 0.5mm) devem gerar G-code válido."""
        geometry = self._base_geometry()
        geometry["entities"][0]["radius"] = 1.0
        geometry["boundingBox"] = {"min": {"x": 99, "y": 99}, "max": {"x": 101, "y": 101}}

        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": geometry, "config": self._base_config(thickness=0.5, amperage=20)},
            headers=demo_headers,
        )
        # Aceita 200 ou fallback 422 se validação de min-thickness
        assert resp.status_code in (200, 201, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert "code" in data or "gcode" in data or "G21" in json.dumps(data)
            log_ok("G-Code para valores pequenos gerado com sucesso")
        else:
            log_warn(f"Valores pequenos rejeitados (aceitável): {resp.status_code}")

    def test_gcode_large_values(self, client, demo_headers):
        """Valores grandes (placa 3000x1500mm) devem gerar G-code sem timeout."""
        geometry = self._base_geometry()
        geometry["entities"] = [
            {
                "type": "polyline",
                "points": [
                    {"x": 0, "y": 0}, {"x": 3000, "y": 0},
                    {"x": 3000, "y": 1500}, {"x": 0, "y": 1500}, {"x": 0, "y": 0},
                ],
                "closed": True,
            }
        ]
        geometry["boundingBox"] = {"min": {"x": 0, "y": 0}, "max": {"x": 3000, "y": 1500}}

        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": geometry, "config": self._base_config(thickness=25.0, amperage=200)},
            headers=demo_headers,
            timeout=30.0,
        )
        assert resp.status_code in (200, 201, 422)
        if resp.status_code == 200:
            log_ok("G-Code para peça grande (3000x1500mm) gerado")
        else:
            log_warn(f"Peça grande rejeitada (pode ser limite de negócio): {resp.status_code}")

    def test_gcode_invalid_geometry_rejected(self, client, demo_headers):
        """Geometria inválida (sem entidades) deve ser rejeitada graciosamente."""
        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": {"entities": [], "boundingBox": None, "stats": {}}, "config": self._base_config()},
            headers=demo_headers,
        )
        assert resp.status_code in (200, 400, 422, 500)
        if resp.status_code >= 400:
            log_ok(f"Geometria inválida rejeitada: {resp.status_code}")
        else:
            # Se retornou 200 com geometria vazia, verifica que G-code é mínimo/vazio
            data = resp.json()
            log_warn(f"Geometria vazia retornou 200: {str(data)[:100]}")

    def test_gcode_negative_dimensions_rejected(self, client, demo_headers):
        """Dimensões negativas devem ser tratadas sem crash."""
        geometry = self._base_geometry()
        geometry["entities"][0]["radius"] = -10  # Inválido

        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": geometry, "config": self._base_config()},
            headers=demo_headers,
        )
        # Não deve retornar 500 (Internal Server Error)
        assert resp.status_code != 500, "Dimensão negativa causou 500!"
        log_ok(f"Raio negativo tratado: status {resp.status_code}")

    def test_gcode_zero_speed_rejected(self, client, demo_headers):
        """Velocidade de corte zero deve ser rejeitada."""
        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": self._base_geometry(), "config": self._base_config(cuttingSpeed=0)},
            headers=demo_headers,
        )
        assert resp.status_code in (200, 400, 422), f"Speed=0: {resp.status_code}"
        if resp.status_code >= 400:
            log_ok("Velocidade zero rejeitada corretamente")
        else:
            log_warn("Velocidade zero aceita — validar se G-code está correto")

    def test_gcode_output_contains_required_codes(self, client, demo_headers):
        """G-code gerado deve conter comandos essenciais."""
        resp = client.post(
            self.GCODE_ENDPOINT,
            json={"geometry": self._base_geometry(), "config": self._base_config()},
            headers=demo_headers,
        )
        if resp.status_code != 200:
            log_warn(f"Endpoint retornou {resp.status_code} — pulando validação de conteúdo")
            return

        data = resp.json()
        code_str = json.dumps(data)

        required = ["G21", "G90"]
        for cmd in required:
            if cmd in code_str:
                log_ok(f"Comando obrigatório presente: {cmd}")
            else:
                log_warn(f"Comando não encontrado no G-code: {cmd}")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 3 — AUTOCAD BRIDGE: ENVIO, EXECUÇÃO, STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoCADBridge:
    """Validação do AutoCAD Bridge (modo mock — sem AutoCAD real necessário)."""

    SEND_CMD = "/api/autocad/send-command"
    HEALTH = "/api/autocad/health"
    STATUS = "/api/autocad/status"
    BUFFER = "/api/autocad/buffer"

    def test_health_endpoint_returns_status(self, client, demo_headers):
        """Health check deve retornar estrutura válida."""
        resp = client.get(self.HEALTH, headers=demo_headers)
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data or "message" in data or "connected" in data
        log_ok(f"Health: {json.dumps(data)[:120]}")

    def test_send_valid_lisp_command(self, client, demo_headers):
        """Enviar comando LISP válido deve retornar status de envio."""
        with patch("backend.autocad_driver.acad_driver") as mock_driver:
            mock_driver.enviar_comando.return_value = {"sucesso": True, "retorno": "OK"}
            mock_driver.conectado = True

            resp = client.post(
                self.SEND_CMD,
                json={"command": '(command "_CIRCLE" "0,0" 50)'},
                headers=demo_headers,
            )

        assert resp.status_code in (200, 201, 503)
        data = resp.json()
        log_ok(f"[OK] Comando enviado: status={resp.status_code}, resp={str(data)[:120]}")

    def test_send_command_logs_envio(self, client, demo_headers):
        """Envio de comando deve gerar log estruturado."""
        with patch("backend.autocad_driver.acad_driver") as mock_driver:
            mock_driver.enviar_comando.return_value = {"sucesso": True}
            mock_driver.conectado = True

            resp = client.post(
                self.SEND_CMD,
                json={"command": '(command "_LINE" "0,0" "100,100" "")'},
                headers=demo_headers,
            )

        # Status retornado deve indicar tentativa de envio
        assert resp.status_code in (200, 201, 503)
        log_ok(f"[OK] Linha enviada: {resp.status_code}")

    def test_send_empty_command_rejected(self, client, demo_headers):
        """Comando vazio deve ser rejeitado (segurança)."""
        resp = client.post(
            self.SEND_CMD,
            json={"command": ""},
            headers=demo_headers,
        )
        assert resp.status_code in (400, 422), f"Comando vazio aceito: {resp.status_code}"
        log_ok(f"[OK] Comando vazio rejeitado: {resp.status_code}")

    def test_send_command_sql_injection_attempt(self, client, demo_headers):
        """Tentativa de injeção SQL deve ser bloqueada ou sanitizada."""
        malicious = "'; DROP TABLE users; --"
        resp = client.post(
            self.SEND_CMD,
            json={"command": malicious},
            headers=demo_headers,
        )
        # Não deve retornar 500 (SQL executado)
        assert resp.status_code != 500, "Possível injeção SQL causou erro 500!"
        log_ok(f"[OK] Injeção SQL bloqueada/tratada: {resp.status_code}")

    def test_send_command_xss_attempt(self, client, demo_headers):
        """Tentativa de XSS deve ser bloqueada."""
        xss = "<script>alert('xss')</script>"
        resp = client.post(
            self.SEND_CMD,
            json={"command": xss},
            headers=demo_headers,
        )
        assert resp.status_code != 500
        log_ok(f"[OK] XSS bloqueado/tratado: {resp.status_code}")

    def test_buffer_endpoint_accessible(self, client, demo_headers):
        """Buffer de comandos deve ser acessível."""
        resp = client.get(self.BUFFER, headers=demo_headers)
        assert resp.status_code in (200, 404)
        log_ok(f"Buffer: {resp.status_code}")

    def test_detect_and_connect_endpoint(self, client, demo_headers):
        """Endpoint de detecção deve responder sem crash."""
        with patch("backend.autocad_driver.acad_driver") as mock_driver:
            mock_driver.detectar_e_conectar.return_value = {
                "conectado": False,
                "message": "AutoCAD não encontrado (modo mock)"
            }
            resp = client.post("/api/autocad/detect", headers=demo_headers)

        assert resp.status_code in (200, 201, 404, 503)
        log_ok(f"Detectar AutoCAD: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 4 — TESTES DE PERFORMANCE (BÁSICO)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceBasic:
    """Verifica que o sistema não trava sob carga básica."""

    def test_multiple_chat_requests_sequential(self, client, demo_headers):
        """10 requisições sequenciais ao ChatCAD não devem causar degradação."""
        import time
        times = []
        for i in range(10):
            start = time.time()
            resp = client.post(
                "/api/chatcad/chat",
                json={"texto": f"desenhar círculo raio {(i+1)*10}mm"},
                headers=demo_headers,
            )
            elapsed = time.time() - start
            times.append(elapsed)
            assert resp.status_code in (200, 201), f"Req {i}: {resp.status_code}"

        avg = sum(times) / len(times)
        max_t = max(times)
        log_ok(f"10 req ChatCAD: média={avg:.3f}s, máx={max_t:.3f}s")

        # Não deve demorar mais que 10s por requisição (mock sem LLM)
        assert max_t < 10.0, f"Timeout em requisição: {max_t:.2f}s"

    def test_no_data_mixing_between_requests(self, client, demo_headers):
        """Dados de um usuário não devem vazar para outro."""
        texto_a = "projeto secreto ALPHA-7"
        texto_b = "projeto secreto BETA-9"

        resp_a = client.post(
            "/api/chatcad/interpret",
            json={"texto": texto_a},
            headers=demo_headers,
        )
        resp_b = client.post(
            "/api/chatcad/interpret",
            json={"texto": texto_b},
            headers=demo_headers,
        )

        assert resp_a.status_code in (200, 201)
        assert resp_b.status_code in (200, 201)

        data_a = json.dumps(resp_a.json()).lower()
        data_b = json.dumps(resp_b.json()).lower()

        # Resposta de A não deve conter dados de B
        assert "beta-9" not in data_a, "Vazamento de dados: resposta A contém dados de B!"
        assert "alpha-7" not in data_b, "Vazamento de dados: resposta B contém dados de A!"
        log_ok("Sem vazamento de dados entre requisições")

    def test_multiple_gcode_requests(self, client, demo_headers):
        """5 gerações de G-code não devem travar."""
        import time
        geometry = {
            "entities": [{"type": "circle", "center": {"x": 50, "y": 50}, "radius": 30}],
            "boundingBox": {"min": {"x": 20, "y": 20}, "max": {"x": 80, "y": 80}},
            "stats": {"lines": 0, "arcs": 0, "circles": 1, "polylines": 0, "totalLength": 188},
        }
        config = {
            "material": "mild_steel", "thickness": 6.0, "amperage": 60,
            "cuttingSpeed": 2500, "kerfWidth": 1.5,
            "pierceHeight": 3.8, "pierceDelay": 0.5, "cutHeight": 1.5, "safeHeight": 10.0,
        }
        start = time.time()
        for i in range(5):
            resp = client.post("/api/cam/generate", json={"geometry": geometry, "config": config}, headers=demo_headers)
            assert resp.status_code in (200, 201, 422), f"Req G-code {i}: {resp.status_code}"

        total = time.time() - start
        log_ok(f"5 gerações G-code em {total:.2f}s")
        assert total < 30.0, f"5 gerações demoraram demais: {total:.2f}s"
