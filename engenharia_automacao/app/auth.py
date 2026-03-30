from __future__ import annotations

import hmac
import json
from pathlib import Path
from threading import Lock
from os import PathLike
from uuid import uuid4

try:
    from passlib.context import CryptContext
except ImportError:
    raise RuntimeError(
        "passlib[bcrypt] nao esta instalado. Instale a dependencia no ambiente antes de iniciar a API."
    )

# Configure bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_FILE = Path(__file__).resolve().parents[1] / "data" / "users.json"
_USERS_LOCK = Lock()


class AuthenticationError(Exception):
    pass


class LicenseError(Exception):
    pass


class UserRegistrationError(Exception):
    pass


class AuthService:
    """Servico simples de autenticacao e controle de licenca."""

    def __init__(self, user_repository=None) -> None:
        # Backward compatibility: callers may still pass a JSON path instead of a repository.
        if isinstance(user_repository, (str, PathLike, Path)):
            self.user_repository = None
            self.users_file = Path(user_repository)
        elif user_repository is None:
            self.user_repository = None
            self.users_file = USERS_FILE
        else:
            self.user_repository = user_repository
            self.users_file = None

    def _load_users(self) -> list[dict]:
        if self.user_repository is not None:
            # If using repository, this method should not be called
            raise RuntimeError("Using repository but called legacy _load_users")
        if not self.users_file.exists():
            raise FileNotFoundError(f"Arquivo de usuarios nao encontrado: {self.users_file}")
        with open(self.users_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_users(self, users: list[dict]) -> None:
        if self.user_repository is not None:
            raise RuntimeError("Using repository but called legacy _save_users")
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.users_file.with_name(f"{self.users_file.stem}.{uuid4().hex}.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        temp_file.replace(self.users_file)

    def _is_password_hashed(self, senha: str) -> bool:
        return str(senha or "").startswith("$2")

    def _hash_password(self, senha: str) -> str:
        return pwd_context.hash(str(senha or ""))

    def authenticate(self, email: str, senha: str) -> dict:
        normalized_email = str(email or "").strip().lower()
        normalized_password = str(senha or "")
        
        if not normalized_email or not normalized_password:
            raise AuthenticationError("Credenciais invalidas")
        
        if self.user_repository is not None:
            user = self.user_repository.get_user_by_email(normalized_email)
            if not user:
                raise AuthenticationError("Credenciais invalidas")
            if self._is_password_hashed(user.hashed_password):
                if pwd_context.verify(normalized_password, user.hashed_password):
                    return {
                        "id": user.id,
                        "email": user.email,
                        "empresa": user.company,
                        "limite": user.usage_limit,
                        "usado": user.usage_count,
                    }
            else:
                # Auto-upgrade legacy passwords
                if hmac.compare_digest(user.hashed_password, normalized_password):
                    self.user_repository.update_user_usage(user.id, user.usage_count)  # Trigger update to hash password
                    return {
                        "id": user.id,
                        "email": user.email,
                        "empresa": user.company,
                        "limite": user.usage_limit,
                        "usado": user.usage_count,
                    }
            raise AuthenticationError("Credenciais invalidas")
        else:
            # Legacy JSON-based authentication
            users = self._load_users()
            for user in users:
                user_email = str(user.get("email", "")).strip().lower()
                user_password = str(user.get("senha", ""))
                if hmac.compare_digest(user_email, normalized_email):
                    # Auto-upgrade senhas legadas em texto puro no primeiro login valido.
                    if self._is_password_hashed(user_password):
                        if pwd_context.verify(normalized_password, user_password):
                            return user
                    else:
                        if hmac.compare_digest(user_password, normalized_password):
                            self._upgrade_password_hash(normalized_email, normalized_password)
                            return user
            raise AuthenticationError("Credenciais invalidas")

    def verificar_limite(self, usuario: dict) -> bool:
        return usuario.get("usado", 0) < usuario.get("limite", 0)

    def find_user_by_email(self, email: str) -> dict | None:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            return None
        
        if self.user_repository is not None:
            user = self.user_repository.get_user_by_email(normalized_email)
            if not user:
                return None
            return {
                "id": user.id,
                "email": user.email,
                "empresa": user.company,
                "limite": user.usage_limit,
                "usado": user.usage_count,
            }
        else:
            # Legacy implementation
            users = self._load_users()
            for user in users:
                user_email = str(user.get("email", "")).strip().lower()
                if hmac.compare_digest(user_email, normalized_email):
                    return user
            return None

    def incrementar_uso(self, usuario: dict, quantidade: int = 1) -> dict:
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")
        if not self.verificar_limite(usuario):
            raise LicenseError("Limite de uso atingido.")
        if str(usuario.get("email", "")).strip().lower() == "public@system.com":
            usuario["usado"] = int(usuario.get("usado", 0)) + quantidade
            return usuario

        if self.user_repository is not None:
            user_id = usuario.get("id")
            if not user_id:
                raise AuthenticationError("Usuario nao encontrado para atualizar uso")
            new_usage = int(usuario.get("usado", 0)) + quantidade
            if new_usage > int(usuario.get("limite", 0)):
                raise LicenseError("Limite de uso atingido.")
            updated_user = self.user_repository.update_user_usage(user_id, new_usage)
            return {
                "id": updated_user.id,
                "email": updated_user.email,
                "empresa": updated_user.company,
                "limite": updated_user.usage_limit,
                "usado": updated_user.usage_count,
            }
        else:
            # Legacy implementation
            with _USERS_LOCK:
                users = self._load_users()
                for record in users:
                    if record.get("email") == usuario.get("email"):
                        novo_uso = int(record.get("usado", 0)) + quantidade
                        if novo_uso > int(record.get("limite", 0)):
                            raise LicenseError("Limite de uso atingido.")
                        record["usado"] = novo_uso
                        usuario["usado"] = record["usado"]
                        self._save_users(users)
                        return usuario

        raise AuthenticationError("Usuario nao encontrado para atualizar uso")

    def _upgrade_password_hash(self, email: str, senha: str) -> None:
        if self.user_repository is not None:
            # Repository handles password hashing automatically
            return
        with _USERS_LOCK:
            users = self._load_users()
            for record in users:
                record_email = str(record.get("email", "")).strip().lower()
                if hmac.compare_digest(record_email, email):
                    if not self._is_password_hashed(record.get("senha", "")):
                        record["senha"] = self._hash_password(senha)
                        self._save_users(users)
                    return

    def migrate_plaintext_passwords(self) -> int:
        if self.user_repository is not None:
            return self.user_repository.migrate_plaintext_passwords()
        else:
            migrated = 0
            with _USERS_LOCK:
                users = self._load_users()
                for record in users:
                    current_password = str(record.get("senha", ""))
                    if current_password and not self._is_password_hashed(current_password):
                        record["senha"] = self._hash_password(current_password)
                        migrated += 1
                if migrated:
                    self._save_users(users)
            return migrated

    def register_user(self, email: str, senha: str, empresa: str | None = None) -> dict:
        normalized_email = str(email or "").strip().lower()
        normalized_password = str(senha or "").strip()
        normalized_company = str(empresa or "").strip()

        if "@" not in normalized_email or normalized_email.startswith("@") or normalized_email.endswith("@"):
            raise UserRegistrationError("Email invalido")
        if len(normalized_email) > 120:
            raise UserRegistrationError("Email invalido")
        if len(normalized_password) < 8 or len(normalized_password) > 120:
            raise UserRegistrationError("Senha deve ter entre 8 e 120 caracteres")

        company_name = normalized_company or normalized_email.split("@", 1)[0]
        company_name = company_name[:120] or "Empresa"

        if self.user_repository is not None:
            user = self.user_repository.create_user(
                email=normalized_email,
                hashed_password=self._hash_password(normalized_password),
                company=company_name,
                usage_limit=100
            )
            return {
                "id": user.id,
                "email": user.email,
                "empresa": user.company,
                "limite": user.usage_limit,
                "usado": user.usage_count,
            }
        else:
            # Legacy implementation
            with _USERS_LOCK:
                users = self._load_users()
                for user in users:
                    user_email = str(user.get("email", "")).strip().lower()
                    if hmac.compare_digest(user_email, normalized_email):
                        raise UserRegistrationError("Usuario ja cadastrado")

                user = {
                    "email": normalized_email,
                    "senha": self._hash_password(normalized_password),
                    "empresa": company_name,
                    "limite": 100,
                    "usado": 0,
                }
                users.append(user)
                self._save_users(users)
                return user
