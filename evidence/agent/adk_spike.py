"""W-10 spike: can Google ADK run a tiny agent with one tool on our Gemini key?

Setup: a separate virtual environment with `pip install google-adk` (not added to
backend/requirements.txt yet). Run: python evidence/agent/adk_spike.py
It reads the key from the repo's .env and never prints it.
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path

from dotenv import dotenv_values
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

REPO = Path(__file__).resolve().parents[2]  # the repo root
settings = dotenv_values(REPO / ".env")
os.environ["GOOGLE_API_KEY"] = settings["GEMINI_API_KEY"]  # the name ADK looks for (to be confirmed)
MODEL = settings["LLM_MODEL"]

WORKDIR = Path(tempfile.mkdtemp(prefix="adk-spike-"))


def write_file(path: str, content: str) -> dict:
    """Write a text file inside the project folder.

    Args:
        path: file name, for example "hello.py"
        content: the full text of the file
    """
    target = WORKDIR / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"status": "ok", "path": path, "characters": len(content)}


agent = Agent(
    name="spike_agent",
    model=MODEL,
    instruction=(
        "You write small Python projects by calling the write_file tool once per file. "
        "When all files are written, reply with one short sentence."
    ),
    tools=[write_file],
)


async def main() -> None:
    runner = InMemoryRunner(agent=agent, app_name="spike")
    session = await runner.session_service.create_session(app_name="spike", user_id="u1")
    message = types.Content(
        role="user",
        parts=[types.Part(text="Create two files: math_utils.py with an add(a, b) function, and test_math_utils.py with a pytest test for it.")],
    )

    started = time.time()
    async for event in runner.run_async(user_id="u1", session_id=session.id, new_message=message):
        parts = event.content.parts if event.content and event.content.parts else []
        for part in parts:
            if part.function_call:
                print(f"[{event.author}] TOOL CALL  {part.function_call.name}({list((part.function_call.args or {}).keys())})")
            elif part.function_response:
                print(f"[{event.author}] TOOL RESULT {part.function_response.response}")
            elif part.text:
                print(f"[{event.author}] TEXT        {part.text.strip()[:200]}")
        if event.is_final_response():
            print("(final response event)")

    print(f"\nTook {time.time() - started:.1f}s. Files written: {sorted(p.name for p in WORKDIR.iterdir())}")
    for p in sorted(WORKDIR.iterdir()):
        print(f"--- {p.name}\n{p.read_text()}")


asyncio.run(main())
