"""Shared test setup. pytest loads this file automatically before the tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth, llm
from app.config import settings
from app.db import reset_engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Every test gets its own empty SQLite file, so tests never see each other's data."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setattr(settings, "demand_log_path", str(tmp_path / "demand.jsonl"))
    reset_engine()
    yield db_file
    reset_engine()


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never reach OpenAI (it costs money and needs the network). Any call that a test did
    not fake on purpose fails here, which the code under test must handle like "the LLM is down"."""

    def refuse(*args, **kwargs):
        raise RuntimeError("Real LLM calls are blocked in tests")

    monkeypatch.setattr(llm, "_complete", refuse)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


Headers = dict[str, str]


@pytest.fixture
def sign_in(client: TestClient) -> Callable[..., Headers]:
    """sign_in("ama@example.com") signs up, logs in and returns the Authorization header.
    sign_in("boss@example.com", role="admin") also makes that account an admin."""

    def make(email: str = "ama@example.com", password: str = "long-password-1", role: str = "user") -> Headers:
        assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
        if role != "user":
            auth.set_role(email, role)
        token = client.post("/auth/login", json={"email": email, "password": password}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return make
