"""Step 4 (memory) and step 5 (RAG). No real LLM: every model reply here is faked."""

from __future__ import annotations

import json
import sqlite3

import pytest

from app import memory, rag_check, retrieval
from app.config import settings
from app.db import get_engine, reset_engine
from app.learning import after_approval, before_understanding
from app.models import Analysis, FieldSpec, Understanding
from app.validators import blueprint_problems


def _design(*names: str, title: str = "Salon Bookings API") -> Analysis:
    return Analysis(
        title=title, description="Bookings.", resource_name="booking", resource_plural="bookings",
        fields=[FieldSpec(name=n, type="str", required=True) for n in names],
    )


def _user_id(email: str = "ama@example.com") -> int:
    from app.auth import find_user

    return find_user(email).id


# =========================================================================== step 4: memory


def test_describe_changes_lists_every_kind_of_edit() -> None:
    before = _design("customer_name", "service", "notes")
    edited = before.resources[0].model_copy(update={"fields": [
        FieldSpec(name="customer_name", type="str", required=False),
        FieldSpec(name="service", type="int", required=True),
        FieldSpec(name="phone_number", type="str", required=True),
    ]})
    after = before.model_copy(update={"title": "Hair Bookings API", "resources": [edited]})
    assert memory.describe_changes(before, after) == [
        "Added detail 'phone_number' (str)",
        "Changed 'service' from str to int",
        "Made 'customer_name' optional",
        "Removed detail 'notes'",
        "Renamed the API from 'Salon Bookings API' to 'Hair Bookings API'",
    ]
    assert memory.describe_changes(None, after) == []


@pytest.mark.parametrize("fact", [
    "Email them at ama@example.com",
    "Call 024 123 4567 for orders",
    "Website is https://shop.example",
    "Their password is hunter2",
    "x" * 151,
    "",
])
def test_unsafe_facts_are_dropped(fact: str) -> None:
    assert not memory.is_safe_fact(fact)


def test_clean_facts_keeps_three_new_safe_facts() -> None:
    raw = ["Runs a hair salon.", "runs a hair salon", "Uses GHS for prices", "Email ama@example.com",
           "Wants phone numbers on customers", "Works on Saturdays"]
    assert memory.clean_facts(raw, existing=["Uses GHS for prices"]) == [
        "Runs a hair salon", "Wants phone numbers on customers", "Works on Saturdays",
    ]
    assert memory.clean_facts("not a list", existing=[]) == []


def test_extract_facts_sends_the_edits_to_the_small_model(monkeypatch) -> None:
    calls = []

    def fake_chat(messages, json_mode=False, use_fallback_first=False):
        calls.append((messages, json_mode, use_fallback_first))
        return json.dumps({"facts": ["Wants a phone number on bookings"]})

    monkeypatch.setattr(memory, "chat", fake_chat)
    facts = memory.extract_facts("salon bookings", {"q1": "Yes"}, _design("a", "b"), _design("a", "b", "phone_number"), [])

    assert facts == ["Wants a phone number on bookings"]
    messages, json_mode, small_model = calls[0]
    assert json_mode and small_model
    assert "Added detail 'phone_number' (str)" in json.loads(messages[1]["content"])["changes_they_made"]


def test_only_the_newest_facts_are_kept(monkeypatch, sign_in) -> None:
    sign_in()
    monkeypatch.setattr(settings, "memory_max_facts", 3)
    for number in range(5):
        memory.save_facts(_user_id(), [f"Fact number {number}"], "s1")
    assert [row.fact for row in memory.list_memories(_user_id())] == ["Fact number 4", "Fact number 3", "Fact number 2"]


# --------------------------------------------------------------------------- the whole loop through the API

READY = Understanding(verdict="clear", message="Here it is.", blueprint=_design("customer_name", "service"))


