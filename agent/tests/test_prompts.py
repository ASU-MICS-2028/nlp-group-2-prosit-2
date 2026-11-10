"""Tests for the builder prompt and its loader (W-4)."""

import json
import re

import pytest

from agent import prompts
from backend.runner import run_tests

BOOKSHOP_PLAN = {
    "name": "Bookshop API",
    "summary": "Add books, list them, and see which ones are in stock.",
    "endpoints": [
        {"method": "GET", "path": "/books", "description": "See all books"},
        {"method": "POST", "path": "/books", "description": "Add a book"},
    ],
    "tables": [
        {
            "name": "books",
            "fields": [
                {"name": "id", "type": "int", "required": True, "auto": True},
                {"name": "title", "type": "str", "required": True},
            ],
        }
    ],
    "test_count": 4,
    "not_included": ["Taking card payments"],
}


def example_files(prompt: str) -> dict[str, str]:
    """Pull the example project out of the prompt: every '#### File: <path>' heading and the code block under it."""
    pattern = r"#### File: (\S+)\n```\w*\n(.*?)```"
    return {path: code for path, code in re.findall(pattern, prompt, flags=re.DOTALL)}


# --- loading ----------------------------------------------------------------


def test_builder_prompt_loads():
    text = prompts.load_prompt("builder")
    assert text.startswith("# Builder agent instructions")


def test_missing_prompt_is_a_clear_error():
    with pytest.raises(prompts.PromptError, match="no prompt called"):
        prompts.load_prompt("does-not-exist")


def test_builder_instruction_is_a_function_returning_the_prompt():
    instruction = prompts.builder_instruction()
    assert callable(instruction)
    assert instruction(None) == prompts.load_prompt("builder")


def test_prompt_has_curly_brace_words_so_it_must_go_to_adk_as_a_function():
    # ADK would try to fill in {note_id} from its session if it got the prompt as plain text.
    assert "{note_id}" in prompts.load_prompt("builder")


# --- what the prompt says ---------------------------------------------------


def test_prompt_names_every_tool():
    text = prompts.load_prompt("builder")
    for tool in ("write_file", "read_file", "list_files", "run_tests"):
        assert tool in text


def test_prompt_sets_a_limit_on_test_runs():
    assert "after **3** test runs" in prompts.load_prompt("builder")


def test_prompt_asks_for_a_json_final_reply_with_both_outcomes():
    text = prompts.load_prompt("builder")
    for outcome in ('"status": "done"', '"status": "gave_up"'):
        assert outcome in text


def test_final_reply_examples_are_valid_json():
    text = prompts.load_prompt("builder")
    final_part = text.split("## Your final reply")[1]
    blocks = re.findall(r"```json\n(.*?)```", final_part, flags=re.DOTALL)
    assert len(blocks) == 2
    for block in blocks:
        reply = json.loads(block)
        assert set(reply) == {"status", "summary", "tests_passed", "tests_total"}


# --- the example project inside the prompt really works ---------------------


def test_example_has_the_whole_fixed_layout():
    files = example_files(prompts.load_prompt("builder"))
    assert set(files) == {
        "requirements.txt",
        "conftest.py",
        "app/__init__.py",
        "app/database.py",
        "app/main.py",
        "tests/test_notes.py",
    }


def test_example_project_passes_its_own_tests():
    # If the example we show the model is broken, the model copies the mistake. So we run it.
    files = example_files(prompts.load_prompt("builder"))
    result = run_tests(files, timeout_seconds=60)
    assert result.passed, result.output
    assert "9 passed" in result.output


def test_example_uses_only_allowed_imports():
    files = example_files(prompts.load_prompt("builder"))
    allowed = {"contextlib", "sqlite3", "fastapi", "pydantic", "pytest", "app"}
    for path, code in files.items():
        for module in re.findall(r"^(?:from|import) (\w+)", code, flags=re.MULTILINE):
            assert module in allowed, f"{path} imports {module}"


# --- the first message to the agent ----------------------------------------


def test_builder_message_contains_the_plan_as_json():
    message = prompts.builder_message(BOOKSHOP_PLAN)
    plan_json = message.split("```json\n")[1].split("\n```")[0]
    assert json.loads(plan_json) == BOOKSHOP_PLAN


@pytest.mark.parametrize("missing", ["name", "endpoints", "tables"])
def test_plan_without_a_key_part_is_refused(missing):
    plan = {key: value for key, value in BOOKSHOP_PLAN.items() if key != missing}
    with pytest.raises(prompts.PromptError, match=missing):
        prompts.builder_message(plan)


def test_plan_with_no_endpoints_is_refused():
    with pytest.raises(prompts.PromptError):
        prompts.builder_message({**BOOKSHOP_PLAN, "endpoints": []})


def test_huge_plan_is_refused():
    huge = {**BOOKSHOP_PLAN, "summary": "x" * (prompts.MAX_PLAN_CHARACTERS + 1)}
    with pytest.raises(prompts.PromptError, match="too big"):
        prompts.builder_message(huge)


def test_non_english_text_is_kept_readable():
    message = prompts.builder_message({**BOOKSHOP_PLAN, "name": "Akwaaba Shop"})
    assert "Akwaaba Shop" in message
