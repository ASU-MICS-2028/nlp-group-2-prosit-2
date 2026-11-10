"""Tests for step 1 (SQLite storage) and step 2 (accounts, roles, ownership, daily limit)."""

from __future__ import annotations

import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlmodel import Session as DbSession
from sqlmodel import select

from app import auth, make_admin
from app.config import settings
from app.db import TokenRow, UserRow, get_engine, reset_engine
from app.jobs import INTERRUPTED, create_job, get_job, recover_interrupted_jobs, run_job, save_job
from app.models import Understanding

REQUEST = {"requirement": "Keep track of my salon bookings please"}


@pytest.fixture
def fake_understand(monkeypatch: pytest.MonkeyPatch) -> None:
    """No OpenAI calls: every request is 'understood' as a refusal, which needs no blueprint."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        "app.main.understand",
        lambda requirement, background="": Understanding(verdict="disallowed", message="No."),
    )


# =========================================================================== step 1: storage


def test_session_survives_a_restart(client, sign_in, fake_understand) -> None:
    me = sign_in()
    created = client.post("/sessions", json=REQUEST, headers=me).json()

    reset_engine()  # acts like stopping and starting the server: nothing is left in memory

    again = client.get(f"/sessions/{created['id']}", headers=me)
    assert again.status_code == 200
    assert again.json()["requirement"] == REQUEST["requirement"]
    assert again.json()["status"] == "refused"


def test_build_progress_is_saved_at_every_stage(monkeypatch, sign_in) -> None:
    sign_in()
    owner = auth.find_user("ama@example.com")
    job = create_job("todo api", owner_id=owner.id)
    seen_stages: list[str] = []

    def fake_generate(requirement, output_dir, on_stage, analysis):
        for stage in ["analyzing", "generating_code"]:
            on_stage(stage)
            # Read it back from the database, like a polling browser would
            seen_stages.append(get_job(job.id).stage)
        return {"analysis": {"title": "Todo API"}, "files": ["a.py"], "latency_s": 1.5,
                "metrics": {}, "zip_path": "x.zip"}

    monkeypatch.setattr("app.jobs.generate_project", fake_generate)
    run_job(job.id)

    assert seen_stages == ["analyzing", "generating_code"]
    finished = get_job(job.id)
    assert finished.status == "succeeded"
    assert finished.title == "Todo API" and finished.files == ["a.py"]


def test_failed_build_is_saved_with_its_error(monkeypatch, sign_in) -> None:
    sign_in()
    job = create_job("todo api", owner_id=auth.find_user("ama@example.com").id)

    def broken(*args, **kwargs):
        raise RuntimeError("LLM timed out")

    monkeypatch.setattr("app.jobs.generate_project", broken)
    run_job(job.id)

    failed = get_job(job.id)
    assert failed.status == "failed" and failed.error == "LLM timed out"
    assert "traceback" in failed.metrics


def test_builds_cut_off_by_a_restart_are_marked_failed(sign_in) -> None:
    sign_in()
    owner_id = auth.find_user("ama@example.com").id
    running = create_job("a", owner_id=owner_id)
    running.status = "running"
    save_job(running)
    done = create_job("b", owner_id=owner_id)
    done.status = "succeeded"
    save_job(done)

    assert recover_interrupted_jobs() == 1
    assert get_job(running.id).status == "failed"
    assert get_job(running.id).error == INTERRUPTED
    assert get_job(done.id).status == "succeeded"  # finished builds are left alone


def test_unknown_job_is_404(client, sign_in) -> None:
    assert client.get("/jobs/nope", headers=sign_in()).status_code == 404


# =========================================================================== step 2: accounts


def test_register_login_me(client) -> None:
    created = client.post("/auth/register", json={"email": " Ama@Example.COM ", "password": "long-password-1"})
    assert created.status_code == 201
    assert created.json() == {"id": 1, "email": "ama@example.com", "role": "user"}

    logged_in = client.post("/auth/login", json={"email": "ama@example.com", "password": "long-password-1"})
    assert logged_in.status_code == 200
    token = logged_in.json()["token"]
    assert len(token) >= 40

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "ama@example.com"


def test_password_and_token_are_never_stored_as_plain_text(client, sign_in) -> None:
    headers = sign_in(password="my-secret-pass")
    token = headers["Authorization"].removeprefix("Bearer ")
    with DbSession(get_engine()) as db:
        user = db.exec(select(UserRow)).one()
        stored_tokens = [row.token_hash for row in db.exec(select(TokenRow)).all()]
    assert user.password_hash.startswith("scrypt$")
    assert "my-secret-pass" not in user.password_hash
    assert token not in stored_tokens


def test_same_password_gets_a_different_hash_each_time() -> None:
    first, second = auth.hash_password("same-password"), auth.hash_password("same-password")
    assert first != second  # different salts
    assert auth.verify_password("same-password", first) and auth.verify_password("same-password", second)
    assert not auth.verify_password("other-password", first)
    assert not auth.verify_password("x", "not-a-real-hash")


def test_wrong_password_and_unknown_email_get_the_same_answer(client, sign_in) -> None:
    sign_in()
    wrong = client.post("/auth/login", json={"email": "ama@example.com", "password": "wrong-password"})
    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Email or password is wrong."}


def test_sql_looking_input_is_just_a_wrong_login(client, sign_in) -> None:
    sign_in()
    sneaky = client.post("/auth/login", json={"email": "' OR '1'='1", "password": "' OR '1'='1"})
    assert sneaky.status_code == 401


def test_duplicate_email_is_refused_even_with_different_case(client, sign_in) -> None:
    sign_in("ama@example.com")
    again = client.post("/auth/register", json={"email": "AMA@example.com", "password": "long-password-2"})
    assert again.status_code == 409
    assert "already exists" in again.json()["detail"]


def test_two_sign_ups_at_the_same_moment_make_one_account() -> None:
    def try_register(_: int) -> str:
        try:
            auth.register("race@example.com", "long-password-1")
            return "ok"
        except auth.AuthError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(try_register, range(5)))

    assert results.count("ok") == 1
    assert results.count("duplicate") == 4


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"email": "not-an-email", "password": "long-password-1"}, 400),
        ({"email": "ama@example.com", "password": "short"}, 422),
        ({"email": "ama@example.com", "password": "x" * 129}, 422),
        ({"email": "ama@example.com"}, 422),
        ({}, 422),
    ],
)
def test_bad_sign_up_input_is_refused(client, body, code) -> None:
    assert client.post("/auth/register", json=body).status_code == code


def test_no_token_bad_token_and_expired_token_are_all_401(client, sign_in) -> None:
    missing = client.get("/sessions/x")
    assert missing.status_code == 401 and missing.json()["detail"] == "Please log in first."

    forged = client.get("/sessions/x", headers={"Authorization": "Bearer made-up-token"})
    assert forged.status_code == 401

    headers = sign_in()
    with DbSession(get_engine()) as db:
        for row in db.exec(select(TokenRow)).all():
            row.expires_at = "2000-01-01T00:00:00+00:00"
            db.add(row)
        db.commit()
    expired = client.get("/auth/me", headers=headers)
    assert expired.status_code == 401
    assert "log in again" in expired.json()["detail"]


def test_logout_ends_the_token(client, sign_in) -> None:
    headers = sign_in()
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401
    # Logging out twice is harmless (the token is simply not found)
    assert client.post("/auth/logout", headers=headers).status_code == 204


def test_health_needs_no_login(client) -> None:
    assert client.get("/health").status_code == 200


# =========================================================================== step 2: ownership and roles


def _ready_job_for(email: str, tmp_path: Path) -> str:
    """A finished build with a real zip file, owned by `email`."""
    zip_path = tmp_path / "project.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("README.md", "hello")
    job = create_job("todo api", owner_id=auth.find_user(email).id)
    job.status, job.zip_path, job.title = "succeeded", str(zip_path), "Todo API"
    save_job(job)
    return job.id


def test_people_cannot_see_each_others_projects(client, sign_in, fake_understand, tmp_path) -> None:
    ama = sign_in("ama@example.com")
    kofi = sign_in("kofi@example.com")
    session_id = client.post("/sessions", json=REQUEST, headers=ama).json()["id"]
    job_id = _ready_job_for("ama@example.com", tmp_path)

    # Kofi gets the same 404 as for something that does not exist
    assert client.get(f"/sessions/{session_id}", headers=kofi).status_code == 404
    assert client.post(f"/sessions/{session_id}/build", headers=kofi).status_code == 404
    assert client.get(f"/jobs/{job_id}", headers=kofi).status_code == 404
    assert client.get(f"/jobs/{job_id}/download", headers=kofi).status_code == 404

    # Ama, the owner, can
    assert client.get(f"/sessions/{session_id}", headers=ama).status_code == 200
    download = client.get(f"/jobs/{job_id}/download", headers=ama)
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"


def test_admin_can_see_everyones_projects(client, sign_in, fake_understand, tmp_path) -> None:
    ama = sign_in("ama@example.com")
    admin = sign_in("boss@example.com", role="admin")
    session_id = client.post("/sessions", json=REQUEST, headers=ama).json()["id"]
    job_id = _ready_job_for("ama@example.com", tmp_path)

    assert client.get(f"/sessions/{session_id}", headers=admin).status_code == 200
    assert client.get(f"/jobs/{job_id}/download", headers=admin).status_code == 200
    assert client.get("/demand-log", headers=admin).status_code == 200


def test_new_accounts_are_never_admins(client) -> None:
    body = {"email": "sneaky@example.com", "password": "long-password-1", "role": "admin"}
    assert client.post("/auth/register", json=body).json()["role"] == "user"


def test_make_admin_command(sign_in, capsys) -> None:
    sign_in("boss@example.com")
    assert make_admin.main(["boss@example.com"]) == 0
    assert auth.find_user("boss@example.com").role == "admin"
    assert make_admin.main(["boss@example.com", "user"]) == 0
    assert auth.find_user("boss@example.com").role == "user"

    assert make_admin.main(["nobody@example.com"]) == 1
    assert make_admin.main(["boss@example.com", "superuser"]) == 1
    assert make_admin.main([]) == 2
    assert "Usage" in capsys.readouterr().out


# =========================================================================== step 2: daily limit


def test_daily_limit_stops_the_next_request(client, sign_in, fake_understand, monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_request_limit", 2)
    me = sign_in()

    # A request the backend rejects for free does not use up the limit
    assert client.post("/sessions", json={"requirement": "word " * 201}, headers=me).status_code == 400

    assert client.post("/sessions", json=REQUEST, headers=me).status_code == 200
    assert client.post("/sessions", json=REQUEST, headers=me).status_code == 200
    third = client.post("/sessions", json=REQUEST, headers=me)
    assert third.status_code == 429
    assert "today's 2 requests" in third.json()["detail"]

    # Another person has their own limit
    assert client.post("/sessions", json=REQUEST, headers=sign_in("kofi@example.com")).status_code == 200


def test_admins_have_no_daily_limit(client, sign_in, fake_understand, monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    admin = sign_in("boss@example.com", role="admin")
    for _ in range(3):
        assert client.post("/sessions", json=REQUEST, headers=admin).status_code == 200
