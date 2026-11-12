# Evaluation

Owner: Nana · Last updated: 2026-11-10 · Status: partly working (test set ready; scoring script E-1 waits on W-9)

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

## 3. Why we did it this way
- **Five kinds, not 20 easy ones**: a platform that only handles clear one-table requests would score 100% on an easy set and tell us nothing.
- **`{id}` instead of the real parameter name**: the builder names it per table (`{book_id}`), so the scorer should accept any name there.
- **Expected endpoints only where the request names them**: for vague requests we can only say "at least N tables", so we do.
- **Synthetic only**: the repo is public; no real people or businesses.

## 4. How to check it works
```
$ pytest evaluation
6 passed
```

## 5. What is NOT done or is faked
- No scoring script yet (E-1, blocked by W-9). Nothing has been run through the platform; there are no results.
- "Ask first" and "refuse" assume the platform can ask questions and refuse; if it cannot yet, those requests will fail, and that is a real finding, not a bug in the test set.
- Table names may differ from ours (e.g. `classrooms` for `classes`, `products` for `produce`); the notes say which. The scorer must accept singular/plural and these noted alternatives.

## 6. What will bite us
- Free-tier rate limits during E-2: pace the 20 requests and record limit failures separately from bad code.
- Do not change the set between run 1 and run 2 (E-2, E-4), or the two runs cannot be compared.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Evaluation set | A fixed list of inputs with the expected result, run the same way every time |
| Endpoint | One address and method of an API, e.g. `GET /books` (list the books) |
| Path parameter | The changing part of an address, e.g. the `{book_id}` in `/books/{book_id}` |
| Synthetic | Made up for testing; not real data |

## 8. Lines ready for the report
- We evaluate on 20 synthetic requests in five kinds (clear one-table, several tables, vague, partly supported, out of scope), written before any run.
- A request passes when the build succeeds, its own tests pass and every expected endpoint exists. A passing test is not proof of a good API.
- Results: to fill after the test (E-2, E-4).
