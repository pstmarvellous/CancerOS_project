# Evidence corpus

Admin curators first register source versions and action-specific review evidence
through the existing source registry. Text reuse, indexing, display and external
processing are separate permissions. Engineering fixture reviews cannot authorize
real-source processing. No source URL is fetched by the import API.

Use project `POST evidence-document-metadata` for metadata_only manifests, or
`POST evidence-document-excerpts` with a manifest/media_type/text envelope for a
licensed, approved plain-text excerpt. Include Idempotency-Key. Source SHA must
match original UTF-8 bytes; actual normalized SHA and passage IDs are computed.
Required unknown date reasons preserve missing metadata. Excerpts with uncertain
retraction status remain needs_review and cannot be activated. Do not upload raw
patient notes, full copyrighted papers, private links, binaries or images here.

`POST evidence-corpora` freezes up to50 eligible document IDs. `GET
evidence-corpus-current` returns the current activation and strong ETag (initial
`"empty"`). POST `evidence-corpus-activations` with corpus_id,
expected_activation_id (null initially), Idempotency-Key and that exact If-Match.
Missing/stale preconditions return428/412; idempotent replay returns its original
receipt after current permission checks. Use the current head to recover conflicts.

An authorized viewer can read corpus/document metadata and exact permitted passages
at `evidence-corpora/{corpus_id}/passages/{passage_id}`. The response explicitly
states that citation resolution does not establish meaningful claim support.
Render excerpts as escaped text; source text never executes code or model tools.
Retrieval/ranking is the subsequent COS-061 task.

For withdrawal/retraction or retention review, POST
`evidence-documents/{document_id}/restrictions` with an allowed action/reason and
Idempotency-Key. Search projection text/lexemes are removed; historical metadata
hashes remain. Existing corps containing the document become unavailable until a
new eligible corpus is built and activated. Current source-policy checks also deny
access after rights expire/change. Curators must separately resolve the private
original object's retention/deletion; this receipt does not claim complete erasure.

```powershell
uv run python scripts/run_checks.py evidence-corpus
```

The test corpus is artificial. Genuine corpus curation/rights signoff, extraction of
PDFs/OCR, complete object-retention verification and scientific review remain open.
