"""Tests for the clarifying questions (F-1). They use a fake AI reply, never the real Gemini."""

import json

import pytest

from agent import llm, questions

# A good reply, in the exact shape the instructions ask for.
BAKERY_REPLY = json.dumps(
    {
        "questions": [
            {
                "id": "q1",
                "text": "Do you want to keep track of customer orders?",
                "why": "This decides whether we store orders, not just your products.",
                "options": ["Yes, orders too", "No, just my products"],
            }
        ]
    }
)


def fake_ai(monkeypatch: pytest.MonkeyPatch, reply: str) -> None:
    """Make llm.generate return `reply` instead of calling Gemini (for this test only)."""
    monkeypatch.setattr(llm, "generate", lambda prompt, system=None: reply)


def test_good_reply_gives_the_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ai(monkeypatch, BAKERY_REPLY)

    result = questions.ask_questions("An API for my small bakery")

    assert len(result) == 1
    assert result[0]["text"] == "Do you want to keep track of customer orders?"

def test_reply_inside_a_code_fence_is_still_read(monkeypatch: pytest.MonkeyPatch) -> None:
    # Gemini sometimes wraps its JSON in ```json ... ``` even when told not to (Opei saw this in W-4).
    fake_ai(monkeypatch, "```json\n" + BAKERY_REPLY + "\n```")

    result = questions.ask_questions("An API for my small bakery")

    assert len(result) == 1


def test_reply_that_is_not_json_gives_a_plain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ai(monkeypatch, "Sure! Here are some questions for you...")

    # pytest.raises means: "this code SHOULD raise this error; the test fails if it doesn't".
    with pytest.raises(questions.QuestionsError, match="could not be read"):
        questions.ask_questions("An API for my small bakery")

def make_question(number: int) -> dict[str, object]:
    """A good question, numbered, for building test replies."""
    return {"id": f"q{number}", "text": f"Question {number}?", "why": "Because.", "options": ["Yes", "No"]}


def test_more_than_three_questions_keeps_the_first_three(monkeypatch: pytest.MonkeyPatch) -> None:
    # The rules say at most 3, most important first. If the AI sends 5, keep the first 3.
    five = [make_question(number) for number in range(1, 6)]
    fake_ai(monkeypatch, json.dumps({"questions": five}))

    result = questions.ask_questions("An API for my small bakery")

    assert [question["id"] for question in result] == ["q1", "q2", "q3"]


def test_question_without_options_gives_a_plain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = make_question(1)
    del broken["options"]  # remove one part, like a forgetful AI would
    fake_ai(monkeypatch, json.dumps({"questions": [broken]}))

    with pytest.raises(questions.QuestionsError, match="could not be read"):
        questions.ask_questions("An API for my small bakery")

def test_clear_request_gives_no_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    # The instructions allow "ask nothing" when the request is already clear.
    fake_ai(monkeypatch, '{"questions": []}')

    result = questions.ask_questions("A list of my books with a title, an author and a price.")

    assert result == []


def test_ai_service_down_gives_the_wrappers_plain_message(monkeypatch: pytest.MonkeyPatch) -> None:
    # A fake AI that fails the way Opei's llm.py does when Gemini is busy.
    def busy_ai(prompt: str, system: str | None = None) -> str:
        raise llm.LLMError("The model is busy (free-tier limit). Try again shortly.")

    monkeypatch.setattr(llm, "generate", busy_ai)

    # We don't catch it: llm.py's message is already plain and safe, so it goes straight to the person.
    with pytest.raises(llm.LLMError, match="busy"):
        questions.ask_questions("An API for my small bakery")
