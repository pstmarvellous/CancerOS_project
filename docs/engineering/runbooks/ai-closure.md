# AI interpretation and evidence closure

Submit bounded jobs at `POST interpretation-jobs` with state_id, purpose
(`research_summary` or `fact_extraction`), mode (`template` only until the
external path is authorized) and an idempotency key. The job builds the
frozen context, renders the template, validates through the grounding gate
and persists validated results; replay returns the original receipt.
`202` is acceptance, never validation — read `GET interpretation-jobs/{job_id}`
for the gated verdict and inspect the linked `saved_id` on success.

Results label their execution mode (`Rule-based summary`, `Saved result`,
or a precise unavailable status) with freshness, limitations and source
drill-down per finding. Persistent IDs drive citation navigation; model
text is escaped and restricted to verified safe references. Evidence reads
return permitted excerpts and locators; viewer summary access never grants
raw notes, linkage or rejected outputs.

```powershell
uv run python scripts/run_checks.py ai-closure
```

The checked flow uses synthetic states, fixture reports and mocked auth
boundaries. Live model behavior, genuine curation, qualified review and
SPEC-011 evaluation remain open.
