"""SQLite storage (step 1). Every table the builder needs, and one way to open the database.

Why SQLite: it is a single file, needs no server, is free, and ships with Python.
Why JSON columns: the understanding, answers and metrics are nested Pydantic data. We only ever
load them whole, so storing them as JSON text keeps this file short and easy to explain.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine

from app.config import settings


def now_iso() -> str:
    """UTC time as text, always in the same format, so comparing two of them as text is correct."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class UserRow(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    # unique=True makes the database itself refuse a second account with the same email
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = "user"  # "user" or "admin"
    created_at: str = Field(default_factory=now_iso)


class TokenRow(SQLModel, table=True):
    __tablename__ = "tokens"
    # We store a SHA-256 hash of the token, never the token itself
    token_hash: str = Field(primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    expires_at: str


class SessionRow(SQLModel, table=True):
    __tablename__ = "sessions"
    id: str = Field(primary_key=True)
    owner_id: int = Field(index=True, foreign_key="users.id")
    requirement: str
    understanding_json: str
    answers_json: str = "{}"
    job_id: str | None = None
    logged_json: str = "[]"  # "Not included yet" items already written to the demand log
    # Step 4: the design we suggested, saved before the person's first edit, so we can see what they changed
    suggested_json: str | None = None
    created_at: str = Field(default_factory=now_iso)


class JobRow(SQLModel, table=True):
    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    owner_id: int = Field(index=True, foreign_key="users.id")
    requirement: str
    analysis_json: str | None = None
    status: str = "queued"
    stage: str = "queued"
    error: str | None = None
    title: str | None = None
    files_json: str = "[]"
    latency_s: float | None = None
    metrics_json: str = "{}"
    zip_path: str | None = None
    # The build timeline: Thinking / Doing / Result steps, and the generated project's test results.
    # Nullable so older database files can get these columns added (see _add_missing_columns).
    steps_json: str | None = None
    tests_json: str | None = None
    created_at: str = Field(default_factory=now_iso)


class UsageRow(SQLModel, table=True):
    """One row per request that spends money on the LLM, for the daily limit."""

    __tablename__ = "usage"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    kind: str  # "session" or "generate"
    created_at: str = Field(default_factory=now_iso, index=True)


class MemoryRow(SQLModel, table=True):
    """Step 4: one lasting fact about a person, e.g. "Prices are in Ghana cedis (GHS)"."""

    __tablename__ = "memories"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    fact: str
    source_session_id: str | None = None
    created_at: str = Field(default_factory=now_iso)


class ExampleRow(SQLModel, table=True):
    """Step 5: a design the person approved, kept to help with their similar requests later.
    We store the design and a neutral summary, never the person's own request text."""

    __tablename__ = "examples"
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(index=True, foreign_key="users.id")
    title: str
    text: str  # what retrieval matches against: title, description and detail names
    blueprint_json: str
    created_at: str = Field(default_factory=now_iso)


def _add_missing_columns(engine: Engine) -> None:
    """create_all makes new tables but never changes existing ones. When a column is added to a
    class above (like sessions.suggested_json), add it to an older database file too.
    Only nullable columns are ever added this way, so old rows stay valid (their value is empty)."""
    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            # Table and column names come from our own classes, never from users, so building SQL text is safe
            existing = {row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{table.name}")')}
            for column in table.columns:
                if column.name not in existing:
                    column_type = column.type.compile(engine.dialect)
                    connection.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}')


_engine: Engine | None = None
# Only one thread may set up the database. Without this, two requests arriving together after a
# restart could both start setting up, and one could write before the tables exist (a test caught this).
_engine_lock = threading.Lock()


def get_engine() -> Engine:
    """Opens the database the first time it is needed and creates any missing tables."""
    global _engine
    with _engine_lock:
        if _engine is None:
            url = settings.database_url
            if url.startswith("sqlite:///"):
                # Make sure the folder for the database file exists
                Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
            # check_same_thread=False: builds run in a background thread and also use the database
            engine = create_engine(url, connect_args={"check_same_thread": False})
            SQLModel.metadata.create_all(engine)
            _add_missing_columns(engine)
            # Share the engine only once its tables exist
            _engine = engine
        return _engine


def reset_engine() -> None:
    """Closes the database. Tests use this to point at a fresh file, or to act like a restart."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