@pytest.fixture
def builder(client, sign_in, monkeypatch):
    """A logged-in person, a fake 'understand' that records the background it got, and builds that do nothing."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    seen_backgrounds: list[str] = []

    def fake_understand(requirement, background=""):
        seen_backgrounds.append(background)
        return READY

    monkeypatch.setattr("app.main.understand", fake_understand)
    monkeypatch.setattr("app.main.run_job", lambda job_id: None)
    return {"headers": sign_in(), "backgrounds": seen_backgrounds}


def _approve_with_an_edit(client, headers) -> str:
    session_id = client.post("/sessions", json={"requirement": "Bookings for my hair salon"}, headers=headers).json()["id"]
    edited = _design("customer_name", "service", "phone_number").model_dump()
    assert client.put(f"/sessions/{session_id}/blueprint", json=edited, headers=headers).status_code == 200
    assert client.post(f"/sessions/{session_id}/build", headers=headers).status_code == 200
    return session_id


def test_approving_a_plan_teaches_memories_that_shape_the_next_request(client, builder, monkeypatch) -> None:
    sent = []

    def fake_chat(messages, json_mode=False, use_fallback_first=False):
        sent.append(json.loads(messages[1]["content"]))
        return json.dumps({"facts": ["Runs a hair salon", "Wants a phone number on bookings"]})

    monkeypatch.setattr(memory, "chat", fake_chat)
    headers = builder["headers"]
    _approve_with_an_edit(client, headers)

    # The model saw our suggestion from before the edit, and the edit itself
    assert sent[0]["suggested_design"]["resources"][0]["fields"][-1]["name"] == "service"
    assert "Added detail 'phone_number' (str)" in sent[0]["changes_they_made"]
    facts = [m["fact"] for m in client.get("/memories", headers=headers).json()]
    assert facts == ["Wants a phone number on bookings", "Runs a hair salon"]

    nxt = client.post("/sessions", json={"requirement": "Customers of my salon"}, headers=headers).json()
    assert "Runs a hair salon" in builder["backgrounds"][-1]
    assert "the request itself always wins" in builder["backgrounds"][-1]
    assert set(nxt["understanding"]["memories_used"]) == set(facts)


def test_the_build_still_works_when_learning_fails(client, builder) -> None:
    # memory.chat is the real one here; conftest blocks real LLM calls, so it fails like "the LLM is down"
    _approve_with_an_edit(client, builder["headers"])
    assert client.get("/memories", headers=builder["headers"]).json() == []
    # ...but the approved design was still kept for RAG (it needs no LLM)
    assert [e.title for e in retrieval.own_examples(_user_id())] == ["Salon Bookings API"]


def test_memory_can_be_switched_off(client, builder, monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_enabled", False)
    monkeypatch.setattr(memory, "chat", lambda *a, **k: pytest.fail("the model must not be called"))
    _approve_with_an_edit(client, builder["headers"])
    assert client.get("/memories", headers=builder["headers"]).json() == []


def test_people_see_and_delete_only_their_own_memories(client, sign_in) -> None:
    ama, kofi = sign_in("ama@example.com"), sign_in("kofi@example.com")
    memory.save_facts(_user_id("ama@example.com"), ["Runs a salon", "Uses GHS"], "s1")
    memory.save_facts(_user_id("kofi@example.com"), ["Sells phones"], "s2")
    amas = client.get("/memories", headers=ama).json()
    assert [m["fact"] for m in amas] == ["Uses GHS", "Runs a salon"]

    assert client.delete(f"/memories/{amas[0]['id']}", headers=kofi).status_code == 404  # not Kofi's
    assert client.delete(f"/memories/{amas[0]['id']}", headers=ama).status_code == 204
    assert client.delete(f"/memories/{amas[0]['id']}", headers=ama).status_code == 404  # already gone
    assert client.delete("/memories", headers=ama).status_code == 204
    assert client.get("/memories", headers=ama).json() == []
    assert [m["fact"] for m in client.get("/memories", headers=kofi).json()] == ["Sells phones"]
    assert client.get("/memories").status_code == 401


def test_one_persons_memories_never_reach_anothers_prompt(sign_in) -> None:
    sign_in("ama@example.com")
    sign_in("kofi@example.com")
    memory.save_facts(_user_id("ama@example.com"), ["Runs a hair salon"], "s1")
    assert "Runs a hair salon" not in before_understanding(_user_id("kofi@example.com"), "my salon").text


def test_refused_requests_show_no_help_used(client, sign_in, monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr("app.main.understand", lambda r, background="": Understanding(verdict="disallowed", message="No."))
    headers = sign_in()
    memory.save_facts(_user_id(), ["Runs a hair salon"], "s1")
    body = client.post("/sessions", json={"requirement": "Bookings for my hair salon"}, headers=headers).json()
    assert body["understanding"]["memories_used"] == [] and body["understanding"]["examples_used"] == []


def test_after_approval_ignores_missing_sessions() -> None:
    after_approval("does-not-exist")  # must not raise


# =========================================================================== step 5: RAG


def test_words_drop_common_words_and_plurals() -> None:
    assert retrieval.words("Keep track of my Books and the customer_names") == ["book", "customer", "name"]
    assert retrieval.words("glass") == ["glass"]  # "ss" is not a plural


def test_cosine_is_one_for_the_same_text_and_zero_for_no_shared_words() -> None:
    idf = retrieval.idf_weights([["salon", "booking"], ["farm", "order"]])
    same = retrieval.vector(["salon", "booking"], idf)
    assert retrieval.cosine(same, same) == pytest.approx(1.0)
    assert retrieval.cosine(same, retrieval.vector(["farm", "order"], idf)) == 0.0
    assert retrieval.vector([], idf) == {}


def test_every_seed_example_is_a_valid_design() -> None:
    seeds = retrieval.seed_examples()
    assert len(seeds) == 21  # 20 one-record examples + 1 school example with 7 linked record types
    assert len({seed.title for seed in seeds}) == 21
    for seed in seeds:
        assert blueprint_problems(seed.blueprint) == [], seed.title


def test_retrieval_check_numbers() -> None:
    """The measured result (see local/evidence/rag_check_step5.txt). If retrieval changes, update both."""
    result = rag_check.evaluate()
    # 21 requests since the school example was added; its own request uses other words and is missed
    assert (result["top1"], result["top3"], result["total"]) == (7, 7, 21)
    wrong = [row for row in result["rows"] if row["got"] and not row["top1"]]
    assert wrong == []  # what it finds is right; it just misses requests that use other words
    assert all(titles == [] for titles in result["unrelated"].values())


def test_your_approved_designs_help_you_and_nobody_else(sign_in) -> None:
    sign_in("ama@example.com")
    sign_in("kofi@example.com")
    braids = Analysis(title="Braiding Styles API", description="Braiding styles offered.", resource_name="braid_style",
                      resource_plural="braid_styles", fields=[FieldSpec(name="style_name", type="str"),
                                                              FieldSpec(name="hours", type="int")])
    assert retrieval.add_approved(_user_id("ama@example.com"), braids) is True
    assert retrieval.add_approved(_user_id("ama@example.com"), braids) is False  # a repeat is not stored twice

    amas = [e.title for e, _ in retrieval.similar_examples("braiding styles and hours", _user_id("ama@example.com"))]
    kofis = [e.title for e, _ in retrieval.similar_examples("braiding styles and hours", _user_id("kofi@example.com"))]
    assert amas[0] == "Braiding Styles API"
    assert "Braiding Styles API" not in kofis


def test_the_background_lists_similar_designs_and_can_be_switched_off(sign_in, monkeypatch) -> None:
    sign_in()
    background = before_understanding(_user_id(), "hotel rooms and nightly rates")
    assert background.examples_used == ["Guest House Rooms API"]
    assert '"Guest House Rooms API": rooms with room_number (str, required)' in background.text

    monkeypatch.setattr(settings, "rag_enabled", False)
    assert before_understanding(_user_id(), "hotel rooms and nightly rates").text == ""


def test_no_memories_and_no_matches_means_no_background(sign_in) -> None:
    sign_in()
    assert before_understanding(_user_id(), "write me a poem about the sea").text == ""


# =========================================================================== storage upgrade


def test_an_older_database_gets_the_new_column(tmp_path, monkeypatch) -> None:
    old = tmp_path / "old.db"
    with sqlite3.connect(old) as db:
        # The sessions table as it was before step 4 (no suggested_json column)
        db.execute("CREATE TABLE sessions (id VARCHAR PRIMARY KEY, owner_id INTEGER, requirement VARCHAR, "
                   "understanding_json VARCHAR, answers_json VARCHAR, job_id VARCHAR, logged_json VARCHAR, created_at VARCHAR)")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{old.as_posix()}")
    reset_engine()
    get_engine()
    with sqlite3.connect(old) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "suggested_json" in columns
    assert {"memories", "examples"} <= tables


# =========================================================================== step 5b: meaning-based search

needs_model = pytest.mark.skipif(retrieval.embedding_model() is None, reason="embedding model not installed")


@needs_model
def test_embeddings_beat_tfidf_on_both_sets() -> None:
    """The measured result (local/evidence/rag_check_embeddings.txt). The cut-off was chosen on the
    tuning set only; the held-out set was written before any embedding run."""
    tuning = rag_check.evaluate("embedding")
    held_out = rag_check.evaluate("embedding", held_out=True)
    assert (tuning["top1"], tuning["wrong"]) == (21, 0)
    assert (held_out["top1"], held_out["wrong"]) == (20, 0)
    matched = [q for q, titles in held_out["unrelated"].items() if titles]
    assert matched == ["how do I cook jollof rice"]  # the one known false match, kept honest
    assert rag_check.evaluate("tfidf", held_out=True)["top1"] == 11


@needs_model
def test_meaning_finds_what_shared_words_miss() -> None:
    seeds = list(retrieval.seed_examples())
    request = "register of people in our congregation"  # shares no words with the church example
    assert retrieval.search(request, seeds, 3, settings.rag_min_score) == []
    found = retrieval.search_by_meaning(request, seeds, 3, settings.rag_embedding_min_score)
    assert found[0][0].title == "Church Members API"


@needs_model
def test_the_builder_uses_embeddings_when_installed(sign_in) -> None:
    sign_in()
    assert retrieval.active_method() == "embedding"
    used = before_understanding(_user_id(), "pupils and their classes at our basic school").examples_used
    assert used[0] == "Students API"


def test_without_the_model_retrieval_falls_back_to_tfidf(sign_in, monkeypatch, tmp_path) -> None:
    sign_in()
    monkeypatch.setattr(settings, "embedding_model_path", str(tmp_path / "no-model-here"))
    retrieval.embedding_model.cache_clear()
    try:
        assert retrieval.active_method() == "tfidf"
        # Still works, with word matching
        assert before_understanding(_user_id(), "hotel rooms and nightly rates").examples_used == ["Guest House Rooms API"]
    finally:
        retrieval.embedding_model.cache_clear()  # the next test loads the real model again


def test_tfidf_can_be_chosen_on_purpose(sign_in, monkeypatch) -> None:
    sign_in()
    monkeypatch.setattr(settings, "rag_method", "tfidf")
    assert retrieval.active_method() == "tfidf"
