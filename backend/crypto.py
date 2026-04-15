"""
Engenharia CAD — Criptografia End-to-End para Comandos

Sistema de criptografia para proteger comandos sensíveis
entre o agente local e o backend.

Usa:
- AES-256-GCM para criptografia simétrica
- RSA-2048 para troca de chaves
- HMAC-SHA256 para integridade
"""
from __future__ import annotations

import os
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("engcad.crypto")

# Tentar importar cryptography (opcional)
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography não instalado. Criptografia avançada indisponível.")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

# Chave de assinatura (deve ser definida via variável de ambiente)
SIGNING_KEY = os.getenv("COMMAND_SIGNING_KEY", "").encode() or secrets.token_bytes(32)

# Tempo máximo para comandos (evita replay attacks)
MAX_COMMAND_AGE_SECONDS = 300  # 5 minutos


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSES DE DADOS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EncryptedCommand:
    """Comando criptografado."""
    ciphertext: str  # Base64
    nonce: str  # Base64
    tag: str  # Base64
    timestamp: int
    signature: str  # HMAC-SHA256
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": self.ciphertext,
            "nonce": self.nonce,
            "tag": self.tag,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedCommand":
        return cls(
            ciphertext=data["ciphertext"],
            nonce=data["nonce"],
            tag=data.get("tag", ""),
            timestamp=data["timestamp"],
            signature=data["signature"],
        )


