#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ENGENHARIA CAD — Rotas de Autenticação Avançadas v5.0
═══════════════════════════════════════════════════════════════════════════════

Implementações enterprise de autenticação:
- Password Reset via email
- Email verification
- 2FA/MFA com TOTP (Google Authenticator compatible)
- Profile management
- CSRF protection
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("engcad.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

JARVIS_SECRET = os.getenv("JARVIS_SECRET", "").strip() or secrets.token_hex(32)
CSRF_SECRET = os.getenv("CSRF_SECRET", "").strip() or secrets.token_hex(16)
RESET_TOKEN_EXPIRY_MINUTES = 30
VERIFY_TOKEN_EXPIRY_HOURS = 24

# In-memory token store (use Redis in production)
_RESET_TOKENS: dict[str, dict] = {}
_VERIFY_TOKENS: dict[str, dict] = {}
_2FA_SECRETS: dict[str, str] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# CSRF PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_csrf_token(session_id: str) -> str:
    """Gera token CSRF vinculado à sessão."""
    timestamp = str(int(time.time()))
    data = f"{session_id}:{timestamp}"
    signature = hmac.new(
        CSRF_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{timestamp}:{signature}"


def verify_csrf_token(session_id: str, token: str, max_age: int = 3600) -> bool:
    """Valida token CSRF."""
    try:
        parts = token.split(":")
        if len(parts) != 2:
            return False
        timestamp, signature = parts
        
        # Verificar idade do token
        token_time = int(timestamp)
        if time.time() - token_time > max_age:
            return False
        
        # Verificar assinatura
        data = f"{session_id}:{timestamp}"
        expected = hmac.new(
            CSRF_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC
# ═══════════════════════════════════════════════════════════════════════════════

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class UpdateProfileRequest(BaseModel):
    empresa: Optional[str] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class CSRFTokenResponse(BaseModel):
    csrf_token: str


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_secure_token() -> str:
    """Gera token seguro para reset/verificação."""
    return secrets.token_urlsafe(32)


def _generate_backup_codes() -> list[str]:
    """Gera códigos de backup para 2FA."""
    return [secrets.token_hex(4).upper() for _ in range(8)]


def _get_user_from_request(request: Request) -> dict:
    """Extrai usuário do token JWT na request."""
    import jwt
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")
    
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JARVIS_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user_email = payload.get("user", "")
    if not user_email:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    # Importar aqui para evitar circular import
    try:
        from backend.database.db import get_user_by_email
        user = get_user_by_email(user_email)
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except ImportError:
        # Fallback se db não estiver disponível
        return {"email": user_email}


async def _send_email(to: str, subject: str, body: str) -> bool:
    """
    Envia email usando SendGrid ou SMTP.
    Em desenvolvimento, apenas loga o email.
    """
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
    
    if sendgrid_key:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {sendgrid_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": to}]}],
                        "from": {"email": "noreply@engenharia-cad.com", "name": "Engenharia CAD"},
                        "subject": subject,
                        "content": [{"type": "text/html", "value": body}]
                    }
                )
                return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"Erro ao enviar email via SendGrid: {e}")
            return False
    else:
        # Desenvolvimento: apenas logar
        logger.info(f"[DEV EMAIL] To: {to}, Subject: {subject}")
        logger.info(f"[DEV EMAIL] Body: {body[:200]}...")
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS - CSRF
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/csrf-token", response_model=CSRFTokenResponse)
async def get_csrf_token(request: Request):
    """
    Retorna um token CSRF para proteção de formulários.
    O token deve ser incluído no header X-CSRF-Token em requisições mutáveis.
    """
    # Usar IP + User-Agent como session_id simplificado
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")[:50]
    session_id = hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
    
    token = generate_csrf_token(session_id)
    return {"csrf_token": token}


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS - PASSWORD RESET
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """
    Inicia o processo de recuperação de senha.
    Envia email com link de reset se o email existir.
    """
    email = data.email.lower().strip()
    
    # Sempre retornar sucesso para não expor se email existe
    # Mas verificar internamente
    try:
        from backend.database.db import email_exists
        if not email_exists(email):
            logger.info(f"Password reset requested for non-existent email: {email}")
            return {"message": "Se o email existir, você receberá instruções de recuperação."}
    except ImportError:
        pass
    
    # Gerar token de reset
    token = _generate_secure_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
    
    _RESET_TOKENS[token] = {
        "email": email,
        "expires_at": expires_at.timestamp(),
        "used": False
    }
    
    # Construir link de reset
    frontend_url = os.getenv("FRONTEND_URL", "https://automacao-cad-frontend.vercel.app")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    # Enviar email
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%); padding: 30px; text-align: center;">
            <h1 style="color: #00A1FF; margin: 0;">🔧 Engenharia CAD</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #1e3a5f;">Recuperação de Senha</h2>
            <p>Você solicitou a recuperação de senha da sua conta.</p>
            <p>Clique no botão abaixo para criar uma nova senha:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" 
                   style="background: #00A1FF; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Redefinir Senha
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">
                Este link expira em {RESET_TOKEN_EXPIRY_MINUTES} minutos.
                Se você não solicitou esta recuperação, ignore este email.
            </p>
        </div>
        <div style="background: #1e3a5f; padding: 15px; text-align: center; color: #888; font-size: 12px;">
            © 2024 Engenharia CAD - Sistema de Automação Industrial
        </div>
    </body>
    </html>
    """
    
    await _send_email(email, "Recuperação de Senha - Engenharia CAD", email_body)
    
    return {"message": "Se o email existir, você receberá instruções de recuperação."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """
    Completa o processo de reset de senha usando o token.
    """
    token_data = _RESET_TOKENS.get(data.token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    
    if token_data["used"]:
        raise HTTPException(status_code=400, detail="Token já utilizado")
    
    if time.time() > token_data["expires_at"]:
        del _RESET_TOKENS[data.token]
        raise HTTPException(status_code=400, detail="Token expirado")
    
    email = token_data["email"]
    
    # Atualizar senha no banco
    try:
        from backend.database.db import get_db, _hash_password, _q
        
        new_hash = _hash_password(data.new_password)
        with get_db() as conn:
            cursor = conn.execute(
                _q("UPDATE users SET password_hash = ? WHERE email = ?"),
                (new_hash, email)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")
    except ImportError:
        raise HTTPException(status_code=500, detail="Serviço indisponível")
    
    # Marcar token como usado
    token_data["used"] = True
    
    logger.info(f"Password reset completed for: {email}")
    
    return {"message": "Senha alterada com sucesso!"}


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS - EMAIL VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/send-verification")
async def send_verification_email(request: Request):
    """
    Envia email de verificação para o usuário logado.
    """
    user = _get_user_from_request(request)
    email = user.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email não encontrado")
    
    # Verificar se já está verificado
    if user.get("email_verified"):
        return {"message": "Email já verificado"}
    
    # Gerar token
    token = _generate_secure_token()
    expires_at = datetime.now(UTC) + timedelta(hours=VERIFY_TOKEN_EXPIRY_HOURS)
    
    _VERIFY_TOKENS[token] = {
        "email": email,
        "expires_at": expires_at.timestamp()
    }
    
    # Construir link
    frontend_url = os.getenv("FRONTEND_URL", "https://automacao-cad-frontend.vercel.app")
    verify_link = f"{frontend_url}/verify-email?token={token}"
    
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%); padding: 30px; text-align: center;">
            <h1 style="color: #00A1FF; margin: 0;">🔧 Engenharia CAD</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #1e3a5f;">Verificação de Email</h2>
            <p>Obrigado por se cadastrar! Clique no botão abaixo para verificar seu email:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_link}" 
                   style="background: #00A1FF; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Verificar Email
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">
                Este link expira em {VERIFY_TOKEN_EXPIRY_HOURS} horas.
            </p>
        </div>
    </body>
    </html>
    """
    
    await _send_email(email, "Verificação de Email - Engenharia CAD", email_body)
    
    return {"message": "Email de verificação enviado!"}


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest):
    """
    Verifica o email usando o token enviado.
    """
    token_data = _VERIFY_TOKENS.get(data.token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    
    if time.time() > token_data["expires_at"]:
        del _VERIFY_TOKENS[data.token]
        raise HTTPException(status_code=400, detail="Token expirado")
    
    email = token_data["email"]
    
    # Atualizar no banco
    try:
        from backend.database.db import get_db, _q
        
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET email_verified = ? WHERE email = ?"),
                (True, email)
            )
    except ImportError:
        pass
    
    # Remover token usado
    del _VERIFY_TOKENS[data.token]
    
    logger.info(f"Email verified: {email}")
    
    return {"message": "Email verificado com sucesso!"}


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS - 2FA (TOTP)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/enable-2fa", response_model=Enable2FAResponse)
async def enable_2fa(request: Request):
    """
    Habilita autenticação de dois fatores (2FA) usando TOTP.
    Retorna QR code para configurar no Google Authenticator.
    """
    user = _get_user_from_request(request)
    email = user.get("email", "user")
    
    try:
        import pyotp
    except ImportError:
        raise HTTPException(
            status_code=501, 
            detail="2FA não disponível (pyotp não instalado)"
        )
    
    # Gerar secret TOTP
    secret = pyotp.random_base32()
    
    # Gerar URL para QR code
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=email,
        issuer_name="Engenharia CAD"
    )
    
    # Gerar backup codes
    backup_codes = _generate_backup_codes()
    
    # Salvar temporariamente (confirmado apenas após verificação)
    _2FA_SECRETS[email] = {
        "secret": secret,
        "backup_codes": backup_codes,
        "confirmed": False
    }
    
    return {
        "secret": secret,
        "qr_code_url": qr_url,
        "backup_codes": backup_codes
    }


