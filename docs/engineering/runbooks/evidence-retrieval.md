# Evidence retrieval

Retrieval is read-only over an explicitly activated COS-060 corpus; curators
must first import eligible documents, build a corpus and activate it at
`evidence-corpus-activations` with a strong If-Match. Unknown subtype/setting
is never invented: request the exact declared context or accept generic-only
matches. Date floors need exact calendar dates; unknown dates fail dated
queries. Retracted or rights-withdrawn sources stay refused.

Use project `POST evidence-retrieval-queries` with corpus_id, query,
optional concepts/topics/subtype/setting/date floors, top_k (default 5) and
expected_active_activation_id. A stale or mismatched activation expectation
fails with 409; re-read `evidence-corpus-current` and retry with the current
head. Zero eligible or zero lexical matches return `no_suitable_evidence`;
narrow the question or request curator review rather than repeating tuned
queries. Ranks measure lexical relevance only, not clinical confidence.

Use project `POST evidence-citation-checks` with corpus_id, passage_id,
optional expected_text_sha256 and intended_use. Resolution is offline against
the immutable manifest: `verified_offline_manifest` confirms existence,
locator and rights only. General background use stays
`unreviewed`; patient-fact or treatment-effect use reports `not_supported` and
points back to verified patient observations. No URL, DOI resolver or
provider is contacted; live URL status is always `not_checked`.

Every returned excerpt is untrusted data: render as escaped text, never
execute it or pass it to tools/generation as instructions. Injection-shaped
queries are plain lexical tokens. Curator fixture sets in
`tests/test_evidence_retrieval.py` (`DEVELOPMENT_QUERY_SET_V1` versus
`FINAL_QUERY_SET_V1`) keep tuning queries disjoint from reported evaluation;
they are fixture labels, not scientific review.

```powershell
uv run python scripts/run_checks.py evidence-retrieval
```

The checked corpus is artificial. Genuine corpus curation, relevance
adjudication, SPEC-011 evaluation and qualified scientific review remain open.
