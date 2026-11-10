"""Intake sessions: request -> understand -> (questions) -> confirmation card -> build.

Step 1: sessions are saved in SQLite (app/db.py), so a restart no longer loses them.
Changing a Session object does NOT save it: call save_session() afterwards.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import literal_column
from sqlmodel import Session as DbSession
from sqlmodel import select

from app import demand
from app.db import SessionRow, get_engine
from app.models import Analysis, NotIncludedItem, SessionPublic, Understanding

# Turns a list of NotIncludedItem into JSON text and back
_items = TypeAdapter(list[NotIncludedItem])


@dataclass
class Session:
    id: str
    owner_id: int
    requirement: str
    understanding: Understanding
    answers: dict[str, Any] = field(default_factory=dict)
    job_id: str | None = None
    logged: list[NotIncludedItem] = field(default_factory=list)
    # Step 4: the design we suggested before the person's first edit (None until they edit)
    suggested: Analysis | None = None

    @property
    def status(self) -> str:
        u = self.understanding
        if u.verdict == "disallowed":
            return "refused"
        if u.questions:
            return "needs_answers"
        if u.blueprint is None:
            return "unsupported"
        return "ready"

    def set_understanding(self, understanding: Understanding) -> None:
        self.understanding = understanding
        new = [item for item in understanding.not_included if item not in self.logged]
        demand.record(new, self.id)
        self.logged.extend(new)

    def public(self) -> SessionPublic:
        return SessionPublic(
            id=self.id,
            requirement=self.requirement,
            status=self.status,
            understanding=self.understanding,
            answers=self.answers,
            job_id=self.job_id,
        )


def _to_row(session: Session) -> SessionRow:
    return SessionRow(
        id=session.id,
        owner_id=session.owner_id,
        requirement=session.requirement,
        understanding_json=session.understanding.model_dump_json(),
        answers_json=json.dumps(session.answers),
        job_id=session.job_id,
        logged_json=_items.dump_json(session.logged).decode(),
        suggested_json=session.suggested.model_dump_json() if session.suggested else None,
    )


def _from_row(row: SessionRow) -> Session:
    return Session(
        id=row.id,
        owner_id=row.owner_id,
        requirement=row.requirement,
        understanding=Understanding.model_validate_json(row.understanding_json),
        answers=json.loads(row.answers_json),
        job_id=row.job_id,
        logged=_items.validate_json(row.logged_json),
        suggested=Analysis.model_validate_json(row.suggested_json) if row.suggested_json else None,
    )


def save_session(session: Session) -> None:
    with DbSession(get_engine()) as db:
        existing = db.get(SessionRow, session.id)
        row = _to_row(session)
        if existing:
            # Keep the original created_at; replace everything else
            row.created_at = existing.created_at
            db.merge(row)
        else:
            db.add(row)
        db.commit()


def create_session(requirement: str, understanding: Understanding, owner_id: int) -> Session:
    session = Session(
        id=uuid.uuid4().hex[:12],
        owner_id=owner_id,
        requirement=requirement,
        understanding=understanding,
    )
    session.set_understanding(understanding)
    save_session(session)
    return session


def get_session(session_id: str) -> Session | None:
    with DbSession(get_engine()) as db:
        row = db.get(SessionRow, session_id)
        return _from_row(row) if row else None


def list_sessions(owner_id: int, limit: int = 50) -> list[Session]:
    """This person's sessions, newest first (for the sidebar's project list)."""
    with DbSession(get_engine()) as db:
        query = (
            select(SessionRow)
            .where(SessionRow.owner_id == owner_id)
            # rowid = the order rows were added; it breaks ties between sessions made in the same second
            .order_by(SessionRow.created_at.desc(), literal_column("rowid").desc())
            .limit(limit)
        )
        rows = db.exec(query).all()
        # created_at is kept separately: the Session class has no field for it
        return [_from_row(row) for row in rows]


def created_at(session_id: str) -> str | None:
    with DbSession(get_engine()) as db:
        row = db.get(SessionRow, session_id)
        return row.created_at if row else None
