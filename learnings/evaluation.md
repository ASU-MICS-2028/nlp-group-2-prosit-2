# Evaluation

Owner: Nana · Last updated: 2026-11-15 · Status: partly working (test set and scoring script ready; no real results yet: the free quota ran out)

## 1. In one sentence
Twenty made-up requests a non-developer might type, each with what the platform should do, so we can measure how often it gets it right.

## 2. What I did, step by step
1. Read the builder prompt (`agent/prompts/builder.md`) to see exactly which endpoints a plan produces: for each table, `GET /x`, `POST /x`, `GET /x/{x_id}`, `PUT /x/{x_id}`, `DELETE /x/{x_id}`.
2. Wrote 20 synthetic requests in `evaluation/requests.json`, in five kinds so the test is not only easy cases:
   | Kind | How many | What should happen (`expect`) |
   |---|---|---|
   | clear, one table | 8 | build that table with its 5 endpoints and the named details |
   | several tables | 4 | build every named table (at least 3) |
   | vague | 4 | ask questions first, then build at least `min_tables` |
   | partly supported | 2 | build the supported part; list the rest (payments, SMS, logins, photos) as not included |
   | out of scope | 2 | build nothing, say why plainly (a website; collecting personal data) |
3. Wrote `evaluation/tests/test_requests.py`: 6 checks that the file has the right shape (20 unique requests, known kinds, endpoints written the same way, every table has its 5 endpoints, refusals expect nothing).
4. 2026-11-15: wrote the scoring script `evaluation/score.py` (E-1). For each request it runs the builder, then records:
   - **outcome**: `pass`, `fail`, `limit` (Gemini's free-tier limit stopped it), `timeout` (no answer in 15 minutes) or `error` (the build crashed);
   - **seconds**, and **retries** (extra whole tries the builder needed, from its `attempt` events);
   - for failures, which expected endpoints are missing and how many tables there are.
   It reads the endpoints from the generated `app/main.py` (`@app.get("/books/{book_id}")` and so on) and the tables from `app/database.py`.
5. Wrote 15 tests (`evaluation/tests/test_score.py`) with a pretend builder, so no Gemini request is made: a passing build, retries, a failed build, the limit,
   a missing endpoint, `book` vs `books` and `{book_id}` vs `{id}`, too few tables, a malformed result (no `app/main.py`), a crashing builder,
   a timeout, refusals, an empty set, and the summary.
6. Live run 0 (r01 and r19, laptop key): both hit Gemini's **daily** limit (429). That showed a bug: r19 should be refused, and "nothing was built"
   was scored `pass`, but nothing was built only because the quota was used up. Fixed: a quota or busy stop is now `limit` first, for every kind.
   The run is kept, with a note, in `evidence/evaluation/outputs_e1_run0_scorer_bug.txt`.

## 3. Why we did it this way
- **Five kinds, not 20 easy ones**: a platform that only handles clear one-table requests would score 100% on an easy set and tell us nothing.
- **`{id}` instead of the real parameter name**: the builder names it per table (`{book_id}`), so the scorer should accept any name there.
- **Expected endpoints only where the request names them**: for vague requests we can only say "at least N tables", so we do.
- **Synthetic only**: the repo is public; no real people or businesses.

## 4. How to check it works
```
$ pytest evaluation
21 passed
```
A live run (from the repo root, with the backend's venv; reads `GEMINI_API_KEY` and `LLM_MODEL` from `.env`):
```
python -m evaluation.score --only r01,r02 --out evidence/evaluation/outputs_e1_<name>.txt
```
It refuses to overwrite an existing output file, so every run is kept.

## 5. What is NOT done or is faked
- **No real results yet.** Run 0 hit the daily quota on both requests. E-1 is done when 2 requests run without the limit.
- **The scorer calls the builder directly**, in its own Python process, not through the server's HTTP API, because the server does not hand out the generated files yet. It sends the same first message as the server (`backend/projects.py`), so the result is what a user gets; but the server's own steps (the request queue, the live stream) are not part of the score.
- **Questions and plans are not scored.** For `ask_first` requests only the build part is scored, because the builder does not ask questions yet (F-2). The `not_included` lists and `must_have_fields` are not checked either.
- **Table names**: `book`/`books` match, and the other names in the notes (`classrooms`, `products`, `crops`); anything else would fail as a missing endpoint, so read the missing list before calling it a real failure.
- "Ask first" and "refuse" assume the platform can ask questions and refuse; if it cannot yet, those requests will fail, and that is a real finding, not a bug in the test set.
- Table names may differ from ours (e.g. `classrooms` for `classes`, `products` for `produce`); the notes say which. The scorer must accept singular/plural and these noted alternatives.

## 6. What will bite us
- **The free quota is 20 Gemini requests per day per Google project, and one build uses about 10-20.** So E-2's 20 requests cannot run in one day on one key: about 1-2 requests a day per key. Plan E-2 across days (or keys in different Google projects), use `--only` to run a few at a time, and never use the Render key for it (that would break the live demo). Changing the model name does not give a fresh quota.
- Limit failures are counted apart (`limit`) and left out of the pass rate, but they must still be reported.
- Do not change the set between run 1 and run 2 (E-2, E-4), or the two runs cannot be compared.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Evaluation set | A fixed list of inputs with the expected result, run the same way every time |
| Endpoint | One address and method of an API, e.g. `GET /books` (list the books) |
| Path parameter | The changing part of an address, e.g. the `{book_id}` in `/books/{book_id}` |
| Synthetic | Made up for testing; not real data |
| Pretend builder | A small test function that returns a ready-made result instead of calling Gemini, so the tests are fast, free and the same every time |
| Pass rate | Passed requests divided by the requests that could be judged (the `limit` ones are left out) |
| Timeout | Giving up on a request that takes longer than a set time (here 15 minutes) |

## 8. Lines ready for the report
- We evaluate on 20 synthetic requests in five kinds (clear one-table, several tables, vague, partly supported, out of scope), written before any run.
- A request passes when the build succeeds, its own tests pass and every expected endpoint exists. A passing test is not proof of a good API.
- Results: to fill after the test (E-2, E-4).
