"""W-3 live check: one real build with Gemini, through our agent loop (backend/builder.py).

Needs GEMINI_API_KEY and LLM_MODEL in the repo's .env (never committed).
Run from the repo root:   python -m evidence.backend.w3_live_check
It never prints the key.
"""

import asyncio
import os
import time
from pathlib import Path

from dotenv import dotenv_values

from agent.prompts import builder_instruction, builder_message
from backend.builder import build_project

REPO = Path(__file__).resolve().parents[2]  # the repo root
settings = dotenv_values(REPO / ".env")
os.environ["GOOGLE_API_KEY"] = settings.get("GEMINI_API_KEY") or ""  # ADK looks for the key under this name
MODEL = settings.get("LLM_MODEL") or ""
if not MODEL:
    # With no model name, ADK quietly picks its own default. We want to know exactly which model ran.
    raise SystemExit("LLM_MODEL is empty in .env. Set it, for example LLM_MODEL=gemini-3.5-flash")

# A small plan, so the check uses little free-tier quota. Same shape as Opei's W-4 check.
PLAN = {
    "name": "Notes API",
    "summary": "Write short notes and read them back.",
    "endpoints": [
        {"method": "GET", "path": "/notes", "description": "See all notes"},
        {"method": "POST", "path": "/notes", "description": "Add a note"},
        {"method": "GET", "path": "/notes/{note_id}", "description": "See one note"},
    ],
    "tables": [
        {
            "name": "notes",
            "fields": [
                {"name": "id", "type": "int", "required": True, "auto": True},
                {"name": "text", "type": "str", "required": True},
            ],
        }
    ],
    "test_count": 5,
}


def show(event: dict) -> None:
    # Print each timeline step as it happens: this is what the Building screen will show.
    step = event["step"]
    print(f"{event['status']:<8} {step['kind']:<9} {step['text'][:150]}")


async def main() -> None:
    print(f"Model: {MODEL}")
    started = time.time()
    result = await build_project(builder_message(PLAN), builder_instruction(), MODEL, report=show)
    print(f"\nResult: {result.status}. {result.reason}")
    print(f"Took {time.time() - started:.0f}s. Files: {sorted(result.files)}")


asyncio.run(main())
