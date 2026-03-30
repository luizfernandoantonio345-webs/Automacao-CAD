#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    company = Column(String(120), nullable=False)
    usage_limit = Column(Integer, nullable=False, default=100)
    usage_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectEventModel(Base):
    __tablename__ = "project_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(120), nullable=False, index=True)
    company = Column(String(120), nullable=False, index=True)
    part_name = Column(String(120), nullable=False, index=True)
    diameter = Column(Float, nullable=False)
    length = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    result_path = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class DraftFeedbackModel(Base):
    __tablename__ = "draft_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=False)
    feedback = Column(String(20), nullable=False, index=True)
    company = Column(String(120), nullable=False)
    part_name = Column(String(120), nullable=False)
    code = Column(String(120), nullable=False)
    ai_response = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class ProjectStatsModel(Base):
    __tablename__ = "project_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    total_projects = Column(Integer, nullable=False)
    seed_projects = Column(Integer, nullable=False)
    real_projects = Column(Integer, nullable=False)
    top_part_names = Column(Text, nullable=False)
    top_companies = Column(Text, nullable=False)
    diameter_min = Column(Float, nullable=False)
    diameter_max = Column(Float, nullable=False)
    length_min = Column(Float, nullable=False)
    length_max = Column(Float, nullable=False)
    draft_feedback_accepted = Column(Integer, nullable=False)
    draft_feedback_rejected = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

if __name__ == "__main__":
    engine = create_engine("sqlite:///data/engenharia_automacao.db", echo=True)
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")