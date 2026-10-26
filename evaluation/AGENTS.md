# evaluation/ (Nana, backup owner: anyone)

The 20-request test set and the scoring script.

## Files
- `requests.json`: 20 plain-English API requests with the endpoints each should produce (S-7). Synthetic examples only.
- `score.py`: runs each request through the platform; records pass/fail (generated tests pass and expected endpoints exist), retries used, seconds taken (E-1).

## Traps this area enforces
- Measure first, then write: results go into the report only after E-2 and E-4 are saved in `evidence/evaluation/`.
- Free-tier rate limits: pace requests; record failures caused by limits separately from bad code.
- Keep run 1 and run 2 outputs both. Never overwrite.
- State honestly what the metric does not measure (e.g. a passing test is not proof of a good API).

## Tests needed
The scoring script handles: a request that fails, a timeout, a malformed result, and an empty set.
