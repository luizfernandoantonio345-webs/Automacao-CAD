from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path
from threading import Lock
from typing import List, Optional
from uuid import uuid4

from integration.python_api.repositories import (
    DraftFeedback,
    DraftFeedbackRepository,
    ProjectEvent,
    ProjectEventRepository,
    ProjectStats,
    ProjectStatsRepository,
    User,
    UserRepository,
)


class JSONUserRepository(UserRepository):
    def __init__(self, users_file: Path):
        self.users_file = users_file
        self._lock = Lock()

    def _load_users(self) -> List[dict]:
        if not self.users_file.exists():
            return []
        with open(self.users_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_users(self, users: List[dict]) -> None:
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.users_file.with_name(f"{self.users_file.stem}.{uuid4().hex}.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        temp_file.replace(self.users_file)

    def get_user_by_email(self, email: str) -> Optional[User]:
        users = self._load_users()
        for user_dict in users:
            if user_dict.get("email") == email:
                return User(
                    id=user_dict.get("id", hash(email) % 2**31),  # Fallback ID for legacy data
                    email=user_dict["email"],
                    hashed_password=user_dict["senha"],
                    company=user_dict.get("empresa", ""),
                    usage_limit=user_dict.get("limite", 100),
                    usage_count=user_dict.get("usado", 0),
                    created_at=datetime.fromisoformat(user_dict.get("created_at", datetime.now(UTC).isoformat())),
                    updated_at=datetime.fromisoformat(user_dict.get("updated_at", datetime.now(UTC).isoformat())),
                )
        return None

    def create_user(self, email: str, hashed_password: str, company: str, usage_limit: int = 100) -> User:
        # ✓ PROBLEMA #20: Validar que a senha JÁ é bcrypt antes de salvar
        import logging
        logger = logging.getLogger("json_repositories")
        
        if not hashed_password or not str(hashed_password).startswith("$2"):
            logger.error(f"Tentativa de criar usuário com senha não-bcrypt: {email[:5]}***")
            raise ValueError(
                "Senha deve estar em hash bcrypt ($2a$ ou $2b$ ou $2y$). "
                "Nunca salve senhas em plaintext!"
            )
        
        with self._lock:
            users = self._load_users()
            user_dict = {
                "id": max((u.get("id", 0) for u in users), default=0) + 1,
                "email": email,
                "senha": hashed_password,
                "empresa": company,
                "limite": usage_limit,
                "usado": 0,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            users.append(user_dict)
            self._save_users(users)
            logger.info(f"Usuário criado com sucesso: {email}")
            return User(
                id=user_dict["id"],
                email=user_dict["email"],
                hashed_password=user_dict["senha"],
                company=user_dict["empresa"],
                usage_limit=user_dict["limite"],
                usage_count=user_dict["usado"],
                created_at=datetime.fromisoformat(user_dict["created_at"]),
                updated_at=datetime.fromisoformat(user_dict["updated_at"]),
            )

    def update_user_usage(self, user_id: int, new_usage: int) -> User:
        with self._lock:
            users = self._load_users()
            for user_dict in users:
                if user_dict.get("id") == user_id:
                    user_dict["usado"] = new_usage
                    user_dict["updated_at"] = datetime.now(UTC).isoformat()
                    self._save_users(users)
                    return User(
                        id=user_dict["id"],
                        email=user_dict["email"],
                        hashed_password=user_dict["senha"],
                        company=user_dict["empresa"],
                        usage_limit=user_dict["limite"],
                        usage_count=user_dict["usado"],
                        created_at=datetime.fromisoformat(user_dict["created_at"]),
                        updated_at=datetime.fromisoformat(user_dict["updated_at"]),
                    )
            raise ValueError(f"User with id {user_id} not found")

    def migrate_plaintext_passwords(self) -> int:
        """✓ PROBLEMA #20: Migrar senhas em plaintext para bcrypt com validação rigorosa."""
        from passlib.context import CryptContext
        import logging
        
        logger = logging.getLogger("json_repositories")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        migrated = 0
        with self._lock:
            users = self._load_users()
            for user_dict in users:
                current_password = user_dict.get("senha", "")
                email = user_dict.get("email", "unknown")
                
                if not current_password:
                    logger.warning(f"Usuário {email} com senha vazia")
                    continue
                
                # Verificar se JÁ é bcrypt (começa com $2)
                if str(current_password).startswith("$2"):
                    logger.debug(f"Usuário {email} JÁ tem senha bcrypt")
                    continue
                
                # Plaintext encontrado - migrar para bcrypt
                logger.warning(f"Migrando senha plaintext para bcrypt: {email}")
                hashed = pwd_context.hash(current_password)
                
                # ✓ PROBLEMA #20: Validar que hash foi criado corretamente
                assert str(hashed).startswith("$2"), f"Falha ao gerar bcrypt para {email}"
                
                user_dict["senha"] = hashed
                migrated += 1
            
            if migrated > 0:
                self._save_users(users)
                logger.info(f"✓ {migrated} senhas migradas para bcrypt")
            else:
                logger.info("✓ Nenhuma migração necessária - todas as senhas já estão bcrypt")
        
        return migrated


class JSONProjectEventRepository(ProjectEventRepository):
    def __init__(self, events_file: Path):
        self.events_file = events_file
        self._lock = Lock()

    def _append_event(self, event_dict: dict) -> None:
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event_dict, ensure_ascii=False) + "\n")

    def record_event(self, event: ProjectEvent) -> None:
        event_dict = {
            "id": event.id,
            "code": event.code,
            "company": event.company,
            "part_name": event.part_name,
            "diameter": event.diameter,
            "length": event.length,
            "source": event.source,
            "result_path": event.result_path,
            "created_at": event.created_at.isoformat(),
        }
        self._append_event(event_dict)

    def get_all_events(self) -> List[ProjectEvent]:
        if not self.events_file.exists():
            return []
        events = []
        with self.events_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                event_dict = json.loads(line)
                events.append(ProjectEvent(
                    id=event_dict.get("id", len(events) + 1),
                    code=event_dict["code"],
                    company=event_dict["company"],
                    part_name=event_dict["part_name"],
                    diameter=event_dict["diameter"],
                    length=event_dict["length"],
                    source=event_dict["source"],
                    result_path=event_dict.get("result_path"),
                    created_at=datetime.fromisoformat(event_dict.get("created_at", datetime.now(UTC).isoformat())),
                ))
        return events

    def get_events_since(self, since: datetime) -> List[ProjectEvent]:
        all_events = self.get_all_events()
        return [event for event in all_events if event.created_at >= since]


class JSONDraftFeedbackRepository(DraftFeedbackRepository):
    def __init__(self, feedback_file: Path):
        self.feedback_file = feedback_file
        self._lock = Lock()

    def _append_feedback(self, feedback_dict: dict) -> None:
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.feedback_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(feedback_dict, ensure_ascii=False) + "\n")

    def record_feedback(self, feedback: DraftFeedback) -> None:
        feedback_dict = {
            "id": feedback.id,
            "prompt": feedback.prompt,
            "feedback": feedback.feedback,
            "company": feedback.company,
            "part_name": feedback.part_name,
            "code": feedback.code,
            "ai_response": feedback.ai_response,
            "tokens_used": feedback.tokens_used,
            "created_at": feedback.created_at.isoformat(),
        }
        self._append_feedback(feedback_dict)

    def get_all_feedback(self) -> List[DraftFeedback]:
        if not self.feedback_file.exists():
            return []
        feedback_list = []
        with self.feedback_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                feedback_dict = json.loads(line)
                feedback_list.append(DraftFeedback(
                    id=feedback_dict.get("id", len(feedback_list) + 1),
                    prompt=feedback_dict["prompt"],
                    feedback=feedback_dict["feedback"],
                    company=feedback_dict["company"],
                    part_name=feedback_dict["part_name"],
                    code=feedback_dict["code"],
                    ai_response=feedback_dict.get("ai_response"),
                    tokens_used=feedback_dict.get("tokens_used"),
                    created_at=datetime.fromisoformat(feedback_dict.get("created_at", datetime.now(UTC).isoformat())),
                ))
        return feedback_list

    def get_feedback_since(self, since: datetime) -> List[DraftFeedback]:
        all_feedback = self.get_all_feedback()
        return [feedback for feedback in all_feedback if feedback.created_at >= since]


