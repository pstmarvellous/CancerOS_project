# ADR-004: immutable source versions and action-specific review

2026-10-27; bounded Phase 2 implementation decision under SPEC-008.
This does not assert owner adoption of the complete audit baseline.

Use one typed, immutable hierarchy: collection → release → component → artifact
source. Every version has a new opaque UUID; record key/version are project unique.
Children pin parent versions. New versions do not inherit rights reviews. Citation
URLs are metadata only; the application makes no URL requests or cohort downloads.
No unrestricted network-fetch API exists.

Rights are append-only administrator attestations for a component version and a
single intended action. Latest sequence governs; absent/unknown/denied/expired
reviews deny that action. Source availability is an independent requirement.
Review actor/time come from verified identity/server clock. Engineering fixture
attestations are a separate scope, rejected when real-data authorization is required.
The rights service does not establish legal correctness or override export policy.
External inference additionally remains denied by the existing provider gateway.

Canonical runtime additions under `/api/v1/projects/{project_id}/sources`:
POST source version, GET immutable version, POST `/{id}/rights-reviews`, GET
`/{id}/capabilities/{action}`. New synchronous resources return 201 and Location.
All writes require administrator membership and Idempotency-Key; replay rechecks
authorization and input hash atomically. Conflict is 409; bad input 422; inaccessible
project/source 404. Existing safe Problem envelope applies. No patient key is used.
OpenAPI/Pydantic generate the TypeScript contracts in the established package.

Database foreign keys protect project/parent ownership; immutable triggers protect
versions, reviews and command receipts. Application validates hierarchy and origin.
Database login remains a trusted application boundary: production restricted SQL
roles and a rights-review personnel policy still need deployment work.

Acceptance evidence: `source-registry.json` and `tests/test_source_registry.py`.
Actual approved-release onboarding remains blocked by D01/D03; no synthetic fixture
attestation closes those gates. Source retention text is captured; retention deletion
is a separate reviewed maintenance workflow and is not implemented by this task.
