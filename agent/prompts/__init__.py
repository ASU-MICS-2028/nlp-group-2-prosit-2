"""Prompt files for the agent (task W-4).

The prompts themselves are Markdown files in this folder, so the whole team can
read and review them without reading Python. This file only loads them and
builds the first message the builder agent receives.
"""

import json
from pathlib import Path

PROMPTS_FOLDER = Path(__file__).parent
MAX_PLAN_CHARACTERS = 10_000  # a real plan is about 1,000 characters; more means something went wrong


class PromptError(Exception):
    """A prompt file is missing or the plan cannot be sent. The message is safe to show."""


def load_prompt(name: str) -> str:
    """Return the text of agent/prompts/<name>.md, for example load_prompt("builder")."""
    path = PROMPTS_FOLDER / f"{name}.md"
    if not path.is_file():
        raise PromptError(f"There is no prompt called '{name}'.")
    return path.read_text(encoding="utf-8")


def builder_instruction():
    """Return the builder prompt as a function, ready for the ADK agent: Agent(instruction=builder_instruction()).

    Why a function and not the text itself: when ADK gets instructions as text, it treats any word
    in curly braces, like the {note_id} in a FastAPI path, as a value to fill in from its session,
    and fails when there is none. When it gets a function, it uses the returned text exactly as it is.
    """
    text = load_prompt("builder")

    def instruction(context) -> str:  # ADK passes a context; we do not need it
        return text

    return instruction


def builder_message(plan: dict) -> str:
    """Turn the plan the person approved into the builder agent's first message.

    The plan has the shape in docs/api-contract.md: name, summary, endpoints, tables, test_count
    (and maybe not_included). It is sent as JSON so the model sees exactly what was approved.
    """
    for key in ("name", "endpoints", "tables"):
        if not plan.get(key):
            raise PromptError(f"The plan has no '{key}', so there is nothing to build.")
    plan_json = json.dumps(plan, indent=2, ensure_ascii=False)
    if len(plan_json) > MAX_PLAN_CHARACTERS:
        raise PromptError("The plan is too big to build in one go.")
    return f"Here is the approved plan. Build it now.\n\n```json\n{plan_json}\n```"