class JSONProjectStatsRepository(ProjectStatsRepository):
    def __init__(self, stats_file: Path):
        self.stats_file = stats_file
        self._lock = Lock()

    def _write_stats_atomic(self, stats_dict: dict) -> None:
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.stats_file.with_name(f"{self.stats_file.stem}.{uuid4().hex}.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(stats_dict, f, ensure_ascii=False, indent=2)
        temp_file.replace(self.stats_file)

    def rebuild_stats(self, events: List[ProjectEvent], feedback: List[DraftFeedback]) -> ProjectStats:
        part_names = Counter()
        companies = Counter()
        diameters = []
        lengths = []
        count = 0
        seed_count = 0
        real_count = 0

        for event in events:
            count += 1
            if event.source.startswith("seed."):
                seed_count += 1
            else:
                real_count += 1
            part_names[event.part_name] += 1
            companies[event.company] += 1
            diameters.append(event.diameter)
            lengths.append(event.length)

        accepted_feedback = sum(1 for f in feedback if f.feedback == "accepted")
        rejected_feedback = sum(1 for f in feedback if f.feedback == "rejected")

        stats = ProjectStats(
            total_projects=count,
            seed_projects=seed_count,
            real_projects=real_count,
            top_part_names=part_names.most_common(10),
            top_companies=companies.most_common(10),
            diameter_range=(min(diameters) if diameters else 0, max(diameters) if diameters else 0),
            length_range=(min(lengths) if lengths else 0, max(lengths) if lengths else 0),
            draft_feedback_accepted=accepted_feedback,
            draft_feedback_rejected=rejected_feedback,
        )
        self.save_stats(stats)
        return stats

    def get_stats(self) -> ProjectStats:
        if not self.stats_file.exists():
            return ProjectStats(
                total_projects=0,
                seed_projects=0,
                real_projects=0,
                top_part_names=[],
                top_companies=[],
                diameter_range=(0, 0),
                length_range=(0, 0),
                draft_feedback_accepted=0,
                draft_feedback_rejected=0,
            )
        with open(self.stats_file, "r", encoding="utf-8") as f:
            stats_dict = json.load(f)
        return ProjectStats(
            total_projects=stats_dict.get("total_projects", 0),
            seed_projects=stats_dict.get("seed_projects", 0),
            real_projects=stats_dict.get("real_projects", 0),
            top_part_names=stats_dict.get("top_part_names", []),
            top_companies=stats_dict.get("top_companies", []),
            diameter_range=tuple(stats_dict.get("diameter_range", [0, 0])),
            length_range=tuple(stats_dict.get("length_range", [0, 0])),
            draft_feedback_accepted=stats_dict.get("draft_feedback", {}).get("accepted", 0),
            draft_feedback_rejected=stats_dict.get("draft_feedback", {}).get("rejected", 0),
        )

    def save_stats(self, stats: ProjectStats) -> None:
        stats_dict = {
            "total_projects": stats.total_projects,
            "seed_projects": stats.seed_projects,
            "real_projects": stats.real_projects,
            "top_part_names": stats.top_part_names,
            "top_companies": stats.top_companies,
            "diameter_range": list(stats.diameter_range),
            "length_range": list(stats.length_range),
            "draft_feedback": {
                "accepted": stats.draft_feedback_accepted,
                "rejected": stats.draft_feedback_rejected,
            },
        }
        self._write_stats_atomic(stats_dict)