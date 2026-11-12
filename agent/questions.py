"""Clarifying questions (F-1): ask the AI what is unclear about a request, and check its answer.

The instructions are in agent/prompts/questions.md, in plain English. This file only sends them to
the AI through agent/llm.py (the team's only door to the AI, D-002) and checks the answer's shape.
"""

import json

from agent import llm
from agent.prompts import load_prompt


MAX_QUESTIONS = 3  # the instructions allow at most 3 (agent/prompts/questions.md)
UNREADABLE = "The AI's answer could not be read. Please try again."  # one plain message for every bad answer


class QuestionsError(Exception):
    """The AI's answer could not be used. The message is safe to show to the person."""


def ask_questions(request: str) -> list[dict[str, object]]:
    # The instructions go in as the "system" message: standing rules the AI follows for every request.
    # The person's request goes in as the normal message.
    reply = llm.generate(request, system=load_prompt("questions"))
    return read_questions(reply)


def read_questions(reply: str) -> list[dict[str, object]]:
    try:
        data = json.loads(strip_fence(reply))  # turn the AI's JSON text into Python lists and dictionaries
    except json.JSONDecodeError:
        # Not JSON at all, so we can't guess what the AI meant. Say so plainly instead of crashing.
        raise QuestionsError(UNREADABLE) from None

    # It must be {"questions": [...]}: a dictionary holding a list.
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise QuestionsError(UNREADABLE)

    # Too many? The instructions say "most important first", so keep the first 3 instead of failing.
    found = data["questions"][:MAX_QUESTIONS]  # [:3] means "the first 3 items" (or all, if fewer)

    for question in found:
        if not is_complete(question):
            raise QuestionsError(UNREADABLE)
    return found


def is_complete(question: object) -> bool:
    # Perfect's question card shows every part, so a question missing one is no use to the person.
    if not isinstance(question, dict):
        return False
    for part in ("id", "text", "why"):
        value = question.get(part)
        if not isinstance(value, str) or not value.strip():  # missing, not text, or only spaces
            return False
    options = question.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:  # the instructions ask for 2 to 4
        return False
    return all(isinstance(option, str) for option in options)  # every option must be text


def strip_fence(reply: str) -> str:
    # The AI sometimes wraps its JSON like this, even when told not to:
    #   ```json
    #   {"questions": [...]}
    #   ```
    # Remove the first and last ``` lines, so only the JSON is left.
    text = reply.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")  # the opening fence, with or without "json"
        text = text.removesuffix("```")  # the closing fence
    return text.strip()
