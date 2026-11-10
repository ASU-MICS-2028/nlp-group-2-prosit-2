# Design: storage, accounts and roles, memory and RAG for the API builder

Author: Nana · Date: 2026-11-03 · Lives in: `local/` (this laptop only, git-ignored)
Applies to: the prototype backend in `local/prototype-backend/` (copy of `coding_agent/backend`).

| Step | What | State |
|---|---|---|
| 1 | Save sessions and builds in SQLite | **Built and tested** |
| 2 | Accounts, login tokens, roles, ownership, daily limit (+ login card in the frontend) | **Built and tested** |
| 3 | Real keys and reader/editor roles inside the *generated* APIs | **Built and tested** (2026-11-03, see section 5) |
| 4 | Memory: remember lasting facts about each person | **Built and tested** (2026-11-03, see section 6b) |
| 5 | RAG: reuse similar approved designs as examples | **Built and tested**, retrieval is weak (see section 7b) |

How this relates to the team project: in `PLAN.md`, auth, accounts and RAG are **"Design-doc only"**, and the prosit deadline (1 Nov) has passed. Steps 1–2 here are a working proof on the prototype; the text below can feed the report's "future work" section. The prototype uses OpenAI (paid). Anything moved into the team backend must call the model only through `agent/llm.py` (free Gemini tier) and follow `docs/api-contract.md`.

---

## 1. The problem

| What was wrong | Why it matters |
|---|---|
| Sessions and builds lived in Python dictionaries in memory | A restart lost every conversation and build ("the builder restarted and lost this build") |
| No accounts | Anyone could use the paid OpenAI key |
| Anyone who knew a build id could download the project | A person's project was not private |
| `/demand-log` was public | Product-planning data was open to everyone |
| Generated APIs all ship with the key `demo-api-key` | Anyone who reads the README can change the data |

---

## 2. Step 1: storage (built)

**Choice: SQLite through SQLModel.** One file (`data/builder.db`), no server to run, free, and `sqlmodel` was already a dependency.

### Tables (`app/db.py`)

| Table | Holds | Notes |
|---|---|---|
| `users` | email (unique), password hash, role, created | The database itself refuses a second account with the same email |
| `tokens` | SHA-256 **hash** of each login token, user, expiry | The token itself is never stored |
| `sessions` | owner, request, understanding (JSON), answers (JSON), build id, demand items already logged | |
| `jobs` | owner, request, design (JSON), status, stage, error, files, timing, zip path | Saved at every stage, so polling shows progress |
| `usage` | user, kind (`session`/`generate`), time | Counts requests for the daily limit |

**Why JSON columns:** the understanding and design are nested data that we always load whole. JSON text keeps the code short; we lose the ability to search inside them with SQL, which we do not need.

### Behaviour

- `sessions.py` and `jobs.py` keep the same `Session` and `Job` classes the rest of the code already used. They now load from and save to rows. **Changing an object does not save it**: `main.py` calls `save_session()` / `save_job()` after each change.
- **Restarts:** a build runs in a background thread, which cannot survive a restart. On start-up, `recover_interrupted_jobs()` marks any build still `queued`/`running` as `failed` with "The builder restarted during this build. Please click the build button again." Before, it would have looked stuck forever.
- **A race the tests found:** opening the database shared the engine *before* the tables were created. Two requests arriving together after a restart could write before the `users` table existed. Fixed with a lock, and the engine is shared only after its tables exist (`get_engine()`).

---

## 3. Step 2: accounts, roles and ownership (built)

### How logging in works

```
sign up    POST /auth/register {email, password}  → account (always role "user")
log in     POST /auth/login    {email, password}  → {token, user}
every call Authorization: Bearer <token>
log out    POST /auth/logout                       → token deleted
who am I   GET  /auth/me
```

| Decision | Why | Gave up |
|---|---|---|
| Passwords hashed with **scrypt** (`hashlib`, built into Python), 16-byte random salt each | Slow on purpose, so guessing many passwords is expensive; no new package | Nothing |
| **Random opaque tokens** stored in the database, not JWT | Easy to explain: the server looks the token up. Logging out really ends it | One database read per request (fine at this size) |
| Store only the **SHA-256 of the token** | A copied database file cannot be used to log in | Nothing |
| Tokens last **7 days** (`token_days`) | Fewer log-ins for a demo | A stolen token works until it expires or the person logs out |
| Same message for wrong password and unknown email | Outsiders cannot test which emails have accounts | Sign-up still says "already exists" (needed for a helpful message) |
| Email: trimmed and lower-cased, simple shape check | `Ama@Shop.com` and `ama@shop.com` are one account | Not a full email validator; no email confirmation |
| Password 8–128 characters | Long enough to be safe; the upper limit stops someone sending a huge password to make scrypt slow | — |
| Token kept in **sessionStorage** in the browser | Survives a refresh, gone when the tab closes | Any script on the page could read it, so the page must never run untrusted code |

