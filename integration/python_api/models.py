from __future__ import annotations

# LEGACY FILE — not imported anywhere in the codebase.
# All ORM models have been migrated to postgres_repositories.py,
# which uses the modern SQLAlchemy 2.x DeclarativeBase style.
# This file is kept for historical reference only.

from sqlalchemy import Column, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)
    empresa = Column(String(120), nullable=False)
    limite = Column(Integer, nullable=False, default=100)
    usado = Column(Integer, nullable=False, default=0)


class ProjectEvent(Base):
    __tablename__ = "project_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(120), nullable=False, index=True)
    company = Column(String(120), nullable=False, index=True)
    part_name = Column(String(120), nullable=False, index=True)
    diameter = Column(Float, nullable=False)
    length = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    result_path = Column(Text, nullable=True)


class DraftFeedback(Base):
    __tablename__ = "draft_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=False)
    feedback = Column(String(20), nullable=False)
    company = Column(String(120), nullable=False, index=True)
    part_name = Column(String(120), nullable=False, index=True)
    code = Column(String(120), nullable=False)
    ai_response = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    ai_model_version = Column(String(50), nullable=True, default="unknown")  # ✓ PROBLEMA #14: Rastrear versão


def create_engine_and_session(database_url: str):
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def init_db(engine):
    Base.metadata.create_all(bind=engine)