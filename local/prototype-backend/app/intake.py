"""Understand step (Phase 2, M1): verdict, draft blueprint, "Not included yet" list and guided questions."""

from __future__ import annotations

import json
import keyword
import re
from typing import Any

from app.llm import chat, parse_json_object
from app.models import Analysis, FieldSpec, NotIncludedItem, Question, Resource, Understanding
from app.policy import PLATFORM_SUMMARY, REFUSAL_MESSAGE
from app.prompts import MERGE_SYSTEM, NOT_INCLUDED_CATEGORIES, UNDERSTAND_SYSTEM
from app.validators import blueprint_problems

MAX_QUESTIONS = 8
# A vague request should get at least this many questions, so the person has enough context to plan
MIN_QUESTIONS = 5
MAX_OPTIONS = 8
VERDICTS = {"clear", "vague", "reducible", "unsupported", "disallowed"}
QUESTION_KINDS = {"single_choice", "multi_choice", "yes_no", "short_text", "editable_list"}

# Section 4.7: words a non-developer must never see, and what to say instead.
_JARGON = [
    (r"\bCRUD\b", "add, view, change and delete"),
    (r"\bendpoints?\b", "actions"),
    (r"\bforeign keys?\b", "linked records"),
    (r"\brelationships?\b", "linked records"),
    (r"\bentit(?:y|ies)\b", "type of record"),
    (r"\bresources?\b", "type of record"),
    (r"\bout of scope\b", "not supported yet"),
    (r"\bschemas?\b", "design"),
    (r"\bauthentication\b", "logins"),
]


def plain_english(text: str) -> str:
    for pattern, replacement in _JARGON:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