### Roles and who can see what

| | Not logged in | `user` | `admin` |
|---|---|---|---|
| `/health`, `/auth/register`, `/auth/login` | ✅ | ✅ | ✅ |
| Start a session, answer, edit, build, `/generate` | 401 | ✅ own | ✅ |
| Read a session or build, download the zip | 401 | own only (others: **404**) | everyone's |
| `/demand-log` | 401 | **403** | ✅ |
| Daily request limit (`daily_request_limit`, 20) | — | applies (429 when used up) | none |

- **404, not 403, for someone else's project**, so outsiders cannot even tell it exists.
- **No web route makes an admin.** Only `python -m app.make_admin <email>` on this computer can. Sign-up ignores a `"role"` field.
- **The daily limit counts only requests that reach the LLM.** Requests the backend rejects for free (too short, too long) are not counted.
- An admin who builds someone else's session does not take it over: the build belongs to the session's owner.

### Frontend changes (`local/prototype-frontend`)

- A **login card** in the same layout (same card, input and button styles). It switches between "Log in" and "Create an account", checks the password length before sending, and works with the Enter key.
- `call()` adds the token to every request. If the backend says 401, the token is forgotten and the login card comes back.
- **Downloads** now use `fetch` with the token and save the file from memory, because a plain link cannot send the header.
- "Signed in as … (admin) · Log out" line at the top of the main column.

### Known gaps (not done)

| Gap | Risk | Fix later |
|---|---|---|
| No limit on failed log-ins | Someone can keep guessing a password (each guess is slow because of scrypt, but not blocked) | Lock an email for 15 minutes after 5 failures |
| Daily limit is check-then-record | Two requests in the same instant could go one over | One database transaction for both |
| No password reset or email confirmation | A forgotten password needs an admin | Needs an email service |
| No HTTPS | Fine on one laptop; a token on the network would be readable | The host (Render) gives HTTPS |
| CORS allows credentials and all headers | Only matters for the listed origins | Narrow to `Authorization, Content-Type` |
| Old builds and tokens are never cleaned up | The file grows slowly | A clean-up job |

---

## 4. How steps 1–2 were tested

Evidence: `local/evidence/backend_tests_step1_step2.txt`, `frontend_tests_step2.txt`, `live_check_step1_step2.txt`.

| Check | Result |
|---|---|
| Backend `pytest` | **62 passed** (36 original, 4 of them updated to log in; 26 new). The race test passed 10 runs out of 10 after the fix |
| Frontend `vitest` | **49 passed** (35 component + 14 flow and login). Typecheck, build and lint pass |
| Live server, no OpenAI call (fake key) | All rows as expected: sign-up 201; duplicate (other case) 409; bad email 400; short password 422; wrong password and unknown email the same 401; no or forged token 401; user on demand log 403; `make_admin` then 200; LLM unavailable → plain 502 |
| Live restart | A token made before the restart still works; a build cut off by the restart reads as failed with the plain message; after log out the token gets 401 |
| Database file | Holds `scrypt$…` hashes and token hashes; the plain password and token are **not** in the file |

What each new test covers: normal flow; restart; stage saving; failed build; interrupted builds; hashing and salts; same answer for wrong password and unknown email; SQL-looking input; duplicate email in any case; **five sign-ups at the same moment → exactly one account**; bad, missing and oversized input; missing, forged and expired tokens; log out (twice); other people's sessions, builds and downloads → 404; admin sees all; sign-up cannot make an admin; `make_admin` command; daily limit, per person, admins exempt, free rejects not counted. Frontend: login card first, log in, wrong password, sign-up rules, login ending mid-flow, stale token after refresh, log out, token on every call and on the download.

**Not tested:** a real request through OpenAI (costs money); clicking through in a browser; many users at once on the real server; the token in a browser other than the test one (jsdom).

---

## 5. Step 3: keys and roles inside the generated APIs (built)

**Before:** every generated API read one `API_KEY` and fell back to `demo-api-key`, which is printed in every README. Anyone who had seen one README could change anyone's data.

**Change from the plan above (decided while building):** no new intake question. Every API simply gets **both** keys; the owner shares the reader key only if they want to. Same protection, no extra question for a non-developer, no change to the LLM intake.