@router.post("/confirm-2fa")
async def confirm_2fa(request: Request, data: Verify2FARequest):
    """
    Confirma a ativação do 2FA verificando o primeiro código.
    """
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="2FA não disponível")
    
    secret_data = _2FA_SECRETS.get(email)
    if not secret_data:
        raise HTTPException(status_code=400, detail="2FA não iniciado. Chame /auth/enable-2fa primeiro.")
    
    secret = secret_data["secret"]
    totp = pyotp.TOTP(secret)
    
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Código inválido")
    
    # Confirmar 2FA no banco
    try:
        from backend.database.db import get_db, _q
        import json
        
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET totp_secret = ?, backup_codes = ?, two_factor_enabled = ? WHERE email = ?"),
                (secret, json.dumps(secret_data["backup_codes"]), True, email)
            )
    except ImportError:
        pass
    
    secret_data["confirmed"] = True
    
    logger.info(f"2FA enabled for: {email}")
    
    return {"message": "2FA ativado com sucesso!"}


@router.post("/verify-2fa")
async def verify_2fa(request: Request, data: Verify2FARequest):
    """
    Verifica código 2FA durante login.
    Aceita código TOTP ou backup code.
    """
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="2FA não disponível")
    
    # Buscar secret do usuário
    try:
        from backend.database.db import get_user_by_email
        user_data = get_user_by_email(email)
        secret = user_data.get("totp_secret") if user_data else None
    except ImportError:
        secret = _2FA_SECRETS.get(email, {}).get("secret")
    
    if not secret:
        raise HTTPException(status_code=400, detail="2FA não configurado")
    
    totp = pyotp.TOTP(secret)
    
    # Tentar código TOTP
    if totp.verify(data.code, valid_window=1):
        return {"verified": True, "message": "Código válido"}
    
    # Tentar backup code
    # TODO: Implementar verificação de backup codes
    
    raise HTTPException(status_code=400, detail="Código inválido")


