# COS-PRODUCT-001-BACKEND reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: patient, clinical, authorization, provenance against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-PRODUCT-001-BACKEND.json](COS-PRODUCT-001-BACKEND.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: Existing patient linkage, source rights, clinical contracts and immutable ingestion services.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## Source Learning Record and Three-Source Decision Note

Map source IDs are retrieved pointers only. Academic text, upstream interfaces and
empirical papers are NOT claimed read or reproduced by this refresh. Append actual
source learning, pinned interface inspection and empirical scope below before
enabling consequential scientific or security behavior. Medical reading exemptions
must be justified for the actual task; this refresh grants no exemption.
Missing academic/repository/empirical categories remain unverified for future domain
enablement. No weights, datasets or upstream code are adopted by a lookup.

Decision: preserve scoped specifications and keep unsupported capabilities disabled.
Verification: task-specific evidence and ledger, not map
existence. Failure fallback: disable affected domain/provider capability. Map drift
is recorded separately; original maps are unchanged.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.

## Implemented backend scope and decisions

COS-PRODUCT-001 sections 4–6/8/10–14. Existing `source.research_patients`, encrypted
`patient_mappings`, patient grants, private object storage, canonical `clinical/1`
observations, source locators, revision manifests, subtype tables, rights reviews and
lineage services are reused. No second patient identity or clinical record store was
introduced. New research profile revisions hold explicitly sourced administrative
profile annotations; medical history there is not a published clinical observation.

Creation and source ingestion preserve the existing administrator restriction.
Full draft profiles require editor or administrator plus patient authorization.
Project viewer access to published summaries does not grant access to private draft
profile history. The original project membership verifier remains RS256 with database
roles; no credential, user, role or source permission is synthesized by these APIs.

`GET /api/v1/workspace` discovers only authorized named projects. New source options
derive availability from existing action-specific source reviews and active linkage
configuration. Case creation/profile revision and manual entry are thin adapters over
existing identity and ingestion services. Case identifiers are case-normalized and
unique per project; source pseudonyms use existing encrypted lookup within a release.
Both identifiers remain immutable during profile edits; changes require reviewed
identity handling rather than relabeling a protected source mapping.

The previous hard-coded real-source block becomes an explicit **default-deny**
`patient_linkage_privacy` action in the existing rights ledger. It requires a current
administrator-documented review with evidence hash/reference and expiry, independently
of internal-processing and derivative rights. This implementation creates no actual
rights or privacy approval. The action authorizes new source linkage/ingestion within
its reviewed scope; it does not approve external inference or publication.

Manually entered records create private source artifacts and server-owned locators,
then use existing validate/accept, correction heads, patient revision/outbox and subtype
services. Seven supported kinds are laboratory, vital, symptom, treatment, diagnosis,
visit (including imaging examination metadata), and note. No image pixels, mask or
reconstruction is manufactured by creating examination metadata. Real source bytes
retain REAL_OBSERVED root lineage; canonical normalized records retain REAL_DERIVED /
OBSERVED. Synthetic fixture input remains SYNTHETIC_GENERATED / SYNTHETIC and uses
simulation time. Source clinical dictionaries and structural validation are preserved;
no clinical reference thresholds, stage, receptor or treatment facts were invented.

The existing private note document/version service is reused for authored source notes.
The clinical note-pointer database guard was extended to accept strictly matching
observed/real-derived pairs while rejecting branch pointers and origin/context/time
promotion. Extracted note assertions still do not become accepted observations.

Source references are retained on patient-owned immutable source locators and returned
as optional `ClinicalRecord.source_reference` through existing protected reads. Generated
registry children contain generic metadata; their digest-bearing metadata additionally
requires editor and owning-patient access. Thus project-source discovery does not expose
patient-specific source descriptions. Note text remains in private storage. Idempotency
uses a content digest, not the redacted SecretStr placeholder or raw note contents.

Migrations 0050–0052 are forward-only: add profile/identifier records, expand the existing
rights-action check, add nullable locator source reference, and replace the note guard
compatibly. Existing profile-independent patients and source artifacts are unchanged.
Existing immutable published twin states remain pinned to their original data revision;
accepting a draft source observation does not silently republish those states.

## Sources actually inspected

- Core capability nodes include DATA.PATIENT, DATA.PROV, DATA.NOTE, UX.PROFILE,
  UX.TIMELINE and GOV privacy/provenance guards shown in the saved adjacent edges.
  Academic pointers include DAT.01, DAT.02, DAT.04, TWIN.02 and UX.01. The full refresh
  records 32 capability nodes, 14 academic behaviors and 157 adjacent edges. The literal
  `authorization` query returned no match; it is not claimed as coverage.
- COS-SPEC-008 version 1.0 (22 October 2026), actual local
  `CancerOS_Database_API_Contracts.pdf`, pages 1–2,4 and15: server identities,
  source-owned assertions, exact/missing time, immutable corrections, private objects,
  role boundaries and expandable migrations. COS-SPEC-003 local
  `image_dataset_specification.pdf` pages 7–8: narrow-task eligibility and source-linked
  patient-centered records. COS-SPEC-010 local
  `CancerOS_AI_Safety_Privacy_Integrity.pdf` pages 2/4: source truth, pseudonymization,
  least exposure and denied external inference. Source PDFs were text-extracted without
  modification using an ephemeral `uv --with pypdf` execution; no dependency was added.
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
  recommendations on least privilege, deny-by-default and request-by-request authorization,
  actually opened 2026-11-05. Principle: authentication alone does not authorize each
  patient resource; failures and retries must preserve the same resource boundary.
