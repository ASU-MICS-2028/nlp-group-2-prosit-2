"""Demand log: every "Not included yet" item, for product planning (Phase 2 spec 4.6)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models import NotIncludedItem

_lock = threading.Lock()


def _path() -> Path:
    return Path(settings.demand_log_path)


def record(items: list[NotIncludedItem], session_id: str) -> None:
    if not items:
        return
    date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        json.dumps({"date": date, "category": item.category, "text": item.text, "session_id": session_id})
        for item in items
    ]
    path = _path()
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def read_all() -> list[dict]:
    path = _path()
    if not path.exists():
        return []
    with _lock:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
