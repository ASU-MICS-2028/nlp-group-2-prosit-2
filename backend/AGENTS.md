# backend/ (Elise, backup owner: Opei)

FastAPI platform server, the agent loop, and the sandbox runner. Python, plain code.

## Commands (fill in as the skeleton lands, S-5)
- Install: `pip install -r backend/requirements.txt`
- Run: `uvicorn backend.main:app --reload`
- Test: `pytest`
- API docs: http://localhost:8000/docs

## Traps this area enforces
- Keep the OpenAPI schema accurate: the frontend client is generated from it (D-001). Give every endpoint typed request/response models.
- Generated code is untrusted: run only in a temp folder, with a timeout and size limits (D-007).
- Never log secrets or the user's full request data. Read keys only from environment variables.
- Call the model only through `agent/llm.py`.
- SSE (progress stream): handle the client disconnecting.

## Every feature needs tests for
Normal input · empty/missing/oversized input · same request twice · LLM down or rate-limited · timeout · cleanup of temp folders.
