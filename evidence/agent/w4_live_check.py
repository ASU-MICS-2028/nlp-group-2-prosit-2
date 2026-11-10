"""W-4 live check: does Gemini, given the builder prompt and the tools, build a working project?

Needs: the tools (agent/tools.py, PR #9) and the prompt (agent/prompts, PR #10) in the same checkout,
`pip install google-adk==2.13.0`, and GEMINI_API_KEY + LLM_MODEL in the repo's .env.
Run from the repo root:  python evidence/agent/w4_live_check.py
It never prints the key.
"""

import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import dotenv_values
from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.prompts import builder_instruction, builder_message
from agent.tools import Workspace, make_tools
from backend.runner import run_tests

REPO = Path(__file__).resolve().parents[2]
settings = dotenv_values(REPO / ".env")
os.environ["GOOGLE_API_KEY"] = settings["GEMINI_API_KEY"]  # the name ADK looks for
MODEL = settings["LLM_MODEL"]

PLAN = {
    "name": "Bookshop API",
    "summary": "Add books, list them, and see which ones are in stock.",
    "endpoints": [
        {"method": "GET", "path": "/books", "description": "See all books"},
        {"method": "POST", "path": "/books", "description": "Add a book"},
        {"method": "GET", "path": "/books/{book_id}", "description": "See one book"},
        {"method": "DELETE", "path": "/books/{book_id}", "description": "Remove a book"},
    ],
    "tables": [
        {
            "name": "books",
            "fields": [
                {"name": "id", "type": "int", "required": True, "auto": True},
                {"name": "title", "type": "str", "required": True},
                {"name": "author", "type": "str", "required": True},
                {"name": "price", "type": "float", "required": False},
                {"name": "in_stock", "type": "bool", "required": True},
            ],
        }
    ],
    "test_count": 8,
    "not_included": ["Taking card payments"],
}


async def main() -> None:
    workspace = Workspace()
    agent = Agent(
        name="builder",
        model=MODEL,
        instruction=builder_instruction(),  # a function, so ADK leaves {book_id} alone
        tools=make_tools(workspace),
    )
    runner = InMemoryRunner(agent=agent, app_name="w4_check")
    session = await runner.session_service.create_session(app_name="w4_check", user_id="u1")
    message = types.Content(role="user", parts=[types.Part(text=builder_message(PLAN))])

    print(f"Model: {MODEL}")
    started = time.time()
    final_text = ""
    async for event in runner.run_async(
        user_id="u1",
        session_id=session.id,
        new_message=message,
        run_config=RunConfig(max_llm_calls=40),  # a hard stop so a looping model cannot burn the free quota
    ):
        parts = event.content.parts if event.content and event.content.parts else []
        for part in parts:
            if part.function_call:
                args = part.function_call.args or {}
                print(f"DOING   {part.function_call.name}({args.get('path', '')})")
            elif part.function_response:
                response = part.function_response.response or {}
                short = {key: response[key] for key in ("status", "passed", "path") if key in response}
                print(f"RESULT  {short}")
            elif part.text:
                print(f"TEXT    {part.text.strip()[:300]}")
                if event.is_final_response():
                    final_text = part.text.strip()

    print(f"\nTook {time.time() - started:.0f}s; test runs by the agent: {workspace.test_runs}")
    print(f"Files: {sorted(workspace.files)}")

    # Check the agent's claim ourselves instead of trusting its final reply.
    result = run_tests(workspace.files, timeout_seconds=60)
    print(f"Our own test run: passed={result.passed}")
    print(result.output[-1500:])

    try:
        print("Final reply parsed as JSON:", json.loads(final_text.strip("`").removeprefix("json").strip()))
    except ValueError:
        print("Final reply was NOT plain JSON:", final_text[:300])


asyncio.run(main())
