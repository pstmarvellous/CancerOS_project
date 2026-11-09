# COS-REC-06 critical remediation audit — 2026-11-09

Scope: prompt_7.md, independent code/evidence inspection followed by authorized bounded fixes. The shared COS-REC-06-09-AUDIT context records the map lookup; original maps and source files were not changed.

## Findings and implemented corrections

- The original panel offered only previously associated studies. Its “uploaded” message described a read. Added an explicitly administrator-only, registered-source NIfTI byte uploader (675,000 byte bound), an explicit study manifest preview/confirmation, and an existing-mask association path. Source rights, registered SHA-256 and patient mapping remain server enforced; authentic-source enrollment remains denied.
- All patient masks were offered against any selected image. Discovery now carries canonical source-image and study IDs; the selector requires both to equal the selected volume/study. New mask association executes exact-grid alignment and declared label/annotation import. No mask, spacing or annotation meaning is inferred.
- A technical segmentation QC pass was labeled “measurements available” without any measurement or reconstruction call. The panel now distinguishes QC, deterministic numerical region measurement, worker mesh reconstruction and worker mesh QC. The exact completed report identifies the model and synthetic baseline link. No numerical values come from an LLM.
- The lesion viewer tried lesion/segmentation UUIDs as mesh-QC UUIDs, which cannot resolve ordinary generated reports. Added an owned backend lookup through QC → mesh → measurement selections with immutable-report/current-lineage checks and a 100-candidate ceiling; replaced the guessed-ID proxy. Explicit mesh_qc links can render a newly completed model without inventing lesion identity.
- Existing component state could remain visible after switching patients. The case-bound workflow is keyed by project/patient and aborts prior work; its prior geometry/QC/measurement are cleared on reselection.
- The browser test explicitly excluded a mesh-render FAIL from its success assertion. Root owns the acceptance-harness correction and browser verification; a passing component test is not browser-render evidence.

## Source learning and decision

Read the actual local SPEC-005 extract, sections 3.1–3.2 and 4–6: source eligibility, annotation classes, physical pipeline, IMG-001–008 and spatial preprocessing. The source requires known physical metadata, immutable originals, explicit annotation meaning and DCE acquisitions distinct from visits. Read the guide, four governing documents, authority/scope and reference policy; mapped source IDs remain pointers, not a claim to have read their textbooks.

Inspected the existing owned staging, source-registry and mapping gates; mask binding/alignment/annotation contracts; measurement, mesh, mesh-QC and worker APIs; immutable SQL report ownership. No new imaging algorithm, model, dataset or upstream package was adopted. Reused the existing exact-grid validator and deterministic measurement engine. No new clinical/scientific capability is enabled. Academic/upstream reproduction and empirical authentic-MRI evidence remain absent for this UI integration; existing synthetic tests establish only engineering behavior.

## Verification

- Actual SQL/private-storage closure suite: 5 passed, including distinct lesion/QC IDs, owned HTTP resolution, unauthenticated/cross-patient denial and withdrawal.
- Focused frontend suite: 33 passed across workflow, proxy, imaging discovery and viewer tests. Added a subsequent mask-upload test: workflow suite 10 passed. Tests use mocked fetches and synthetic byte strings; they do not establish live processing or authentic data performance.
- Targeted ESLint passed; mypy passed for the 2 modified backend files.
- Canonical OpenAPI/TypeScript generation and drift check passed after concurrent API changes landed. An earlier drift attempt failed before regeneration; it was not counted as a pass.
- A later project typecheck identified an unrelated new context_input required-field error in insights-explorer.tsx and was reported to its owner. No final full-project typecheck claim here.
- Broader selected imaging regression: `uv run pytest tests/test_imaging_closure.py tests/test_imaging_ingestion.py tests/test_alignment_runs.py tests/test_measurement_runs.py tests/test_mesh_quality_runs.py -q` passed 22 tests in 80.19 seconds. A subsequent Ruff check found only test import ordering, which was fixed; the format check passed for all 3 changed Python files. Browser full-chain checks are tracked by root; do not infer browser completion from this note.

## Remaining gates and limits

Authentic input rights, genuine source de-identification, qualified annotation review and authentic MRI acceptance remain blocked. DICOM remains supported by the reviewed administrator API; this bounded browser upload exposes NIfTI only. Source registration/mapping are existing prerequisite administration, not automatically manufactured by upload. Long-operation status comes from persisted worker jobs; no simulated percentages are displayed. Synthetic pipeline results cannot close the authentic scientific gate. Publication and external inference are not authorized.

## Hackathon Compliance Impact

Preserves private input, deterministic geometry and truthful origin labels. No external model calls, source-data exports, new licenses or publication actions. Source-rights/live-provider/scientific-review gates remain open.

## Actual browser upload acceptance (2026-11-09)

Executed `uv run python scripts/seed_recovery_upload.py`, which created only an artificial case and registered synthetic source manifests under the existing fixture component permissions; it wrote synthetic NIfTI bytes to ignored `.local/` files and did not call source-byte staging. Initial owned import discovery was empty.

Executed `npx.cmd playwright test -c playwright.audit-upload.config.ts`: **1 passed in 36.3 seconds** (scenario 31.3 seconds). Browser file inputs performed actual private image/mask staging with exact registered SHA receipts, explicit import preview/confirmation, server geometry (2×3×4 mm), honest no-mask state, association restoration after refresh, explicit mask binding/alignment/functional-region annotation/QC, deterministic 192 mm³ measurement, real mesh and mesh-QC worker jobs, and exact mesh WebGL rendering with authoritative measurement overlay. No page errors. An initial earlier attempt failed at first navigation because the temporary server had already stopped; it performed no browser writes.

Evidence: `docs/engineering/testing/rec06-09-audit/upload/audit-browser-upload.json` and its three `AUDIT-upload-*.png` screenshots. These four new artifacts were relocated from the previous output directory after the passing run; existing REC09 evidence was preserved. The spec now defaults to the new output path. The synthetic 3×4×2 volume is an engineering acceptance fixture, not an authentic MRI performance or clinical validation result.