- Local implementation inspected at Git 9221233f263226dfcd66dd59731a09191d6fcf15 plus
  existing user work: identity, patient linkage/reads, source registry, clinical
  contracts/ingestion, note registration/pointers, lineage, migrations and HTTP tests.
  No new upstream medical repository, model, weights or dataset was adopted; separate
  source/model rights remain absent. No medical textbook chapter or clinical cohort
  experiment is claimed. No disease interpretation, thresholds, model or prognosis
  capability is enabled by this engineering workflow.

Three-source decision: source-preserving identity/provenance and least-privilege
principles → inspected existing SQL/HTTP/storage services → artificial fixtures on real
PostgreSQL/private storage only → bounded source-entry adapters plus explicit review
gates → negative ownership/revision/unit/source-time tests and signed-token integration.
Clinical empirical validation and qualified privacy/source review remain unavailable.
The session-agent's concrete review caught mutable source aliases and project-scoped
source-description exposure; both were fixed and covered before any patient use. This
is agent review, not review by a clinician, privacy officer or institution.

## Checks actually executed

- `uv run pytest tests/test_research_workspace.py tests/test_clinical_ingestion.py
  tests/test_patient_linkage.py tests/test_note_extraction.py tests/test_note_runs.py
  tests/test_source_registry.py -q -x --tb=short`: 161 passed in 46.35 seconds.
- After adding two source-reference negatives, reran `tests/test_research_workspace.py`:
  **18 passed in 19.97 seconds**. These overlap the 161-test run and are not an additional
  independent cohort. Includes all seven clinical kinds, explicit source/real gate,
  real-labelled artificial note pointer, immutable correction, profile persistence,
  duplicate source pseudonym/case, stale revision, search/pagination, source-time rejection,
  unit quarantine, forged locator, editor/patient grant isolation, actual RS256/SQL
  HTTP creation and replay, and secret-content idempotency/log/source-metadata checks.
- `scripts/check_contract_drift.py`:passed canonical schemas, runtime OpenAPI and
  generated TypeScript. New routes/models and optional clinical source reference are
  generated together; `ClinicalSourceUpload.source_reference` is write-only SecretStr.
- Focused Ruff checks and formatting for 12 affected/new backend/migration/test files:
  passed. `git diff --check` for owned files:passed.
- Existing disposable database upgraded to 0052 without reset. A newly created empty
  uniquely named disposable database then ran **all** migrations through the final 0052,
  verified the strict note-origin guard and empty profile store, and was removed. No
  existing database was reset or removed; only that script-created empty DB was dropped.

Initial failures were corrected: environment-enabled external inference was explicitly
disabled for checks (the user's `.env` was not edited); nullable cursor SQL needed an
explicit UUID cast; test savepoint order and a missing-idempotency-header expectation
were fixed; fixture lookup keys needed a stable ring; the old database note guard
required the corresponding reviewed-source extension. An attempted regression command
named nonexistent `test_note_observations.py` and ran no tests; the corrected command
above passed. None of these failed attempts are recorded as passing evidence.

Changed backend files: `research_workspace.py`, `research_api.py`, `api.py`,
`patient_linkage.py`, `source_registry.py`, `clinical_contracts.py`,
`clinical_ingestion.py`, `note_runs.py`, `note_observation_adapter.py`; migrations 0050–52;
`tests/test_research_workspace.py`, contract generator/runtime OpenAPI/generated API and
clinical clients. No edits were made to pre-existing `grounding_runs.py` user changes.
Browser/frontend verification belongs to the parent COS-PRODUCT-001 integration report.

Remaining boundaries: source rights, privacy review, scientific review, authentic
imaging eligibility, state publication and external-provider/export/publication gates
are not supplied by these fixtures. This backend work makes the authorized workflow
available; it does not certify a real clinical record, infer a diagnosis or authorize
patient transmission. Live Meta was not called.

## Integration follow-up: correction history

The browser integration review found an existing inverted summary flag in
`patient_runs.query_observations`: checking whether a row has `supersedes_id` labels
the replacement as obsolete. The query now checks whether another row in the same
project and patient supersedes the requested row. A later retraction does not erase
that historical replacement relationship. No observation or snapshot is rewritten.

The manual correction integration test now verifies original superseded=true,
replacement superseded=false, and continued exact reads of both original and revised
values. `tests/test_research_workspace.py`:18 passed in24.14 seconds;
`tests/test_patient_closure.py`:4 passed in9.78 seconds. Focused Ruff and
`git diff --check` passed. These are follow-up checks, with overlap in the focused
suite; no extra independent clinical denominator is implied. JSON shape is unchanged,
so no generated contract change is required. Other `patient_runs.py` differences are
formatter reflow. The pre-existing observation-query cursor still hashes returned
IDs/filter rather than every history flag; it is not a claimed snapshot guarantee
for corrections outside a bounded page.
