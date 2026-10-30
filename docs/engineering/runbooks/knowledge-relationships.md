# Source-linked relationships

Use existing identity and source registration. A link does not create or approve
its endpoint records; every patient resource must already exist and be accessible.

Admin vocabulary registration uses project `POST clinical-concepts` with a local
code/label and Idempotency-Key. Corrections include supersedes_id and retain the
original version. Codes are local vocabulary, not claimed standardized ontologies.

Patient `POST relationships` accepts an input object with relation, typed source/
target refs, assertion_kind and supporting_resource_ids, plus optional branch_id.
For a note assertion, use ABOUT_CONCEPT, source kind note_extraction, target kind
clinical_concept, assertion_kind extracted_assertion, exact extraction_id/fact_id,
and that extraction ID in the support list. The concept code must match the fact.
The record returns “Extracted assertion”, its unverified status and synthetic origin
when applicable. Source text is available only through the separately authorized
note-extraction source-span route; the relationship does not broaden access.

For a simulated baseline link, use source kind twin_branch and its exact branch
ID, target kind physical_measurement and that branch's recorded baseline ID,
GENERATED_FROM_BASELINE, hypothetical_simulation and the same branch_id. This
demonstrates lineage, not an authentic or validated clinical baseline.

Generic lexical proposals use project `POST concept-relationships`, RELATED_TO,
two clinical_concept refs and model_proposal. They cannot include patient records.
These proposals can form cycles; no causal meaning or clinical approval follows.
Publication/evidence/outcome/treatment edge types currently fail closed.

`POST relationship-queries` in the patient scope, or project
`POST concept-relationship-queries`, accepts a typed start ref, depth, limit,
relation filters, branch and optional expected_snapshot_hash. Preserve the returned
hash when requesting another offset; a409 means restart the query with current
rights/history. A budget_exhausted result requires narrowing the scope; it is not
a complete empty graph. Old event IDs remain available for authorized historical
reads even after a correction changes the current traversal.

```powershell
uv run python scripts/run_checks.py knowledge-relationships
```

Fixture verification is distinct from authentic source rights and independent
scientific review. No traversal result diagnoses disease, proves causation, selects
treatment or promotes an extracted assertion to an accepted observation.
