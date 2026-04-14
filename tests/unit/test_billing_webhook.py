# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - BILLING, WEBHOOK & RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes críticos para:
- Stripe webhook idempotency
- Rate limiting (in-memory fallback)
- Checkout endpoint security
"""
import json
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from collections import defaultdict, OrderedDict
from collections import deque

# Disable watchdog CPU blocking during tests
os.environ["WATCHDOG_CPU_BLOCK"] = "101"
os.environ["WATCHDOG_RAM_BLOCK"] = "101"


class TestWebhookIdempotency:
    """Testa deduplicação de webhooks Stripe."""

    @pytest.fixture(autouse=True)
    def _disable_watchdog(self):
        """Disable AI watchdog resource blocking during tests."""
        try:
            from ai_watchdog import watchdog as _wd
            if _wd and hasattr(_wd, "guardian"):
                original_block = _wd.guardian.cpu_block
                original_ram = _wd.guardian.ram_block
                _wd.guardian.cpu_block = 101.0
                _wd.guardian.ram_block = 101.0
                yield
                _wd.guardian.cpu_block = original_block
                _wd.guardian.ram_block = original_ram
            else:
                yield
        except ImportError:
            yield

    def test_duplicate_event_rejected(self, client):
        """Webhook com mesmo event ID deve ser aceito mas marcado como duplicado."""
        event_payload = {
            "id": "evt_test_duplicate_001",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": "webhook_test@example.com",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {"tier": "starter", "email": "webhook_test@example.com"},
                }
            },
        }

        # First call should process
        r1 = client.post(
            "/api/billing/webhooks/stripe",
            content=json.dumps(event_payload),
            headers={"Content-Type": "application/json"},
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1.get("received") is True

        # Second call with same ID should be duplicate
        r2 = client.post(
            "/api/billing/webhooks/stripe",
            content=json.dumps(event_payload),
            headers={"Content-Type": "application/json"},
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("received") is True
        assert d2.get("duplicate") is True

    def test_different_events_both_processed(self, client):
        """Eventos com IDs diferentes devem ser processados."""
        for i in range(3):
            payload = {
                "id": f"evt_test_unique_{i}_{time.time()}",
                "type": "invoice.paid",
                "data": {"object": {"customer": f"cus_diff_{i}"}},
            }
            r = client.post(
                "/api/billing/webhooks/stripe",
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            assert r.status_code == 200
            assert r.json().get("duplicate") is not True

    def test_invalid_json_rejected(self, client):
        """Payload inválido deve retornar 400."""
        r = client.post(
            "/api/billing/webhooks/stripe",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_checkout_completed_creates_subscription(self, client):
        """checkout.session.completed deve criar assinatura."""
        email = f"sub_create_{int(time.time())}@test.com"
        payload = {
            "id": f"evt_sub_create_{time.time()}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": email,
                    "customer": "cus_create_test",
                    "subscription": "sub_create_test",
                    "metadata": {"tier": "professional", "email": email},
                }
            },
        }
        r = client.post(
            "/api/billing/webhooks/stripe",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200

        # Verify subscription was created
        r2 = client.get(f"/api/billing/subscription/{email}")
        assert r2.status_code == 200
        data = r2.json()
        assert data.get("tier") == "professional"
        assert data.get("status") == "active"


class TestRateLimiting:
    """Testa rate limiting genérico (in-memory fallback)."""

    def test_rate_limit_enforcement(self):
        """Verifica que rate limiting rejeita após exceder limite."""
        from server import _enforce_rate_generic

        history: defaultdict[str, deque] = defaultdict(deque)
        ip = "192.168.99.99"

        # Should allow up to max
        for _ in range(5):
            _enforce_rate_generic(ip, "rl:test", history, 5, "Rate limited")

        # Next one should raise
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _enforce_rate_generic(ip, "rl:test", history, 5, "Rate limited")
        assert exc_info.value.status_code == 429

    def test_rate_limit_window_expiry(self):
        """Verifica que entradas expiram após a janela."""
        from server import _enforce_rate_generic, RATE_LIMIT_WINDOW_SECONDS

        history: defaultdict[str, deque] = defaultdict(deque)
        ip = "10.0.0.1"

        # Fill to max
        for _ in range(3):
            _enforce_rate_generic(ip, "rl:exp", history, 3, "Limited")

        # Manually expire entries
        expired_time = time.time() - RATE_LIMIT_WINDOW_SECONDS - 1
        history[ip] = deque([expired_time, expired_time, expired_time])

        # Should now allow again
        _enforce_rate_generic(ip, "rl:exp", history, 3, "Limited")
        assert len(history[ip]) == 1


class TestCheckoutSecurity:
    """Testa segurança do checkout."""

    def test_checkout_requires_auth(self, client):
        """Checkout sem token deve retornar 401."""
        r = client.post(
            "/api/billing/checkout",
            json={
                "email": "security_test@example.com",
                "tier": "starter",
                "billing_cycle": "monthly",
                "success_url": "http://localhost/success",
                "cancel_url": "http://localhost/cancel",
            },
        )
        assert r.status_code == 401

    def test_subscription_status_nonexistent(self, client):
        """Consulta de subscription inexistente deve retornar dados padrão."""
        r = client.get("/api/billing/subscription/nonexistent@test.com")
        assert r.status_code == 200
        data = r.json()
        # Should indicate no active subscription
        assert data.get("status") != "active" or data.get("tier") == "demo"
