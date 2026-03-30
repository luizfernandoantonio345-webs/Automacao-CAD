from __future__ import annotations

from integration.python_api.config import AppConfig
from integration.python_api.json_repositories import (
    JSONDraftFeedbackRepository,
    JSONProjectEventRepository,
    JSONProjectStatsRepository,
    JSONUserRepository,
)
from integration.python_api.postgres_repositories import (
    PostgreSQLDraftFeedbackRepository,
    PostgreSQLProjectEventRepository,
    PostgreSQLProjectStatsRepository,
    PostgreSQLUserRepository,
    create_database_engine,
    create_session_factory,
    init_database,
)
from integration.python_api.repositories import (
    DraftFeedbackRepository,
    ProjectEventRepository,
    ProjectStatsRepository,
    UserRepository,
)


def create_repositories(config: AppConfig) -> tuple[
    UserRepository,
    ProjectEventRepository,
    DraftFeedbackRepository,
    ProjectStatsRepository,
]:
    if config.database_url:
        # Use PostgreSQL repositories
        engine = create_database_engine(config.database_url)
        init_database(engine)
        session_factory = create_session_factory(engine)

        user_repo = PostgreSQLUserRepository(session_factory)
        event_repo = PostgreSQLProjectEventRepository(session_factory)
        feedback_repo = PostgreSQLDraftFeedbackRepository(session_factory)
        stats_repo = PostgreSQLProjectStatsRepository(session_factory)
    else:
        # Use JSON repositories as fallback
        telemetry_dir = config.data_dir / "telemetry"
        users_file = config.data_dir / "users.json"
        events_file = telemetry_dir / "project_events.jsonl"
        feedback_file = telemetry_dir / "draft_feedback.jsonl"
        stats_file = telemetry_dir / "project_stats.json"

        user_repo = JSONUserRepository(users_file)
        event_repo = JSONProjectEventRepository(events_file)
        feedback_repo = JSONDraftFeedbackRepository(feedback_file)
        stats_repo = JSONProjectStatsRepository(stats_file)

    return user_repo, event_repo, feedback_repo, stats_repo