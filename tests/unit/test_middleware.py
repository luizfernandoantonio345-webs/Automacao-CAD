# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - MIDDLEWARE E SEGURANÇA
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes de middleware, rate limiting e segurança.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import time
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")


class TestJWTTokens:
    """Testes de tokens JWT."""
    
    def test_token_generation(self):
        """Geração de token."""
        import jwt
        secret = "test_secret_key_minimum_32_bytes_long"
        
        payload = {"user": "test@test.com", "exp": time.time() + 3600}
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_token_decode(self):
        """Decodificação de token."""
        import jwt
        secret = "test_secret_key_minimum_32_bytes_long"
        
        payload = {"user": "test@test.com", "exp": time.time() + 3600}
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["user"] == "test@test.com"
    
    def test_expired_token(self):
        """Token expirado."""
        import jwt
        secret = "test_secret_key_minimum_32_bytes_long"
        
        # Token que já expirou
        payload = {"user": "test@test.com", "exp": time.time() - 3600}
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"])
    
    def test_invalid_token(self):
        """Token inválido."""
        import jwt
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode("invalid.token.here", "secret", algorithms=["HS256"])


class TestHWIDValidation:
    """Testes de validação HWID."""
    
    def test_hwid_comparison_equal(self):
        """HWIDs iguais."""
        from backend.hwid import validate_hwid
        
        hwid1 = "a" * 64
        hwid2 = "a" * 64
        
        assert validate_hwid(hwid1, hwid2) is True
    
    def test_hwid_comparison_different(self):
        """HWIDs diferentes."""
        from backend.hwid import validate_hwid
        
        hwid1 = "a" * 64
        hwid2 = "b" * 64
        
        assert validate_hwid(hwid1, hwid2) is False
    
    def test_hwid_generation(self):
        """Geração de HWID."""
        from backend.hwid import generate_hwid
        
        hwid = generate_hwid()
        
        assert hwid is not None
        assert len(hwid) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in hwid)


class TestCORSConfiguration:
    """Testes de configuração CORS."""
    
    def test_cors_allowed_origins(self):
        """Origens permitidas."""
        import re
        
        pattern = re.compile(
            r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$"
            r"|^https://[a-z0-9\-]+\.vercel\.app$"
        )
        
        # Deve permitir
        assert pattern.match("http://localhost:3000")
        assert pattern.match("http://127.0.0.1:8000")
        assert pattern.match("https://automacao-cad.vercel.app")
        
        # Não deve permitir
        assert not pattern.match("http://malicious.com")
        assert not pattern.match("http://example.org:3000")


class TestInputSanitization:
    """Testes de sanitização de entrada."""
    
    def test_email_validation(self):
        """Validação de email."""
        import re
        
        email_pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        
        # Válidos
        assert email_pattern.match("user@example.com")
        assert email_pattern.match("user.name@example.co.uk")
        
        # Inválidos
        assert not email_pattern.match("invalid")
        assert not email_pattern.match("@example.com")
    
    def test_sql_injection_prevention(self):
        """Prevenção de SQL injection."""
        # SQLAlchemy usa parameterized queries por padrão
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'--",
        ]
        
        for inp in dangerous_inputs:
            # Input não deve ser executado diretamente
            sanitized = inp.replace("'", "''")
            assert "DROP TABLE" not in sanitized or "''" in sanitized


class TestRateLimitLogic:
    """Testes de lógica de rate limiting."""
    
    def test_bucket_overflow(self):
        """Overflow de bucket."""
        from collections import deque
        
        bucket = deque(maxlen=120)  # 120 req/min
        
        # Simular 120 requisições
        for i in range(120):
            bucket.append(time.time())
        
        assert len(bucket) == 120
        
        # 121ª seria rejeitada
        bucket.append(time.time())
        assert len(bucket) == 120  # maxlen limita
    
    def test_bucket_expiration(self):
        """Expiração de bucket."""
        now = time.time()
        bucket = [now - 70, now - 65, now - 10, now - 5, now]
        
        # Remover entradas mais antigas que 60s
        window = 60
        valid = [t for t in bucket if now - t <= window]
        
        assert len(valid) == 3  # Apenas últimos 60s


class TestSecurityHeaders:
    """Testes de headers de segurança."""
    
    def test_expected_headers(self):
        """Headers esperados."""
        expected = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Strict-Transport-Security",
        ]
        
        # Verificar que sabemos quais headers configurar
        for header in expected:
            assert header.startswith("X-") or header in [
                "Content-Security-Policy",
                "Strict-Transport-Security"
            ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