def sanitize_ident(value: str, fallback: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    if not cleaned or cleaned[0].isdigit():
        return fallback
    return cleaned


# Python words that cannot be names in generated code, and what to call them instead
_KEYWORD_NAMES = {"class": "classroom", "classes": "classrooms"}


def record_name(value: str, fallback: str) -> str:
    """A safe snake_case name for a record type: 'Class' becomes classroom, other Python words get _group."""
    name = sanitize_ident(value, fallback)
    if name in _KEYWORD_NAMES:
        return _KEYWORD_NAMES[name]
    return f"{name}_group" if keyword.iskeyword(name) else name


def _normalize_field(item: dict[str, Any]) -> FieldSpec | None:
    name = sanitize_ident(str(item.get("name", "")), "")
    if not name or name == "id":
        return None  # every record gets its own id automatically
    ftype = item.get("type", "str")
    if ftype not in {"str", "int", "float", "bool", "datetime", "link"}:
        ftype = "str"
    links_to = None
    if ftype == "link":
        links_to = record_name(str(item.get("links_to") or name.removesuffix("_id")), "")
        if not name.endswith("_id"):
            name = f"{links_to}_id"  # a link is always named <record>_id, e.g. classroom_id
    auto = ftype != "link" and (bool(item.get("auto")) or name in {"created_at", "updated_at"})
    default = item.get("default")
    if default is not None:
        default = str(default).lower()
    return FieldSpec(
        name=name,
        type=ftype,
        required=bool(item.get("required", True)) and not auto,
        default=default,
        description=str(item.get("description") or name),
        auto=auto,
        links_to=links_to,
    )


def _normalize_resource(raw: dict[str, Any]) -> Resource:
    fields = [f for f in (_normalize_field(item) for item in raw.get("fields") or [] if isinstance(item, dict)) if f]
    if not fields:
        raise ValueError("The model returned a record type without usable fields.")
    name = record_name(str(raw.get("name") or raw.get("resource_name") or "item"), "item")
    plural = record_name(str(raw.get("plural") or raw.get("resource_plural") or f"{name}s"), f"{name}s")
    return Resource(name=name, plural=plural, description=str(raw.get("description") or ""), fields=fields)


def normalize_analysis(raw: dict[str, Any]) -> Analysis:
    # Older single-record replies (resource_name / fields at the top) are read as one record type
    raw_resources = raw.get("resources")
    if not isinstance(raw_resources, list):
        raw_resources = [raw]
    resources = [_normalize_resource(item) for item in raw_resources if isinstance(item, dict)]
    if not resources:
        raise ValueError("The model did not return any record types.")
    first = resources[0].name
    return Analysis(
        title=str(raw.get("title") or f"{first.replace('_', ' ').title()} API"),
        description=str(raw.get("description") or "Generated API."),
        resources=resources,
    )


def checked_blueprint(raw: Any) -> Analysis:
    if not isinstance(raw, dict):
        raise ValueError("blueprint must be a JSON object")
    blueprint = normalize_analysis(raw)
    problems = blueprint_problems(blueprint)
    if problems:
        raise ValueError("Blueprint breaks the rules: " + " ".join(problems))
    return blueprint


# --------------------------------------------------------------------------- not included


def _same_item(a: str, b: str) -> bool:
    a, b = a.lower().strip(" ."), b.lower().strip(" .")
    return a == b or a in b or b in a


def merge_not_included(*groups: list[NotIncludedItem]) -> list[NotIncludedItem]:
    merged: list[NotIncludedItem] = []
    for group in groups:
        for item in group:
            if not any(_same_item(item.text, kept.text) for kept in merged):
                merged.append(item)
    return merged


def _normalize_not_included(raw: Any) -> list[NotIncludedItem]:
    items = []
    for entry in raw or []:
        if isinstance(entry, str):
            entry = {"text": entry}
        if not isinstance(entry, dict):
            continue
        text = plain_english(str(entry.get("text") or entry.get("item") or ""))
        if not text:
            continue
        category = str(entry.get("category") or "other")
        items.append(NotIncludedItem(category=category if category in NOT_INCLUDED_CATEGORIES else "other", text=text))
    return merge_not_included(items)


def _unbuilt_requests(raw: Any) -> list[NotIncludedItem]:
    """Requested items the model marked as not built. They must reach "Not included yet" even if it forgot to list them."""
    items = []
    for entry in raw or []:
        if isinstance(entry, dict) and entry.get("built") is False and str(entry.get("text") or "").strip():
            items.append(NotIncludedItem(category="other", text=plain_english(str(entry["text"]))))
    return items


# --------------------------------------------------------------------------- questions


def _normalize_question(raw: Any, used_ids: set[str]) -> Question | None:
    if not isinstance(raw, dict):
        return None
    text = plain_english(str(raw.get("text") or ""))
    if not text:
        return None
    qid = sanitize_ident(str(raw.get("id") or ""), f"q{len(used_ids) + 1}")
    while qid in used_ids:
        qid += "_2"
    kind = raw.get("kind") if raw.get("kind") in QUESTION_KINDS else "single_choice"
    raw_options = [plain_english(str(o)) for o in raw.get("options") or [] if str(o).strip()]
    # The form always adds its own "Other" box, so a model-written "Other" option would appear twice.
    wants_other = any(o.lower().startswith("other") for o in raw_options)
    options = list(dict.fromkeys(o for o in raw_options if not o.lower().startswith("other")))[:MAX_OPTIONS]
    default = raw.get("default")

    if kind == "yes_no":
        options = ["Yes", "No"]
        default = "No" if str(default).strip().lower() in {"false", "no", "0"} else "Yes"
    elif kind in {"single_choice", "multi_choice"} and len(options) < 2:
        kind, options = "short_text", []
    if kind == "single_choice":
        default = default if default in options else options[0]
    elif kind == "multi_choice":
        chosen = default if isinstance(default, list) else [default]
        default = [o for o in chosen if o in options]
    elif kind == "editable_list":
        default = [str(o) for o in default] if isinstance(default, list) and default else options
    elif kind == "short_text":
        default = "" if default is None else str(default)

    used_ids.add(qid)
    return Question(
        id=qid,
        text=text,
        kind=kind,
        options=options,
        allow_other=(wants_other or bool(raw.get("allow_other", True))) and kind in {"single_choice", "multi_choice"},
        default=default,
        why=plain_english(str(raw.get("why") or "")),
    )


def _normalize_questions(raw: Any) -> list[Question]:
    used: set[str] = set()
    questions = [q for q in (_normalize_question(item, used) for item in raw or []) if q]
    return questions[:MAX_QUESTIONS]


# --------------------------------------------------------------------------- understand


def normalize_understanding(raw: dict[str, Any]) -> Understanding:
    verdict = str(raw.get("verdict", "")).strip().lower()
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {sorted(VERDICTS)}, got {verdict!r}")
    if verdict == "disallowed":
        return Understanding(verdict="disallowed", message=REFUSAL_MESSAGE)

    not_included = merge_not_included(
        _normalize_not_included(raw.get("not_included")), _unbuilt_requests(raw.get("requested_items"))
    )
    message = plain_english(str(raw.get("message") or ""))

    if verdict == "unsupported":
        try:
            blueprint = checked_blueprint(raw.get("blueprint")) if raw.get("blueprint") else None
        except ValueError:
            blueprint = None  # the alternative is optional; the explanation still stands
        alternative = plain_english(str(raw.get("alternative") or "")) or None
        return Understanding(
            verdict="unsupported",
            message=f"{message} {PLATFORM_SUMMARY}".strip(),
            blueprint=blueprint,
            not_included=not_included,
            alternative=alternative,
        )

    blueprint = checked_blueprint(raw.get("blueprint"))
    if verdict == "reducible" and not not_included:
        verdict = "clear"  # nothing was actually left out
    questions = _normalize_questions(raw.get("questions")) if verdict in {"vague", "reducible"} else []
    return Understanding(
        verdict=verdict,
        message=message or f"Here's what I'll build: {blueprint.resource_plural.replace('_', ' ')}.",
        blueprint=blueprint,
        not_included=not_included,
        questions=questions,
    )


def _ask_with_retry(messages: list[dict], normalize, use_fallback_first: bool = False):
    """One call, then one retry with a "fix these errors" message if the output fails validation."""
    first = chat(messages, json_mode=True, use_fallback_first=use_fallback_first)
    try:
        return normalize(parse_json_object(first))
    except Exception as exc:
        retry = [
            *messages,
            {"role": "assistant", "content": first},
            {"role": "user", "content": f"Fix these errors and return the complete JSON again:\n{exc}"},
        ]
        return normalize(parse_json_object(chat(retry, json_mode=True, use_fallback_first=use_fallback_first)))


def understand(requirement: str, background: str = "") -> Understanding:
    """background (steps 4 and 5): remembered facts and similar approved designs, as plain text.
    It goes in its own message BEFORE the request, so the request is always the last word."""
    messages = [{"role": "system", "content": UNDERSTAND_SYSTEM}]
    if background:
        messages.append({"role": "system", "content": background})
    messages.append({"role": "user", "content": requirement})
    result = _ask_with_retry(messages, normalize_understanding)
    return _with_enough_questions(messages, result)


def _with_enough_questions(messages: list[dict], result: Understanding) -> Understanding:
    """A vague request should get at least MIN_QUESTIONS questions. If the model asked fewer, ask it once
    more with a reminder and keep whichever reply has more questions. Never fails because of this."""
    if result.verdict not in {"vague", "reducible"} or len(result.questions) >= MIN_QUESTIONS:
        return result
    reminder = {
        "role": "user",
        "content": (
            f"You asked only {len(result.questions)} questions. Ask between {MIN_QUESTIONS} and {MAX_QUESTIONS}, "
            "one topic each, following the question topics in your instructions. Return the complete JSON again."
        ),
    }
    try:
        again = _ask_with_retry([*messages, reminder], normalize_understanding)
    except Exception:
        return result  # the first reply is still a usable design
    return again if len(again.questions) > len(result.questions) else result


# --------------------------------------------------------------------------- answers


def answers_with_defaults(questions: list[Question], answers: dict[str, Any]) -> dict[str, Any]:
    filled = {}
    for question in questions:
        value = answers.get(question.id)
        filled[question.id] = question.default if value in (None, "", []) else value
    return filled


def apply_answers(requirement: str, current: Understanding, answers: dict[str, Any]) -> Understanding:
    """Merge answers into the draft (gpt-4o-mini). If that fails twice, keep the best-guess draft."""
    filled = answers_with_defaults(current.questions, answers)
    payload = {
        "requirement": requirement,
        "blueprint": current.blueprint.model_dump() if current.blueprint else None,
        "not_included": [item.model_dump() for item in current.not_included],
        "questions": [q.model_dump() for q in current.questions],
        "answers": filled,
    }
    messages = [
        {"role": "system", "content": MERGE_SYSTEM},
        {"role": "user", "content": json.dumps(payload, indent=2, default=str)},
    ]

    def normalize(raw: dict[str, Any]) -> Understanding:
        blueprint = checked_blueprint(raw.get("blueprint"))
        not_included = merge_not_included(current.not_included, _normalize_not_included(raw.get("not_included")))
        return Understanding(
            verdict="reducible" if not_included else "clear",
            message=plain_english(str(raw.get("message") or "")) or current.message,
            blueprint=blueprint,
            not_included=not_included,
        )

    try:
        return _ask_with_retry(messages, normalize, use_fallback_first=True)
    except Exception:
        return current.model_copy(
            update={
                "questions": [],
                "message": "I kept my best-guess design. You can change any detail below before building.",
            }
        )
