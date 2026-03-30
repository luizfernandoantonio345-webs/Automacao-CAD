from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

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


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    usage_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectEventModel(Base):
    __tablename__ = "project_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    part_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    diameter: Mapped[float] = mapped_column(Float, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    result_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class DraftFeedbackModel(Base):
    __tablename__ = "draft_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    part_name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class MaterialModel(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    density: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cad_hatch: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ProjectHistoryModel(Base):
    __tablename__ = "project_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_weight: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    selected_profile: Mapped[str] = mapped_column(String(80), nullable=False)
    material_name: Mapped[str] = mapped_column(String(50), nullable=False)
    report_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cad_payload_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProjectStatsModel(Base):
    __tablename__ = "project_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    real_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    top_part_names: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized
    top_companies: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized
    diameter_min: Mapped[float] = mapped_column(Float, nullable=False)
    diameter_max: Mapped[float] = mapped_column(Float, nullable=False)
    length_min: Mapped[float] = mapped_column(Float, nullable=False)
    length_max: Mapped[float] = mapped_column(Float, nullable=False)
    draft_feedback_accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_feedback_rejected: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostgreSQLUserRepository(UserRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self.session_factory() as session:
            user_model = session.query(UserModel).filter(UserModel.email == email).first()
            if not user_model:
                return None
            return User(
                id=user_model.id,
                email=user_model.email,
                hashed_password=user_model.hashed_password,
                company=user_model.company,
                usage_limit=user_model.usage_limit,
                usage_count=user_model.usage_count,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )

    def create_user(self, email: str, hashed_password: str, company: str, usage_limit: int = 100) -> User:
        with self.session_factory() as session:
            user_model = UserModel(
                email=email,
                hashed_password=hashed_password,
                company=company,
                usage_limit=usage_limit,
                usage_count=0,
            )
            session.add(user_model)
            session.commit()
            session.refresh(user_model)
            return User(
                id=user_model.id,
                email=user_model.email,
                hashed_password=user_model.hashed_password,
                company=user_model.company,
                usage_limit=user_model.usage_limit,
                usage_count=user_model.usage_count,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )

    def update_user_usage(self, user_id: int, new_usage: int) -> User:
        with self.session_factory() as session:
            user_model = session.query(UserModel).filter(UserModel.id == user_id).first()
            if not user_model:
                raise ValueError(f"User with id {user_id} not found")
            user_model.usage_count = new_usage
            session.commit()
            session.refresh(user_model)
            return User(
                id=user_model.id,
                email=user_model.email,
                hashed_password=user_model.hashed_password,
                company=user_model.company,
                usage_limit=user_model.usage_limit,
                usage_count=user_model.usage_count,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )

    def migrate_plaintext_passwords(self) -> int:
        # PostgreSQL implementation doesn't need migration as passwords are always hashed
        return 0


class PostgreSQLProjectEventRepository(ProjectEventRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def record_event(self, event: ProjectEvent) -> None:
        with self.session_factory() as session:
            event_model = ProjectEventModel(
                code=event.code,
                company=event.company,
                part_name=event.part_name,
                diameter=event.diameter,
                length=event.length,
                source=event.source,
                result_path=event.result_path,
            )
            session.add(event_model)
            session.commit()

    def get_all_events(self) -> List[ProjectEvent]:
        with self.session_factory() as session:
            event_models = session.query(ProjectEventModel).order_by(ProjectEventModel.created_at).all()
            return [
                ProjectEvent(
                    id=event_model.id,
                    code=event_model.code,
                    company=event_model.company,
                    part_name=event_model.part_name,
                    diameter=event_model.diameter,
                    length=event_model.length,
                    source=event_model.source,
                    result_path=event_model.result_path,
                    created_at=event_model.created_at,
                )
                for event_model in event_models
            ]

    def get_events_since(self, since: datetime) -> List[ProjectEvent]:
        with self.session_factory() as session:
            event_models = session.query(ProjectEventModel).filter(ProjectEventModel.created_at >= since).order_by(ProjectEventModel.created_at).all()
            return [
                ProjectEvent(
                    id=event_model.id,
                    code=event_model.code,
                    company=event_model.company,
                    part_name=event_model.part_name,
                    diameter=event_model.diameter,
                    length=event_model.length,
                    source=event_model.source,
                    result_path=event_model.result_path,
                    created_at=event_model.created_at,
                )
                for event_model in event_models
            ]


class PostgreSQLDraftFeedbackRepository(DraftFeedbackRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def record_feedback(self, feedback: DraftFeedback) -> None:
        with self.session_factory() as session:
            feedback_model = DraftFeedbackModel(
                prompt=feedback.prompt,
                feedback=feedback.feedback,
                company=feedback.company,
                part_name=feedback.part_name,
                code=feedback.code,
                ai_response=feedback.ai_response,
                tokens_used=feedback.tokens_used,
            )
            session.add(feedback_model)
            session.commit()

    def get_all_feedback(self) -> List[DraftFeedback]:
        with self.session_factory() as session:
            feedback_models = session.query(DraftFeedbackModel).order_by(DraftFeedbackModel.created_at).all()
            return [
                DraftFeedback(
                    id=feedback_model.id,
                    prompt=feedback_model.prompt,
                    feedback=feedback_model.feedback,
                    company=feedback_model.company,
                    part_name=feedback_model.part_name,
                    code=feedback_model.code,
                    ai_response=feedback_model.ai_response,
                    tokens_used=feedback_model.tokens_used,
                    created_at=feedback_model.created_at,
                )
                for feedback_model in feedback_models
            ]

    def get_feedback_since(self, since: datetime) -> List[DraftFeedback]:
        with self.session_factory() as session:
            feedback_models = session.query(DraftFeedbackModel).filter(DraftFeedbackModel.created_at >= since).order_by(DraftFeedbackModel.created_at).all()
            return [
                DraftFeedback(
                    id=feedback_model.id,
                    prompt=feedback_model.prompt,
                    feedback=feedback_model.feedback,
                    company=feedback_model.company,
                    part_name=feedback_model.part_name,
                    code=feedback_model.code,
                    ai_response=feedback_model.ai_response,
                    tokens_used=feedback_model.tokens_used,
                    created_at=feedback_model.created_at,
                )
                for feedback_model in feedback_models
            ]


class PostgreSQLProjectStatsRepository(ProjectStatsRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def rebuild_stats(self, events: List[ProjectEvent], feedback: List[DraftFeedback]) -> ProjectStats:
        import json
        from collections import Counter

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
        import json
        with self.session_factory() as session:
            stats_model = session.query(ProjectStatsModel).order_by(ProjectStatsModel.created_at.desc()).first()
            if not stats_model:
                # Return empty stats if none exist
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
            return ProjectStats(
                total_projects=stats_model.total_projects,
                seed_projects=stats_model.seed_projects,
                real_projects=stats_model.real_projects,
                top_part_names=json.loads(stats_model.top_part_names),
                top_companies=json.loads(stats_model.top_companies),
                diameter_range=(stats_model.diameter_min, stats_model.diameter_max),
                length_range=(stats_model.length_min, stats_model.length_max),
                draft_feedback_accepted=stats_model.draft_feedback_accepted,
                draft_feedback_rejected=stats_model.draft_feedback_rejected,
            )

    def save_stats(self, stats: ProjectStats) -> None:
        import json
        with self.session_factory() as session:
            stats_model = ProjectStatsModel(
                total_projects=stats.total_projects,
                seed_projects=stats.seed_projects,
                real_projects=stats.real_projects,
                top_part_names=json.dumps(stats.top_part_names),
                top_companies=json.dumps(stats.top_companies),
                diameter_min=stats.diameter_range[0],
                diameter_max=stats.diameter_range[1],
                length_min=stats.length_range[0],
                length_max=stats.length_range[1],
                draft_feedback_accepted=stats.draft_feedback_accepted,
                draft_feedback_rejected=stats.draft_feedback_rejected,
            )
            session.add(stats_model)
            session.commit()


def create_database_engine(database_url: str):
    return create_engine(database_url, echo=False, pool_pre_ping=True)


def create_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine):
    Base.metadata.create_all(engine)
    _ensure_schema_compatibility(engine)


def _ensure_schema_compatibility(engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "draft_feedback" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("draft_feedback")}
    missing_columns = {
        "ai_response": "TEXT",
        "tokens_used": "INTEGER",
        "ai_model_version": "VARCHAR(50) DEFAULT 'unknown'",
    }

    with engine.begin() as connection:
        for column_name, ddl in missing_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE draft_feedback ADD COLUMN {column_name} {ddl}"))