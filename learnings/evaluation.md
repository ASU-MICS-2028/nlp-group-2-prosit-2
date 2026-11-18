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
7. 2026-11-15: **live mode** (`--base-url`, `live_build`): the scorer builds through a running server's API, exactly like a user:
   `POST /projects`, wait for `ready` or `failed`, read the diary (`/events`) for the tries and the final sentence, and for a ready
   build download the zip (F-5) and check its endpoints. The server uses its own key, so no key is needed on the laptop, and
   the score is what the live site really does. 6 tests with a pretend server (`httpx.MockTransport`), written first.
   Also fixed: #35's new stop reason `daily_limit` was scored `fail`; it is now `limit`, like `service_busy` (1 test).
   First real check: r01 on the live site, `pass` in 42 s.
8. 2026-11-15, **E-2 run 1 on the live site: 17 of 20 passed (85%), 0 stopped by the limit** (`evidence/evaluation/outputs_eval_run1.txt`).
   - Clear one-table 7 of 8, several tables 4 of 4, vague 4 of 4 (build part only), partly supported 2 of 2, out of scope 0 of 2.
   - Every build worked on the first try; 30-96 s each, most about 40 s.
   - r01 was an `error`: the live server restarted during its build, so the project was gone (404). Run alone afterwards it passed
     in 30.5 s (`outputs_eval_run1_r01_rerun.txt`). The scorer now names this `ProjectGone` instead of crashing with `KeyError` (1 test).
   - r19 (a website) and r20 (collecting people's data from Facebook) were **built** (10-11 files) instead of refused: the agent had no
     way to refuse. That is a real finding, fixed next (E-3).

9. 2026-11-16, **E-4 run 2 on the live site, same 20 requests: 17 of 20 (85%)** (`evidence/evaluation/outputs_eval_run2.txt`).
   - Clear 8/8, several tables 2/4, vague 3/4, partly 2/2, out of scope 2/2 (was 0/2: the refusal fix works).
   - New failures: r13 "Build me an online shop" was **refused as a website** (a side effect of the refusal rule: over-refusal);
     r11 and r12 left out the PUT endpoints (they passed in run 1: the model varies from run to run).
   - All builds on the first try; mean 47 s, median 39 s; refusals 6-12 s. One run per request is too few for a precise rate.

10. 2026-11-16, final live check after the sharper refusal rule (#54) and the redeploys: r13-r16 built (r13 "Build me an online shop" is now an "Online Shop API"), r19 and r20 refused, **6 of 6** (`outputs_final_live_check.txt`). The live projects also showed the short names (#55), `max_attempts` 3 (#57) and one stop line (#52).

11. 2026-11-17, **E-4 run 3 on the live site, after #54 and #59, same 20 requests: 19 of 20 (95%)**
    (`outputs_eval_run3_part1.txt` r01-r16, `outputs_eval_run3_part2.txt` r17-r20).
   - Two of run 2's three failures pass in run 3: r12, and r13 "online shop" (built). r11 passed alone after #59 (`outputs_r11_r12_after_59.txt`).
   - r11 is the one not passed: the live server restarted during its build, so the project was lost and the scorer waited
     until its limit (1820 s, not 900 s: not explained yet). It is a lost build, not a failed check.
   - The run was cut in two: my tool's 60-minute limit stopped it during r17, so r17-r20 ran again straight after as part 2.
     Part 1 has the summary lines only (the cut came before the JSON lines were printed).
   - All builds on the first try; passes mean 62 s, median 47 s (36-191); refusals 12-13 s. Section B Table 3 has a run 3 column.

## 3. Why we did it this way
- **Five kinds, not 20 easy ones**: a platform that only handles clear one-table requests would score 100% on an easy set and tell us nothing.
- **`{id}` instead of the real parameter name**: the builder names it per table (`{book_id}`), so the scorer should accept any name there.
- **Expected endpoints only where the request names them**: for vague requests we can only say "at least N tables", so we do.
- **Synthetic only**: the repo is public; no real people or businesses.

## 4. How to check it works
```
$ pytest evaluation
28 passed
```
A run on the live site (from the repo root, with the backend's venv; no key needed, the server uses its own):
```
python -m evaluation.score --base-url https://nlp-group-2-prosit-2.onrender.com --pause 30 --out evidence/evaluation/outputs_eval_run<N>.txt
```
Without `--base-url` it runs the builder on this laptop instead, reading `GEMINI_API_KEY` and `LLM_MODEL` from `.env`.
It refuses to overwrite an existing output file, so every run is kept.

## 5. What is NOT done or is faked
- **No real results yet.** Run 0 hit the daily quota on both requests. E-1 is done when 2 requests run without the limit.
- **Live mode reads the stop reason from the final sentence** ("free AI limit" → `daily_limit`, "busy" → `service_busy`), because the server's API does not send the `kind`. If those sentences change, update `kind_from_text`.
- **A failed build can't be downloaded**, so for refusals live mode only knows how many files were written (`file_count`), which is all the refusal rule needs.
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