### What a generated project now contains

| File | What changed |
|---|---|
| `.env` | **New.** Two random keys made for this project (`secrets.token_urlsafe(32)`, 43 characters each) plus comments saying what each one does |
| `.env.example` | Key **names only**, no values. If someone copies it as it is, the API refuses everything (see below) instead of using a guessable key |
| `app/auth.py` | `require_reader` (reader **or** editor key) and `require_editor` (editor key only). Keys compared with `hmac.compare_digest` (no timing hints). **No default key** |
| `app/routers/<plural>.py` | Each route says what it needs: `GET` → `CAN_LOOK`; `POST`, `PUT`, `DELETE` → `CAN_CHANGE` |
| `docker-compose.yml` | Reads the keys with `env_file: .env` (`.env` stays out of the image through `.dockerignore`, and out of git through `.gitignore`) |
| `README.md` | New "Your keys" section; curl examples use `YOUR_READER_KEY` for looking and `YOUR_EDITOR_KEY` for changing |
| `openapi.yaml` | `403` documented on `POST`, `PUT`, `DELETE` only; the key scheme says which key is which |
| `tests/` | 4 new checks (11 in total), also shown in plain words in `TEST_RESULTS.md` |

### Rules the generated API follows

| Situation | Answer |
|---|---|
| Reader or editor key, looking | 200 |
| Editor key, adding / editing / deleting | 201 / 200 / 204 |
| Reader key, adding / editing / deleting | **403** "This key can only look at records. Use the EDITOR_KEY…" |
| Wrong or missing key | 401 |
| `EDITOR_KEY` missing, or any key shorter than 16 characters | **503** for every protected request, with a plain message saying to put keys in `.env` (fail closed: refuse rather than let anyone in) |
| `/health` | 200 always, no key |

### Builder-side changes

- `render_project(..., keys=None)` makes fresh keys unless a test passes its own.
- **README check** (`readme_problems`) now also requires `EDITOR_KEY`, `READER_KEY` and `.env`, and **rejects any README that mentions `demo-api-key`**. The LLM writes the README; if it slips back to the old key, the builder falls back to the template README (tested).
- The LLM prompts (`prompts.py`, the README contract in `pipeline.py`) describe the two keys and say "never write a real-looking key".
- Local frontend: a notice under "Your API is ready" says where the two keys are and what each can do.

### Trade-offs and gaps

| Choice / gap | Why or risk |
|---|---|
| The zip contains `.env` with the keys | The person needs them to use the API. Only the project's owner can download the zip (step 2). The builder's own copy is in `generated/<job id>/` on this laptop |
| Keys are not shown on screen in the builder | Keeps them out of the builder's database and the browser; the person opens `.env` instead |
| Rotating a key means editing `.env` and restarting | Simple and explainable; no key-management screen |
| One key per role, not per person | You cannot tell *which* reader made a request, or revoke one reader without changing the key for all |

### How it was tested

Evidence: `local/evidence/backend_tests_step3.txt`, `generated_api_step3.txt`, `frontend_tests_step3.txt`.

- Builder `pytest`: **74 passed** (62 before + 12 new in `tests/test_project_keys.py`; `test_generated_apps.py` now expects 11 generated checks, run three ways each for three sample APIs).
- The most important test **runs a generated project with the `.env` it actually ships with** (not test keys): editor adds 201, reader lists and opens 200, reader adds/edits/deletes 403, wrong key 401, no key 401, health 200, editor deletes 204.
- Fail-closed tests: `.env` copied from `.env.example` (no keys), editor key `change-me`, reader key `short` → every protected request 503 with the plain message; health still 200.
- Also tested: keys are random and different per project and per build; no file contains `demo-api-key`; `.env` is in the zip but in `.gitignore` and `.dockerignore`; README template passes the new checks and uses the placeholders; README check catches the old key and missing key names; an LLM README with the old key is replaced by the template; `403` appears only on changing operations.
- A freshly generated "Bookshop API", tested the way a user would (`pytest` in its folder): **11 of 11 checks passed**.
- Frontend: 49 passed (the flow test now also checks the keys notice).

