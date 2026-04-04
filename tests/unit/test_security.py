# ═══════════════════════════════════════════════════════════════════════════════
# TESTES - BACKEND SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes unitários para middleware de segurança.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def security_module():
    """Importa módulo de segurança."""
    from backend import security
    return security


@pytest.fixture
def security_config(security_module):
    """Configuração padrão de segurança."""
    return security_module.SecurityConfig()


@pytest.fixture
def custom_config(security_module):
    """Configuração customizada."""
    return security_module.SecurityConfig(
        hsts_enabled=True,
        hsts_max_age=86400,  # 1 dia
        csp_enabled=True,
        frame_options="SAMEORIGIN",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES SECURITY CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityConfig:
    """Testes para SecurityConfig."""
    
    def test_default_config(self, security_config):
        """Testa configuração padrão."""
        assert security_config.hsts_enabled is True
        assert security_config.hsts_max_age == 31536000  # 1 ano
        assert security_config.csp_enabled is True
        assert security_config.frame_options == "DENY"
    
    def test_custom_config(self, custom_config):
        """Testa configuração customizada."""
        assert custom_config.hsts_max_age == 86400
        assert custom_config.frame_options == "SAMEORIGIN"
    
    def test_from_env(self, security_module):
        """Testa carregamento do ambiente."""
        with patch.dict("os.environ", {
            "SECURITY_HSTS_DISABLED": "1",
            "SECURITY_FRAME_OPTIONS": "SAMEORIGIN"
        }):
            config = security_module.SecurityConfig.from_env()
            
            assert config.hsts_enabled is False
            assert config.frame_options == "SAMEORIGIN"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES HEADER BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHeaderBuilders:
    """Testes para funções construtoras de headers."""
    
    def test_build_hsts_header(self, security_module, security_config):
        """Testa construção do header HSTS."""
        header = security_module.build_hsts_header(security_config)
        
        assert "max-age=31536000" in header
        assert "includeSubDomains" in header
    
    def test_build_hsts_with_preload(self, security_module):
        """Testa HSTS com preload."""
        config = security_module.SecurityConfig(
            hsts_preload=True,
            hsts_include_subdomains=True
        )
        header = security_module.build_hsts_header(config)
        
        assert "preload" in header
    
    def test_build_csp_header(self, security_module, security_config):
        """Testa construção do header CSP."""
        header = security_module.build_csp_header(security_config)
        
        assert "default-src" in header
        assert "'self'" in header
        assert "script-src" in header
        assert "frame-ancestors" in header
    
    def test_build_permissions_policy(self, security_module, security_config):
        """Testa construção do Permissions-Policy."""
        header = security_module.build_permissions_policy(security_config)
        
        assert "geolocation=()" in header
        assert "microphone=()" in header
        assert "camera=()" in header


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    """Testes para SimpleRateLimiter."""
    
    def test_allows_under_limit(self, security_module):
        """Testa que permite requisições dentro do limite."""
        config = security_module.RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100
        )
        limiter = security_module.SimpleRateLimiter(config)
        
        for i in range(5):
            assert limiter.is_allowed("client1") is True
    
    def test_blocks_over_limit(self, security_module):
        """Testa bloqueio quando limite é excedido."""
        config = security_module.RateLimitConfig(
            requests_per_minute=3,
            requests_per_hour=100
        )
        limiter = security_module.SimpleRateLimiter(config)
        
        # Primeiras 3 passam
        for i in range(3):
            assert limiter.is_allowed("client1") is True
        
        # 4ª é bloqueada
        assert limiter.is_allowed("client1") is False
    
    def test_different_clients(self, security_module):
        """Testa que clientes diferentes têm limites separados."""
        config = security_module.RateLimitConfig(requests_per_minute=2)
        limiter = security_module.SimpleRateLimiter(config)
        
        # Cliente 1 usa seus 2
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False
        
        # Cliente 2 ainda tem seus 2
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is False
    
    def test_disabled_limiter(self, security_module):
        """Testa limiter desabilitado."""
        config = security_module.RateLimitConfig(
            requests_per_minute=1,
            enabled=False
        )
        limiter = security_module.SimpleRateLimiter(config)
        
        # Tudo passa quando desabilitado
        for i in range(10):
            assert limiter.is_allowed("client1") is True


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES CORS CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestCORSConfig:
    """Testes para configuração CORS."""
    
    def test_default_origins(self, security_module):
        """Testa origens padrão."""
        config = security_module.get_secure_cors_config()
        
        assert "allow_origins" in config
        assert "http://localhost:3000" in config["allow_origins"]
    
    def test_custom_origins_from_env(self, security_module):
        """Testa origens do ambiente."""
        with patch.dict("os.environ", {
            "CORS_ORIGINS": "https://app1.com,https://app2.com"
        }):
            config = security_module.get_secure_cors_config()
            
            assert "https://app1.com" in config["allow_origins"]
            assert "https://app2.com" in config["allow_origins"]
    
    def test_cors_credentials(self, security_module):
        """Testa que credentials está habilitado."""
        config = security_module.get_secure_cors_config()
        assert config["allow_credentials"] is True
    
    def test_cors_methods(self, security_module):
        """Testa métodos permitidos."""
        config = security_module.get_secure_cors_config()
        
        assert "GET" in config["allow_methods"]
        assert "POST" in config["allow_methods"]
        assert "DELETE" in config["allow_methods"]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES SECURE RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecureResponse:
    """Testes para secure_response helper."""
    
    def test_adds_headers_to_response(self, security_module):
        """Testa que headers são adicionados."""
        from starlette.responses import JSONResponse
        
        response = JSONResponse({"data": "test"})
        secured = security_module.secure_response(response)
        
        assert "X-Content-Type-Options" in secured.headers
        assert "X-Frame-Options" in secured.headers
        assert "X-XSS-Protection" in secured.headers
        assert "Referrer-Policy" in secured.headers
    
    def test_hsts_when_enabled(self, security_module):
        """Testa HSTS quando habilitado."""
        from starlette.responses import JSONResponse
        
        config = security_module.SecurityConfig(hsts_enabled=True)
        response = JSONResponse({"data": "test"})
        secured = security_module.secure_response(response, config)
        
        assert "Strict-Transport-Security" in secured.headers
    
    def test_no_hsts_when_disabled(self, security_module):
        """Testa sem HSTS quando desabilitado."""
        from starlette.responses import JSONResponse
        
        config = security_module.SecurityConfig(hsts_enabled=False)
        response = JSONResponse({"data": "test"})
        secured = security_module.secure_response(response, config)
        
        assert "Strict-Transport-Security" not in secured.headers


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityIntegration:
    """Testes de integração com FastAPI."""
    
    @pytest.mark.asyncio
    async def test_middleware_adds_headers(self, security_module):
        """Testa que middleware adiciona headers a todas as respostas."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        security_module.add_security_headers(app)
        
        @app.get("/test")
        async def test_route():
            return {"status": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_setup_security(self, security_module):
        """Testa setup_security completo."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        security_module.setup_security(app)
        
        client = TestClient(app)
        
        # Verifica endpoint de check
        response = client.get("/api/security/check")
        assert response.status_code == 200
        
        data = response.json()
        assert "cors_origins" in data
        assert "hsts_enabled" in data
        assert data["headers_active"] is True