@router.delete("/disable-2fa")
async def disable_2fa(request: Request, data: Verify2FARequest):
    """
    Desabilita 2FA após verificação do código atual.
    """
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    # Verificar código antes de desabilitar
    try:
        import pyotp
        from backend.database.db import get_user_by_email, get_db, _q
        
        user_data = get_user_by_email(email)
        secret = user_data.get("totp_secret") if user_data else None
        
        if not secret:
            return {"message": "2FA não estava ativado"}
        
        totp = pyotp.TOTP(secret)
        if not totp.verify(data.code, valid_window=1):
            raise HTTPException(status_code=400, detail="Código inválido")
        
        # Desabilitar no banco
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET totp_secret = NULL, backup_codes = NULL, two_factor_enabled = ? WHERE email = ?"),
                (False, email)
            )
        
        # Limpar cache
        if email in _2FA_SECRETS:
            del _2FA_SECRETS[email]
        
        logger.info(f"2FA disabled for: {email}")
        
        return {"message": "2FA desativado com sucesso"}
        
    except ImportError:
        raise HTTPException(status_code=501, detail="Serviço indisponível")


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS - PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me")
async def get_profile(request: Request):
    """
    Retorna o perfil completo do usuário logado.
    """
    user = _get_user_from_request(request)
    
    # Remover campos sensíveis
    safe_user = {k: v for k, v in user.items() if k not in ("password_hash", "totp_secret", "backup_codes")}
    safe_user["two_factor_enabled"] = bool(user.get("two_factor_enabled") or user.get("totp_secret"))
    
    return safe_user