**Not tested:** `Start.bat` / `Start.command` and `docker compose up` on a real machine (they download Python or build an image); an LLM-written OpenAPI file (only the fallback builder's file was checked for `403`); a real build through OpenAI.

---

## 6. Step 4: memory (design)

Two kinds:

| Kind | Remembers | Where |
|---|---|---|
| Short-term (one conversation) | request, answers, design, edits | The `sessions` row from step 1 (**already done**) |
| Long-term (one person, across projects) | lasting facts: "prices are in GHS", "always wants a phone number on customers", "is a salon in Accra" | New table `memories` |

**Table:** `memories(id, user_id, fact, source_session_id, created_at)`, at most 20 facts per person (oldest dropped).

**Write:** when a person **approves** a plan, ask the small model for at most 3 lasting facts, given the request, the answers and **what the person changed** on the plan card (the strongest signal). Reject facts that contain an email, a phone number or a name (simple patterns), and never write memories from a refused request.

**Read:** at the start of `understand()` in `intake.py`, add up to 10 facts to the prompt under "What we know about this person". Expected effect: fewer questions and fewer edits on later projects.

**Privacy and control:** a "What I remember" list in the UI with a delete button per fact (`GET /memories`, `DELETE /memories/{id}`, owner only, same 404 rule). Deleting an account deletes its memories.

**Cost:** one extra small-model call per approved plan. **Risk:** a wrong fact makes later plans worse, which is why people can see and delete them.

---

## 7. Step 5: RAG, reuse similar approved designs (design)

RAG (retrieval-augmented generation) = find relevant saved text and put it in the prompt before the model answers.

**What we retrieve:** past **approved** designs: the request plus the plan the person approved *after* their edits. These are known-good examples. Seed with about 20 hand-written ones (shop, salon bookings, church members, clinic, farm orders) so it helps from day one. Only examples that people approved, and never another person's private text: store the request text only for seed examples; for real users, store the design and a short neutral summary.

**How (all free, on this laptop):**

| Part | Choice | Why |
|---|---|---|
| Turn text into numbers (embedding) | Start with **TF-IDF** (scikit-learn); upgrade to `sentence-transformers/all-MiniLM-L6-v2` if TF-IDF misses obvious matches | TF-IDF matches shared words and is easy to explain; MiniLM matches meaning, free on CPU. Not OpenAI embeddings (they cost money) |
| Store | A `examples` table in the same SQLite file, vector as JSON | A few thousand rows need no vector database |
| Search | Cosine similarity in numpy, top 3, only above a threshold | Below the threshold, add nothing (a bad example is worse than none) |
| Use | In `understand()`, add them to the prompt in `prompts.py` as "Request → approved design" examples | The model copies good structure |

New files: `app/retrieval.py` (add, search), seed file `data/examples.json`. Changed: `understand()`, `prompts.py`.

**How we would know it helps:** run the 20 evaluation requests with RAG off and on, and compare: questions asked, fields people would edit (judged against the expected endpoints in `evaluation/`), build success rate, and time. Put the numbers in the report only after measuring.

---

## 6b. Step 4 as built (2026-11-03)

Mostly as designed in section 6. Files: `app/memory.py`, `app/learning.py`, `MEMORY_SYSTEM` in `app/prompts.py`, table `memories`, column `sessions.suggested_json`.

- **What the person changed** is now known: the first edit on the plan card saves our suggestion (`suggested_json`), and `describe_changes()` turns the difference into plain lines ("Added detail 'phone_number' (str)"). These go to the small model with the request and answers.
- **Learning runs after approval, in the background, after the build task.** If the LLM is down, the person simply gets no new memory; the build is unaffected (tested). Never from a refused request.
- **Code filters every fact** again after the model: at most 3 per approval, at most 150 characters, no email, phone number (7+ digits), link, or words like password/key; repeats dropped; at most 20 kept per person (oldest dropped).
- **Read:** up to 10 facts go into a separate background message *before* the request ("Use it only where it fits; the request itself always wins").
- **Shown and deletable:** `GET /memories`, `DELETE /memories/{id}`, `DELETE /memories` (only ever your own; someone else's id gets 404). The plan says "I used 2 notes about you…"; the start screen has "What I remember about you" with delete buttons and "Forget everything".
- **Older database files** get the new column automatically (`_add_missing_columns`, tested on a pre-step-4 file).
- Switch off with `MEMORY_ENABLED=false`.

## 7b. Step 5 as built (2026-11-03)

Files: `app/retrieval.py`, `app/seed_examples.json` (20 hand-written examples), `app/rag_check.py`, table `examples`.

- **TF-IDF and cosine similarity written by hand** (no scikit-learn): words lower-cased, common words dropped, a plural "s" cut. About 40 lines; every line explainable.
- **Candidates:** the 20 seed examples plus **only your own** approved designs (newest 200). Stored as the design and a neutral summary (title, description, detail names), never your request text. Never shared between people (tested).
- Top 3 above a minimum score go into the background message as one line each, e.g. `"Guest House Rooms API": rooms with room_number (str, required), …`. The plan says which designs were used.
- Switch off with `RAG_ENABLED=false`.

### Measured (retrieval only, no LLM): `local/evidence/rag_check_step5.txt`

20 new requests, each written in **different words** from the seed it should find, plus 3 unrelated requests:

| Minimum score | Right example first | Wrong example first | Found nothing | Unrelated requests matched |
|---|---|---|---|---|
| 0.20 (first try) | 7 of 20 | **2** (barbershop → Clinic, "hospital… book" → Bookshop) | 11 | 0 of 3 |
| **0.25 (kept)** | 7 of 20 | **0** | 13 | 0 of 3 |

**What this means, honestly:**
- TF-IDF only matches the **same words**. "congregation" never finds "church", "drugs" never finds "medicines". So retrieval misses 13 of 20 requests that use other words. When it does find something, it was right every time (at 0.25).
- 0.25 was chosen on this same set of 20, so these numbers are **optimistic**; a fresh set may do worse.
- A miss is safe: the request simply goes to the model without examples, exactly as before step 5.
- **Next step if this matters:** swap `words()`/`vector()` for a meaning-based embedding (`sentence-transformers/all-MiniLM-L6-v2`, free on CPU but a large download), re-run `python -m app.rag_check`, and keep whichever scores better.
- **Not measured yet:** whether examples and memories actually make plans better (fewer questions, fewer edits). That needs the 20 evaluation requests run through the LLM with `RAG_ENABLED`/`MEMORY_ENABLED` on and off, which costs money.

### How steps 4–5 were tested

Evidence: `local/evidence/backend_tests_step4_5.txt` (**99 passed**: 74 before + 25 new in `tests/test_memory_and_rag.py`), `frontend_tests_step4_5.txt` (**52 passed**: 49 + 3 new).

Covered: describing edits; unsafe facts (email, phone, link, password, too long, empty) dropped; at most 3 new facts, repeats dropped; the small model and JSON mode are used and get the edits; only the newest 20 kept; **the full loop through the API** (edit → approve → facts saved → next request's background contains them and the response lists them); build still succeeds when learning fails; memory switched off calls no model; seeing and deleting only your own memories (404 for others', 401 logged out); one person's facts never reach another's prompt; refused requests list no help; missing session ignored; words/plurals; cosine 1 and 0; all 20 seeds are valid designs; the retrieval numbers above; your approved designs help only you, repeats not stored twice; background text and switch-off; nothing matched → no background; older database upgraded. Frontend: memory list, forget one, forget everything, memory failing does not block the builder, "I used …" line.

A test safety net blocks every real OpenAI call in the backend tests (`no_real_llm` in `tests/conftest.py`).

**Not tested:** any of this with the real model (cost); how good the model's facts are; the off/on comparison above.

## 8. Order and effort

1. ✅ Storage. 2. ✅ Accounts and roles. 3. ✅ Keys in generated APIs. 4. ✅ Memory. 5. ✅ RAG (retrieval only measured; the off/on comparison with the LLM is still to do).
Each step works on its own and can be tested on its own.

## 9. Open questions

- Should a person be able to delete their account (and all projects, memories and tokens) from the UI?
- Is 20 requests a day right? It depends on the OpenAI budget.
- For the team backend: should memory and RAG examples be shared between users at all, or only per person?

## 10. Terms

| Term | One-line meaning |
|---|---|
| SQLite | A database that is just one file; no server needed |
| SQLModel | A Python library to describe tables as classes and read/write rows |
| Hash / salt | A one-way scramble / random bytes mixed in so equal passwords look different |
| scrypt | A password hash that is slow on purpose |
| Token (bearer) | A long random string sent in the `Authorization` header instead of the password |
| 401 / 403 / 404 / 429 | Not logged in / logged in but not allowed / not found (or not yours) / too many requests |
| Dependency (FastAPI) | A function FastAPI runs before an endpoint, e.g. "who is calling?" |
| Race condition | A bug that appears only when two things happen at the same moment |
| sessionStorage | Browser storage that lasts until the tab closes |
| Embedding | Text turned into a list of numbers so similar texts have similar numbers |
| TF-IDF | An embedding based on which words a text uses and how rare they are |
| Cosine similarity | A score from −1 to 1 for how alike two embeddings are |
| RAG | Retrieve relevant saved text, add it to the prompt, then generate |
| Editor key / reader key | In a generated API: the key that can change records / the key that can only look |
| Fail closed | When something is not set up, refuse everything instead of letting everyone in |
| 503 | "Service unavailable": here, the API is running but has no safe keys set up yet |
