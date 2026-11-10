"""Step 4: long-term memory. Lasting facts about each person, learned from plans they approve.

Write: after a plan is approved, the small model suggests at most 3 facts; code filters them.
Read:  when a new request comes in, up to 10 facts go into the prompt as background.
Control: people can see every fact and delete one or all of them.
"""

from __future__ import annotations

import json
import re

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.config import settings
from app.db import MemoryRow, get_engine
from app.llm import chat, parse_json_object
from app.models import Analysis
from app.prompts import MEMORY_SYSTEM

MAX_FACTS_PER_APPROVAL = 3
MAX_FACT_LENGTH = 150

# Things a fact must never contain, checked in code as well as asked of the model
_EMAIL = re.compile(r"\S+@\S+\.\S+")
_PHONE = re.compile(r"(?:\+?\d[\s-]?){7,}")  # 7 or more digits, with optional spaces or dashes
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_SECRET_WORDS = re.compile(r"\b(password|passcode|api key|token|editor_key|reader_key)\b", re.IGNORECASE)


# --------------------------------------------------------------------------- what the person changed


def describe_changes(suggested: Analysis | None, approved: Analysis) -> list[str]:
    """Plain-English list of edits between the design we suggested and the one approved."""
    if suggested is None:
        return []
    changes: list[str] = []
    old_types = {r.plural for r in suggested.resources}
    new_types = {r.plural for r in approved.resources}
    changes += [f"Added record type '{plural}'" for plural in new_types - old_types]
    changes += [f"Removed record type '{plural}'" for plural in old_types - new_types]
    # Details are compared within each record type that is in both designs
    for plural in old_types & new_types:
        before = {f.name: f for r in suggested.resources if r.plural == plural for f in r.fields}
        after = {f.name: f for r in approved.resources if r.plural == plural for f in r.fields}
        where = "" if len(approved.resources) == 1 else f" in {plural}"
        for name in after.keys() - before.keys():
            changes.append(f"Added detail '{name}' ({after[name].type}){where}")
        for name in before.keys() - after.keys():
            changes.append(f"Removed detail '{name}'{where}")
        for name in before.keys() & after.keys():
            if before[name].type != after[name].type:
                changes.append(f"Changed '{name}' from {before[name].type} to {after[name].type}{where}")
            if before[name].required != after[name].required:
                changes.append(f"Made '{name}' {'required' if after[name].required else 'optional'}{where}")
    if suggested.title != approved.title:
        changes.append(f"Renamed the API from '{suggested.title}' to '{approved.title}'")
    # Sorted so the same edits always give the same list (easier to test and to read)
    return sorted(changes)


# --------------------------------------------------------------------------- choosing facts


def is_safe_fact(fact: str) -> bool:
    """A fact is kept only if it is short and has no contact details, links or secrets."""
    if not fact or len(fact) > MAX_FACT_LENGTH:
        return False
    return not (_EMAIL.search(fact) or _PHONE.search(fact) or _URL.search(fact) or _SECRET_WORDS.search(fact))


def clean_facts(raw: object, existing: list[str]) -> list[str]:
    """Keeps at most 3 safe, new facts from the model's reply. Repeats of known facts are dropped."""
    if not isinstance(raw, list):
        return []
    known = {fact.strip().lower() for fact in existing}
    kept: list[str] = []
    for item in raw:
        fact = str(item).strip().rstrip(".")
        if is_safe_fact(fact) and fact.lower() not in known:
            kept.append(fact)
            known.add(fact.lower())
        if len(kept) == MAX_FACTS_PER_APPROVAL:
            break
    return kept


def extract_facts(
    requirement: str,
    answers: dict,
    suggested: Analysis | None,
    approved: Analysis,
    existing: list[str],
) -> list[str]:
    payload = {
        "request": requirement,
        "answers": answers,
        "suggested_design": suggested.model_dump() if suggested else None,
        "approved_design": approved.model_dump(),
        "changes_they_made": describe_changes(suggested, approved),
        "facts_we_already_know": existing,
    }
    messages = [
        {"role": "system", "content": MEMORY_SYSTEM},
        {"role": "user", "content": json.dumps(payload, indent=2, default=str)},
    ]
    # use_fallback_first=True: the smaller, cheaper model is good enough for short notes
    reply = parse_json_object(chat(messages, json_mode=True, use_fallback_first=True))
    return clean_facts(reply.get("facts"), existing)


# --------------------------------------------------------------------------- storage


def list_memories(user_id: int) -> list[MemoryRow]:
    """Newest first."""
    with DbSession(get_engine()) as db:
        query = select(MemoryRow).where(MemoryRow.user_id == user_id).order_by(MemoryRow.id.desc())
        return list(db.exec(query).all())


def facts_for_prompt(user_id: int) -> list[str]:
    return [row.fact for row in list_memories(user_id)[: settings.memory_facts_in_prompt]]


def save_facts(user_id: int, facts: list[str], session_id: str) -> None:
    with DbSession(get_engine()) as db:
        for fact in facts:
            db.add(MemoryRow(user_id=user_id, fact=fact, source_session_id=session_id))
        db.commit()
        # Keep only the newest memory_max_facts; drop the oldest
        rows = db.exec(select(MemoryRow).where(MemoryRow.user_id == user_id).order_by(MemoryRow.id.desc())).all()
        for old in rows[settings.memory_max_facts :]:
            db.delete(old)
        db.commit()


def remember(
    user_id: int,
    session_id: str,
    requirement: str,
    answers: dict,
    suggested: Analysis | None,
    approved: Analysis,
) -> list[str]:
    """Learns from one approved plan. Returns the facts that were saved."""
    existing = [row.fact for row in list_memories(user_id)]
    facts = extract_facts(requirement, answers, suggested, approved, existing)
    save_facts(user_id, facts, session_id)
    return facts


def forget(user_id: int, memory_id: int) -> bool:
    """Deletes one fact. Returns False if it does not exist or belongs to someone else."""
    with DbSession(get_engine()) as db:
        row = db.get(MemoryRow, memory_id)
        if not row or row.user_id != user_id:
            return False
        db.delete(row)
        db.commit()
        return True


def forget_all(user_id: int) -> int:
    with DbSession(get_engine()) as db:
        rows = db.exec(select(MemoryRow).where(MemoryRow.user_id == user_id)).all()
        for row in rows:
            db.delete(row)
        db.commit()
        return len(rows)
