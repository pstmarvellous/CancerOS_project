# Scoped note extraction

This is a deterministic four-symptom parser, not general clinical NLP. Live model,
authentic-note onboarding and numerical/diagnosis/therapy extraction remain gated.

An authorized admin ingestion process must stage verified immutable private UTF-8
bytes and source lineage with kind `note_source_artifact`. Source manifests, hashes
and internal/derivative rights must match; current runtime imports are restricted
to synthetic engineering sources. No raw-text upload HTTP route was introduced.
The integration test fixture demonstrates this privileged ingestion precondition
against actual private S3/PostgreSQL using artificial notes only.

With the usual authenticated project/patient context:

1. POST `note-documents` with `artifact_id`, optional owned simulated `branch_id`,
   optional declared simulation `anchor` and optional `supersedes_id`. Supply the
   normal Idempotency-Key. Receive201/Location and immutable metadata.
2. POST `note-extractions` with `note_id` and a fresh scoped Idempotency-Key. The
   response contains deterministic-scoped-parser mode, versions/hash, assertions,
   qualifiers, unsupported clause spans and limitations. It never publishes facts.
3. GET `note-extractions/{id}/facts/{index}/source-span` as an authorized editor or
   admin to inspect exact mention/assertion text beside its labels. Render returned
   strings as escaped text. Viewer research summaries do not imply note permission.
4. Corrections register a different source artifact with `supersedes_id`; the old
   source, extraction and state histories are preserved. Unsupported language or
   unresolved time needs source review, not automatic observation insertion.

Supported examples: “Patient denies nausea.”, “Possible fatigue.”, “Family history
of pain.”, “Plan to assess swelling.”, “Patient reports pain at last visit.”.
The last example retains unresolved time. “Pain 7/10”, laboratory values, treatment
recommendations, receptor status, stages, compound clauses and unrecognized
phrasing are not extracted in this version. No absent value is guessed.

Focused commands:

```powershell
uv run python scripts/migrate_test.py
uv run pytest tests/test_note_extraction.py tests/test_note_runs.py -q
uv run python scripts/generate_contracts.py --check
```

Fixture metrics and failures are recorded separately from unavailable real-note,
clinician-reviewed and model-comparison results. A source withdrawal blocks new
use/read even when the corresponding note or request was previously accepted.