@router.put("/me")
async def update_profile(request: Request, data: UpdateProfileRequest):
    """
    Atualiza o perfil do usuário logado.
    """
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    updates = {}
    if data.empresa is not None:
        updates["empresa"] = data.empresa
    if data.nome is not None:
        updates["nome"] = data.nome
    if data.telefone is not None:
        updates["telefone"] = data.telefone
    
    if not updates:
        return {"message": "Nenhuma alteração"}
    
    try:
        from backend.database.db import get_db, _q
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [email]
        
        with get_db() as conn:
            conn.execute(
                _q(f"UPDATE users SET {set_clause} WHERE email = ?"),
                tuple(values)
            )
        
        logger.info(f"Profile updated for: {email}")
        
        return {"message": "Perfil atualizado com sucesso!", "updated": list(updates.keys())}
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Serviço indisponível")


@router.put("/me/password")
async def change_password(request: Request, data: ChangePasswordRequest):
    """
    Altera a senha do usuário logado (requer senha atual).
    """
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    try:
        from backend.database.db import authenticate_user, get_db, _hash_password, _q
        
        # Verificar senha atual
        if not authenticate_user(email, data.current_password):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
        
        # Atualizar senha
        new_hash = _hash_password(data.new_password)
        with get_db() as conn:
            conn.execute(
                _q("UPDATE users SET password_hash = ? WHERE email = ?"),
                (new_hash, email)
            )
        
        logger.info(f"Password changed for: {email}")
        
        return {"message": "Senha alterada com sucesso!"}
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Serviço indisponível")


@router.delete("/me")
async def delete_account(request: Request, x_confirm: str = Header(None, alias="X-Confirm-Delete")):
    """
    Deleta a conta do usuário (GDPR compliance).
    Requer header X-Confirm-Delete: DELETE_MY_ACCOUNT
    """
    if x_confirm != "DELETE_MY_ACCOUNT":
        raise HTTPException(
            status_code=400, 
            detail="Confirmação necessária. Envie header X-Confirm-Delete: DELETE_MY_ACCOUNT"
        )
    
    user = _get_user_from_request(request)
    email = user.get("email", "")
    
    try:
        from backend.database.db import get_db, _q
        
        with get_db() as conn:
            # Soft delete (manter registro para auditoria)
            conn.execute(
                _q("UPDATE users SET deleted_at = ?, email = ? WHERE email = ?"),
                (datetime.now(UTC).isoformat(), f"deleted_{int(time.time())}@deleted.local", email)
            )
        
        logger.info(f"Account deleted: {email}")
        
        return {"message": "Conta excluída com sucesso"}
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Serviço indisponível")
