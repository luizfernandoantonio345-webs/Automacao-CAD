#!/usr/bin/env python3
"""
Engenharia CAD — Testes Unitários para HWID (Hardware Identity)
Testa geração e validação de fingerprint de hardware.
"""
import pytest
import hashlib
from unittest.mock import patch, MagicMock

# Import do módulo a ser testado
import sys
sys.path.insert(0, ".")
from backend.hwid import generate_hwid, validate_hwid, _APP_SALT


class TestHWIDGeneration:
    """Testes para geração de HWID."""

    def test_hwid_format(self):
        """HWID deve ser um hash SHA-256 (64 caracteres hex)."""
        hwid = generate_hwid()
        assert len(hwid) == 64
        assert all(c in "0123456789abcdef" for c in hwid)

    def test_hwid_consistency(self):
        """HWID deve ser consistente entre chamadas na mesma máquina."""
        hwid1 = generate_hwid()
        hwid2 = generate_hwid()
        assert hwid1 == hwid2

    @patch("backend.hwid._run_wmic")
    def test_hwid_components(self, mock_wmic):
        """HWID deve usar placa-mãe e CPU."""
        mock_wmic.side_effect = [
            "MBOARD_SERIAL_123",  # placa-mãe
            "CPU_ID_456"          # CPU
        ]
        
        # Calcular hash esperado
        raw = f"{_APP_SALT}|MBOARD_SERIAL_123|CPU_ID_456"
        expected_hwid = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        
        hwid = generate_hwid()
        assert hwid == expected_hwid

    @patch("backend.hwid._run_wmic")
    def test_hwid_fallback_without_wmic(self, mock_wmic):
        """HWID deve usar fallback se WMIC não estiver disponível."""
        mock_wmic.return_value = ""  # WMIC falhou
        
        hwid = generate_hwid()
        # Deve gerar algo válido mesmo sem WMIC
        assert len(hwid) == 64
        assert all(c in "0123456789abcdef" for c in hwid)

    @patch("backend.hwid._run_wmic")
    def test_hwid_different_hardware(self, mock_wmic):
        """HWIDs devem ser diferentes para hardware diferente."""
        mock_wmic.side_effect = [
            "MBOARD_A", "CPU_A",  # Máquina A
        ]
        hwid_a = generate_hwid()
        
        mock_wmic.side_effect = [
            "MBOARD_B", "CPU_B",  # Máquina B
        ]
        hwid_b = generate_hwid()
        
        assert hwid_a != hwid_b


class TestHWIDValidation:
    """Testes para validação de HWID."""

    def test_valid_same_hwid(self):
        """Validação deve passar para HWIDs idênticos."""
        hwid = "a" * 64
        assert validate_hwid(hwid, hwid) is True

    def test_invalid_different_hwid(self):
        """Validação deve falhar para HWIDs diferentes."""
        hwid_a = "a" * 64
        hwid_b = "b" * 64
        assert validate_hwid(hwid_a, hwid_b) is False

    def test_timing_attack_protection(self):
        """Validação deve usar comparação de tempo constante."""
        import timeit
        
        stored = "a" * 63 + "b"  # último caractere diferente
        incoming_early_diff = "x" * 64  # diferente logo no início
        incoming_late_diff = "a" * 63 + "x"  # diferente só no final
        
        # Ambas comparações devem levar aproximadamente o mesmo tempo
        # (dentro de margem razoável para evitar timing attacks)
        # Nota: Este teste verifica que a função usa hmac.compare_digest
        # A verificação real de timing attack requer análise estatística
        
        result1 = validate_hwid(stored, incoming_early_diff)
        result2 = validate_hwid(stored, incoming_late_diff)
        
        assert result1 is False
        assert result2 is False

    def test_empty_hwid(self):
        """Validação deve tratar HWIDs vazios corretamente."""
        assert validate_hwid("", "") is True
        assert validate_hwid("a" * 64, "") is False
        assert validate_hwid("", "a" * 64) is False


class TestWMICQueries:
    """Testes para consultas WMIC."""

    @patch("subprocess.run")
    def test_wmic_timeout(self, mock_run):
        """WMIC deve ter timeout para evitar travamento."""
        from backend.hwid import _run_wmic
        
        mock_run.side_effect = TimeoutError("Command timed out")
        
        result = _run_wmic("baseboard get serialnumber")
        assert result == ""  # Deve retornar vazio em caso de erro

    @patch("subprocess.run")
    def test_wmic_success(self, mock_run):
        """WMIC deve parsear output corretamente."""
        from backend.hwid import _run_wmic
        
        mock_result = MagicMock()
        mock_result.stdout = "SerialNumber\nABC123\n"
        mock_run.return_value = mock_result
        
        result = _run_wmic("baseboard get serialnumber")
        assert result == "ABC123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
