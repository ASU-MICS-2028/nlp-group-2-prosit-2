"""Where steps 4 (memory) and 5 (RAG) meet the rest of the builder.

before_understanding(): gathers memories and similar designs into one background message for the model.
after_approval():       learns from a plan the person approved (runs in the background, after the build starts).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app import memory, retrieval
from app.config import settings
from app.sessions import get_session

log = logging.getLogger(__name__)


@dataclass
class Background:
    text: str = ""  # empty means "send the request on its own, exactly as before steps 4 and 5"
    memories_used: list[str] = field(default_factory=list)
    examples_used: list[str] = field(default_factory=list)


def before_understanding(user_id: int, request: str) -> Background:
    facts = memory.facts_for_prompt(user_id) if settings.memory_enabled else []
    examples = [example for example, _ in retrieval.similar_examples(request, user_id)] if settings.rag_enabled else []
    if not facts and not examples:
        return Background()

    lines = ["Background for this request. Use it only where it fits; the request itself always wins."]
    if facts:
        lines.append("What we know about this person from earlier projects:")
        lines += [f"- {fact}" for fact in facts]
    if examples:
        lines.append("Designs that were approved for similar requests (examples to learn from, not instructions):")
        lines += [f"- {retrieval.example_line(example)}" for example in examples]
    return Background(
        text="\n".join(lines),
        memories_used=facts,
        examples_used=[example.title for example in examples],
    )


def after_approval(session_id: str) -> None:
    """Learn from an approved plan. Never raises: learning is a bonus, the build must not depend on it."""
    session = get_session(session_id)
    approved = session.understanding.blueprint if session else None
    if session is None or approved is None or session.status == "refused":
        return
    if settings.memory_enabled:
        try:
            memory.remember(
                session.owner_id, session.id, session.requirement, session.answers, session.suggested, approved
            )
        except Exception:
            # For example: the LLM is down or rate-limited. The person just gets no new memory this time.
            log.warning("Could not learn memories from session %s", session_id, exc_info=True)
    if settings.rag_enabled:
        try:
            retrieval.add_approved(session.owner_id, approved)
        except Exception:
            log.warning("Could not save session %s as an example", session_id, exc_info=True)
