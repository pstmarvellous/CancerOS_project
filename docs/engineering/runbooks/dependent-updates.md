# Explicit accepted-revision calculations

COS-054 uses the existing clinical revision journal, domain outbox and durable
imaging worker. Authentic observed-source worker execution remains disabled; the
current operation accepts authorized synthetic source fixtures only.

1. Accept or correct a source observation through the normal source commands.
2. Open that exact source-fixture revision/window in `/timeline` and explicitly
   check revision update status. The read does not enqueue any work.
3. Queue its eligible accepted event. `POST /dependent-updates` pins event ID,
   expected revision, revision hash and full `TimelineQuery` with `cursor: null`.
   Use an `Idempotency-Key`; transport retries reuse identical inputs/key.
4. Dispatch/run the existing worker and refresh the existing job status. A failed
   terminal calculation requires inspection/correction; a refresh does not retry it.
   Expired leases and undelivered jobs use existing durable recovery.
5. Inspect `GET /dependent-updates/latest` and its last valid report. The loaded
   timeline stays pinned; new values do not merge into the selected view.

The API can accept an explicit `state_input` for a newly assembled draft with exact
source membership. It cannot insert new labs into an old immutable snapshot. The
thin branch panel reads status; explicit membership construction uses the existing
state contract. No state input means fusion remains unavailable with a next action.
For `state_input`, set the window's event cutoff to that state's exact time; a
different or omitted cutoff is rejected before any durable dispatch.
Event receipts distinguish source and explicitly requested branch scopes; processing
one does not automatically regenerate or consume another scope's calculation.

Input and output dependency hashes preserve revision, window, source content and
exact state/measurement/asset identity. Laboratory-only calculations never invoke
mesh generation. Completed old-revision reports remain retained; only coherent,
ready current-revision calculations can advance the separate preview head.
Published state/current-run pointers require their original explicit publication
commands. Laboratory freshness alone does not assert a physical baseline changed.

Run `uv run python scripts/run_checks.py dependent-updates`, then
`uv run python scripts/run_checks.py frontend`. Actual evidence and task status
remain separate from scientific review, authentic-source rights and evaluation.
