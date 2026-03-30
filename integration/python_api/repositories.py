from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    email: str
    hashed_password: str
    company: str
    usage_limit: int
    usage_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ProjectEvent:
    id: int
    code: str
    company: str
    part_name: str
    diameter: float
    length: float
    source: str
    result_path: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class DraftFeedback:
    id: int
    prompt: str
    feedback: str
    company: str
    part_name: str
    code: str
    ai_response: str | None
    tokens_used: int | None
    created_at: datetime


@dataclass(frozen=True)
class ProjectStats:
    total_projects: int
    seed_projects: int
    real_projects: int
    top_part_names: List[tuple[str, int]]
    top_companies: List[tuple[str, int]]
    diameter_range: tuple[float, float]
    length_range: tuple[float, float]
    draft_feedback_accepted: int
    draft_feedback_rejected: int


class UserRepository(ABC):
    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def create_user(self, email: str, hashed_password: str, company: str, usage_limit: int = 100) -> User:
        pass

    @abstractmethod
    def update_user_usage(self, user_id: int, new_usage: int) -> User:
        pass

    @abstractmethod
    def migrate_plaintext_passwords(self) -> int:
        pass


class ProjectEventRepository(ABC):
    @abstractmethod
    def record_event(self, event: ProjectEvent) -> None:
        pass

    @abstractmethod
    def get_all_events(self) -> List[ProjectEvent]:
        pass

    @abstractmethod
    def get_events_since(self, since: datetime) -> List[ProjectEvent]:
        pass


class DraftFeedbackRepository(ABC):
    @abstractmethod
    def record_feedback(self, feedback: DraftFeedback) -> None:
        pass

    @abstractmethod
    def get_all_feedback(self) -> List[DraftFeedback]:
        pass

    @abstractmethod
    def get_feedback_since(self, since: datetime) -> List[DraftFeedback]:
        pass


class ProjectStatsRepository(ABC):
    @abstractmethod
    def rebuild_stats(self, events: List[ProjectEvent], feedback: List[DraftFeedback]) -> ProjectStats:
        pass

    @abstractmethod
    def get_stats(self) -> ProjectStats:
        pass

    @abstractmethod
    def save_stats(self, stats: ProjectStats) -> None:
        pass