@dataclass  
class SignedPayload:
    """Payload assinado (sem criptografia)."""
    payload: str  # JSON string
    timestamp: int
    signature: str  # HMAC-SHA256
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "payload": self.payload,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedPayload":
        return cls(
            payload=data["payload"],
            timestamp=data["timestamp"],
            signature=data["signature"],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HMAC SIGNING (SEMPRE DISPONÍVEL)
# ═══════════════════════════════════════════════════════════════════════════════

def sign_data(data: bytes, key: bytes = SIGNING_KEY) -> str:
    """Assina dados com HMAC-SHA256."""
    signature = hmac.new(key, data, hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def verify_signature(data: bytes, signature: str, key: bytes = SIGNING_KEY) -> bool:
    """Verifica assinatura HMAC-SHA256."""
    try:
        expected = base64.b64decode(signature)
        actual = hmac.new(key, data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def sign_payload(payload: Dict[str, Any]) -> SignedPayload:
    """
    Assina um payload JSON.
    
    Args:
        payload: Dados a assinar
        
    Returns:
        SignedPayload com assinatura
    """
    timestamp = int(time.time())
    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    # Dados a assinar: payload + timestamp
    sign_data_bytes = f"{payload_str}:{timestamp}".encode()
    signature = sign_data(sign_data_bytes)
    
    return SignedPayload(
        payload=payload_str,
        timestamp=timestamp,
        signature=signature,
    )


def verify_payload(signed: SignedPayload, max_age: int = MAX_COMMAND_AGE_SECONDS) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifica e extrai payload assinado.
    
    Args:
        signed: Payload assinado
        max_age: Idade máxima em segundos
        
    Returns:
        Tuple[válido, payload_dict ou None]
    """
    # Verificar timestamp
    now = int(time.time())
    if abs(now - signed.timestamp) > max_age:
        logger.warning(f"Payload expirado: age={now - signed.timestamp}s")
        return False, None
    
    # Verificar assinatura
    sign_data_bytes = f"{signed.payload}:{signed.timestamp}".encode()
    if not verify_signature(sign_data_bytes, signed.signature):
        logger.warning("Assinatura inválida")
        return False, None
    
    try:
        payload = json.loads(signed.payload)
        return True, payload
    except json.JSONDecodeError:
        return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# AES-GCM ENCRYPTION (REQUER CRYPTOGRAPHY)
# ═══════════════════════════════════════════════════════════════════════════════

class CommandEncryptor:
    """
    Encriptador de comandos usando AES-256-GCM.
    
    Cada instância usa uma chave de sessão diferente.
    """
    
    def __init__(self, session_key: Optional[bytes] = None):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography não instalado")
        
        self.session_key = session_key or secrets.token_bytes(32)
        self._aesgcm = AESGCM(self.session_key)
    
    @property
    def session_key_b64(self) -> str:
        """Chave de sessão em base64 (para troca)."""
        return base64.b64encode(self.session_key).decode()
    
    @classmethod
    def from_session_key(cls, key_b64: str) -> "CommandEncryptor":
        """Cria encriptador a partir de chave em base64."""
        key = base64.b64decode(key_b64)
        return cls(session_key=key)
    
    def encrypt(self, command: Dict[str, Any]) -> EncryptedCommand:
        """
        Encripta um comando.
        
        Args:
            command: Comando a encriptar
            
        Returns:
            EncryptedCommand
        """
        timestamp = int(time.time())
        
        # Adicionar timestamp ao comando
        command_with_ts = {**command, "_ts": timestamp}
        plaintext = json.dumps(command_with_ts, separators=(",", ":")).encode()
        
        # Gerar nonce (12 bytes para GCM)
        nonce = secrets.token_bytes(12)
        
        # Encriptar
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        
        # Separar tag (últimos 16 bytes do ciphertext do AESGCM)
        actual_ciphertext = ciphertext[:-16]
        tag = ciphertext[-16:]
        
        # Assinar o pacote completo
        sign_data_bytes = nonce + actual_ciphertext + tag + str(timestamp).encode()
        signature = sign_data(sign_data_bytes)
        
        return EncryptedCommand(
            ciphertext=base64.b64encode(actual_ciphertext).decode(),
            nonce=base64.b64encode(nonce).decode(),
            tag=base64.b64encode(tag).decode(),
            timestamp=timestamp,
            signature=signature,
        )
    
    def decrypt(
        self,
        encrypted: EncryptedCommand,
        max_age: int = MAX_COMMAND_AGE_SECONDS
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Decripta um comando.
        
        Args:
            encrypted: Comando encriptado
            max_age: Idade máxima em segundos
            
        Returns:
            Tuple[sucesso, comando ou None]
        """
        try:
            # Verificar timestamp
            now = int(time.time())
            if abs(now - encrypted.timestamp) > max_age:
                logger.warning(f"Comando expirado: age={now - encrypted.timestamp}s")
                return False, None
            
            # Decodificar
            ciphertext = base64.b64decode(encrypted.ciphertext)
            nonce = base64.b64decode(encrypted.nonce)
            tag = base64.b64decode(encrypted.tag)
            
            # Verificar assinatura
            sign_data_bytes = nonce + ciphertext + tag + str(encrypted.timestamp).encode()
            if not verify_signature(sign_data_bytes, encrypted.signature):
                logger.warning("Assinatura inválida no comando encriptado")
                return False, None
            
            # Reconstruir ciphertext com tag
            full_ciphertext = ciphertext + tag
            
            # Decriptar
            plaintext = self._aesgcm.decrypt(nonce, full_ciphertext, None)
            command = json.loads(plaintext.decode())
            
            # Remover timestamp interno
            command.pop("_ts", None)
            
            return True, command
            
        except Exception as e:
            logger.error(f"Erro ao decriptar comando: {e}")
            return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# RSA KEY EXCHANGE
# ═══════════════════════════════════════════════════════════════════════════════

class KeyExchange:
    """
    Troca de chaves usando RSA-2048.
    
    O agente gera um par de chaves RSA e envia a pública ao backend.
    O backend encripta a chave de sessão AES com a pública RSA.
    O agente decripta com a chave privada.
    """
    
    def __init__(self):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography não instalado")
        
        # Gerar par de chaves
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
    
    @property
    def public_key_pem(self) -> str:
        """Chave pública em formato PEM."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
    
    def encrypt_session_key(self, session_key: bytes, public_key_pem: str) -> str:
        """
        Encripta chave de sessão com chave pública RSA.
        
        Args:
            session_key: Chave AES de 32 bytes
            public_key_pem: Chave pública PEM do destinatário
            
        Returns:
            Chave encriptada em base64
        """
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        
        encrypted = public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt_session_key(self, encrypted_key_b64: str) -> bytes:
        """
        Decripta chave de sessão com chave privada RSA.
        
        Args:
            encrypted_key_b64: Chave encriptada em base64
            
        Returns:
            Chave AES de 32 bytes
        """
        encrypted = base64.b64decode(encrypted_key_b64)
        
        session_key = self._private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return session_key


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def is_encryption_available() -> bool:
    """Verifica se criptografia está disponível."""
    return CRYPTO_AVAILABLE


def generate_session_key() -> str:
    """Gera nova chave de sessão AES-256."""
    return base64.b64encode(secrets.token_bytes(32)).decode()


def hash_command(command: Dict[str, Any]) -> str:
    """Gera hash de um comando para deduplicação."""
    data = json.dumps(command, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# SECURE COMMAND API
# ═══════════════════════════════════════════════════════════════════════════════

class SecureCommandChannel:
    """
    Canal seguro para envio de comandos.
    
    Combina assinatura (sempre) + criptografia (quando disponível).
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        self._encryptor = None
        
        if encryption_key and CRYPTO_AVAILABLE:
            self._encryptor = CommandEncryptor.from_session_key(encryption_key)
    
    @property
    def is_encrypted(self) -> bool:
        return self._encryptor is not None
    
    def send(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara comando para envio seguro.
        
        Args:
            command: Comando a enviar
            
        Returns:
            Payload seguro (assinado e opcionalmente encriptado)
        """
        if self._encryptor:
            # Encriptar + assinar
            encrypted = self._encryptor.encrypt(command)
            return {
                "type": "encrypted",
                "data": encrypted.to_dict(),
            }
        else:
            # Apenas assinar
            signed = sign_payload(command)
            return {
                "type": "signed",
                "data": signed.to_dict(),
            }
    
    def receive(self, secure_payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Processa payload seguro recebido.
        
        Args:
            secure_payload: Payload recebido
            
        Returns:
            Tuple[válido, comando ou None]
        """
        payload_type = secure_payload.get("type")
        data = secure_payload.get("data", {})
        
        if payload_type == "encrypted":
            if not self._encryptor:
                logger.error("Payload encriptado mas sem chave de sessão")
                return False, None
            
            encrypted = EncryptedCommand.from_dict(data)
            return self._encryptor.decrypt(encrypted)
        
        elif payload_type == "signed":
            signed = SignedPayload.from_dict(data)
            return verify_payload(signed)
        
        else:
            logger.error(f"Tipo de payload desconhecido: {payload_type}")
            return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "CRYPTO_AVAILABLE",
    "sign_payload",
    "verify_payload",
    "SignedPayload",
    "EncryptedCommand",
    "CommandEncryptor",
    "KeyExchange",
    "SecureCommandChannel",
    "is_encryption_available",
    "generate_session_key",
    "hash_command",
]
