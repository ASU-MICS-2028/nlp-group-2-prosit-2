# docs/

- `decisions.md`: the log of decisions (Architecture Decision Records, ADRs).
- `ai-tools-usage.md`: who used which AI tool, for what, and how the output was checked.

## ADR format
Each entry in `decisions.md`:

```
## D-0xx: <decision as a short statement>
Date: YYYY-MM-DD · Status: Proposed | Accepted | Replaced by D-0yy
Affects: who must do something differently
Decision: what we chose
Why: the reasons
Gave up: what we did not choose, and what that costs us
```

## Rules
- New decisions go at the bottom.
- A decision stays **Proposed** until the people it affects agree.
- Never edit an Accepted decision. Write a new one that replaces it.
